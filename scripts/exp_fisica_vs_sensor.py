# -*- coding: utf-8 -*-
"""Experimento alterno: aislar la FISICA del acumulador termico del SENSOR lexico.

Pregunta central: si toda la matematica (I2t, decaimiento, disparo por
acumulacion) esta bien construida, ¿por que no pasa los benchmarks?

Hipotesis a falsar, por separado:
  H1. La ecuacion del acumulador NO implementa lo que dice implementar (bug).
  H2. La fisica implementada NO separa deriva sostenida de picos transitorios
      ni siquiera con señal perfecta (fallo de concepto).
  H3. El sensor (CCA lexico) NO produce señal correlacionada con riesgo real
      sobre texto en ingles (fallo de sensor, no de fisica).
  H4. El pipeline (estructura de trayectoria real de ATBench + acumulador)
      esta roto en algun punto intermedio (fallo de ingenieria).

Experimentos:
  A. Verificacion matematica cerrada de record() contra la recurrencia
     T_t = T_{t-1} * exp(-dt/tau) + max(0, c - theta)^2   (H1)
  B. Separacion pura con señal sintetica de maximo EMPAREJADO entre clases:
     el mejor detector de un turno posible tiene AUROC ~0.5 POR CONSTRUCCION;
     si la memoria separa, la fisica aporta algo real. (H2)
  C. Control de disipacion: misma energia total, eventos espaciados -> no
     debe disparar. (H2)
  D. Control de confound de longitud: trayectoria segura LARGA vs insegura
     CORTA -> la memoria no debe premiar longitud cuando la señal es limpia. (H2)
  E. Diagnostico del sensor CCA sobre las 1000 trayectorias reales de ATBench:
     ¿de donde sale realmente el criticality? (H3)
  F. Oraculo sobre estructura real: longitudes y labels reales de ATBench,
     señal sintetica limpia -> si el AUROC es alto, el pipeline esta sano y
     el cuello de botella es unicamente el sensor. (H4)

No toca core/ de 4r2v6 (solo lectura via FOURR2_REPO_PATH).
Etiquetas de veracidad en el JSON de salida: demostrable / empirico / ND.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import re
import sys
from collections import Counter

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent  # Benchmark2026/


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
for extra in (str(_root), str(_root / "antigravity_wings"), str(_root / "core")):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from antigravity_wings.thermal import ThermalAccumulator, ThermalParams  # noqa: E402
from kernel_1240421 import CCA  # noqa: E402

THETA, TAU, T_TRIP = 0.35, 5.0, 0.30
SEED = 42
rng = np.random.default_rng(SEED)


# ----------------------------------------------------------------------------
def auroc(y_true, y_score) -> float:
    """AUROC via Mann-Whitney con correccion de empates."""
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score, dtype=float)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]))
    ranks = np.empty(len(order), dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    # empates -> rango promedio
    allv = np.concatenate([pos, neg])
    for v in np.unique(allv):
        m = allv == v
        ranks[m] = ranks[m].mean()
    r_pos = ranks[: len(pos)].sum()
    u = r_pos - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


def run_accumulator(crits, dts=None) -> dict:
    """Corre una secuencia por un ThermalAccumulator NUEVO. Devuelve max_T y trip."""
    acc = ThermalAccumulator(
        params=ThermalParams(tau=TAU, T_trip=T_TRIP, theta_ref=THETA)
    )
    t = 0.0
    max_T = 0.0
    tripped, trip_turn = False, None
    for i, c in enumerate(crits):
        if i > 0:
            t += 1.0 if dts is None else float(dts[i - 1])
        req = acc.record(criticality=float(c), t=t, path="x")
        max_T = max(max_T, acc.log[-1].temperature)
        if req is not None and not tripped:
            tripped, trip_turn = True, i
    return {"max_T": max_T, "tripped": tripped, "trip_turn": trip_turn}


results: dict = {"seed": SEED, "params": {"theta": THETA, "tau": TAU, "T_trip": T_TRIP}}

# ============================================================================
# EXP A — Verificacion matematica cerrada (H1)
# ============================================================================
print("=" * 70)
print(
    "EXP A — ¿record() implementa exactamente T_t = T_{t-1}e^(-dt/tau) + max(0,c-theta)^2 ?"
)
max_err = 0.0
trip_semantics_ok = True
for trial in range(200):
    n = int(rng.integers(3, 40))
    crits = rng.uniform(0.0, 1.0, n)
    dts = rng.uniform(0.1, 12.0, n - 1)
    tau_i = float(rng.uniform(0.5, 20.0))
    ttrip_i = float(rng.uniform(0.05, 2.0))
    acc = ThermalAccumulator(
        params=ThermalParams(tau=tau_i, T_trip=ttrip_i, theta_ref=THETA)
    )
    # referencia independiente (recurrencia a mano, con reset tras disparo)
    T_ref = 0.0
    t = 0.0
    for i, c in enumerate(crits):
        if i > 0:
            t += dts[i - 1]
            T_ref *= math.exp(-dts[i - 1] / tau_i)
        e = max(0.0, c - THETA) ** 2
        T_ref += e
        req = acc.record(criticality=float(c), t=t, path="p")
        logged = acc.log[-1].temperature
        max_err = max(max_err, abs(logged - round(T_ref, 6)))
        ref_trip = T_ref >= ttrip_i
        if ref_trip != (req is not None):
            trip_semantics_ok = False
        if ref_trip:
            T_ref = 0.0  # el fusible salta y se resetea, igual que el codigo
exp_a = {
    "max_abs_error_vs_recurrencia": max_err,
    "trip_reset_semantics_ok": trip_semantics_ok,
    "veredicto": "demostrable: la implementacion ES la ecuacion declarada"
    if max_err < 1e-9 and trip_semantics_ok
    else "BUG ENCONTRADO",
}
print(json.dumps(exp_a, indent=2, ensure_ascii=False))
results["exp_A_matematica"] = exp_a

# ============================================================================
# EXP B — Separacion pura con maximo EMPAREJADO (H2)
# ============================================================================
print("=" * 70)
print("EXP B — Deriva sostenida vs pico transitorio, MISMO maximo por construccion")
# Diseño: ambas clases reciben exactamente UN pico ~ U(0.62, 0.70) en un turno
# aleatorio. La clase insegura ademas sostiene una meseta sub-pico
# (N(0.55, 0.03) clip [0.45, 0.60]); la segura esta en calma (N(0.22, 0.05)
# clip [0.05, 0.34], bajo theta). El max por trayectoria es SIEMPRE el pico,
# identicamente distribuido en ambas clases -> el mejor detector de un solo
# turno (umbral sobre el maximo) tiene AUROC ~ 0.5 por construccion.
N_PER, LEN = 400, 12


def make_traj(unsafe: bool, n_turns: int = LEN):
    if unsafe:
        base = np.clip(rng.normal(0.55, 0.03, n_turns), 0.45, 0.60)
    else:
        base = np.clip(rng.normal(0.22, 0.05, n_turns), 0.05, 0.34)
    peak_pos = int(rng.integers(0, n_turns))
    base[peak_pos] = rng.uniform(0.62, 0.70)
    return base


y, s_single, s_mem, trips_u, trips_s = [], [], [], 0, 0
for label in (1, 0):
    for _ in range(N_PER):
        tr = make_traj(unsafe=bool(label))
        r = run_accumulator(tr)
        y.append(label)
        s_single.append(float(tr.max()))  # mejor score de un turno posible
        s_mem.append(r["max_T"])
        if label == 1 and r["tripped"]:
            trips_u += 1
        if label == 0 and r["tripped"]:
            trips_s += 1

exp_b = {
    "n_por_clase": N_PER,
    "auroc_mejor_detector_un_turno(max_crit)": round(auroc(y, s_single), 4),
    "auroc_memoria(max_T)": round(auroc(y, s_mem), 4),
    "trip_rate_unsafe_params_default": round(trips_u / N_PER, 4),
    "trip_rate_safe_params_default": round(trips_s / N_PER, 4),
    "nota": "max emparejado entre clases: un turno no puede separar por construccion",
}
print(json.dumps(exp_b, indent=2, ensure_ascii=False))
results["exp_B_separacion_pura"] = exp_b

# ============================================================================
# EXP C — Control de disipacion (H2)
# ============================================================================
print("=" * 70)
print("EXP C — Misma energia total, eventos espaciados: la disipacion debe proteger")
tr = make_traj(unsafe=True)
r_denso = run_accumulator(tr)  # dt = 1 entre turnos
r_sparse = run_accumulator(tr, dts=[10.0] * (LEN - 1))  # dt = 10
exp_c = {
    "max_T_denso_dt1": round(r_denso["max_T"], 4),
    "max_T_espaciado_dt10": round(r_sparse["max_T"], 4),
    "disparo_denso": r_denso["tripped"],
    "disparo_espaciado": r_sparse["tripped"],
    "veredicto": "demostrable: el decaimiento disipa eventos espaciados"
    if r_sparse["max_T"] < r_denso["max_T"]
    else "ANOMALIA",
}
print(json.dumps(exp_c, indent=2, ensure_ascii=False))
results["exp_C_disipacion"] = exp_c

# ============================================================================
# EXP D — Confound de longitud con señal limpia (H2)
# ============================================================================
print("=" * 70)
print("EXP D — Segura LARGA (30 turnos) vs insegura CORTA (6 turnos)")
y2, s2_mem, s2_len = [], [], []
for _ in range(N_PER):
    tr_u = make_traj(unsafe=True, n_turns=6)
    tr_s = make_traj(unsafe=False, n_turns=30)
    y2 += [1, 0]
    s2_mem += [run_accumulator(tr_u)["max_T"], run_accumulator(tr_s)["max_T"]]
    s2_len += [6, 30]
exp_d = {
    "auroc_memoria": round(auroc(y2, s2_mem), 4),
    "auroc_solo_longitud": round(auroc(y2, s2_len), 4),
    "nota": "si la memoria mantiene AUROC alto con longitudes invertidas, "
    "no esta midiendo longitud cuando la señal es limpia",
}
print(json.dumps(exp_d, indent=2, ensure_ascii=False))
results["exp_D_confound_longitud"] = exp_d

# ============================================================================
# EXP E — Diagnostico del sensor CCA sobre ATBench real (H3)
# ============================================================================
print("=" * 70)
print("EXP E — ¿De donde sale el criticality del CCA sobre texto real en ingles?")
DATA = HERE / "data" / "atbench_test.jsonl"
rows = [json.loads(line) for line in open(DATA, encoding="utf-8")]


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


ACTION_VERBS = ["ejecuta", "borra", "transfiere", "firma", "pago", "desplaza"]
n_turns_tot = 0
hit_kw = 0
hit_only_substring_es = 0  # keyword hit SOLO por subcadena dentro de palabra inglesa
sat_len = 0  # semantic_risk saturado por longitud (>= 80 palabras)
unclassified = 0
substr_words = Counter()
crit_by_label = {0: [], 1: []}
maxcrit_traj, meancrit_traj, ylab, nturns_traj, maxT_traj = [], [], [], [], []

word_re = re.compile(r"[a-z]+")
for row in rows:
    contents = (
        row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
    )
    cca = CCA(session_id=str(row["id"]))
    crits = []
    for m in contents:
        txt = turn_text(m)
        low = txt.lower()
        if m.get("role") == "user":
            tel = cca.observe(user_input=txt, ai_output="")
        else:
            tel = cca.observe(user_input="", ai_output=txt)
        c = float(tel["criticality"])
        crits.append(c)
        n_turns_tot += 1
        crit_by_label[int(row["label"])].append(c)
        kw = any(v in low for v in ACTION_VERBS) or "dinero" in low or "ip" in low
        if kw:
            hit_kw += 1
            # ¿el hit se explica SOLO por subcadenas dentro de palabras inglesas?
            words = word_re.findall(low)
            standalone = False
            culpables = []
            for token in ACTION_VERBS + ["dinero", "ip"]:
                if token in low:
                    for w in words:
                        if token in w:
                            if w == token:
                                standalone = True
                            else:
                                culpables.append(w)
            if not standalone and culpables:
                hit_only_substring_es += 1
                substr_words.update(culpables[:3])
        if len(low.split()) >= 80:
            sat_len += 1
        if tel["cca_class"] == "unclassified":
            unclassified += 1
    r = run_accumulator(crits)
    maxcrit_traj.append(max(crits) if crits else 0.0)
    meancrit_traj.append(float(np.mean(crits)) if crits else 0.0)
    maxT_traj.append(r["max_T"])
    nturns_traj.append(len(crits))
    ylab.append(int(row["label"]))

exp_e = {
    "n_trayectorias": len(rows),
    "n_turnos_totales": n_turns_tot,
    "pct_turnos_keyword_hit": round(100 * hit_kw / n_turns_tot, 2),
    "pct_turnos_hit_SOLO_por_subcadena_en_palabra_inglesa": round(
        100 * hit_only_substring_es / n_turns_tot, 2
    ),
    "palabras_inglesas_que_disparan_keywords_espanolas_top15": substr_words.most_common(
        15
    ),
    "pct_turnos_semantic_risk_saturado_por_longitud": round(
        100 * sat_len / n_turns_tot, 2
    ),
    "pct_turnos_unclassified": round(100 * unclassified / n_turns_tot, 2),
    "criticality_medio_turnos_en_trayectorias_SEGURAS": round(
        float(np.mean(crit_by_label[0])), 4
    ),
    "criticality_medio_turnos_en_trayectorias_INSEGURAS": round(
        float(np.mean(crit_by_label[1])), 4
    ),
    "auroc_max_criticality_un_turno_vs_label": round(auroc(ylab, maxcrit_traj), 4),
    "auroc_mean_criticality_vs_label": round(auroc(ylab, meancrit_traj), 4),
    "auroc_max_T_memoria_vs_label": round(auroc(ylab, maxT_traj), 4),
    "auroc_SOLO_numero_de_turnos_vs_label": round(auroc(ylab, nturns_traj), 4),
    "corr_spearman_maxT_vs_nturnos": None,  # se llena abajo
}


def spearman(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float((ra * rb).mean())


exp_e["corr_spearman_maxT_vs_nturnos"] = round(spearman(maxT_traj, nturns_traj), 4)
print(json.dumps(exp_e, indent=2, ensure_ascii=False))
results["exp_E_diagnostico_sensor"] = exp_e

# ============================================================================
# EXP F — Oraculo sobre la estructura REAL de ATBench (H4)
# ============================================================================
print("=" * 70)
print("EXP F — Longitudes y labels reales de ATBench + señal sintetica limpia")
y3, s3_single, s3_mem = [], [], []
for row in rows:
    contents = (
        row["contents"][0] if isinstance(row["contents"][0], list) else row["contents"]
    )
    n = max(2, len(contents))
    label = int(row["label"])
    if label == 1:
        plant = int(rng.integers(0, max(1, n - 1)))  # turno donde se planta el riesgo
        base = np.clip(rng.normal(0.22, 0.05, n), 0.05, 0.34)
        base[plant:] = np.clip(rng.normal(0.55, 0.03, n - plant), 0.45, 0.60)
    else:
        base = np.clip(rng.normal(0.22, 0.05, n), 0.05, 0.34)
    peak_pos = int(rng.integers(0, n))
    base[peak_pos] = rng.uniform(0.62, 0.70)  # mismo pico en ambas clases
    r = run_accumulator(base)
    y3.append(label)
    s3_single.append(float(base.max()))
    s3_mem.append(r["max_T"])
exp_f = {
    "n": len(y3),
    "auroc_mejor_un_turno(max_crit)": round(auroc(y3, s3_single), 4),
    "auroc_memoria(max_T)": round(auroc(y3, s3_mem), 4),
    "nota": "misma estructura real (longitudes, balance de labels) que la corrida "
    "que dio AUROC 0.58 con sensor CCA; unico cambio: señal de criticidad limpia",
}
print(json.dumps(exp_f, indent=2, ensure_ascii=False))
results["exp_F_oraculo_estructura_real"] = exp_f

# ============================================================================
out = HERE / "evidence" / "exp_fisica_vs_sensor_20260718.json"
payload = json.dumps(results, indent=2, ensure_ascii=False)
out.write_bytes(payload.encode("utf-8"))  # binario: evita CRLF de Windows
sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()
(HERE / "evidence" / "exp_fisica_vs_sensor_20260718.sha256").write_text(sha + "\n")
print("=" * 70)
print(f"Guardado: {out}\nSHA-256: {sha}")
