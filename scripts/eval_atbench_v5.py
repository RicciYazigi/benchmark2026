# -*- coding: utf-8 -*-
"""Script para evaluar y comparar los adaptadores de trayectoria de 4R2 (Fase v5).

Compara la eficacia del acumulador térmico (con memoria) contra la línea base sin memoria
utilizando el dataset ATBench bajo validación cruzada y test de diferencia pareada de AUROC,
e implementando ablación por longitud de interacción.
"""

import os
import sys

# Forzar PYTHONHASHSEED=0 al inicio para reproducibilidad absoluta a nivel de bit
if os.environ.get("ATBENCH_V5_CHILD") != "true":
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["ATBENCH_V5_CHILD"] = "true"
    import subprocess

    result = subprocess.run(
        [sys.executable] + sys.argv, capture_output=False, check=False
    )
    sys.exit(result.returncode)

import datetime
import hashlib
import json
import pathlib
import time

import numpy as np
import scipy.stats
from scipy.stats import rankdata

# Configurar sys.path para importar componentes locales
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[1] / "adapters_external")
)

from fourr2_singleturn_baseline_adapter import FourR2SingleTurnBaselineAdapter
from fourr2_trajectory_adapter import FourR2TrajectoryAdapter

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
    """Ejecuta la evaluación OOF, bootstrap pareado y ablación de longitud."""
    print(f"\n--- Evaluando en MODO: {mode.upper()} ---")

    # 1. Instanciar adaptadores
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

    # 2. Extraer scores continuos
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

    # FASE 4 — ABLACIÓN DE LONGITUD (Trabajar SOLO sobre el subconjunto tardío)
    tardio_idx = tardio_indices_list
    y_true_tardio = np.array([y_true[i] for i in tardio_idx])
    crits_base_tardio = np.array([crits_base[i] for i in tardio_idx])
    temps_acc_tardio = np.array([temps_acc[i] for i in tardio_idx])
    n_turns_tardio = np.array([len(samples[i].turns) for i in tardio_idx])

    # A) Longitud media de turnos: unsafe-tardío vs benign-tardío
    unsafe_tardio_lens = [len(samples[i].turns) for i in tardio_idx if y_true[i] == 1]
    benign_tardio_lens = [
        len(samples[i].turns)
        for i in tardio_idx
        if samples[i].metadata.get("risk_source") == "benign"
    ]

    len_stats = {
        "unsafe_tardio": {
            "mean": round(float(np.mean(unsafe_tardio_lens)), 4),
            "median": round(float(np.median(unsafe_tardio_lens)), 4),
            "std": round(float(np.std(unsafe_tardio_lens)), 4),
        },
        "benign_tardio": {
            "mean": round(float(np.mean(benign_tardio_lens)), 4),
            "median": round(float(np.median(benign_tardio_lens)), 4),
            "std": round(float(np.std(benign_tardio_lens)), 4),
        },
    }

    # B) Baseline-solo-longitud
    auroc_length = auroc(y_true_tardio, n_turns_tardio)

    # C) Spearman(rho)
    rho, pval = scipy.stats.spearmanr(temps_acc_tardio, n_turns_tardio)
    spearman_rho = {"rho": round(float(rho), 4), "pvalue": float(pval)}

    # D) ΔAUROC pareado ESTRATIFICADO por longitud (3 terciles)
    tardio_with_len = [(i, len(samples[i].turns)) for i in tardio_idx]
    # Ordenar por n_turns y por sample_id (como int) para determinismo absoluto
    tardio_with_len.sort(key=lambda x: (x[1], int(samples[x[0]].sample_id)))

    n_tardio = len(tardio_idx)
    size1 = n_tardio // 3
    size2 = n_tardio // 3

    tercil1 = [x[0] for x in tardio_with_len[:size1]]
    tercil2 = [x[0] for x in tardio_with_len[size1 : size1 + size2]]
    tercil3 = [x[0] for x in tardio_with_len[size1 + size2 :]]

    terciles_results = []
    for t_idx, t_name in zip(
        [tercil1, tercil2, tercil3], ["tercil1", "tercil2", "tercil3"]
    ):
        yt_t = np.array([y_true[i] for i in t_idx])
        sb_t = np.array([crits_base[i] for i in t_idx])
        sm_t = np.array([temps_acc[i] for i in t_idx])

        # Bootstrap pareado en este tercil
        rng_t = np.random.default_rng(42)
        deltas_t = []
        for _ in range(10000):
            r = rng_t.integers(0, len(t_idx), len(t_idx))
            if len(np.unique(yt_t[r])) < 2:
                continue
            deltas_t.append(auroc(yt_t[r], sm_t[r]) - auroc(yt_t[r], sb_t[r]))
        deltas_t = np.array(deltas_t)
        d_point_t = auroc(yt_t, sm_t) - auroc(yt_t, sb_t)
        ci_t = np.percentile(deltas_t, [2.5, 97.5])
        p_better_t = float((deltas_t > 0).mean())

        terciles_results.append(
            {
                "name": t_name,
                "size": len(t_idx),
                "delta_point": round(float(d_point_t), 4),
                "ci": [round(float(ci_t[0]), 4), round(float(ci_t[1]), 4)],
                "p_mem_better": round(float(p_better_t), 4),
            }
        )

    # E) Memoria normalizada por longitud
    mem_norm_tardio = np.array(
        [temps_acc[i] / max(1, len(samples[i].turns)) for i in tardio_idx]
    )
    auroc_mem_norm = auroc(y_true_tardio, mem_norm_tardio)

    # Bootstrap pareado memoria_normalizada vs baseline
    rng_norm = np.random.default_rng(42)
    deltas_norm = []
    for _ in range(10000):
        r = rng_norm.integers(0, len(tardio_idx), len(tardio_idx))
        if len(np.unique(y_true_tardio[r])) < 2:
            continue
        deltas_norm.append(
            auroc(y_true_tardio[r], mem_norm_tardio[r])
            - auroc(y_true_tardio[r], crits_base_tardio[r])
        )
    deltas_norm = np.array(deltas_norm)
    delta_point_norm = auroc(y_true_tardio, mem_norm_tardio) - auroc(
        y_true_tardio, crits_base_tardio
    )
    ci_norm = np.percentile(deltas_norm, [2.5, 97.5])
    p_better_norm = float((deltas_norm > 0).mean())

    length_ablation_metrics = {
        "length_stats": len_stats,
        "auroc_baseline_length": round(float(auroc_length), 4),
        "spearman_rho": spearman_rho,
        "terciles": terciles_results,
        "auroc_mem_norm": round(float(auroc_mem_norm), 4),
        "paired_delta_vs_baseline_norm": {
            "delta_point": round(float(delta_point_norm), 4),
            "ci": [round(float(ci_norm[0]), 4), round(float(ci_norm[1]), 4)],
            "p_mem_better": round(float(p_better_norm), 4),
        },
    }

    # 5. Análisis de turnos sobre el conjunto completo usando predicciones OOF (opt_cv)
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
            "length_ablation": length_ablation_metrics,
        },
    }


