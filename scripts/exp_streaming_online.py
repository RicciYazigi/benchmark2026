# -*- coding: utf-8 -*-
"""Regimen ONLINE: deteccion en vivo, turno a turno — el terreno del fusible.

Motivacion (RESULTADOS_ATBENCH_SENSOR_REAL.md): en retrospectiva la media
simple gana, pero la media de trayectoria completa NO existe en produccion:
un guardrail decide EN VIVO, en cada turno, sin conocer el futuro. Aqui se
compara el acumulador termico contra los rivales online justos:

  runmax  : max score visto hasta el turno k (detector reactivo)
  runmean : media acumulada hasta k (agregador trivial online)
  ewma    : media movil exponencial (rival online estandar, alpha=0.3)
  thermal : temperatura I2t (tau=5 y tau=2, theta p90-safe del train del fold)

Metricas:
  1. AUROC de trayectoria usando max_k stat_k (equivale a "¿disparo alguna
     vez?" barriendo el umbral) — todos online, comparacion justa.
  2. Deteccion temprana a FPR igualado (5% y 10%): TPR y fraccion media de
     la trayectoria transcurrida al detectar (lead time). Detectar igual pero
     ANTES = valor de producto real (menos daño ya ejecutado).

Mismo protocolo OOF de siempre (5-fold por trayectoria, seed 42), scores del
sensor tfidf-logreg-v1. Checkpoints por fold, reanudable. core/ intacto.
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
CKPT = HERE / "evidence" / "streaming_ckpt"
SEED = 42
N_FOLDS = 5
ALPHA_EWMA = 0.3
TAUS = [5.0, 2.0]
FPR_TARGETS = [0.05, 0.10]


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


for extra in (str(_resolve_4r2() / "antigravity_wings"), str(HERE / "src")):
    if extra not in sys.path:
        sys.path.insert(0, extra)


def auroc(y, s) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y), np.asarray(s, dtype=float)))


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def stage1_scores() -> bool:
    """Guarda scores OOF por turno, un checkpoint por fold. True si completo."""
    from sklearn.model_selection import StratifiedKFold

    from aegisbench.sensors import TfidfTurnSensor

    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]
    trajs = []
    for row in rows:
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        trajs.append({"label": int(row["label"]), "turns": [turn_text(m) for m in contents]})
    labels = np.array([t["label"] for t in trajs])
    CKPT.mkdir(exist_ok=True)
    skf = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=SEED)
    done = True
    for fold, (tr_idx, te_idx) in enumerate(skf.split(np.zeros(len(trajs)), labels)):
        f = CKPT / f"scores_fold{fold}.json"
        if f.exists():
            continue
        sensor = TfidfTurnSensor(seed=SEED)
        tr_texts, tr_labels = [], []
        for i in tr_idx:
            tr_texts.extend(trajs[i]["turns"])
            tr_labels.extend([trajs[i]["label"]] * len(trajs[i]["turns"]))
        sensor.fit(tr_texts, tr_labels)
        safe_scores = [s for i in tr_idx if trajs[i]["label"] == 0
                       for s in sensor.score(trajs[i]["turns"])]
        theta_f = float(np.percentile(safe_scores, 90))
        payload = {"theta": theta_f, "scores": {}, "labels": {}}
        for i in te_idx:
            payload["scores"][str(i)] = sensor.score(trajs[i]["turns"])
            payload["labels"][str(i)] = trajs[i]["label"]
        f.write_text(json.dumps(payload), encoding="utf-8")
        print(f"fold {fold} scores listos (theta={theta_f:.4f})", flush=True)
        done = False
    return done or all((CKPT / f"scores_fold{f}.json").exists() for f in range(N_FOLDS))


def series_stats(scores, theta, tau) -> dict:
    """Series online por turno de cada estadistico."""
    n = len(scores)
    runmax, runmean, ewma, thermal = [], [], [], []
    mx, sm, ew, T = -1e9, 0.0, scores[0] if n else 0.0, 0.0
    for k, s in enumerate(scores):
        mx = max(mx, s)
        sm += s
        ew = s if k == 0 else ALPHA_EWMA * s + (1 - ALPHA_EWMA) * ew
        if k > 0:
            T *= math.exp(-1.0 / tau)
        T += max(0.0, s - theta) ** 2
        runmax.append(mx)
        runmean.append(sm / (k + 1))
        ewma.append(ew)
        thermal.append(T)
    return {"runmax": runmax, "runmean": runmean, "ewma": ewma, "thermal": thermal}


def main() -> None:
    if not stage1_scores():
        print("checkpoints incompletos; relanzar", flush=True)
        return
    # cargar todo
    all_series: dict = {}   # idx -> {"label", stats por metodo}
    methods = ["runmax", "runmean", "ewma"] + [f"thermal_tau{t:g}" for t in TAUS]
    for fold in range(N_FOLDS):
        z = json.loads((CKPT / f"scores_fold{fold}.json").read_text(encoding="utf-8"))
        theta = z["theta"]
        for k, scores in z["scores"].items():
            st5 = series_stats(scores, theta, TAUS[0])
            st2 = series_stats(scores, theta, TAUS[1])
            all_series[int(k)] = {
                "label": z["labels"][k],
                "runmax": st5["runmax"],
                "runmean": st5["runmean"],
                "ewma": st5["ewma"],
                f"thermal_tau{TAUS[0]:g}": st5["thermal"],
                f"thermal_tau{TAUS[1]:g}": st2["thermal"],
            }
    idxs = sorted(all_series)
    y = np.array([all_series[i]["label"] for i in idxs])

    res = {
        "fecha": str(date.today()),
        "protocolo": "OOF 5-fold por trayectoria, seed 42, sensor tfidf-logreg-v1; "
        "estadisticos 100% online (sin conocer el futuro); "
        f"ewma alpha={ALPHA_EWMA}; theta=p90 turnos seguros train por fold",
        "n": len(idxs),
        "auroc_online": {},
        "deteccion_temprana": {},
        "etiqueta_veracidad": "empirico con limites (sensor en dominio; umbral de "
        "operacion elegido sobre el pool global de seguras — igual para todos los metodos)",
    }
    peak = {m: np.array([max(all_series[i][m]) for i in idxs]) for m in methods}
    for m in methods:
        res["auroc_online"][m] = round(auroc(y, peak[m]), 4)

    for fpr in FPR_TARGETS:
        block = {}
        safe_peaks = {m: np.sort(peak[m][y == 0]) for m in methods}
        for m in methods:
            th = float(np.quantile(safe_peaks[m], 1.0 - fpr, method="higher"))
            det_fracs, det_turns, tp = [], [], 0
            for i in idxs:
                if all_series[i]["label"] != 1:
                    continue
                series = all_series[i][m]
                hit = next((k for k, v in enumerate(series) if v >= th), None)
                if hit is not None:
                    tp += 1
                    det_turns.append(hit)
                    det_fracs.append((hit + 1) / len(series))
            n_unsafe = int(y.sum())
            block[m] = {
                "umbral": round(th, 4),
                "tpr": round(tp / n_unsafe, 4),
                "frac_trayectoria_al_detectar_media": round(float(np.mean(det_fracs)), 4) if det_fracs else None,
                "turno_medio_deteccion": round(float(np.mean(det_turns)), 2) if det_turns else None,
            }
        res["deteccion_temprana"][f"fpr_{int(fpr*100)}pct"] = block

    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = HERE / "evidence" / f"exp_streaming_online_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(payload.encode()).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n")
    print(f"\nGuardado: {out}\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
