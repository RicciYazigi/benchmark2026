# -*- coding: utf-8 -*-
"""Normalización de scores de sensor contra referencia benigna (Fase 1.5, tarea 1).

Problema que resuelve (dos veces observado): sensores descalibrados rompen la
calibración θ del acumulador — llama-guard binario dio θ=p90=1.0 (térmico
muerto), qwen comprimido en banda alta dio θ=0.95 (energía ≈ 0). La
transformación por cuantiles mapea el score crudo a su RANGO dentro de la
distribución de turnos benignos de referencia:

    score_norm = fracción de scores benignos de referencia <= score crudo

Propiedades: (a) los benignos quedan ~Uniforme[0,1] POR CONSTRUCCIÓN, así
θ = p90 normalizado ≈ 0.90 y k_ref CUSUM = p75 ≈ 0.75, estables para CUALQUIER
sensor; (b) monotónica: no cambia el ranking de un turno, solo la escala;
(c) barata: un sort en fit, un searchsorted por score.
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np


class QuantileNormalizer:
    """Mapea scores crudos al rango empírico de una referencia benigna."""

    def __init__(self) -> None:
        self._ref: np.ndarray | None = None

    def fit(self, benign_scores: Sequence[float]) -> "QuantileNormalizer":
        if len(benign_scores) == 0:
            raise ValueError("referencia benigna vacía")
        self._ref = np.sort(np.asarray(benign_scores, dtype=float))
        return self

    def transform(self, scores: Sequence[float]) -> List[float]:
        if self._ref is None:
            raise RuntimeError("fit() primero")
        s = np.asarray(scores, dtype=float)
        # rango medio entre 'estrictamente menor' y 'menor o igual' (maneja empates
        # masivos, p.ej. sensores binarios, sin sesgar a 0 ni a 1)
        lo = np.searchsorted(self._ref, s, side="left")
        hi = np.searchsorted(self._ref, s, side="right")
        rank = (lo + hi) / 2.0 / len(self._ref)
        return [float(x) for x in np.clip(rank, 0.0, 1.0)]

    def transform_one(self, score: float) -> float:
        return self.transform([score])[0]

    def fit_transform(self, benign_scores: Sequence[float]) -> List[float]:
        return self.fit(benign_scores).transform(benign_scores)

