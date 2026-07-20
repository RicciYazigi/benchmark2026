# -*- coding: utf-8 -*-
"""FASE 1.5 — Ensamble online (adenda 9 del plan maestro, hipótesis pre-registrada).

Hipótesis: el térmico gana donde la evidencia es dispersa y pierde en eventos
puntuales → un ensamble reactivo+acumulativo debería dominar a cada uno solo.

Ensamble por rangos (online, sin futuro): en cada turno k, cada estadístico
emite su valor; el score de trayectoria de cada método es su pico. El ensamble
convierte el pico de cada método a su rango empírico frente a safe_eval y
promedia: ens = mean(rank(runmax), rank(thermal), rank(cusum)).
(El rango frente a benignos es estimable online con un buffer de referencia —
misma lógica del QuantileNormalizer — así que el ensamble es desplegable.)

Inferencia: global (bootstrap por trayectoria) + por familia (bootstrap por
clúster + test de signos, estadística post-3a-auditoría).

Uso:  python scripts/eval_guard_ensemble.py [modelo]
Env:  GUARD_CACHE · NORM=quantile|none (default quantile) · N_BOOT
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import sys
from datetime import date
from math import comb

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "src"))

SEED = 42
TAU = 5.0
ALPHA = 0.3
N_BOOT = int(os.environ.get("N_BOOT", "1000"))
NORM = os.environ.get("NORM", "quantile").lower()


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def auc_rank(pos, neg) -> float:
    allv = np.concatenate([pos, neg])
    order = np.argsort(allv, kind="mergesort")
    ranks = np.empty(len(allv))
    ranks[order] = np.arange(1, len(allv) + 1)
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    u = ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def peaks(scores, theta, k_ref):
    mx, S, T = -1e9, 0.0, 0.0
    p_mx = p_S = p_T = -1e9
    for k, s in enumerate(scores):
        mx = max(mx, s)
        S = max(0.0, S + (s - k_ref))
        if k > 0:
            T *= math.exp(-1.0 / TAU)
        T += max(0.0, s - theta) ** 2
        p_mx, p_S, p_T = max(p_mx, mx), max(p_S, S), max(p_T, T)
    return {"runmax": p_mx, "cusum": p_S, "thermal": p_T}


def emp_rank(values, ref_sorted):
    lo = np.searchsorted(ref_sorted, values, side="left")
    hi = np.searchsorted(ref_sorted, values, side="right")
    return (lo + hi) / 2.0 / max(1, len(ref_sorted))


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "llama-guard3:1b"
    cache_path = os.environ.get("GUARD_CACHE", str(HERE / "evidence" / "guard_cache.json"))
    cache = json.loads(pathlib.Path(cache_path).read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]

    trajs = []
    for row in rows:
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        sc = []
        for m in contents:
            key = hashlib.sha256(turn_text(m).encode()).hexdigest()[:24]
            if key not in cache:
                raise SystemExit(f"Cache incompleto ({key}); completar warming primero")
            sc.append(float(cache[key]))
        trajs.append({"label": int(row["label"]), "fam": str(row.get("risk_source") or ""),
                      "scores": sc})

    rng = np.random.default_rng(SEED)
    safe_idx = [i for i, t in enumerate(trajs) if t["label"] == 0]
    rng.shuffle(safe_idx)
    half = len(safe_idx) // 2
    safe_cal, safe_eval = set(safe_idx[:half]), sorted(safe_idx[half:])
    cal_raw = [s for i in safe_cal for s in trajs[i]["scores"]]

    if NORM == "quantile":
        from aegisbench.sensors.normalize import QuantileNormalizer

        qn = QuantileNormalizer().fit(cal_raw)
        for t in trajs:
            t["s"] = qn.transform(t["scores"])
        cal_n = [s for i in safe_cal for s in trajs[i]["s"]]
        theta, k_ref = float(np.percentile(cal_n, 90)), float(np.percentile(cal_n, 75))
    else:
        for t in trajs:
            t["s"] = t["scores"]
        theta = min(0.5, float(np.percentile(cal_raw, 90)))
        k_ref = min(0.5, float(np.percentile(cal_raw, 75)))

    P = {i: peaks(trajs[i]["s"], theta, k_ref) for i in range(len(trajs))}
    base = ["runmax", "cusum", "thermal"]
    ref_sorted = {m: np.sort([P[i][m] for i in safe_eval]) for m in base}

    def ens(i):
        return float(np.mean([emp_rank(np.array([P[i][m]]), ref_sorted[m])[0] for m in base]))

    unsafe_idx = sorted(i for i, t in enumerate(trajs) if t["label"] == 1)
    eval_idx = unsafe_idx + safe_eval
    y = np.array([trajs[i]["label"] for i in eval_idx])
    scores_by = {m: np.array([P[i][m] for i in eval_idx]) for m in base}
    scores_by["ensemble"] = np.array([ens(i) for i in eval_idx])

    from sklearn.metrics import roc_auc_score

    global_auroc = {m: round(float(roc_auc_score(y, v)), 4) for m, v in scores_by.items()}

    def boot_delta(a, b):
        vals = []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(y), len(y))
            if len(np.unique(y[idx])) < 2:
                continue
            vals.append(float(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx])))
        lo, hi = np.percentile(vals, [2.5, 97.5])
        return {"delta_medio": round(float(np.mean(vals)), 4),
                "ci95": [round(float(lo), 4), round(float(hi), 4)],
                "p_mejora": round(float(np.mean(np.array(vals) > 0)), 4)}

    best_single = max(base, key=lambda m: global_auroc[m])
    deltas = {f"ensemble_vs_{best_single}(mejor_individual)":
              boot_delta(scores_by["ensemble"], scores_by[best_single])}

    # por familia: ensamble vs mejor individual, cluster bootstrap + signos
    fams = sorted({trajs[i]["fam"] for i in unsafe_idx})
    s_eval_ens = np.array([ens(i) for i in safe_eval])
    s_eval_best = np.array([P[i][best_single] for i in safe_eval])
    per_fam, wins = {}, 0
    u_by_fam = {f: [i for i in unsafe_idx if trajs[i]["fam"] == f] for f in fams}
    for f in fams:
        ue = np.array([ens(i) for i in u_by_fam[f]])
        ub = np.array([P[i][best_single] for i in u_by_fam[f]])
        a_e, a_b = auc_rank(ue, s_eval_ens), auc_rank(ub, s_eval_best)
        per_fam[f] = {"auroc_ensemble": round(a_e, 4), f"auroc_{best_single}": round(a_b, 4),
                      "delta": round(a_e - a_b, 4)}
        wins += a_e > a_b
    p_sign = sum(comb(len(fams), k) for k in range(wins, len(fams) + 1)) / 2 ** len(fams)

    macros = np.empty(N_BOOT)
    ns = len(safe_eval)
    for b in range(N_BOOT):
        si = rng.integers(0, ns, ns)
        ds = []
        for f in fams:
            us = u_by_fam[f]
            ui = rng.integers(0, len(us), len(us))
            ue = np.array([ens(us[j]) for j in ui])
            ub = np.array([P[us[j]][best_single] for j in ui])
            ds.append(auc_rank(ue, s_eval_ens[si]) - auc_rank(ub, s_eval_best[si]))
        macros[b] = np.mean(ds)
    lo, hi = np.percentile(macros, [2.5, 97.5])

    res = {
        "fecha": str(date.today()),
        "modelo": model,
        "normalizacion": NORM,
        "theta": round(theta, 4),
        "k_ref": round(k_ref, 4),
        "auroc_global": global_auroc,
        "mejor_individual": best_single,
        "deltas_globales": deltas,
        "por_familia_vs_mejor_individual": per_fam,
        "familias_ganadas_ensemble": f"{wins}/{len(fams)}",
        "test_signos_p_unilateral": round(p_sign, 5),
        "bootstrap_cluster_macro_delta": {
            "delta_medio": round(float(macros.mean()), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_mejora": round(float((macros > 0).mean()), 4)},
        "etiqueta_veracidad": "empirico (hipotesis del ensamble pre-registrada en adenda 9 "
        "ANTES de los datos qwen)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    tag = f"{model.replace(':','_').replace('/','_')}_{NORM}"
    out = HERE / "evidence" / f"atbench_guard_ensemble_{tag}_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    out.with_suffix(".sha256").write_text(hashlib.sha256(payload.encode()).hexdigest() + "\n")
    print(f"\nGuardado: {out}\nSHA-256: {hashlib.sha256(payload.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
