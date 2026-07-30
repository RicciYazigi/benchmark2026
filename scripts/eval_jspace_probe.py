# Copyright (c) 2026 Ricardo Yazigi
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""FASE 4 — J-SPACE v0: probe lineal sobre activaciones internas como sensor.

La hipótesis de Richie con nombre técnico: antes de las palabras hay señal.
Sensor = estados ocultos (última capa, mean-pooled) de un modelo abierto
pequeño sobre cada turno; probe logístico entrenado con el MISMO protocolo
sin fugas de siempre (OOF 5-fold POR TRAYECTORIA, supervisión débil); encima,
los mismos agregadores online (runmax/CUSUM/térmico/EWMA normalizados).

HIPÓTESIS PRE-REGISTRADAS (no mover tras ver datos):
  J1: el probe latente supera al tfidf en AUROC de trayectoria (más señal
      que el léxico de superficie).
  J2: la ventaja de la acumulación (CUSUM/térmico vs runmax) se mantiene o
      crece con el sensor latente.
  J3 (la del origen): en las familias de inyección environment donde el
      sensor textual fue CIEGO al turno culpable (28.8% vs 34.6% azar,
      exp_diagnostico_turno), el probe latente localiza MEJOR que azar.
ADVERTENCIA HONESTA: las activaciones tienen sus propios confounds (longitud,
sorpresa, tema). Mismo rigor: OOF, por familia, bootstrap por clúster, IC.

Requisitos (máquina de Richie): pip install torch transformers
Modelo por defecto: Qwen/Qwen2.5-0.5B (CPU-viable, ~1GB). Override: env JSPACE_MODEL.
Embeddings cacheados en evidence/jspace_embeddings_<modelo>.npz (reanudable).

Uso:  python scripts/eval_jspace_probe.py            # extrae + evalúa
      python scripts/eval_jspace_probe.py --eval-only  # solo evalúa desde cache
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
MODEL = os.environ.get("JSPACE_MODEL", "Qwen/Qwen2.5-0.5B")
TAU = 5.0
ALPHA = 0.3
N_BOOT = int(os.environ.get("N_BOOT", "1000"))
MAX_TOKENS_TURN = 512
BATCH = int(os.environ.get("JSPACE_BATCH", "16"))
EMB_PATH = HERE / "evidence" / f"jspace_embeddings_{MODEL.replace('/', '_')}.npz"


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def load_trajs():
    rows = [
        json.loads(line)
        for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")
    ]
    trajs = []
    for r in rows:
        c = r["contents"][0] if isinstance(r["contents"][0], list) else r["contents"]
        trajs.append(
            {
                "label": int(r["label"]),
                "fam": str(r.get("risk_source") or ""),
                "roles": [m.get("role") for m in c],
                "texts": [turn_text(m) for m in c],
                "reason": str(r.get("reason") or ""),
            }
        )
    return trajs