def main():
    print("Iniciando evaluación de ATBench v5 con Ablación de Longitud...")
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

    # 3. Dividir benignas de forma disjunta entre temprano y tardío (por saltos deterministicos)
    benign_pure = groups["benign_pure"]
    benign_temprano = benign_pure[0::2]
    benign_tardio = benign_pure[1::2]

    # 4. Construir temprano y tardío disjuntos
    temprano_indices_list = sorted(
        groups["direct_unsafe"] + groups["direct_safe"] + benign_temprano
    )
    tardio_indices_list = sorted(
        groups["indirect_unsafe"] + groups["indirect_safe"] + benign_tardio
    )

    temprano_indices = set(temprano_indices_list)
    tardio_indices = set(tardio_indices_list)

    y_true = [s.ground_truth_should_block for s in samples]

    # Imprimir tamaños para validacion de Gate 1
    print("--- VALIDACION DE SPLIT Y ESTRATIFICACION (GATE 1) ---")
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

    # Asserts de Gate 1
    assert len(temprano_indices.intersection(tardio_indices)) == 0, (
        "Error: Traslape en los índices temprano/tardío."
    )
    assert len(temprano_indices) + len(tardio_indices) == len(samples), (
        "Error: Pérdida o exceso de muestras al unir temprano/tardío."
    )
    assert sum(fold_counts) == len(samples), (
        "Error: La suma de pliegues no reconstruye las 1000 muestras."
    )
    print("[OK] Asserts de Fase 1 pasados exitosamente.")

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
    canonical = json.dumps(sealed, sort_keys=True, separators=(",", ":"))
    sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # Estructura del reporte completo que incluye los metadatos volátiles fuera de la firma
    report = {
        "trace_id": "ATBENCH-V5",
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
    out_file = f"evidence/atbench_v5_{today_str}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    print("\nEvaluacion finalizada con exito.")
    print(f"Archivo guardado: {out_file}")
    print("SEALED_SHA256:", sha)


if __name__ == "__main__":
    main()
