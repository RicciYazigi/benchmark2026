# -*- coding: utf-8 -*-
"""Script para evaluar y comparar los adaptadores de trayectoria de 4R2.

Compara la eficacia del acumulador térmico (con memoria) contra la línea base sin memoria
utilizando el dataset ATBench.
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

from aegisbench.datasets.atbench_loader import load_atbench


def auroc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    if len(pos) == 0 or len(neg) == 0:
        return 0.0
    allv = np.concatenate([pos, neg])
    ranks = allv.argsort().argsort() + 1
    pos_rank_sum = ranks[: len(pos)].sum()
    u_statistic = pos_rank_sum - len(pos) * (len(pos) + 1) / 2
    return float(u_statistic / (len(pos) * len(neg)))


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


def main():
    print("Iniciando evaluación de ATBench...")
    dataset_path = "data/atbench_test.jsonl"

    if not os.path.exists(dataset_path):
        print(f"Error: No existe el archivo {dataset_path}. Corre la Fase 1 primero.")
        sys.exit(1)

    samples = load_atbench(dataset_path)
    print(f"Cargadas {len(samples)} muestras del dataset.")

    # 1. Instanciar adaptadores usando el modo 'cca' por defecto
    acc_adapter = FourR2TrajectoryAdapter(mode="cca")
    base_adapter = FourR2SingleTurnBaselineAdapter(mode="cca")

    y_true = [s.ground_truth_should_block for s in samples]

    # Listas para almacenar resultados
    results_acc = []
    results_base = []

    print("Evaluando con adaptador de trayectoria (con memoria)...")
    t0 = time.perf_counter()
    for s in samples:
        results_acc.append(acc_adapter.evaluate(s))
    lat_acc = (time.perf_counter() - t0) * 1000.0 / len(samples)

    print("Evaluando con adaptador de línea base (sin memoria)...")
    t0 = time.perf_counter()
    for s in samples:
        results_base.append(base_adapter.evaluate(s))
    lat_base = (time.perf_counter() - t0) * 1000.0 / len(samples)

    # Preparar predicciones
    # Predicciones binarias (1 para BLOCK, 0 para ALLOW)
    y_pred_acc = [1 if r.decision.value == "block" else 0 for r in results_acc]
    y_pred_base = [1 if r.decision.value == "block" else 0 for r in results_base]

    # Scores continuos de riesgo para AUROC
    # Para la memoria, extraemos temp_max / T_trip normalizado (que fue mapeado en evaluate)
    # reconstruct_risk = confidence si es BLOCK, y 1.0 - confidence si es ALLOW
    scores_acc = []
    for r in results_acc:
        if r.decision.value == "block":
            scores_acc.append(r.confidence)
        else:
            scores_acc.append(1.0 - r.confidence)

    scores_base = []
    for r in results_base:
        if r.decision.value == "block":
            scores_base.append(r.confidence)
        else:
            scores_base.append(1.0 - r.confidence)

    # Calcular métricas básicas
    metrics_acc = compute_metrics(y_true, y_pred_acc)
    metrics_base = compute_metrics(y_true, y_pred_base)

    # Calcular AUROC
    pos_scores_acc = [score for yt, score in zip(y_true, scores_acc) if yt]
    neg_scores_acc = [score for yt, score in zip(y_true, scores_acc) if not yt]
    metrics_acc["auroc"] = round(auroc(pos_scores_acc, neg_scores_acc), 4)

    pos_scores_base = [score for yt, score in zip(y_true, scores_base) if yt]
    neg_scores_base = [score for yt, score in zip(y_true, scores_base) if not yt]
    metrics_base["auroc"] = round(auroc(pos_scores_base, neg_scores_base), 4)

    # Latencias promedio
    metrics_acc["mean_latency_ms"] = round(lat_acc, 4)
    metrics_base["mean_latency_ms"] = round(lat_base, 4)

    # 5. Análisis del turno de disparo donde ambos coinciden en detectar
    turns_acc = []
    turns_base = []

    for yt, r_acc, r_base in zip(y_true, results_acc, results_base):
        # Solo donde la muestra es unsafe (yt=True) y AMBOS detectan (decisión = block)
        if yt and r_acc.decision.value == "block" and r_base.decision.value == "block":
            t_acc = parse_tripped_turn(r_acc.raw_output)
            t_base = parse_tripped_turn(r_base.raw_output)
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

    # Estructura del reporte de evidencia
    report = {
        "trace_id": "ATBENCH-TRAYECTORIA-EVAL",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "dataset_info": {
            "name": "ATBench",
            "path": dataset_path,
            "total_samples": len(samples),
            "positives": sum(y_true),
            "negatives": len(samples) - sum(y_true),
        },
        "configs": {
            "theta": acc_adapter.theta,
            "tau": acc_adapter.tau,
            "T_trip": acc_adapter.T_trip,
            "detector_mode": acc_adapter.mode,
        },
        "metrics": {"memory_adapter": metrics_acc, "baseline_adapter": metrics_base},
        "detection_turn_analysis": detection_comparison,
    }

    # 6. Guardar en evidence/atbench_trajectory_results_<fecha>.json con sellado SHA-256
    os.makedirs("evidence", exist_ok=True)
    today_str = datetime.datetime.utcnow().strftime("%Y%m%d")
    out_file = f"evidence/atbench_trajectory_results_{today_str}.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    # Calcular hash de sellado
    with open(out_file, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    print("\nEvaluación finalizada.")
    print(f"Archivo guardado: {out_file}")
    print(f"SHA-256: {sha}")

    # Mostrar resumen por pantalla
    print("\n" + "=" * 50)
    print("RESUMEN DE RESULTADOS")
    print("=" * 50)
    print("Métricas con Memoria (ThermalAccumulator):")
    print(f"  AUROC:     {metrics_acc['auroc']:.4f}")
    print(f"  F1-Score:  {metrics_acc['f1']:.4f}")
    print(f"  Precision: {metrics_acc['precision']:.4f}")
    print(f"  Recall:    {metrics_acc['recall']:.4f}")
    print(
        f"  TP={metrics_acc['tp']}, FP={metrics_acc['fp']}, TN={metrics_acc['tn']}, FN={metrics_acc['fn']}"
    )
    print("Métricas sin Memoria (Línea Base):")
    print(f"  AUROC:     {metrics_base['auroc']:.4f}")
    print(f"  F1-Score:  {metrics_base['f1']:.4f}")
    print(f"  Precision: {metrics_base['precision']:.4f}")
    print(f"  Recall:    {metrics_base['recall']:.4f}")
    print(
        f"  TP={metrics_base['tp']}, FP={metrics_base['fp']}, TN={metrics_base['tn']}, FN={metrics_base['fn']}"
    )
    if detection_comparison:
        print(
            f"\nComparación del Turno de Detección (N={detection_comparison['N_coincidences']}):"
        )
        print(f"  Turno medio memoria:  {detection_comparison['mean_turn_memory']}")
        print(f"  Turno medio baseline: {detection_comparison['mean_turn_baseline']}")
        print(f"  Memoria detecta antes: {detection_comparison['memory_faster_count']}")
        print(
            f"  Baseline detecta antes: {detection_comparison['baseline_faster_count']}"
        )
        print(f"  Mismo turno:          {detection_comparison['same_turn_count']}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
