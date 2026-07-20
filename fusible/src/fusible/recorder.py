# -*- coding: utf-8 -*-
"""Flight recorder — la caja negra de vuelo para agentes (línea Art. 72).

Registra cada observación y cada disparo con contexto completo, y exporta un
informe sellado (SHA-256) apto como anexo de monitoreo post-mercado:
qué agente, qué turno, qué score crudo/normalizado, qué estadístico, qué
temperatura, cuándo disparó y con qué evidencia acumulada. La respuesta a
"¿por qué se contuvo a este agente?" no es una opinión: es un log verificable.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import List, Optional


@dataclass
class Observation:
    path: str               # id del agente/sesión/camino
    t: float                # tiempo lógico o epoch
    raw_score: float
    norm_score: float
    stat_name: str
    stat_value: float
    threshold: float
    tripped: bool
    wall_time: float = field(default_factory=time.time)


@dataclass
class TripEvent:
    path: str
    t: float
    stat_name: str
    stat_value: float
    threshold: float
    turn_index: int             # en qué observación del camino ocurrió
    evidence_window: List[dict]  # últimas N observaciones que construyeron el disparo


class FlightRecorder:
    def __init__(self, evidence_window_size: int = 10):
        self.observations: List[Observation] = []
        self.trips: List[TripEvent] = []
        self._window = evidence_window_size

    def record(self, obs: Observation) -> None:
        self.observations.append(obs)
        if obs.tripped:
            recent = [asdict(o) for o in self.observations
                      if o.path == obs.path][-self._window:]
            turn_index = sum(1 for o in self.observations if o.path == obs.path) - 1
            self.trips.append(TripEvent(
                path=obs.path, t=obs.t, stat_name=obs.stat_name,
                stat_value=obs.stat_value, threshold=obs.threshold,
                turn_index=turn_index, evidence_window=recent))

    # -- exportación sellada ------------------------------------------------
    def export(self, path: Optional[str] = None) -> dict:
        payload = {
            "version": 1,
            "generated_at": time.time(),
            "n_observations": len(self.observations),
            "n_trips": len(self.trips),
            "trips": [asdict(t) for t in self.trips],
            "observations": [asdict(o) for o in self.observations],
        }
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        payload["sha256"] = hashlib.sha256(blob.encode()).hexdigest()
        if path:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)
        return payload

    def summary(self) -> dict:
        """Resumen de monitoreo continuo (campos pensados para el plan Art. 72)."""
        paths = {o.path for o in self.observations}
        return {
            "agentes_monitoreados": len(paths),
            "observaciones_totales": len(self.observations),
            "disparos_totales": len(self.trips),
            "tasa_disparo_por_agente": round(len(self.trips) / max(1, len(paths)), 4),
            "disparos": [{"path": t.path, "turno": t.turn_index,
                          "estadistico": t.stat_name,
                          "valor": round(t.stat_value, 4),
                          "umbral": t.threshold} for t in self.trips],
        }
