# -*- coding: utf-8 -*-
"""ATBench sensor real + acumulador CALIBRADO por fold (train-only).

Identico protocolo que eval_atbench_sensor_real.py, con una adicion legitima:
por cada fold, (theta_pct, tau) del acumulador se eligen maximizando AUROC de
memoria SOBRE TRAIN unicamente (grid pequeño), y se aplican al test del fold.
Nada del test toca la seleccion. Checkpoint por fold (reanudable).
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
from datetime import date

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent


def _resolve_4r2() -> pathlib.Path:
    p = os.environ.get("FOURR2_REPO_PATH")
    if p:
        pp = pathlib.Path(p).expanduser().resolve()
        if (pp / "four_r2" / "guardrail.py").exists():
            return pp
    cand = HERE.parent / "4R2 repo maestro jul2026"
    if (cand / "four_r2" / "guardrail.py").exists():
        return cand
    raise ImportError("Define FOURR2_REPO_PATH")


_root = _resolve_4r2()
for extra in (str(_root), str(_root / "antigravity_wings"), str(HERE / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from antigravity_wings.thermal import ThermalAccumulator, ThermalParams  # noqa: E402

from aegisbench.sensors import TfidfTurnSensor  # noqa: E402

SEED = 42
N_FOLDS = 5
N_BOOT = int(os.environ.get("N_BOOT", "2000"))
GRID_THETA_PCT = [50.0, 70.0, 90.0]
GRID_TAU = [2.0, 5.0, 10.0, 20.0]
CKPT_DIR = HERE / "evidence" / "cal_ckpt"


def auroc(y, s) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y), np.asarray(s, dtype=float)))


def boot_ci(y, s, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    s = np.asarray(s, dtype=float)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        vals.append(auroc(y[idx], s[idx]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return round(float(lo), 4), round(float(hi), 4)


def paired_delta(y, s_a, s_b, n=N_BOOT, seed=SEED):
    rng = np.random.default_rng(seed)
    y = np.asarray(y)
    s_a = np.asarray(s_a, dtype=float)
    s_b = np.asarray(s_b, dtype=float)
    deltas = []
    for _ in range(n):
        idx = rng.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        deltas.append(auroc(y[idx], s_a[idx]) - auroc(y[idx], s_b[idx]))
    deltas = np.asarray(deltas)
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {
        "delta_puntual": round(auroc(y, s_a) - auroc(y, s_b), 4),
        "ci95": [round(float(lo), 4), round(float(hi), 4)],
        "p_mejora": round(float((deltas > 0).mean()), 4),
    }


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def memory_maxT(scores, theta: float, tau: float) -> float:
    acc = ThermalAccumulator(params=ThermalParams(tau=tau, T_trip=1e9, theta_ref=theta))
    mx = 0.0
    for i, c in enumerate(scores):
        acc.record(criticality=float(c), t=float(i), path="x")
        mx = max(mx, acc.log[-1].temperature)
    return mx


def main() -> None:
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
        trajs.append(
            {"label": int(row["label"]), "turns": [turn_text(m) for m in contents]}
        )
    labels = np.array([t["label"] for t in trajs])

    from sklearn.model_selection import StratifiedKFold

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    CKPT_DIR.mkdir(exist_ok=True)

    folds = list(skf.split(np.zeros(len(trajs)), labels))
    for fold, (tr_idx, te_idx) in enumerate(folds):
        fckpt = CKPT_DIR / f"fold{fold}.npz"
        if fckpt.exists():
            print(f"fold {fold}: ya listo (checkpoint)", flush=True)
            continue
        sensor = TfidfTurnSensor(seed=SEED)
        tr_texts, tr_labels = [], []
        for i in tr_idx:
            tr_texts.extend(trajs[i]["turns"])
            tr_labels.extend([trajs[i]["label"]] * len(trajs[i]["turns"]))
        sensor.fit(tr_texts, tr_labels)

        tr_scores = {i: sensor.score(trajs[i]["turns"]) for i in tr_idx}
        safe_scores = [
            s for i in tr_idx if trajs[i]["label"] == 0 for s in tr_scores[i]
        ]
        y_tr = labels[tr_idx]

        best = None
        for pct in GRID_THETA_PCT:
            th = float(np.percentile(safe_scores, pct))
            for tau in GRID_TAU:
                mem_tr = [memory_maxT(tr_scores[i], th, tau) for i in tr_idx]
                a = auroc(y_tr, mem_tr)
                if best is None or a > best[0]:
                    best = (a, pct, th, tau)
        _, pct_b, th_b, tau_b = best

        te_max = np.zeros(len(te_idx))
        te_mean = np.zeros(len(te_idx))
        te_mem = np.zeros(len(te_idx))
        for j, i in enumerate(te_idx):
            s = sensor.score(trajs[i]["turns"])
            te_max[j] = max(s)
            te_mean[j] = float(np.mean(s))
            te_mem[j] = memory_maxT(s, th_b, tau_b)
        np.savez(
            fckpt,
            te_idx=np.array(te_idx),
            te_max=te_max,
            te_mean=te_mean,
            te_mem=te_mem,
            cfg=np.array([pct_b, th_b, tau_b]),
        )
        print(
            f"fold {fold}: cfg=(pct={pct_b}, theta={th_b:.4f}, tau={tau_b}) "
            f"auroc_train_mem={best[0]:.4f} guardado",
            flush=True,
        )

    # agregacion final si todos los folds existen
    if not all((CKPT_DIR / f"fold{f}.npz").exists() for f in range(N_FOLDS)):
        print("faltan folds; relanzar para continuar", flush=True)
        return
    oof = {
        "single_max": np.zeros(len(trajs)),
        "single_mean": np.zeros(len(trajs)),
        "memory_maxT_cal": np.zeros(len(trajs)),
    }
    cfgs = []
    for f in range(N_FOLDS):
        z = np.load(CKPT_DIR / f"fold{f}.npz")
        idx = z["te_idx"]
        oof["single_max"][idx] = z["te_max"]
        oof["single_mean"][idx] = z["te_mean"]
        oof["memory_maxT_cal"][idx] = z["te_mem"]
        cfgs.append([round(float(x), 4) for x in z["cfg"]])

    res = {
        "fecha": str(date.today()),
        "sensor": "tfidf-logreg-v1 (supervision debil OOF)",
        "protocolo": f"{N_FOLDS}-fold estratificado por trayectoria, seed {SEED}; "
        "(theta_pct, tau) calibrados por fold SOLO con train (grid 3x4); "
        "score memoria = max temperatura continua",
        "cfg_por_fold_[pct,theta,tau]": cfgs,
        "n": len(trajs),
        "auroc": {
            k: {"puntual": round(auroc(labels, v), 4), "ci95": list(boot_ci(labels, v))}
            for k, v in oof.items()
        },
        "delta_pareado": {
            "memoria_cal_vs_mejor_un_turno": paired_delta(
                labels, oof["memory_maxT_cal"], oof["single_max"]
            ),
            "memoria_cal_vs_media": paired_delta(
                labels, oof["memory_maxT_cal"], oof["single_mean"]
            ),
        },
        "etiqueta_veracidad": "empirico con limites (sensor en dominio; hiperparametros "
        "elegidos con scores in-fold de train, sin tocar test)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = (
        HERE
        / "evidence"
        / f"atbench_sensor_real_tfidf_CAL_{date.today().strftime('%Y%m%d')}.json"
    )
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_bytes(payload.encode("utf-8"))  # binario: evita CRLF de Windows
    sha = hashlib.sha256(payload.encode()).hexdigest()
    out.with_suffix(".sha256").write_bytes((sha + "\n").encode("utf-8"))
    print(f"\nGuardado: {out}\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
