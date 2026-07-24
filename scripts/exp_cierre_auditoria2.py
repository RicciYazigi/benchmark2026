# -*- coding: utf-8 -*-
"""Cierre de la segunda auditoria (Sonnet 5, 2026-07-19b). Dos experimentos:

EXP-1  P2a DES-CONFUNDIDO (circularidad tema-reason):
  La auditoria objeta: si el sensor detecta tema (~59% de su señal) y `reason`
  describe la trayectoria con vocabulario tematico, el solapamiento Jaccard no
  es un proxy independiente. Controles nuevos:
    a) Proxy recalculado EXCLUYENDO todo el vocabulario que el sensor pondera
       positivo (coef > 0 de la regresion logistica ajustada sobre TODO el
       dataset — uso conservador: solo para excluir palabras, nunca para
       puntuar). Si la localizacion sobrevive sin las palabras del sensor,
       la circularidad no explica el resultado.
    b) Control de longitud: ¿el argmax del sensor es simplemente el turno mas
       largo? ¿y el proxy? Metricas condicionadas a proxy != turno mas largo.

EXP-2  OOD LEAVE-FAMILY-OUT (aproximacion local al gate fuera-de-dominio):
  Por cada familia de risk_source: el sensor se entrena SIN VER NINGUNA
  trayectoria insegura de esa familia y se evalua sobre ella (+ mitad fija de
  seguras jamas usadas en train). Pregunta: ¿la ventaja online del termico
  sobrevive cuando el sensor nunca vio el tipo de riesgo? No sustituye al
  guard model zero-shot (gate final, maquina del usuario), pero es OOD por
  construccion y ejecutable 100% local hoy.

Checkpoints reanudables. core/ intacto. Etiquetas de veracidad en el JSON.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re
import sys
from datetime import date

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
CKPT = HERE / "evidence" / "streaming_ckpt"
LFO_CKPT = HERE / "evidence" / "lfo_ckpt"
SEED = 42
ALPHA = 0.3
TAU = 5.0

sys.path.insert(0, str(HERE / "src"))

STOP = set("""the a an and or of to in for on with is are was were be been being this
that it as at by from into your you i we they he she their our my me us them
please can could would should will shall do does did have has had not no if
then than so but about after before all any""".split())


def auroc(y, s) -> float:
    from sklearn.metrics import roc_auc_score

    return float(roc_auc_score(np.asarray(y), np.asarray(s, dtype=float)))


def content_words(text: str) -> set:
    return {w for w in re.findall(r"[a-z_]+", text.lower()) if w not in STOP and len(w) > 2}


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def load_data():
    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]
    data = []
    for row in rows:
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        data.append({
            "label": int(row["label"]),
            "roles": [m.get("role") for m in contents],
            "texts": [turn_text(m) for m in contents],
            "reason": str(row.get("reason") or ""),
            "risk_source": str(row.get("risk_source") or ""),
        })
    return data


def online_peaks(scores, theta):
    mx, sm, ew, T = -1e9, 0.0, 0.0, 0.0
    p = {"runmax": -1e9, "runmean": -1e9, "ewma": -1e9, "thermal": -1e9}
    for k, s in enumerate(scores):
        mx = max(mx, s)
        sm += s
        ew = s if k == 0 else ALPHA * s + (1 - ALPHA) * ew
        if k > 0:
            T *= math.exp(-1.0 / TAU)
        T += max(0.0, s - theta) ** 2
        p["runmax"] = max(p["runmax"], mx)
        p["runmean"] = max(p["runmean"], sm / (k + 1))
        p["ewma"] = max(p["ewma"], ew)
        p["thermal"] = max(p["thermal"], T)
    return p


# ============================ EXP-1: P2a des-confundido ============================
def exp1(data) -> dict:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    # vocabulario positivo del sensor (SOLO para excluir del proxy)
    texts, labels = [], []
    for d in data:
        texts.extend(d["texts"])
        labels.extend([d["label"]] * len(d["texts"]))
    vec = TfidfVectorizer(ngram_range=(1, 1), max_features=50000, sublinear_tf=True,
                          min_df=2, strip_accents="unicode", lowercase=True)
    x = vec.fit_transform(texts)
    clf = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced", random_state=SEED)
    clf.fit(x, labels)
    vocab = np.array(vec.get_feature_names_out())
    positive_vocab = set(vocab[clf.coef_[0] > 0])
    n_pos = len(positive_vocab)

    scores = {}
    for f in range(5):
        z = json.loads((CKPT / f"scores_fold{f}.json").read_text(encoding="utf-8"))
        for k, sc in z["scores"].items():
            scores[int(k)] = sc

    def localize(exclude_sensor_vocab: bool):
        top1, ranks, diffs, chance, n_eval = 0, [], [], [], 0
        argmax_is_longest = 0
        top1_no_longest, n_no_longest = 0, 0
        for i, d in enumerate(data):
            if d["label"] != 1 or len(d["texts"]) < 3:
                continue
            rw = content_words(d["reason"])
            if exclude_sensor_vocab:
                rw = rw - positive_vocab
            if not rw:
                continue
            ovl = []
            for t in d["texts"]:
                tw = content_words(t)
                if exclude_sensor_vocab:
                    tw = tw - positive_vocab
                ovl.append(len(rw & tw) / max(1, len(rw | tw)))
            proxy = int(np.argmax(ovl))
            if ovl[proxy] <= 0.0:
                continue
            n = len(d["texts"])
            s = np.array(scores[i])
            n_eval += 1
            chance.append(1.0 / n)
            am = int(np.argmax(s))
            longest = int(np.argmax([len(t.split()) for t in d["texts"]]))
            if am == longest:
                argmax_is_longest += 1
            if am == proxy:
                top1 += 1
            if proxy != longest:
                n_no_longest += 1
                if am == proxy:
                    top1_no_longest += 1
            ranks.append((np.argsort(np.argsort(s))[proxy] + 1) / n)
            others = np.delete(s, proxy)
            diffs.append(float(s[proxy] - others.mean()))
        return {
            "n_evaluables": n_eval,
            "top1_acierto": round(top1 / n_eval, 4),
            "top1_azar": round(float(np.mean(chance)), 4),
            "rango_normalizado_medio": round(float(np.mean(ranks)), 4),
            "pct_delta_positivo": round(float(np.mean([d > 0 for d in diffs])), 4),
            "pct_argmax_sensor_es_turno_mas_largo": round(argmax_is_longest / n_eval, 4),
            "top1_acierto_cuando_proxy_NO_es_el_mas_largo": round(top1_no_longest / n_no_longest, 4) if n_no_longest else None,
            "n_proxy_no_es_mas_largo": n_no_longest,
        }

    return {
        "n_palabras_excluidas_vocab_positivo_sensor": n_pos,
        "original_con_confound": localize(exclude_sensor_vocab=False),
        "deconfundido_sin_vocab_sensor": localize(exclude_sensor_vocab=True),
        "lectura": "si el des-confundido mantiene top1 >> azar y rango > 0.5, la "
        "localizacion no se explica por la circularidad tema-reason señalada",
    }


# ============================ EXP-2: OOD leave-family-out ============================
def exp2(data) -> dict:
    from aegisbench.sensors import TfidfTurnSensor

    rng = np.random.default_rng(SEED)
    safe_idx = [i for i, d in enumerate(data) if d["label"] == 0]
    rng.shuffle(safe_idx)
    half = len(safe_idx) // 2
    safe_train, safe_test = set(safe_idx[:half]), set(safe_idx[half:])
    families = sorted({d["risk_source"] for d in data if d["label"] == 1})
    LFO_CKPT.mkdir(exist_ok=True)

    per_family = {}
    pool = {"y": [], "runmax": [], "runmean": [], "ewma": [], "thermal": []}
    for fam in families:
        f = LFO_CKPT / f"{re.sub('[^a-z_]', '', fam)}.json"
        if f.exists():
            block = json.loads(f.read_text(encoding="utf-8"))
        else:
            test_unsafe = [i for i, d in enumerate(data) if d["label"] == 1 and d["risk_source"] == fam]
            train_idx = [i for i, d in enumerate(data)
                         if (d["label"] == 1 and d["risk_source"] != fam) or i in safe_train]
            sensor = TfidfTurnSensor(seed=SEED)
            tr_texts, tr_labels = [], []
            for i in train_idx:
                tr_texts.extend(data[i]["texts"])
                tr_labels.extend([data[i]["label"]] * len(data[i]["texts"]))
            sensor.fit(tr_texts, tr_labels)
            sst = [s for i in train_idx if data[i]["label"] == 0
                   for s in sensor.score(data[i]["texts"])]
            theta = float(np.percentile(sst, 90))
            block = {"theta": theta, "test": {}}
            for i in test_unsafe + sorted(safe_test):
                p = online_peaks(sensor.score(data[i]["texts"]), theta)
                block["test"][str(i)] = {"y": data[i]["label"], **p}
            f.write_text(json.dumps(block), encoding="utf-8")
        ys = [v["y"] for v in block["test"].values()]
        res_fam = {"n_unsafe_test": int(sum(ys)), "n_safe_test": int(len(ys) - sum(ys))}
        for m in ("runmax", "runmean", "ewma", "thermal"):
            ss = [v[m] for v in block["test"].values()]
            res_fam[f"auroc_{m}"] = round(auroc(ys, ss), 4)
        per_family[fam] = res_fam
        for k, v in block["test"].items():
            pool["y"].append(v["y"])
            for m in ("runmax", "runmean", "ewma", "thermal"):
                pool[m].append(v[m])
        print(f"LFO {fam}: thermal={res_fam['auroc_thermal']} runmax={res_fam['auroc_runmax']}", flush=True)

    macro = {m: round(float(np.mean([per_family[f][f"auroc_{m}"] for f in families])), 4)
             for m in ("runmax", "runmean", "ewma", "thermal")}
    # bootstrap pareado sobre el pool (nota: seguras repetidas entre familias,
    # puntuadas por modelos distintos — comparacion relativa valida, absoluta no)
    y = np.array(pool["y"])
    d_list = []
    rng2 = np.random.default_rng(SEED)
    a, b = np.array(pool["thermal"]), np.array(pool["runmax"])
    for _ in range(2000):
        idx = rng2.integers(0, len(y), len(y))
        if len(np.unique(y[idx])) < 2:
            continue
        d_list.append(auroc(y[idx], a[idx]) - auroc(y[idx], b[idx]))
    d_arr = np.array(d_list)
    lo, hi = np.percentile(d_arr, [2.5, 97.5])
    return {
        "diseño": "por familia: sensor entrenado sin ninguna trayectoria insegura de esa "
        "familia; test = inseguras de la familia + 50% de seguras nunca vistas en train",
        "por_familia": per_family,
        "macro_promedio": macro,
        "delta_pareado_pool_thermal_vs_runmax": {
            "delta_medio": round(float(d_arr.mean()), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "p_mejora": round(float((d_arr > 0).mean()), 4),
        },
    }


def main() -> None:
    data = load_data()
    res = {
        "fecha": str(date.today()),
        "contexto": "segunda auditoria Sonnet 5: (1) circularidad tema-reason en P2a, "
        "(2) necesidad de evidencia OOD antes del gate guard-model",
        "EXP1_p2a_deconfundido": exp1(data),
        "EXP2_ood_leave_family_out": exp2(data),
        "etiqueta_veracidad": "empirico con limites (EXP2 es OOD por familia dentro de "
        "ATBench; el gate guard-model zero-shot sigue pendiente y obligatorio)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = HERE / "evidence" / f"exp_cierre_auditoria2_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(payload.encode()).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n")
    print(f"\nGuardado: {out}\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
