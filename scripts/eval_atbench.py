# -*- coding: utf-8 -*-
"""Script para evaluar y comparar los adaptadores de trayectoria de 4R2.

Compara la eficacia del acumulador térmico (con memoria) contra la línea base sin memoria
utilizando el dataset ATBench bajo un esquema calibrado y segmentado (riesgo temprano vs. tardío).
"""

import datetime
import hashlib
import json
import os
import pathlib
import sys
import time

import numpy as np

# Configurar sys.path para importar componentes locales
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[1] / "adapters_external")
)

from fourr2_singleturn_baseline_adapter import FourR2SingleTurnBaselineAdapter
from fourr2_trajectory_adapter import FourR2TrajectoryAdapter
from scipy.stats import rankdata

from aegisbench.datasets.atbench_loader import load_atbench


def auroc(y_true, y_score):
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    r = rankdata(y_score)
    return float((r[y_true == 1].sum() - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def calculate_auroc_bootstrap_ci(
    y_true, y_score, n_resamples=10000, confidence_level=0.95, seed=42
):
    """Calcula el intervalo de confianza bootstrap para el AUROC de manera reproducible."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)
    rng = np.random.default_rng(seed)

    n_samples = len(y_true)
    if n_samples == 0 or len(np.unique(y_true)) < 2:
        return (0.5, 0.5)

    bootstrapped_aurocs = []

    for _ in range(n_resamples):
        indices = rng.choice(n_samples, size=n_samples, replace=True)
        resampled_y_true = y_true[indices]
        resampled_y_score = y_score[indices]

        if len(np.unique(resampled_y_true)) >= 2:
            bootstrapped_aurocs.append(auroc(resampled_y_true, resampled_y_score))
        else:
            bootstrapped_aurocs.append(0.5)

    lower_pct = (1.0 - confidence_level) / 2.0 * 100
    upper_pct = (1.0 - (1.0 - confidence_level) / 2.0) * 100
    ci = np.percentile(bootstrapped_aurocs, [lower_pct, upper_pct])
    return float(ci[0]), float(ci[1])


def compute_metrics(y_true, y_pred):
    tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt and yp)
    fp = sum(1 for yt, yp in zip(y_true, y_pred) if not yt and yp)
    fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt and not yp)
    tn = sum(1 for yt, yp in zip(y_true, y_pred) if not yt and not yp)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def parse_tripped_turn(raw_output: str) -> int:
    """Extrae el turno de disparo de la cadena raw_output."""
    if "tripped_at_turn=" in raw_output:
        parts = raw_output.split("tripped_at_turn=")
        if len(parts) > 1:
            try:
                return int(parts[1].split()[0])
            except ValueError:
                pass
    return -1


def run_evaluation_for_mode(
    mode: str, samples, y_true, fold_of, temprano_indices_list, tardio_indices_list
):
    """Ejecuta la evaluación OOF y bootstrap pareado para un modo de detector específico ('cca' o 'c_ni')."""
    print(f"\n--- Evaluando en MODO: {mode.upper()} ---")

    # 1. Instanciar adaptadores con el modo actual
    acc_adapter = FourR2TrajectoryAdapter(mode=mode)
    base_adapter = FourR2SingleTurnBaselineAdapter(mode=mode)

    results_acc = []
    results_base = []

    t0 = time.perf_counter()
    for s in samples:
        results_acc.append(acc_adapter.evaluate(s))
    lat_acc = (time.perf_counter() - t0) * 1000.0 / len(samples)

    t0 = time.perf_counter()
    for s in samples:
        results_base.append(base_adapter.evaluate(s))
    lat_base = (time.perf_counter() - t0) * 1000.0 / len(samples)

    # 2. Extraer scores continuos y temperaturas máximas
    temps_acc = []
    for r in results_acc:
        parts = r.raw_output.split("temp_max=")
        if len(parts) > 1:
            temps_acc.append(float(parts[1]))
        else:
            temps_acc.append(0.0)

    crits_base = []
    for r in results_base:
        parts = r.raw_output.split("max_crit=")
        if len(parts) > 1:
            crits_base.append(float(parts[1]))
        else:
            crits_base.append(0.0)

    N = len(samples)
    K = 5
    oof_pred_base = [None] * N
    oof_pred_mem = [None] * N

    # Helper functions for argmax F1
    def argmax_F1_base(dev_idxs, scores, yt):
        best_f1 = -1.0
        best_theta = 0.35
        dev_y_true = [yt[i] for i in dev_idxs]
        dev_scores = [scores[i] for i in dev_idxs]
        for th in np.linspace(0.0, 1.0, 101):
            pred = [1 if val >= th else 0 for val in dev_scores]
            m = compute_metrics(dev_y_true, pred)
            if m["f1"] > best_f1:
                best_f1 = m["f1"]
                best_theta = float(th)
        return best_theta

    def argmax_F1_mem(dev_idxs, scores, yt):
        best_f1 = -1.0
        best_ttrip = 0.30
        dev_y_true = [yt[i] for i in dev_idxs]
        dev_scores = [scores[i] for i in dev_idxs]
        for tt in np.linspace(0.01, 1.0, 100):
            pred = [1 if val >= tt else 0 for val in dev_scores]
            m = compute_metrics(dev_y_true, pred)
            if m["f1"] > best_f1:
                best_f1 = m["f1"]
                best_ttrip = float(tt)
        return best_ttrip

    # 3. OOF Predictions
    for k in range(K):
        dev = [i for i in range(N) if fold_of[i] != k]
        ho = [i for i in range(N) if fold_of[i] == k]
        best_theta = argmax_F1_base(dev, crits_base, y_true)
        best_ttrip = argmax_F1_mem(dev, temps_acc, y_true)
        for i in ho:
            oof_pred_base[i] = 1 if crits_base[i] >= best_theta else 0
            oof_pred_mem[i] = 1 if temps_acc[i] >= best_ttrip else 0

    subset_definitions = {
        "completo": list(range(N)),
        "temprano": list(temprano_indices_list),
        "tardio": list(tardio_indices_list),
    }

    subset_metrics = {}

    for name, sub_idxs in subset_definitions.items():
        y_true_sub = [y_true[i] for i in sub_idxs]
        crits_base_sub = [crits_base[i] for i in sub_idxs]
        temps_acc_sub = [temps_acc[i] for i in sub_idxs]
        oof_pred_base_sub = [oof_pred_base[i] for i in sub_idxs]
        oof_pred_mem_sub = [oof_pred_mem[i] for i in sub_idxs]

        # A) Métricas fijas de Baseline (theta = 0.35)
        y_pred_base_fixed = [1 if crit >= 0.35 else 0 for crit in crits_base_sub]
        metrics_base_fixed = compute_metrics(y_true_sub, y_pred_base_fixed)
        metrics_base_fixed["auroc"] = round(auroc(y_true_sub, crits_base_sub), 4)
        base_ci_low, base_ci_high = calculate_auroc_bootstrap_ci(
            y_true_sub, crits_base_sub, n_resamples=10000, seed=42
        )
        metrics_base_fixed["auroc_ci"] = (round(base_ci_low, 4), round(base_ci_high, 4))

        # B) Métricas fijas de Memoria (T_trip = 0.30)
        y_pred_acc_fixed = [1 if temp >= 0.30 else 0 for temp in temps_acc_sub]
        metrics_acc_fixed = compute_metrics(y_true_sub, y_pred_acc_fixed)
        metrics_acc_fixed["auroc"] = round(auroc(y_true_sub, temps_acc_sub), 4)
        acc_ci_low, acc_ci_high = calculate_auroc_bootstrap_ci(
            y_true_sub, temps_acc_sub, n_resamples=10000, seed=42
        )
        metrics_acc_fixed["auroc_ci"] = (round(acc_ci_low, 4), round(acc_ci_high, 4))

        # C) Métricas calibradas de Baseline (Out-of-Fold, opt_cv)
        metrics_base_opt = compute_metrics(y_true_sub, oof_pred_base_sub)
        metrics_base_opt["auroc"] = metrics_base_fixed["auroc"]
        metrics_base_opt["auroc_ci"] = metrics_base_fixed["auroc_ci"]

        # D) Métricas calibradas de Memoria (Out-of-Fold, opt_cv)
        metrics_acc_opt = compute_metrics(y_true_sub, oof_pred_mem_sub)
        metrics_acc_opt["auroc"] = metrics_acc_fixed["auroc"]
        metrics_acc_opt["auroc_ci"] = metrics_acc_fixed["auroc_ci"]

        subset_metrics[name] = {
            "size": len(sub_idxs),
            "positives": sum(y_true_sub),
            "negatives": len(sub_idxs) - sum(y_true_sub),
            "baseline": {"fixed": metrics_base_fixed, "opt_cv": metrics_base_opt},
            "memory": {"fixed": metrics_acc_fixed, "opt_cv": metrics_acc_opt},
        }

    # Fase 4: Test pareado de la diferencia en el subconjunto tardío
    rng = np.random.default_rng(42)
    idx = np.array(tardio_indices_list, dtype=int)
    yt = np.array([y_true[i] for i in idx])
    sb = np.array([crits_base[i] for i in idx])
    sm = np.array([temps_acc[i] for i in idx])
    deltas = []
    for _ in range(10000):
        r = rng.integers(0, len(idx), len(idx))
        if len(np.unique(yt[r])) < 2:
            continue
        deltas.append(auroc(yt[r], sm[r]) - auroc(yt[r], sb[r]))
    deltas = np.array(deltas)
    delta_point = auroc(yt, sm) - auroc(yt, sb)
    ci = np.percentile(deltas, [2.5, 97.5])
    p_mem_better = float((deltas > 0).mean())

    # 4. Análisis de turnos sobre el conjunto completo usando predicciones OOF (opt_cv)
    turns_acc = []
    turns_base = []
    for i in range(N):
        yt = y_true[i]
        if yt:
            det_acc = oof_pred_mem[i] == 1
            det_base = oof_pred_base[i] == 1
            if det_acc and det_base:
                t_acc = parse_tripped_turn(results_acc[i].raw_output)
                t_base = parse_tripped_turn(results_base[i].raw_output)
                if t_acc != -1 and t_base != -1:
                    turns_acc.append(t_acc)
                    turns_base.append(t_base)

    detection_comparison = {}
    if turns_acc:
        detection_comparison = {
            "N_coincidences": len(turns_acc),
            "mean_turn_memory": round(float(np.mean(turns_acc)), 2),
            "mean_turn_baseline": round(float(np.mean(turns_base)), 2),
            "memory_faster_count": sum(
                1 for a, b in zip(turns_acc, turns_base) if a < b
            ),
            "baseline_faster_count": sum(
                1 for a, b in zip(turns_acc, turns_base) if b < a
            ),
            "same_turn_count": sum(1 for a, b in zip(turns_acc, turns_base) if a == b),
        }

    return {
        "latencies": {
            "memory_mean_ms": round(lat_acc, 4),
            "baseline_mean_ms": round(lat_base, 4),
        },
        "sealed_metrics": {
            "subsets": subset_metrics,
            "detection_turn_analysis": detection_comparison,
            "paired_delta_tardio": {
                "delta_point": round(delta_point, 4),
                "ci": [round(float(ci[0]), 4), round(float(ci[1]), 4)],
                "p_mem_better": round(p_mem_better, 4),
            },
        },
    }


def main():
    print("Iniciando evaluación de ATBench con Calibración y Segmentación...")
    dataset_path = "data/atbench_test.jsonl"

    if not os.path.exists(dataset_path):
        print(f"Error: No existe el archivo {dataset_path}. Corre la Fase 1 primero.")
        sys.exit(1)

    samples = load_atbench(dataset_path)
    print(f"Cargadas {len(samples)} muestras del dataset.")

    # 1. Definir los grupos estratificados
    direct_sources = [
        "direct_prompt_injection",
        "malicious_user_instruction_or_jailbreak",
    ]
    indirect_sources = [
        "indirect_prompt_injection",
        "tool_description_injection",
        "corrupted_tool_feedback",
        "inherent_agent_failures",
        "unreliable_or_misinformation",
        "malicious_tool_execution",
    ]

    # Clasificar cada muestra por grupo
    groups = {
        "direct_unsafe": [],
        "direct_safe": [],
        "indirect_unsafe": [],
        "indirect_safe": [],
        "benign_pure": [],
    }

    for i, s in enumerate(samples):
        r_source = s.metadata.get("risk_source")
        label = 1 if s.ground_truth_should_block else 0
        if r_source in direct_sources:
            if label == 1:
                groups["direct_unsafe"].append(i)
            else:
                groups["direct_safe"].append(i)
        elif r_source in indirect_sources:
            if label == 1:
                groups["indirect_unsafe"].append(i)
            else:
                groups["indirect_safe"].append(i)
        elif r_source == "benign":
            groups["benign_pure"].append(i)
        else:
            raise ValueError(f"risk_source desconocido: {r_source}")

    # Ordenar deterministamente los índices por el ID numérico de la muestra
    for g_name in groups:
        groups[g_name].sort(key=lambda idx: int(samples[idx].sample_id))

    # 2. Asignar fold de forma estratificada y determinista (5-fold)
    K = 5
    fold_of = {}
    for g_name, idxs in groups.items():
        for pos, i in enumerate(idxs):
            fold_of[i] = pos % K

    # 3. Dividir benignas de forma disjunta entre temprano y tardío
    benign_pure = groups["benign_pure"]
    benign_temprano = benign_pure[:125]
    benign_tardio = benign_pure[125:]

    # 4. Construir temprano y tardío disjuntos
    temprano_indices_list = (
        groups["direct_unsafe"] + groups["direct_safe"] + benign_temprano
    )
    tardio_indices_list = (
        groups["indirect_unsafe"] + groups["indirect_safe"] + benign_tardio
    )

    temprano_indices_list.sort()
    tardio_indices_list.sort()

    temprano_indices = set(temprano_indices_list)
    tardio_indices = set(tardio_indices_list)

    y_true = [s.ground_truth_should_block for s in samples]

    # Imprimir tamaños para validacion de Gate 2
    print("--- VALIDACION DE SPLIT Y ESTRATIFICACION (GATE 2) ---")
    fold_counts = [0] * K
    fold_positives = [0] * K
    for i in range(len(samples)):
        f = fold_of[i]
        fold_counts[f] += 1
        if y_true[i]:
            fold_positives[f] += 1

    print(f"Muestras totales por fold (K=5): {fold_counts}")
    print(f"Positivos por fold: {fold_positives}")
    print(f"Tamano temprano: {len(temprano_indices_list)}")
    print(f"Tamano tardio: {len(tardio_indices_list)}")

    # Ejecutar para modo 'cca' y 'c_ni'
    results_cca = run_evaluation_for_mode(
        "cca", samples, y_true, fold_of, temprano_indices_list, tardio_indices_list
    )
    results_c_ni = run_evaluation_for_mode(
        "c_ni", samples, y_true, fold_of, temprano_indices_list, tardio_indices_list
    )

    # --- CHEQUEO DE CORDURA ARITMÉTICO EXPLÍCITO ---
    for det_name, results in [("cca", results_cca), ("c_ni", results_c_ni)]:
        subsets = results["sealed_metrics"]["subsets"]

        # A) No traslape ni pérdida de índices en la definición
        assert len(temprano_indices.intersection(tardio_indices)) == 0, (
            f"[{det_name}] Error: Traslape en los índices temprano/tardío."
        )
        assert len(temprano_indices) + len(tardio_indices) == len(samples), (
            f"[{det_name}] Error: Pérdida o exceso de muestras al unir temprano/tardío."
        )

        # B) Consistencia de tamaños
        total_size = subsets["completo"]["size"]
        pos_total = subsets["completo"]["positives"]
        neg_total = subsets["completo"]["negatives"]

        temprano_size = subsets["temprano"]["size"]
        temprano_pos = subsets["temprano"]["positives"]
        temprano_neg = subsets["temprano"]["negatives"]

        tardio_size = subsets["tardio"]["size"]
        tardio_pos = subsets["tardio"]["positives"]
        tardio_neg = subsets["tardio"]["negatives"]

        assert temprano_size + tardio_size == total_size, (
            f"[{det_name}] Error: Los tamaños de temprano y tardío no reconstruyen el total."
        )
        assert temprano_pos + tardio_pos == pos_total, (
            f"[{det_name}] Error: La suma de positivos en temprano y tardío no reconstruye los positivos totales."
        )
        assert temprano_neg + tardio_neg == neg_total, (
            f"[{det_name}] Error: La suma de negativos en temprano y tardío no reconstruye los negativos totales."
        )

        # C) Consistencia interna de la matriz de confusión para cada configuración
        for sys_name in ["baseline", "memory"]:
            for config in ["fixed", "opt_cv"]:
                for sub_name in ["completo", "temprano", "tardio"]:
                    m = subsets[sub_name][sys_name][config]
                    assert m["tp"] + m["fn"] == subsets[sub_name]["positives"], (
                        f"[{det_name}][{sys_name}][{config}][{sub_name}] Inconsistencia: TP+FN != positives"
                    )
                    assert m["fp"] + m["tn"] == subsets[sub_name]["negatives"], (
                        f"[{det_name}][{sys_name}][{config}][{sub_name}] Inconsistencia: FP+TN != negatives"
                    )
                    assert (
                        m["tp"] + m["fp"] + m["tn"] + m["fn"]
                        == subsets[sub_name]["size"]
                    ), (
                        f"[{det_name}][{sys_name}][{config}][{sub_name}] Inconsistencia: TP+FP+TN+FN != size"
                    )

    print(
        "\n[OK] CHEQUEO DE CORDURA ARITMETICO COMPLETADO CON EXITO: Todos los subconjuntos reconstruyen el total sin traslapes ni perdidas."
    )

    # Estructura del payload sellado (sin latencias ni timestamps)
    sealed = {
        "dataset_info": {
            "name": "ATBench",
            "path": dataset_path,
            "total_samples": len(samples),
            "positives": sum(y_true),
            "negatives": len(samples) - sum(y_true),
        },
        "cca_detector": results_cca["sealed_metrics"],
        "c_ni_detector": results_c_ni["sealed_metrics"],
    }

    # Serializacion canonica para hashing determinista
    canonical = json.dumps(
        sealed, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # Estructura del reporte completo que incluye los metadatos volátiles fuera de la firma
    report = {
        "trace_id": "ATBENCH-V4",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sealed_sha256": sha,
        "sealed": sealed,
        "latencies_nonsealed": {
            "cca": results_cca["latencies"],
            "c_ni": results_c_ni["latencies"],
        },
    }

    # Guardar reporte de evidencia con sellado SHA-256
    os.makedirs("evidence", exist_ok=True)
    today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
    out_file = f"evidence/atbench_trajectory_results_{today_str}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    print("\nEvaluacion finalizada con exito.")
    print(f"Archivo guardado: {out_file}")
    print("SEALED_SHA256:", sha)

    # Mostrar tablas de resumen por consola para el reporte
    print("\n" + "=" * 70)
    print("RESUMEN DE METRICAS OUT-OF-FOLD EN TODO EL DATASET (AUROC / F1-Score)")
    print("=" * 70)
    for det_name, det_data in [
        ("CCA", results_cca["sealed_metrics"]),
        ("C_NI", results_c_ni["sealed_metrics"]),
    ]:
        print(f"\nDETECTOR BASE: {det_name}")
        print(
            f"{'Subconjunto':<12} | {'Size':<5} | {'Baseline (Fixed)':<45} | {'Baseline (Opt CV)':<45} | {'Memory (Fixed)':<45} | {'Memory (Opt CV)':<45}"
        )
        print("-" * 210)
        for sub_name in ["completo", "temprano", "tardio"]:
            sub = det_data["subsets"][sub_name]
            bf_ci = sub["baseline"]["fixed"]["auroc_ci"]
            bo_ci = sub["baseline"]["opt_cv"]["auroc_ci"]
            mf_ci = sub["memory"]["fixed"]["auroc_ci"]
            mo_ci = sub["memory"]["opt_cv"]["auroc_ci"]

            base_f = f"AUROC={sub['baseline']['fixed']['auroc']:.4f} [{bf_ci[0]:.4f}, {bf_ci[1]:.4f}] F1={sub['baseline']['fixed']['f1']:.4f}"
            base_o = f"AUROC={sub['baseline']['opt_cv']['auroc']:.4f} [{bo_ci[0]:.4f}, {bo_ci[1]:.4f}] F1={sub['baseline']['opt_cv']['f1']:.4f}"
            mem_f = f"AUROC={sub['memory']['fixed']['auroc']:.4f} [{mf_ci[0]:.4f}, {mf_ci[1]:.4f}] F1={sub['memory']['fixed']['f1']:.4f}"
            mem_o = f"AUROC={sub['memory']['opt_cv']['auroc']:.4f} [{mo_ci[0]:.4f}, {mo_ci[1]:.4f}] F1={sub['memory']['opt_cv']['f1']:.4f}"
            print(
                f"{sub_name:<12} | {sub['size']:<5} | {base_f:<45} | {base_o:<45} | {mem_f:<45} | {mem_o:<45}"
            )
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
