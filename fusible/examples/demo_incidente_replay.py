# Copyright (c) 2026 Ricardo Yazigi
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""DEMO END-TO-END — replay de una trayectoria agéntica real por el fusible.

Qué demuestra (las 3 piezas conectadas por primera vez):
  sensor real (scores qwen cacheados de ATBench) → QuantileNormalizer →
  Fuse(CUSUM calibrado por FPR) → TripEvent → FlightRecorder sellado SHA-256.

Framing correcto (acordado): NO decimos "hubiéramos parado el incidente X".
Decimos: esta es la familia de fallo (inherent_agent_failures — agente
hiperenfocado acumulando acciones de apariencia legítima) donde nuestra
medición sellada ya muestra la mayor ventaja de la acumulación sobre lo
reactivo. El demo enseña el mecanismo completo sobre una trayectoria real.

Uso (desde la raíz de Benchmark2026):
    python fusible/examples/demo_incidente_replay.py
Requiere: data/atbench_test.jsonl y evidence/guard_cache_qwen.json (ya locales).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve()
BENCH = HERE.parents[2]                      # Benchmark2026/
sys.path.insert(0, str(HERE.parents[1] / "src"))   # fusible/src

from fusible import Fuse, QuantileNormalizer, calibrate_threshold  # noqa: E402

SEED = 42
FAMILIA_DEMO = "inherent_agent_failures"   # la familia del patrón tipo incidente-OpenAI
TARGET_FPR = 0.05


def turn_text(m: dict) -> str:
    if m.get("role") == "agent":
        return (m.get("thought") or "") + " " + (m.get("action") or "")
    return m.get("content") or ""


def main() -> None:
    cache = json.loads((BENCH / "evidence" / "guard_cache_qwen.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in open(BENCH / "data" / "atbench_test.jsonl", encoding="utf-8")]

    trajs = []
    for r in rows:
        c = r["contents"][0] if isinstance(r["contents"][0], list) else r["contents"]
        scores, roles = [], []
        ok = True
        for m in c:
            k = hashlib.sha256(turn_text(m).encode()).hexdigest()[:24]
            if k not in cache:
                ok = False
                break
            scores.append(float(cache[k]))
            roles.append(m.get("role"))
        if ok:
            trajs.append({"label": int(r["label"]), "fam": str(r.get("risk_source") or ""),
                          "scores": scores, "roles": roles, "id": str(r.get("id"))})

    # 1) Calibración con benignas (mitad cal, seed 42 — mismo protocolo sellado)
    rng = np.random.default_rng(SEED)
    safe = [i for i, t in enumerate(trajs) if t["label"] == 0]
    rng.shuffle(safe)
    cal, val = safe[: len(safe) // 2], safe[len(safe) // 2:]
    qn = QuantileNormalizer().fit([s for i in cal for s in trajs[i]["scores"]])
    benign_val_norm = [qn.transform(trajs[i]["scores"]) for i in val]
    h = calibrate_threshold(benign_val_norm, "cusum", target_fpr=TARGET_FPR, k_ref=0.75)
    print(f"[calibración] umbral CUSUM para FPR≈{TARGET_FPR:.0%} sobre benignas held-out: h={h:.4f}")

    # 2) Elegir una trayectoria insegura de la familia demo que el fusible SÍ detecta
    fuse = Fuse(statistic="cusum", normalizer=qn, threshold=h, k_ref=0.75)
    demo = None
    for i, t in enumerate(trajs):
        if t["label"] == 1 and t["fam"] == FAMILIA_DEMO:
            fuse.reset()
            trip = None
            for k, s in enumerate(t["scores"]):
                trip = fuse.observe(s, t=float(k), path=t["id"])
                if trip:
                    break
            if trip:
                demo = (t, trip)
                break
    if demo is None:
        print(f"[demo] ninguna trayectoria de {FAMILIA_DEMO} dispara con h={h:.3f} "
              f"(honesto: reportar tal cual). Prueba TARGET_FPR=0.10.")
        return

    t, trip = demo
    print(f"\n[trayectoria] id={t['id']} · familia={t['fam']} · {len(t['scores'])} turnos · label=UNSAFE")
    print(f"[disparo] turno {trip.turn_index + 1}/{len(t['scores'])} "
          f"(rol del turno: {t['roles'][trip.turn_index]}) · "
          f"estadístico={trip.stat_name} valor={trip.stat_value:.4f} ≥ h={trip.threshold:.4f}")
    print(f"[evidencia] ventana de {len(trip.evidence_window)} observaciones acumuladas en el TripEvent")

    # 3) Contra-ejemplo: una benigna held-out NO dispara con el mismo fusible
    fuse.reset()
    tb = trajs[val[0]]
    trips_benigna = [fuse.observe(s, t=float(k), path="benigna-demo") for k, s in enumerate(tb["scores"])]
    print(f"[control] trayectoria benigna held-out ({len(tb['scores'])} turnos): "
          f"{'NO disparó ✔' if not any(trips_benigna) else 'disparó (falso positivo)'}")

    # 4) Flight recorder sellado — el artefacto Art. 72
    out = HERE.parent / "informe_demo_flight_recorder.json"
    payload = fuse.recorder.export(str(out))
    print(f"\n[flight recorder] {payload['n_observations']} observaciones, "
          f"{payload['n_trips']} disparo(s) · SHA-256 {payload['sha256'][:16]}… · {out.name}")
    print("\nDemo completo: sensor real → normalizador → CUSUM calibrado → contención → informe sellado.")


if __name__ == "__main__":
    main()