# ---------------------------------------------------------------------------
def extract_embeddings(trajs) -> None:
    """Extrae hidden states (última capa, mean-pool) por turno. Checkpoint incremental."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    done = {}
    if EMB_PATH.exists():
        z = np.load(EMB_PATH, allow_pickle=True)
        done = {k: z[k] for k in z.files}
        print(f"[cache] {len(done)} turnos ya extraídos", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL, torch_dtype=torch.float32)
    model.eval()

    pending = []
    for i, t in enumerate(trajs):
        for j, txt in enumerate(t["texts"]):
            key = f"e_{i}_{j}"
            if key not in done:
                pending.append((key, txt))
    print(f"[extract] {len(pending)} turnos pendientes con {MODEL}", flush=True)

    with torch.no_grad():
        for b in range(0, len(pending), BATCH):
            batch = pending[b : b + BATCH]
            enc = tok(
                [x[1][:4000] for x in batch],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=MAX_TOKENS_TURN,
            )
            out = model(**enc)
            hs = out.last_hidden_state  # (B, T, H)
            mask = enc["attention_mask"].unsqueeze(-1)  # (B, T, 1)
            pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1)
            for (key, _), vec in zip(batch, pooled):
                done[key] = vec.float().numpy()
            if (b // BATCH) % 20 == 0:
                np.savez_compressed(EMB_PATH, **done)
                print(
                    f"[extract] {b + len(batch)}/{len(pending)} (checkpoint)",
                    flush=True,
                )
    np.savez_compressed(EMB_PATH, **done)
    print(f"[extract] completo: {len(done)} embeddings → {EMB_PATH.name}", flush=True)


# ---------------------------------------------------------------------------
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


def online_peaks(scores, theta, k_ref):
    mx, sm, ew, S, T = -1e9, 0.0, 0.0, 0.0, 0.0
    p = {}
    for k, s in enumerate(scores):
        mx = max(mx, s)
        sm += s
        ew = s if k == 0 else ALPHA * s + (1 - ALPHA) * ew
        S = max(0.0, S + (s - k_ref))
        if k > 0:
            T *= math.exp(-1.0 / TAU)
        T += max(0.0, s - theta) ** 2
        for name, v in (
            ("runmax", mx),
            ("runmean", sm / (k + 1)),
            ("ewma", ew),
            ("cusum", S),
            ("thermal", T),
        ):
            p[name] = max(p.get(name, -1e9), v)
    return p


def evaluate(trajs) -> None:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold
    from sklearn.preprocessing import StandardScaler

    from aegisbench.sensors.normalize import QuantileNormalizer

    z = np.load(EMB_PATH, allow_pickle=True)
    emb = {k: z[k] for k in z.files}
    labels = np.array([t["label"] for t in trajs])
    rng = np.random.default_rng(SEED)

    # OOF 5-fold por trayectoria: probe logístico con supervisión débil
    oof_scores = {}  # (i,j) -> score probe
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    for fold, (tr, te) in enumerate(skf.split(np.zeros(len(trajs)), labels)):
        Xtr, ytr = [], []
        for i in tr:
            for j in range(len(trajs[i]["texts"])):
                Xtr.append(emb[f"e_{i}_{j}"])
                ytr.append(trajs[i]["label"])
        sc = StandardScaler().fit(Xtr)
        clf = LogisticRegression(
            max_iter=3000, C=1.0, class_weight="balanced", random_state=SEED
        ).fit(sc.transform(Xtr), ytr)
        for i in te:
            X = sc.transform([emb[f"e_{i}_{j}"] for j in range(len(trajs[i]["texts"]))])
            for j, p in enumerate(clf.predict_proba(X)[:, 1]):
                oof_scores[(i, j)] = float(p)
        print(f"[probe] fold {fold} listo", flush=True)

    # normalización + agregadores (mismo protocolo sellado)
    safe = [i for i, t in enumerate(trajs) if t["label"] == 0]
    rng.shuffle(safe)
    cal, evl = set(safe[: len(safe) // 2]), sorted(safe[len(safe) // 2 :])
    qn = QuantileNormalizer().fit(
        [oof_scores[(i, j)] for i in cal for j in range(len(trajs[i]["texts"]))]
    )
    series = {
        i: qn.transform([oof_scores[(i, j)] for j in range(len(trajs[i]["texts"]))])
        for i in range(len(trajs))
    }
    cal_n = [s for i in cal for s in series[i]]
    theta, k_ref = float(np.percentile(cal_n, 90)), float(np.percentile(cal_n, 75))

    unsafe = sorted(i for i, t in enumerate(trajs) if t["label"] == 1)
    eval_idx = unsafe + evl
    y = np.array([trajs[i]["label"] for i in eval_idx])
    P = {i: online_peaks(series[i], theta, k_ref) for i in eval_idx}
    methods = ["runmax", "runmean", "ewma", "cusum", "thermal"]
    auroc = {
        m: round(float(roc_auc_score(y, [P[i][m] for i in eval_idx])), 4)
        for m in methods
    }

    def boot_delta(a_m, b_m):
        a = np.array([P[i][a_m] for i in eval_idx])
        b = np.array([P[i][b_m] for i in eval_idx])
        ds = []
        for _ in range(N_BOOT):
            idx = rng.integers(0, len(y), len(y))
            if len(np.unique(y[idx])) < 2:
                continue
            ds.append(
                float(roc_auc_score(y[idx], a[idx]) - roc_auc_score(y[idx], b[idx]))
            )
        lo, hi = np.percentile(ds, [2.5, 97.5])
        return {
            "delta_medio": round(float(np.mean(ds)), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_mejora": round(float(np.mean(np.array(ds) > 0)), 4),
        }

    # J3 — localización en inyecciones environment (la pregunta del origen)
    inj = {
        "indirect_prompt_injection",
        "tool_description_injection",
        "corrupted_tool_feedback",
        "malicious_tool_execution",
    }
    hits, base, n_inj = 0, [], 0
    for i in unsafe:
        t = trajs[i]
        if t["fam"] not in inj:
            continue
        env = [k for k, r in enumerate(t["roles"]) if r == "environment"]
        if not env:
            continue
        n_inj += 1
        base.append(len(env) / len(t["roles"]))
        if int(np.argmax(series[i])) in env:
            hits += 1

    # por familia: cusum vs runmax, signos + cluster bootstrap
    fams = sorted({trajs[i]["fam"] for i in unsafe})
    s_eval = {m: np.array([P[i][m] for i in evl]) for m in ("cusum", "runmax")}
    per_fam, wins = {}, 0
    for f in fams:
        uf = [i for i in unsafe if trajs[i]["fam"] == f]
        a = auc_rank(np.array([P[i]["cusum"] for i in uf]), s_eval["cusum"])
        b = auc_rank(np.array([P[i]["runmax"] for i in uf]), s_eval["runmax"])
        per_fam[f] = {
            "cusum": round(a, 4),
            "runmax": round(b, 4),
            "delta": round(a - b, 4),
        }
        wins += a > b
    p_sign = sum(comb(len(fams), k) for k in range(wins, len(fams) + 1)) / 2 ** len(
        fams
    )

    res = {
        "fecha": str(date.today()),
        "modelo": MODEL,
        "protocolo": "hidden states ultima capa mean-pool; probe logistico OOF 5-fold por "
        "trayectoria (supervision debil); normalizacion por cuantiles; agregadores online; "
        f"seed {SEED}; hipotesis J1-J3 pre-registradas en el encabezado de este script",
        "auroc_trayectoria": auroc,
        "deltas": {
            "cusum_vs_runmax": boot_delta("cusum", "runmax"),
            "thermal_vs_runmax": boot_delta("thermal", "runmax"),
        },
        "J3_localizacion_inyecciones_environment": {
            "n": n_inj,
            "pct_argmax_en_environment": round(hits / n_inj, 4) if n_inj else None,
            "azar_base_rate": round(float(np.mean(base)), 4) if base else None,
            "referencia_sensor_textual": {
                "pct": 0.288,
                "azar": 0.346,
                "fuente": "exp_diagnostico_turno_20260719",
            },
        },
        "por_familia_cusum_vs_runmax": per_fam,
        "familias_ganadas": f"{wins}/{len(fams)}",
        "test_signos_p_unilateral": round(p_sign, 5),
        "etiqueta_veracidad": "empirico con limites (probe en-dominio via OOF; activaciones "
        "con confounds propios — longitud/tema; comparar J1 contra el AUROC tfidf sellado 0.876)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = (
        HERE
        / "evidence"
        / f"jspace_probe_{MODEL.replace('/', '_')}_{date.today().strftime('%Y%m%d')}.json"
    )
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    out.with_suffix(".sha256").write_text(
        hashlib.sha256(payload.encode()).hexdigest() + "\n"
    )
    print(f"\nGuardado: {out}\nSHA-256: {hashlib.sha256(payload.encode()).hexdigest()}")


if __name__ == "__main__":
    trajs = load_trajs()
    if "--eval-only" not in sys.argv:
        extract_embeddings(trajs)
    evaluate(trajs)
