# -*- coding: utf-8 -*-
"""FASE 1, Gate 1-C — Desglose por familia de risk_source con sensor guard zero-shot.

Zero-shot: un solo modelo, sin leave-family-out (no hay entrenamiento del que
excluir). Por familia: AUROC de termico vs runmax sobre inseguras(familia) +
safe_eval (la misma mitad de seguras del Gate 1-B, seed 42).

Inferencia con la ESTRUCTURA DE DEPENDENCIA CORRECTA (leccion de la 3a
auditoria): las seguras se repiten entre familias -> bootstrap por CLUSTER de
trayectoria (cada segura se remuestrea una vez y arrastra su score a las 8
familias; inseguras se remuestrean dentro de su familia) + test de signos
sobre las familias (independientes en sus inseguras).

Uso:  python scripts/eval_guard_por_familia.py [nombre_modelo]
Env:  GUARD_CACHE (default evidence/guard_cache.json)
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
ALPHA = 0.3
TAU = 5.0
N_BOOT = int(os.environ.get("N_BOOT", "1000"))


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
            ranks[order[i : j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    u = ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def peaks(scores, theta):
    mx, T = -1e9, 0.0
    pmax = pth = -1e9
    for k, s in enumerate(scores):
        mx = max(mx, s)
        if k > 0:
            T *= math.exp(-1.0 / TAU)
        T += max(0.0, s - theta) ** 2
        pmax = max(pmax, mx)
        pth = max(pth, T)
    return pmax, pth


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else "llama-guard3:1b"
    cache_path = os.environ.get(
        "GUARD_CACHE", str(HERE / "evidence" / "guard_cache.json")
    )
    cache = json.loads(pathlib.Path(cache_path).read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")
    ]

    trajs = []
    for row in rows:
        contents = (
            row["contents"][0]
            if isinstance(row["contents"][0], list)
            else row["contents"]
        )
        scores = []
        for m in contents:
            key = hashlib.sha256(turn_text(m).encode()).hexdigest()[:24]
            if key not in cache:
                raise SystemExit(
                    f"Cache incompleto (falta {key}); correr primero eval_guard_online.py"
                )
            scores.append(float(cache[key]))
        trajs.append(
            {
                "label": int(row["label"]),
                "fam": str(row.get("risk_source") or ""),
                "scores": scores,
            }
        )

    rng = np.random.default_rng(SEED)
    safe_idx = [i for i, t in enumerate(trajs) if t["label"] == 0]
    rng.shuffle(safe_idx)
    half = len(safe_idx) // 2
    safe_cal, safe_eval = safe_idx[:half], sorted(safe_idx[half:])

    cal_scores = [s for i in safe_cal for s in trajs[i]["scores"]]
    theta = float(np.percentile(cal_scores, 90))
    theta_warning = None
    if theta >= 1.0:
        theta_warning = "theta p90 = 1.0 -> fallback 0.5 (mismo criterio que Gate 1-B)"
        theta = 0.5

    # peaks precomputados
    P = {i: peaks(trajs[i]["scores"], theta) for i in range(len(trajs))}
    s_mx = np.array([P[i][0] for i in safe_eval])
    s_th = np.array([P[i][1] for i in safe_eval])

    fams = sorted({t["fam"] for t in trajs if t["label"] == 1})
    unsafe_by_fam = {
        f: [i for i, t in enumerate(trajs) if t["label"] == 1 and t["fam"] == f]
        for f in fams
    }
    F = {
        f: {
            "u_mx": np.array([P[i][0] for i in unsafe_by_fam[f]]),
            "u_th": np.array([P[i][1] for i in unsafe_by_fam[f]]),
        }
        for f in fams
    }

    point = {}
    for f in fams:
        a_th = auc_rank(F[f]["u_th"], s_th)
        a_mx = auc_rank(F[f]["u_mx"], s_mx)
        point[f] = {
            "n_unsafe": len(unsafe_by_fam[f]),
            "auroc_thermal": round(a_th, 4),
            "auroc_runmax": round(a_mx, 4),
            "delta": round(a_th - a_mx, 4),
        }
    wins = sum(1 for v in point.values() if v["delta"] > 0)
    n_f = len(fams)
    p_sign = sum(comb(n_f, k) for k in range(wins, n_f + 1)) / 2**n_f

    # bootstrap por cluster
    macros = np.empty(N_BOOT)
    ns = len(safe_eval)
    for b in range(N_BOOT):
        si = rng.integers(0, ns, ns)
        ds = []
        for f in fams:
            nu = len(F[f]["u_th"])
            ui = rng.integers(0, nu, nu)
            ds.append(
                auc_rank(F[f]["u_th"][ui], s_th[si])
                - auc_rank(F[f]["u_mx"][ui], s_mx[si])
            )
        macros[b] = np.mean(ds)
    lo, hi = np.percentile(macros, [2.5, 97.5])

    res = {
        "fecha": str(date.today()),
        "modelo": model,
        "protocolo": "zero-shot; safe_eval identica al Gate 1-B (seed 42); theta p90 safe_cal; "
        "bootstrap por CLUSTER de trayectoria + test de signos (estadistica post-3a-auditoria)",
        "theta_usado": round(theta, 4),
        "theta_warning": theta_warning,
        "por_familia": point,
        "familias_ganadas_thermal": f"{wins}/{n_f}",
        "test_signos_p_unilateral": round(p_sign, 5),
        "bootstrap_cluster_macro_delta": {
            "delta_medio": round(float(macros.mean()), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_mejora": round(float((macros > 0).mean()), 4),
        },
        "etiqueta_veracidad": "empirico (sensor OOD real zero-shot)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = (
        HERE
        / "evidence"
        / f"atbench_guard_por_familia_{model.replace(':', '_').replace('/', '_')}_{date.today().strftime('%Y%m%d')}.json"
    )
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    out.with_suffix(".sha256").write_text(
        hashlib.sha256(payload.encode()).hexdigest() + "\n"
    )
    print(f"\nGuardado: {out}\nSHA-256: {hashlib.sha256(payload.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
