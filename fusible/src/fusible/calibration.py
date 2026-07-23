# Copyright (c) 2026 Ricardo Yazigi
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-
"""Calibración: la parte que dos veces demostró ser tan crítica como la física.

Lecciones incorporadas (selladas en evidencia):
  - llama-guard binario: θ = p90 crudo = 1.0 → térmico muerto.
  - qwen comprimido: θ = 0.95 → energía ≈ 0.
Solución: normalizar TODO score al rango empírico de una referencia benigna
antes de tocar el estadístico. Después, calibrar el umbral de disparo h para
una tasa de falsa alarma objetivo sobre trayectorias benignas de validación.
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np

from .statistics import TripStatistic, make_statistic


class QuantileNormalizer:
    """score crudo → rango empírico en la distribución benigna de referencia.

    Benignos quedan ~U[0,1] por construcción: θ=0.90 y k_ref=0.75 son estables
    para cualquier sensor. Monotónica (no cambia rankings). Rango medio en
    empates (soporta sensores binarios sin sesgo).
    """

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
        lo = np.searchsorted(self._ref, s, side="left")
        hi = np.searchsorted(self._ref, s, side="right")
        return [float(x) for x in np.clip((lo + hi) / 2.0 / len(self._ref), 0.0, 1.0)]

    def transform_one(self, score: float) -> float:
        return self.transform([score])[0]


def robust_reference(cal_scores: Sequence[float], pct: float) -> float:
    """Percentil de referencia (θ / k_ref) blindado contra sensores degenerados.

    Caso borde real (llama-guard-1b sobre ATBench, 2026-07-20, sellado): un
    sensor que flaggea ~79% de turnos benignos hace que el percentil caiga
    EXACTAMENTE sobre el nivel superior normalizado → energía/paso = 0 para
    todo evento → estadístico muerto (AUROC 0.5000 exacto). Regla: si el
    percentil alcanza el máximo nivel distinto de la referencia, se devuelve
    el punto medio entre los dos niveles superiores — el nivel de flag vuelve
    a aportar energía > 0. Con sensores sanos es idéntico al percentil normal.
    """
    arr = np.asarray(cal_scores, dtype=float)
    ref = float(np.percentile(arr, pct))
    levels = np.unique(arr)
    if len(levels) >= 2 and ref >= levels[-1]:
        ref = float((levels[-1] + levels[-2]) / 2.0)
    return ref


def peak_statistic(scores: Sequence[float], stat_name: str, **kwargs) -> float:
    """Pico del estadístico sobre una trayectoria (score de trayectoria)."""
    st: TripStatistic = make_statistic(stat_name, **{k: v for k, v in kwargs.items()
                                                     if k != "threshold"})
    peak = 0.0
    for s in scores:
        peak = max(peak, st.update(float(s)))
    return peak


def calibrate_threshold(
    benign_trajectories: Sequence[Sequence[float]],
    stat_name: str,
    target_fpr: float = 0.05,
    **stat_kwargs,
) -> float:
    """Elige h tal que ~target_fpr de las trayectorias benignas dispararían.

    benign_trajectories: scores YA normalizados, trayectorias de validación
    (nunca las mismas usadas para ajustar el normalizador, si es posible).
    """
    if not 0 < target_fpr < 1:
        raise ValueError("target_fpr en (0,1)")
    peaks = sorted(peak_statistic(tr, stat_name, **stat_kwargs) for tr in benign_trajectories)
    if not peaks:
        raise ValueError("sin trayectorias benignas")
    idx = min(len(peaks) - 1, int(np.ceil((1.0 - target_fpr) * len(peaks))))
    h = peaks[idx]
    return float(h) if h > 0 else float(np.finfo(float).eps)


def select_best_statistic(
    benign_trajectories: Sequence[Sequence[float]],
    unsafe_trajectories: Sequence[Sequence[float]],
    candidates: Sequence[str] = ("i2t", "cusum", "ewma"),
) -> dict:
    """Selección empírica del estadístico por AUROC de picos (datos de validación).

    Devuelve {"best": nombre, "auroc": {nombre: valor}}. Implementa la decisión
    pre-registrada: el default se ELIGE con datos, no por lealtad a la ecuación.
    """
    y = [0] * len(benign_trajectories) + [1] * len(unsafe_trajectories)
    aurocs = {}
    for name in candidates:
        s = [peak_statistic(tr, name) for tr in benign_trajectories]
        s += [peak_statistic(tr, name) for tr in unsafe_trajectories]
        aurocs[name] = _auroc(y, s)
    best = max(aurocs, key=aurocs.get)
    return {"best": best, "auroc": {k: round(v, 4) for k, v in aurocs.items()}}


def _auroc(y, s) -> float:
    y = np.asarray(y)
    s = np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
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
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    u = ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))
