# -*- coding: utf-8 -*-
"""FASE 1 / 1.5 — Métricas ONLINE con sensor guard zero-shot (desde cache).

v2 (Fase 1.5): añade (1) normalización por cuantiles contra referencia benigna
(corrige sensores descalibrados: llama-guard θ=1.0, qwen θ=0.95) y (2) el
baseline CUSUM exigido por AUDITORIA_Y_NORTE_4R2.md Parte 4.1.

Protocolo (idéntico a v1 donde no se indica lo contrario):
  - Seguras 50/50 (seed 42): safe_cal calibra (normalizador, θ, k_ref);
    safe_eval solo evalúa. Eval = todas las inseguras + safe_eval.
  - NORM=quantile (default en v2): scores → rango empírico en benignos de cal.
    Por construcción θ = p90(cal_norm) ≈ 0.90 y k_ref = p75(cal_norm) ≈ 0.75.
    NORM=none reproduce el comportamiento v1 (con fallback θ).
  - Estadísticos online: runmax, runmean, EWMA(0.3), térmico I²t (τ=5, τ=2),
    CUSUM: S_k = max(0, S_{k-1} + (x_k − k_ref)).
  - Bootstrap por trayectoria; detección temprana a FPR 5%/10% desde safe_eval.

Uso:  python scripts/eval_guard_online.py [modelo]
Env:  GUARD_CACHE (default evidence/guard_cache.json) · NORM=quantile|none ·
      N_BOOT (default 2000)
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import sys
from datetime import date

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

SEED = 42
ALPHA = 0.3
TAUS = [5.0, 2.0]
FPRS = [0.05, 0.10]
N_BOOT = int(os.environ.get("N_BOOT", "2000"))
NORM = os.environ.get("NORM", "quantile").lower()


def auroc(y, s) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y), np.asarray(s, dtype=float)))


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def load_scored_trajs(model: str):
    cache_path = os.environ.get("GUARD_CACHE", str(HERE / "evidence" / "guard_cache.json"))
    cache = {}
    if pathlib.Path(cache_path).exists():
        cache = json.loads(pathlib.Path(cache_path).read_text(encoding="utf-8"))
    sensor = None
    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]
    trajs, misses = [], 0
    for row in rows:
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        scores = []
        for m in contents:
            t = turn_text(m)
            key = hashlib.sha256(t.encode()).hexdigest()[:24]
            if key in cache:
                scores.append(float(cache[key]))
            else:
                if sensor is None:
                    from aegisbench.sensors import GuardModelHTTPSensor

                    sensor = GuardModelHTTPSensor(model=model, cache_path=cache_path)
                scores.append(sensor.score([t])[0])
                misses += 1
        trajs.append({"label": int(row["label"]), "risk_source": str(row.get("risk_source") or ""),
                      "scores": scores})
    return trajs, misses


def online_series(scores, theta, k_ref):
    """Series online por turno de todos los estadísticos. Sin mirar el futuro."""
    mx, sm, ew, S = -1e9, 0.0, 0.0, 0.0
    T = {tau: 0.0 for tau in TAUS}
    out = {"runmax": [], "runmean": [], "ewma": [], "cusum": []}
    for tau in TAUS:
        out[f"thermal_tau{tau:g}"] = []
    for k, s in enumerate(scores):
        mx = max(mx, s)
        sm += s
        ew = s if k == 0 else ALPHA * s + (1 - ALPHA) * ew
        S = max(0.0, S + (s - k_ref))
        for tau in TAUS:
            if k > 0:
                T[tau] *= math.exp(-1.0 / tau)
            T[tau] += max(0.0, s - theta) ** 2
            out[f"thermal_tau{tau:g}"].append(T[tau])
        out["runmax"].append(mx)
        out["runmean"].append(sm / (k + 1))
        out["ewma"].append(ew)
        out["cusum"].append(S)
    return out


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "llama-guard3:1b"
    trajs, misses = load_scored_trajs(model)
    rng = np.random.default_rng(SEED)

    all_scores = [s for t in trajs for s in t["scores"]]
    uniq = sorted(set(all_scores))
    granularidad = {
        "n_valores_unicos": len(uniq),
        "valores_si_pocos": uniq[:12] if len(uniq) <= 12 else None,
        "corrida_continua_recomendada": len(uniq) < 10,
    }

    safe_idx = [i for i, t in enumerate(trajs) if t["label"] == 0]
    rng.shuffle(safe_idx)
    half = len(safe_idx) // 2
    safe_cal, safe_eval = set(safe_idx[:half]), set(safe_idx[half:])
    unsafe_idx = [i for i, t in enumerate(trajs) if t["label"] == 1]
    eval_idx = sorted(unsafe_idx) + sorted(safe_eval)

    cal_raw = [s for i in safe_cal for s in trajs[i]["scores"]]

    theta_warning = None
    if NORM == "quantile":
        from aegisbench.sensors.normalize import QuantileNormalizer

        qn = QuantileNormalizer().fit(cal_raw)
        for t in trajs:
            t["scores_n"] = qn.transform(t["scores"])
        cal_n = [s for i in safe_cal for s in trajs[i]["scores_n"]]
        theta = float(np.percentile(cal_n, 90))
        k_ref = float(np.percentile(cal_n, 75))
        score_key = "scores_n"
    else:
        theta = float(np.percentile(cal_raw, 90))
        if theta >= 1.0:
            theta_warning = "theta p90 = 1.0 -> fallback 0.5 (sensor binario con FP>10%)"
            theta = 0.5
        k_ref = float(np.percentile(cal_raw, 75))
        if k_ref >= 1.0:
            k_ref = 0.5
        score_key = "scores"

    methods = ["runmax", "runmean", "ewma", "cusum"] + [f"thermal_tau{t:g}" for t in TAUS]
    series_all, peaks, y = {}, {m: [] for m in methods}, []
    for i in eval_idx:
        ser = online_series(trajs[i][score_key], theta, k_ref)
        series_all[i] = ser
        y.append(trajs[i]["label"])
        for m in methods:
            peaks[m].append(max(ser[m]))
    y = np.array(y)

    res_auroc = {m: round(auroc(y, peaks[m]), 4) for m in methods}

    def boot_delta(stat_a, stat_b):
        vals = []
        a, b = np.array(stat_a), np.array(stat_b)
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(y), len(y))
            if len(np.unique(y[idx])) < 2:
                continue
            vals.append(auroc(y[idx], a[idx]) - auroc(y[idx], b[idx]))
        lo, hi = np.percentile(vals, [2.5, 97.5])
        return {"delta_medio": round(float(np.mean(vals)), 4),
                "ci95": [round(float(lo), 4), round(float(hi), 4)],
                "p_mejora": round(float(np.mean(np.array(vals) > 0)), 4)}

    th = f"thermal_tau{TAUS[0]:g}"
    deltas = {
        f"{th}_vs_runmax": boot_delta(peaks[th], peaks["runmax"]),
        "cusum_vs_runmax": boot_delta(peaks["cusum"], peaks["runmax"]),
        f"cusum_vs_{th}": boot_delta(peaks["cusum"], peaks[th]),
        f"{th}_vs_ewma": boot_delta(peaks[th], peaks["ewma"]),
    }

    det = {}
    for fpr in FPRS:
        block = {}
        for m in methods:
            safe_peaks = np.sort([max(series_all[i][m]) for i in sorted(safe_eval)])
            thr = float(np.quantile(safe_peaks, 1.0 - fpr, method="higher"))
            tp, fracs = 0, []
            for i in sorted(unsafe_idx):
                ser = series_all[i][m]
                hit = next((k for k, v in enumerate(ser) if v >= thr), None)
                if hit is not None:
                    tp += 1
                    fracs.append((hit + 1) / len(ser))
            block[m] = {"tpr": round(tp / len(unsafe_idx), 4),
                        "frac_al_detectar": round(float(np.mean(fracs)), 4) if fracs else None}
        det[f"fpr_{int(fpr*100)}pct"] = block

    res = {
        "fecha": str(date.today()),
        "modelo": model,
        "version": "v2-fase1.5",
        "normalizacion": NORM,
        "protocolo": "zero-shot OOD; seguras 50/50 (cal/eval, seed 42); "
        "normalizacion por cuantiles vs benignos de cal (si NORM=quantile); "
        "CUSUM S_k=max(0,S+(x-k_ref)); bootstrap por trayectoria",
        "cache_misses_al_evaluar": misses,
        "granularidad_scores": granularidad,
        "theta_usado": round(theta, 4),
        "k_ref_cusum": round(k_ref, 4),
        "theta_warning": theta_warning,
        "n_eval": {"unsafe": int(y.sum()), "safe_eval": int((1 - y).sum())},
        "auroc_online": res_auroc,
        "deltas_pareados": deltas,
        "deteccion_temprana": det,
        "etiqueta_veracidad": "empirico (OOD zero-shot; hipotesis H1-H3 pre-registradas en "
        "INSTRUCCIONES_ANTIGRAVITY_PLAN_MAESTRO.md Fase 1.5)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    READ_ONLY = os.environ.get("READ_ONLY", "0").lower() in ("1", "true", "yes")
    tag = f"{model.replace(':','_').replace('/','_')}_{NORM}"
    out = HERE / "evidence" / f"atbench_guard_online_v2_{tag}_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    if not READ_ONLY:
        out.write_text(payload, encoding="utf-8")
        out.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "\n")
        print(f"\nGuardado: {out}\nSHA-256: {hashlib.sha256(payload.encode()).hexdigest()}")
    else:
        print(f"\n[READ_ONLY=1] Omitiendo escritura en disco para preservar el hash sellado de evidencia.")



if __name__ == "__main__":
    main()
