# -*- coding: utf-8 -*-
"""Diagnostico turno-por-turno del sensor tfidf (respuesta a auditoria externa).

Dos preguntas que la auditoria (Sonnet 5, 2026-07-19) exige responder antes de
aceptar el resultado online como limpio:

  P1. FUGA TEMATICA: ¿cuanto del AUROC de trayectoria ya esta disponible en el
      turno 0 (la peticion inicial del usuario), ANTES de que ocurra ninguna
      conducta del agente? Si es alto, el sensor clasifica "tema", no conducta.
  P2. LOCALIZACION: dentro de cada trayectoria insegura, ¿el sensor puntua mas
      alto el turno donde vive el riesgo que sus turnos vecinos? Proxy de
      "turno de riesgo" (ATBench no trae etiqueta por turno):
        a) turno con maxima superposicion lexica (Jaccard sobre palabras de
           contenido) con el campo `reason` (que describe el fallo citando
           herramientas/acciones especificas), y
        b) para risk_source de inyeccion (indirect/tool_description/corrupted/
           direct), el rol esperado del turno de riesgo (environment).

Usa los scores OOF por turno ya sellados en evidence/streaming_ckpt/ (mismo
protocolo 5-fold por trayectoria, seed 42) — cero reentrenamiento, cero fuga
nueva. Etiquetas de veracidad en el JSON de salida.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
from collections import Counter
from datetime import date

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
CKPT = HERE / "evidence" / "streaming_ckpt"

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


def main() -> None:
    rows = [json.loads(line) for line in open(HERE / "data" / "atbench_test.jsonl", encoding="utf-8")]
    data = {}
    for i, row in enumerate(rows):
        contents = row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
        data[i] = {
            "label": int(row["label"]),
            "roles": [m.get("role") for m in contents],
            "texts": [turn_text(m) for m in contents],
            "reason": str(row.get("reason") or ""),
            "risk_source": str(row.get("risk_source") or ""),
        }
    # scores OOF por turno (ya sellados)
    scores = {}
    for f in range(5):
        z = json.loads((CKPT / f"scores_fold{f}.json").read_text(encoding="utf-8"))
        for k, sc in z["scores"].items():
            scores[int(k)] = sc

    idxs = sorted(scores)
    y = np.array([data[i]["label"] for i in idxs])

    # ---------------- P1: fuga tematica (prefijos) ----------------
    p1 = {}
    for K in (1, 2, 3):
        s_pref = [max(scores[i][:K]) for i in idxs]
        p1[f"auroc_solo_primeros_{K}_turnos"] = round(auroc(y, s_pref), 4)
    s_full = [max(scores[i]) for i in idxs]
    p1["auroc_trayectoria_completa_maxscore"] = round(auroc(y, s_full), 4)
    p1["lectura"] = (
        "fraccion del poder discriminativo disponible ANTES de conducta del agente; "
        "alto = fuga tematica domina, bajo = el sensor necesita ver la conducta"
    )

    # ---------------- P2a: localizacion via overlap con reason ----------------
    top1_hits, ranks, diffs, n_eval = 0, [], [], 0
    chance_top1 = []
    for i in idxs:
        d = data[i]
        if d["label"] != 1 or len(d["texts"]) < 3:
            continue
        rw = content_words(d["reason"])
        if not rw:
            continue
        overlaps = []
        for t in d["texts"]:
            tw = content_words(t)
            overlaps.append(len(rw & tw) / max(1, len(rw | tw)))
        proxy = int(np.argmax(overlaps))
        if overlaps[proxy] <= 0.0:
            continue
        n = len(d["texts"])
        s = np.array(scores[i])
        n_eval += 1
        chance_top1.append(1.0 / n)
        if int(np.argmax(s)) == proxy:
            top1_hits += 1
        # rango normalizado del turno proxy segun el sensor (1.0 = el mas alto)
        rank = (np.argsort(np.argsort(s))[proxy] + 1) / n
        ranks.append(rank)
        others = np.delete(s, proxy)
        diffs.append(float(s[proxy] - others.mean()))
    p2a = {
        "n_trayectorias_evaluables": n_eval,
        "top1_acierto_sensor": round(top1_hits / n_eval, 4),
        "top1_azar_esperado": round(float(np.mean(chance_top1)), 4),
        "rango_normalizado_medio_turno_riesgo": round(float(np.mean(ranks)), 4),
        "rango_esperado_azar": 0.5,
        "delta_score_turnoriesgo_vs_resto_medio": round(float(np.mean(diffs)), 4),
        "pct_trayectorias_con_delta_positivo": round(float(np.mean([d > 0 for d in diffs])), 4),
        "nota": "proxy de turno de riesgo = max Jaccard con `reason`; imperfecto pero "
        "independiente del sensor",
    }

    # ---------------- P2b: rol esperado en inyecciones ----------------
    injection_sources = {
        "indirect_prompt_injection", "tool_description_injection",
        "corrupted_tool_feedback", "malicious_tool_execution",
    }
    hits_role, base_rate, n_inj = 0, [], 0
    for i in idxs:
        d = data[i]
        if d["label"] != 1 or d["risk_source"] not in injection_sources:
            continue
        env_turns = [k for k, r in enumerate(d["roles"]) if r == "environment"]
        if not env_turns:
            continue
        n_inj += 1
        s = np.array(scores[i])
        base_rate.append(len(env_turns) / len(d["roles"]))
        if int(np.argmax(s)) in env_turns:
            hits_role += 1
    p2b = {
        "n_trayectorias_inyeccion": n_inj,
        "pct_argmax_sensor_en_turno_environment": round(hits_role / n_inj, 4) if n_inj else None,
        "pct_esperado_por_azar(base_rate_env)": round(float(np.mean(base_rate)), 4) if base_rate else None,
    }

    res = {
        "fecha": str(date.today()),
        "contexto": "auditoria Sonnet 5 (2026-07-19): supervision debil propaga label de "
        "trayectoria a turnos benignos; ¿el sensor localiza el riesgo o clasifica el tema?",
        "P1_fuga_tematica": p1,
        "P2a_localizacion_reason": p2a,
        "P2b_localizacion_rol_inyecciones": p2b,
        "etiqueta_veracidad": "empirico con limites (proxy de turno de riesgo imperfecto; "
        "scores OOF sellados previos, sin reentrenamiento)",
    }
    print(json.dumps(res, indent=2, ensure_ascii=False))
    out = HERE / "evidence" / f"exp_diagnostico_turno_{date.today().strftime('%Y%m%d')}.json"
    payload = json.dumps(res, indent=2, ensure_ascii=False)
    out.write_text(payload, encoding="utf-8")
    sha = hashlib.sha256(payload.encode()).hexdigest()
    out.with_suffix(".sha256").write_text(sha + "\n")
    print(f"\nGuardado: {out}\nSHA-256: {sha}")


if __name__ == "__main__":
    main()
