"""fusible — capa de contención temporal, sensor-agnóstica, para sistemas agénticos.

Convierte señales de riesgo por turno (de CUALQUIER detector: Llama Guard,
LlamaFirewall, probes latentes, webhooks) en decisiones de contención en vivo,
con calibración automática y log auditable (flight recorder).

Nacido del proyecto 4R2. La física I²t, CUSUM y EWMA son estadísticos
intercambiables; el default se elige con datos (select_best_statistic).
"""
from .calibration import (
    QuantileNormalizer,
    calibrate_threshold,
    peak_statistic,
    select_best_statistic,
)
from .fuse import Fuse
from .recorder import FlightRecorder, Observation, TripEvent
from .statistics import (
    STATISTICS,
    CusumStatistic,
    EwmaStatistic,
    I2tStatistic,
    make_statistic,
)

__version__ = "0.1.0"
__all__ = [
    "Fuse", "QuantileNormalizer", "FlightRecorder", "TripEvent", "Observation",
    "I2tStatistic", "CusumStatistic", "EwmaStatistic", "make_statistic",
    "STATISTICS", "calibrate_threshold", "peak_statistic", "select_best_statistic",
]
