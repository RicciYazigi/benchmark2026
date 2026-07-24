# -*- coding: utf-8 -*-
"""ATBench con sensor por turno REAL (fase post-aislamiento).

Protocolo (sin fuga, sin trampas):
  1. 5-fold estratificado SOBRE TRAYECTORIAS (los turnos heredan el fold del
     grupo; jamas se entrena y evalua sobre la misma trayectoria).
  2. Por fold: el sensor se entrena solo con turnos de trayectorias de train
     (supervision debil: label del turno = label de su trayectoria).
  3. theta_ref del acumulador se calibra POR FOLD usando solo train: percentil
     90 de los scores de turnos de trayectorias SEGURAS de train.
  4. Scores OOF por trayectoria:
       - single_max : max score de turno (mejor detector de un turno posible)
       - single_mean: media de scores (agregacion trivial sin fisica)
       - memory_maxT: temperatura maxima del ThermalAccumulator (tau=5)
  5. AUROC global + bootstrap CI + delta pareado memoria-vs-max.
Evidencia sellada SHA-256. core/ de 4r2v6 intacto (solo lectura).

Uso:
  python3 scripts/eval_atbench_sensor_real.py            # sensor tfidf
  python3 scripts/eval_atbench_sensor_real.py guard      # guard model via ollama
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

from aegisbench.sensors import GuardModelHTTPSensor, TfidfTurnSensor  # noqa: E402
from antigravity_wings.thermal import ThermalAccumulator, ThermalParams  # noqa: E402

SEED = 42
TAU = 5.0
N_FOLDS = 5
N_BOOT = int(os.environ.get("N_BOOT", "5000"))


def auroc(y_true, y_score) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y_true), np.asarray(y_score, dtype=float)))


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
    """delta AUROC (a - b) pareado por remuestreo de trayectorias."""
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


def run_memory(scores, theta: float) -> float:
    acc = ThermalAccumulator(
        params=ThermalParams(tau=TAU, T_trip=1e9, theta_ref=theta)  # sin trip: score continuo
    )
    max_T = 0.0
    for i, c in enumerate(scores):
        acc.record(criticality=float(c), t=float(i), path="x")
        max_T = max(max_T, acc.log[-1].temperature)
    return max_T


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "tfidf"
    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]
    trajs = []
    for row in rows:
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        trajs.append(
            {
                "id": str(row["id"]),
                "label": int(row["label"]),
                "turns": [turn_text(m) for m in contents],
            }
        )

    labels = np.array([t["label"] for t in trajs])
    ckpt = HERE / "evidence" / f"oof_scores_{mode}.npz"

    if ckpt.exists() and "--metrics-only" in sys.argv:
        z = np.load(ckpt)
        oof = {k: z[k] for k in ("single_max", "single_mean", "memory_maxT")}
        fold_thetas = [float(x) for x in z["thetas"]]
        _report(mode, trajs, labels, oof, fold_thetas)
        return

    from sklearn.model_selection import StratifiedKFold

    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)

    oof = {"single_max": np.zeros(len(trajs)), "single_mean": np.zeros(len(trajs)),
           "memory_maxT": np.zeros(len(trajs))}
    fold_thetas = []

    for fold, (tr_idx, te_idx) in enumerate(skf.split(np.zeros(len(trajs)), labels)):
        if mode == "guard":
            sensor = GuardModelHTTPSensor(cache_path=str(HERE / "evidence" / "guard_cache.json"))
        else:
            sensor = TfidfTurnSensor(seed=SEED)
            tr_texts, tr_labels = [], []
            for i in tr_idx:
                tr_texts.extend(trajs[i]["turns"])
                tr_labels.extend([trajs[i]["label"]] * len(trajs[i]["turns"]))
            sensor.fit(tr_texts, tr_labels)

        # theta por fold: percentil 90 de scores de turnos SEGUROS de train
        safe_scores = []
        for i in tr_idx:
            if trajs[i]["label"] == 0:
                safe_scores.extend(sensor.score(trajs[i]["turns"]))
        theta_f = float(np.percentile(safe_scores, 90))
        fold_thetas.append(round(theta_f, 4))

        for i in te_idx:
            s = sensor.score(trajs[i]["turns"])
            oof["single_max"][i] = max(s)
            oof["single_mean"][i] = float(np.mean(s))
            oof["memory_maxT"][i] = run_memory(s, theta_f)
        print(f"fold {fold}: theta={theta_f:.4f} listo", flush=True)

    np.savez(ckpt, thetas=np.array(fold_thetas), **oof)
    print(f"checkpoint OOF guardado: {ckpt}", flush=True)
    _report(mode, trajs, labels, oof, fold_thetas)


def _report(mode, trajs, labels, oof, fold_thetas) -> None:
    res = {
        "fecha": str(date.today()),
        "modo_sensor": mode,
        "sensor": "tfidf-logreg-v1 (supervision debil OOF)" if mode != "guard" else "guard-http-v1",
        "protocolo": f"{N_FOLDS}-fold estratificado por trayectoria, seed {SEED}, "
        f"tau={TAU}, theta calibrado por fold (p90 turnos seguros train), "
        f"score memoria = max temperatura (continuo, sin T_trip)",
        "theta_por_fold": fold_thetas,
        "n": len(trajs),
        "balance": {"unsafe": int(labels.sum()), "safe": int((1 - labels).sum())},
        "auroc": {},
        "delta_pareado": {},
        "etiqueta_veracidad": "empirico con limites (sensor entrenado en dominio ATBench; "
        "generalizacion fuera de dominio: ND hasta la fase guard model)",
    }
    for k, v in oof.items():
        res["auroc"][k] = {"puntual": round(auroc(labels, v), 4), "ci95": list(boot_ci(labels, v))}
    res["delta_pareado"]["memoria_vs_mejor_un_turno"] = paired_delta(
        labels, oof["memory_maxT"], oof["single_max"]
    )
    res["delta_pareado"]["memoria_vs_media"] = paired_delta(
        labels, oof["memory_maxT"], oof["single_mean"]
    )

    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = HERE / "evidence" / f"atbench_sensor_real_{mode}_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(payload.encode()).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n")
    print(f"\nGuardado: {out}\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
