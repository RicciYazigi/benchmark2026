# fusible

**Capa de contención temporal, sensor-agnóstica, para sistemas agénticos.**

Convierte señales de riesgo por turno — de cualquier detector (Llama Guard, LlamaFirewall, probes latentes, un webhook tuyo) — en decisiones de contención en vivo, con calibración automática y un log auditable (flight recorder) apto para monitoreo post-mercado (EU AI Act, Art. 72).

Nacido del proyecto 4R2. Los estadísticos de disparo son intercambiables por diseño — I²t (térmico), CUSUM, EWMA — y el default se elige con datos, no por lealtad a una ecuación (`select_best_statistic`).

## Instalación (desarrollo)

```bash
cd fusible && pip install -e ".[dev]" && pytest   # 16 tests, incl. equivalencia numérica con el kernel 4r2v6
```

## Quickstart

```python
from fusible import Fuse, QuantileNormalizer, calibrate_threshold, select_best_statistic

# 1. Normaliza contra una referencia benigna (resuelve sensores binarios o comprimidos)
qn = QuantileNormalizer().fit(scores_benignos_de_referencia)

# 2. Elige estadístico y umbral con datos de validación
mejor = select_best_statistic(benignas_norm, inseguras_norm)          # {'best': 'cusum', ...}
h = calibrate_threshold(benignas_norm, mejor["best"], target_fpr=0.05)

# 3. Contención en vivo, multi-agente
fuse = Fuse(statistic=mejor["best"], normalizer=qn, threshold=h)
for k, score in enumerate(stream):
    trip = fuse.observe(raw_score=score, t=float(k), path="agente-42")
    if trip is not None:
        contener(trip)              # trip.turn_index, trip.evidence_window: el porqué, auditable

# 4. Informe sellado (SHA-256) para el expediente de monitoreo
fuse.recorder.export("informe_monitoreo.json")
print(fuse.recorder.summary())
```

## Qué es cada módulo

`statistics.py` — I2t/CUSUM/EWMA bajo un mismo contrato online (jamás miran el futuro). · `calibration.py` — QuantileNormalizer (benignos → U[0,1] por construcción; θ=0.90 y k_ref=0.75 estables para cualquier sensor), calibración de umbral por FPR objetivo, selección empírica de estadístico. · `fuse.py` — multi-camino, semántica V7.7 (el disparo es solicitud de contención, no BLOCK). · `recorder.py` — flight recorder con exportación sellada.

## Evidencia

Resultados, protocolo y retractaciones documentadas: `../MEGAFILE_SESION_4R2_20260719.md` y `../AUDITORIA_Y_NORTE_4R2.md`. Estado del gate OOD: `../RESULTADOS_ATBENCH_GUARD.md` (Fase 1.5 en curso).

*Licencia: pendiente de decisión (Apache-2.0 vs BSL). Dirección humana: Richie.*
