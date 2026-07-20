# -*- coding: utf-8 -*-
"""Estadísticos de disparo intercambiables — el corazón estadístico-agnóstico.

Decisión de diseño (AUDITORIA_Y_NORTE_4R2.md, Parte 4.1, pre-registrada):
el fusible NO está casado con una ecuación. I²t, CUSUM y EWMA implementan el
mismo contrato; el default se elige empíricamente por sensor/dominio con la
calibración de este paquete. La ecuación es un empleado, no el dueño.

Contrato TripStatistic:
    update(score, dt=1.0) -> float   # nuevo valor del estadístico
    value                            # valor actual
    threshold                        # umbral de disparo (h / T_trip)
    tripped(value) -> bool
    reset()
Todos los estadísticos son estrictamente online: jamás miran el futuro.
"""
from __future__ import annotations

import math
from typing import Protocol


class TripStatistic(Protocol):
    name: str
    threshold: float
    value: float

    def update(self, score: float, dt: float = 1.0) -> float: ...
    def reset(self) -> None: ...


class I2tStatistic:
    """Acumulador térmico I²t de 4R2 (equivalencia numérica probada en tests
    contra antigravity_wings.thermal.ThermalAccumulator, error < 1e-9).

    T_k = T_{k-1} · exp(−dt/τ) + max(0, score − θ)²
    """

    name = "i2t"

    def __init__(self, tau: float = 5.0, theta: float = 0.90, threshold: float = 0.30):
        if tau <= 0:
            raise ValueError("tau debe ser > 0")
        self.tau = tau
        self.theta = theta
        self.threshold = threshold
        self.value = 0.0
        self._first = True

    def update(self, score: float, dt: float = 1.0) -> float:
        if not self._first:
            self.value *= math.exp(-dt / self.tau)
        self._first = False
        dev = max(0.0, score - self.theta)
        self.value += dev * dev
        return self.value

    def reset(self) -> None:
        self.value = 0.0
        self._first = True


class CusumStatistic:
    """CUSUM unilateral (Page, 1954): S_k = max(0, S_{k-1} + score − k_ref).

    Con scores normalizados por cuantiles (benignos ~ U[0,1]) y k_ref = 0.75,
    los benignos tienen deriva negativa esperada (−0.25/turno) y el estadístico
    se mantiene cerca de 0; riesgo sostenido sobre el p75 benigno acumula.
    """

    name = "cusum"

    def __init__(self, k_ref: float = 0.75, threshold: float = 2.0):
        self.k_ref = k_ref
        self.threshold = threshold
        self.value = 0.0

    def update(self, score: float, dt: float = 1.0) -> float:
        # dt no aplica al CUSUM clásico (evento-a-evento); se acepta por contrato
        self.value = max(0.0, self.value + (score - self.k_ref))
        return self.value

    def reset(self) -> None:
        self.value = 0.0


class EwmaStatistic:
    """Media móvil exponencial (control chart clásico)."""

    name = "ewma"

    def __init__(self, alpha: float = 0.3, threshold: float = 0.9):
        if not 0 < alpha <= 1:
            raise ValueError("alpha en (0, 1]")
        self.alpha = alpha
        self.threshold = threshold
        self.value = 0.0
        self._first = True

    def update(self, score: float, dt: float = 1.0) -> float:
        self.value = score if self._first else self.alpha * score + (1 - self.alpha) * self.value
        self._first = False
        return self.value

    def reset(self) -> None:
        self.value = 0.0
        self._first = True


class KalmanSlopeStatistic:
    """EXPERIMENTAL — Kalman lineal de tendencia local (nivel + pendiente).

    Origen: discusión Kalman-vs-térmico (Grok, 2026-07-20). Encuadre correcto:
    Kalman no compite con CUSUM/I²t — estima estado; la detección va encima.
    Lo único genuinamente nuevo que aporta es la PENDIENTE: no "cuánto riesgo
    acumulado" sino "a qué velocidad crece". Hipótesis falsable pre-registrada:
    ¿la pendiente estandarizada detecta deriva antes/mejor que I²t/CUSUM en la
    misma batería? Nota: EWMA equivale a un Kalman de ganancia fija solo-nivel,
    ya presente en la batería — este estadístico añade el estado que EWMA no tiene.

    Modelo local-linear-trend: x_k = l_k + ruido;  l_k = l_{k-1} + b_{k-1};
    b_k = b_{k-1} + ruido. Valor del estadístico: pendiente estandarizada
    max(0, b / sqrt(var_b)) — solo deriva ASCENDENTE dispara.
    """

    name = "kalman_slope"

    def __init__(self, q_level: float = 1e-3, q_slope: float = 1e-4,
                 r_obs: float = 0.05, threshold: float = 2.5):
        import numpy as _np

        self._np = _np
        self.threshold = threshold
        self._Q = _np.diag([q_level, q_slope])
        self._r = r_obs
        self.reset()

    def update(self, score: float, dt: float = 1.0) -> float:
        np = self._np
        if self._first:
            self._x = np.array([float(score), 0.0])
            self._first = False
        else:
            F = np.array([[1.0, 1.0], [0.0, 1.0]])
            self._x = F @ self._x
            self._P = F @ self._P @ F.T + self._Q
            innov = float(score) - self._x[0]
            S = self._P[0, 0] + self._r
            K = self._P[:, 0] / S
            self._x = self._x + K * innov
            self._P = self._P - np.outer(K, self._P[0, :])
        var_b = max(self._P[1, 1], 1e-12)
        self.value = max(0.0, float(self._x[1]) / float(var_b) ** 0.5)
        return self.value

    def reset(self) -> None:
        np = self._np
        self._x = np.zeros(2)
        self._P = np.diag([1.0, 1.0])
        self._first = True
        self.value = 0.0


STATISTICS = {"i2t": I2tStatistic, "cusum": CusumStatistic, "ewma": EwmaStatistic,
              "kalman_slope": KalmanSlopeStatistic}


def make_statistic(name: str, **kwargs) -> TripStatistic:
    try:
        return STATISTICS[name.lower()](**kwargs)
    except KeyError:
        raise ValueError(f"Estadístico desconocido: {name}. Opciones: {sorted(STATISTICS)}")
