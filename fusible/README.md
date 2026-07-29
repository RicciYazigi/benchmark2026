# fuse-ai (`fusible`)

**Capa de contención temporal, sensor-agnóstica, para sistemas agénticos.**

Convierte señales de riesgo por turno — de cualquier detector (Llama Guard, LlamaFirewall, probes latentes, un webhook propio) — en decisiones de contención en vivo, con calibración automática y un log auditable (*flight recorder*) apto para monitoreo post-mercado (EU AI Act, Art. 72).

Nacido del proyecto 4R2. Los estadísticos de disparo son intercambiables por diseño — $I^2t$ (térmico), CUSUM, EWMA — y la selección de estadísticos se realiza empíricamente con datos de validación (`select_best_statistic`).

---

## Instalación

```bash
# Desde PyPI (paquete publicado):
pip install fuse-ai

# Desarrollo local:
cd fusible && pip install -e ".[dev]" && py -m pytest
```

---

## Quickstart

```python
from fusible import Fuse, QuantileNormalizer, calibrate_threshold, select_best_statistic

# 1. Normaliza contra una referencia benigna (resuelve sensores binarios, comprimidos o ruidosos)
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

---

## Módulos Principales

- `fusible.statistics`: Implementaciones online de $I^2t$, CUSUM y EWMA (contrato estrictamente online sin mirar el futuro).
- `fusible.calibration`: `QuantileNormalizer` (mapeo a $U[0,1]$ con `robust_reference` para sensores degenerados), calibrador de umbral por FPR y selección empírica de estadístico.
- `fusible.fuse`: Administrador multi-camino (`Fuse`) con semántica V7.7 (la activación solicita contención, no bloqueo ciego).
- `fusible.recorder`: Flight recorder con exportación JSON sellada con SHA-256.

---

## Evidencia Empírica y Tesis

- **Tesis Validada:** El riesgo se acumula a lo largo de una trayectoria; la memoria temporal (CUSUM) detecta fallas agénticas donde los detectores reactivos por turno son ciegos.
- **Resultados Sellados:** En-dominio 8/8 familias ($p=0.0039$), OOD con CUSUM ($IC$ excluye cero).
- Ver la documentación completa de evidencia en [NORTE_UNA_PAGINA.md](../NORTE_UNA_PAGINA.md) y [ANEXO_DEGENERACION_LLAMAGUARD.md](../ANEXO_DEGENERACION_LLAMAGUARD.md).

---

## Licencia

Código distribuido bajo la licencia **Apache License 2.0**. consulte el archivo [LICENSE](LICENSE) y [NOTICE](NOTICE) para más detalles. Copyright (c) 2026 Ricardo Yazigi.

