# Paquete de Auditoría Final — Evaluación Independiente para Sonnet

**TRACE_ID:** ARS-20260729-AUD1  
**Repositorio Canónico de Evidencia:** `https://github.com/RicciYazigi/benchmark2026.git` (Commit `ff989a2`)  
**Licencia de la Capa de Contención:** Apache-2.0 (`fuse-ai`)

Este documento provee las instrucciones exactas, los hashes SHA-256 sellados y la lista de hallazgos negativos/retractaciones para la validación independiente por parte de Sonnet.

---

## 1. Comandos Exactos para Re-ejecutar el Gate 1.5 (A/B/C) desde Cero

Los scripts leen las inferencias de los modelos de guardrail desde las fuentes cacheadas selladas (`evidence/guard_cache_qwen.json` y `evidence/guard_cache_llama.json`) para garantizar reproductibilidad bit a bit sin depender de una GPU/Ollama local.

```bash
# 1. Re-ejecutar Gate OOD sobre Qwen 2.5 3B (Normalización por Cuantiles)
$env:NORM="quantile"
python scripts/eval_guard_online.py qwen2.5:3b

# 2. Re-ejecutar Gate OOD sobre Llama Guard 3 1B (Verificación de Degeneración Absorbida)
$env:NORM="quantile"
python scripts/eval_guard_online.py llama-guard3:1b

# 3. Verificación de la suite de pruebas unitarias de fusible
cd fusible
py -m pytest tests/ -q

# 4. Verificación de la suite del arnés AegisBench
cd ..
py -m pytest tests/ -q
```

*Nota:* Si se desea regenerar las inferencias desde cero vía Ollama en lugar de usar el cache sellado, ejecutar `python scripts/eval_guard_online.py` sin pasar archivos de cache (requiere servidores Ollama activos para `qwen2.5:3b` y `llama-guard3:1b`).

---

## 2. Hashes SHA-256 Esperados de Evidencias Selladas

| Archivo de Evidencia | SHA-256 Esperado |
| :--- | :--- |
| `evidence/atbench_guard_online_v2_qwen2.5_3b_quantile_20260720.json` | `9159ecdfbd4a93d9065e3499b19b8db6f9634e836ddce14ab2b91005a728660e` |
| `evidence/atbench_guard_online_v2_llama-guard3_1b_quantile_20260720.json` | `3e66d75ad1f5a06b1aee8ede480b2cd117260d034b8cc227509367583273b243` |
| `evidence/atbench_guard_ensemble_qwen2.5_3b_quantile_20260720.json` | `7eddd9acc5da8b917c32be50004a5a00ad5f0526419fdbc668e443577430cadd` |
| `evidence/atbench_guard_ensemble_llama-guard3_1b_quantile_20260720.json` | `5df124e369c7e44d9ddfb59e35723ab0be4a8e98dd40e8fa4fb9e9a1f23946a7` |
| `evidence/exp_cierre_auditoria2_20260719.json` | `582ac8b403221190a22d04b40ee3a9bed2ce38ad9c1676eff2c9b750ec791d59` |
| `evidence/exp_lfo_cluster_bootstrap_20260719.json` | `4d22d6ac4f1b242392c92af6c4de6d0863facfd122efa4a1aba98d8f6ef0cc23` |

---

## 3. Las 3 Retractaciones / Hallazgos Negativos Documentados

1. **Kernel NRIF como Clasificador de Un Turno (MATAR como detector):**
   - *Hallazgo:* La coherencia angular de un solo turno sin contexto temporal degeneró por colapso de ejes cuando el texto se evalúa contra sí mismo.
   - *Documentado en:* [RESULTADOS_4R2_HONESTO.md](file:///c:/Users/USER/Documents/Benchmark2026/RESULTADOS_4R2_HONESTO.md) y [AUDITORIA_Y_NORTE_4R2.md](file:///c:/Users/USER/Documents/Benchmark2026/AUDITORIA_Y_NORTE_4R2.md).

2. **Térmico Crudo OOD sin Normalización:**
   - *Hallazgo:* El acumulador térmico $I^2t$ sin normalización previa por cuantiles sufre en distribuciones OOD cuando el nivel del sensor se comprime. Se resolvió integrando `QuantileNormalizer` + CUSUM como default OOD.
   - *Documentado en:* [RESULTADOS_ATBENCH_GUARD.md](file:///c:/Users/USER/Documents/Benchmark2026/RESULTADOS_ATBENCH_GUARD.md) y [ANEXO_DEGENERACION_LLAMAGUARD.md](file:///c:/Users/USER/Documents/Benchmark2026/ANEXO_DEGENERACION_LLAMAGUARD.md).

3. **Ensamble Global por Promedio de Rangos (Δ = -0.024, P=0.001):**
   - *Hallazgo:* Combinar detectores heterogéneos mediante un promedio de rangos global ingenuo reduce el rendimiento frente al mejor sensor individual. La acumulación temporal por sensor supera al ensamble estático.
   - *Documentado en:* [PLAN_PUBLICACION_APACHE.md](file:///c:/Users/USER/Documents/Benchmark2026/PLAN_PUBLICACION_APACHE.md) §1.3.

---

## 4. Estado de Publicación

- **Paquete `fuse-ai`:** Listo en `C:\Users\USER\Documents\fuse-ai` (Apache-2.0, 21 tests pasando). PyPI en espera de la confirmación de este reporte de auditoría por parte de Sonnet.
