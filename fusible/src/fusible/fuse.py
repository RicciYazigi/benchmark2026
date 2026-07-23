# Copyright (c) 2026 Ricardo Yazigi
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""Fuse — la capa de contención: sensor → normalizador → estadístico → decisión.

Multi-camino (un estado independiente por agente/sesión), estadístico-agnóstico,
con flight recorder integrado. Semántica V7.7 conservada: el disparo NO es un
BLOCK — es una solicitud de contención/recalibración; la decisión final es del
orquestador que consuma el TripEvent.

Uso mínimo:
    from fusible import Fuse, QuantileNormalizer
    qn = QuantileNormalizer().fit(scores_benignos_de_referencia)
    fuse = Fuse(statistic="i2t", normalizer=qn)   # o "cusum" / "ewma"
    for k, score in enumerate(stream_de_scores):
        trip = fuse.observe(raw_score=score, t=float(k), path="agente-42")
        if trip is not None:
            contener(trip)   # trip.evidence_window explica el porqué
"""
from __future__ import annotations

from typing import Dict, Optional

from .calibration import QuantileNormalizer
from .recorder import FlightRecorder, Observation, TripEvent
from .statistics import TripStatistic, make_statistic


class Fuse:
    def __init__(
        self,
        statistic: str = "i2t",
        normalizer: Optional[QuantileNormalizer] = None,
        threshold: Optional[float] = None,
        recorder: Optional[FlightRecorder] = None,
        reset_on_trip: bool = True,
        **stat_kwargs,
    ):
        self.stat_name = statistic
        self.stat_kwargs = dict(stat_kwargs)
        if threshold is not None:
            self.stat_kwargs["threshold"] = threshold
        self.normalizer = normalizer
        self.recorder = recorder or FlightRecorder()
        self.reset_on_trip = reset_on_trip
        self._paths: Dict[str, TripStatistic] = {}
        self._last_t: Dict[str, float] = {}

    def _stat_for(self, path: str) -> TripStatistic:
        if path not in self._paths:
            self._paths[path] = make_statistic(self.stat_name, **self.stat_kwargs)
        return self._paths[path]

    def observe(self, raw_score: float, t: float, path: str = "default") -> Optional[TripEvent]:
        st = self._stat_for(path)
        last = self._last_t.get(path)
        if last is not None and t < last:
            raise ValueError(f"timestamp no monótono en path={path}")
        dt = 1.0 if last is None else max(0.0, t - last)
        self._last_t[path] = t

        norm = raw_score if self.normalizer is None else self.normalizer.transform_one(raw_score)
        value = st.update(norm, dt=dt)
        tripped = value >= st.threshold

        self.recorder.record(Observation(
            path=path, t=t, raw_score=float(raw_score), norm_score=float(norm),
            stat_name=st.name, stat_value=float(value),
            threshold=float(st.threshold), tripped=tripped))

        if tripped:
            trip = self.recorder.trips[-1]
            if self.reset_on_trip:
                st.reset()
            return trip
        return None

    def value(self, path: str = "default") -> float:
        st = self._paths.get(path)
        return 0.0 if st is None else st.value

    def reset(self, path: Optional[str] = None) -> None:
        if path is None:
            self._paths.clear()
            self._last_t.clear()
        else:
            self._paths.pop(path, None)
            self._last_t.pop(path, None)
