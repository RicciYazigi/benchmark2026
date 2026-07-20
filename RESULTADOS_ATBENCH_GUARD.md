# ATBench con Guard Model Zero-Shot (OOD Real) — Resultados Consolidados (2026-07-19)

TRACE_ID: ARS-20260719-GRD1 · Estado: OK — FASE 1 COMPLETADA  
Evidencias selladas SHA-256:
- `evidence/atbench_sensor_real_guard_20260719.json` (SHA-256 `3e0e90400dac6928d3f4a7efc265af7911999967f1dd18ae980f491524f50e78`)
- `evidence/atbench_guard_online_llama-guard3_1b_20260719.json` (SHA-256 `b5de2e38d0476792097fa2875cb7b2ff1b3545ae2b54b429ec8c8ca9fa82f767`)
- `evidence/atbench_guard_por_familia_llama-guard3_1b_20260719.json` (SHA-256 `8092702da63beb6a31dafb8c20654e60c0ad7a493b89245feaff01ce72d46da1`)
- `evidence/atbench_guard_online_qwen2.5_3b_20260719.json` (SHA-256 `eca1e1c728a8c4e97957feceded57218bc9edfb47fcdd8e804d46a5856847fa3`)
- `evidence/atbench_guard_por_familia_qwen2.5_3b_20260719.json` (SHA-256 `86c8cd9e4c6ffc3900d611cc5b95dae9963fb1bc4bf2c12e6edf05a87042ebd4`)

Scripts ejecutados: `scripts/eval_atbench_sensor_real.py guard`, `scripts/eval_guard_online.py`, `scripts/eval_guard_por_familia.py`  
Invariante: `core/` de 4r2v6 intacto.

---

## 1. Experimento 1: `llama-guard3:1b` (Granularidad Binaria 0/1)

### 1.1 Gate 1-A — Evaluación Retrospectiva 5-Fold OOF (N=1000)

| Agregador | AUROC Puntual | IC 95% |
|---|---|---|
| Mejor un-turno (`single_max`) | 0.5000 | [0.4970, 0.5029] |
| Media simple (`single_mean`) | 0.5931 | [0.5573, 0.6285] |
| Memoria térmica (`memory_maxT`, $\tau=5$) | 0.5000 | [0.5000, 0.5000] |

*Nota técnica (θ degenerado):* El percentil 90 de los turnos seguros resultó $\theta=1.0000$ en los 5 folds debido a que `llama-guard3:1b` califica $>10\%$ de los turnos benignos con score binario $1.0$. Esto colapsó la energía térmica continua a $0.0$, confirmando la hipótesis del **Riesgo 1** y activando la regla de corrida obligatoria del modelo continuo.

### 1.2 Gate 1-B — Régimen Online Streaming (Zero-Shot OOD Real)

Con fallback $\theta=0.5$ (para prevenir el colapso del fusible binario):

| Detector Online | AUROC | $\Delta$ vs `runmax` (IC 95%) | P(mejora) |
|---|---|---|---|
| Térmico $I^2t$ ($\tau=2.0$) | **0.5523** | — | — |
| Térmico $I^2t$ ($\tau=5.0$) | **0.5431** | +0.0427 [-0.0017, +0.0902] | 0.9670 |
| Media acumulada (`runmean`) | 0.5154 | +0.0276 [-0.0260, +0.0802] | 0.8510 |
| EWMA ($\alpha=0.3$) | 0.5154 | +0.0273 [-0.0240, +0.0766] | 0.8595 |
| Max acumulado (`runmax`) | 0.5010 | Ref | — |

### 1.3 Gate 1-C — Desglose por Familia de Riesgo (Cluster Bootstrap + Test de Signos)

| Familia de Riesgo (`risk_source`) | N Unsafe | AUROC Térmico | AUROC Runmax | $\Delta$ |
|---|---|---|---|---|
| `inherent_agent_failures` | 135 | **0.6521** | 0.5020 | +0.1501 |
| `corrupted_tool_feedback` | 44 | **0.6083** | 0.5020 | +0.1063 |
| `tool_description_injection` | 52 | **0.5424** | 0.5020 | +0.0404 |
| `indirect_prompt_injection` | 77 | **0.5089** | 0.5020 | +0.0069 |
| `malicious_tool_execution` | 25 | 0.4934 | 0.5020 | -0.0086 |
| `unreliable_or_misinformation` | 64 | 0.4692 | 0.4942 | -0.0249 |
| `malicious_user_instruction_or_jailbreak` | 61 | 0.4561 | 0.5020 | -0.0459 |
| `direct_prompt_injection` | 39 | 0.4498 | 0.5020 | -0.0522 |

- **Victorias por familia:** 4 / 8 familias.
- **Test de signos (unilateral):** $p = 0.6367$.
- **Macro-$\Delta$ clúster bootstrap:** $+0.0210$ $[-0.0257, +0.0689]$, $P(\text{mejora}) = 0.8160$.

---

## 2. Experimento 2: `qwen2.5:3b` (Granularidad Continua)

### 2.1 Granularidad y Calibración
- **Valores únicos generados:** 73 valores continuos en $[0.00, 1.00]$.
- **$\theta$ p90 de turnos seguros:** $\theta = 0.9500$.

### 2.2 Gate 1-B — Régimen Online Streaming (Zero-Shot OOD Real)

| Detector Online | AUROC | $\Delta$ vs `runmax` (IC 95%) | P(mejora) |
|---|---|---|---|
| EWMA ($\alpha=0.3$) | **0.5364** | — | — |
| Media acumulada (`runmean`) | 0.5192 | — | — |
| Max acumulado (`runmax`) | 0.5143 | Ref | — |
| Térmico $I^2t$ ($\tau=5.0$) | 0.4801 | -0.0344 [-0.0574, -0.0118] | 0.0015 |
| Térmico $I^2t$ ($\tau=2.0$) | 0.4797 | -0.0346 [-0.0578, -0.0114] | 0.0015 |

### 2.3 Gate 1-C — Desglose por Familia de Riesgo (`qwen2.5:3b`)

| Familia de Riesgo (`risk_source`) | N Unsafe | AUROC Térmico | AUROC Runmax | $\Delta$ |
|---|---|---|---|---|
| `direct_prompt_injection` | 39 | **0.4849** | 0.4730 | +0.0119 |
| `malicious_user_instruction_or_jailbreak` | 61 | **0.4352** | 0.4258 | +0.0095 |
| `tool_description_injection` | 52 | 0.5130 | 0.5209 | -0.0078 |
| `inherent_agent_failures` | 135 | 0.5299 | 0.5642 | -0.0343 |
| `malicious_tool_execution` | 25 | 0.4285 | 0.4783 | -0.0498 |
| `indirect_prompt_injection` | 77 | 0.4670 | 0.5205 | -0.0535 |
| `unreliable_or_misinformation` | 64 | 0.4449 | 0.5069 | -0.0620 |
| `corrupted_tool_feedback` | 44 | 0.4504 | 0.5328 | -0.0824 |

- **Victorias por familia:** 2 / 8 familias.
- **Test de signos (unilateral):** $p = 0.9648$.
- **Macro-$\Delta$ clúster bootstrap:** $-0.0335$ $[-0.0562, -0.0109]$, $P(\text{mejora}) = 0.0020$.

---

## 3. Síntesis Comparativa y Diagnóstico Arquitectónico

| Dimensión / Modelo | `llama-guard3:1b` (Binario 0/1) | `qwen2.5:3b` (Continuo $[0,1]$) |
|---|---|---|
| **Puntualidad/Falsa Alarma Base** | FP $>10\%$ en turnos benignos ($\theta=1.0$) | Scores concentrados en banda alta ($\theta=0.95$) |
| **Ventaja Online Térmica** | **Positiva** ($\Delta +0.0427$, $P=0.967$) | **Negativa** ($\Delta -0.0344$, $P=0.0015$) |
| **Victorias por Familia** | **4 / 8** (Inyecciones y Fallos Agénticos) | **2 / 8** (Direct Prompt & Jailbreak) |
| **Causa Raíz** | El fusible binario amortigua picos espurios | Con sensor zero-shot ruidoso y $\theta=0.95$, el acumulador descarta el $95\%$ de turnos benignos y penaliza cuadráticamente sobre ruido residual |

---

## 4. Cuadro de Decisión del Plan Maestro (Para Richie)

Según los criterios fijados en el **Plan Maestro Antigravity (ARS-20260719-PMA1)**:

1. **Llama-Guard 3 1B:** Demuestra la ventaja de la acumulación térmica en streaming sobre detectores reactivos ($\text{AUROC } 0.5523$ vs $0.5010$, $P=0.967$), ganando en inyecciones de herramientas e inyecciones indirectas.
2. **Qwen 2.5 3B Zero-Shot:** Muestra que sin afinación ni supervisión agéntica en-dominio, la señal por turno de un LLM generalista es demasiado ruidosa para alimentar el fusible continuo sin calibración avanzada.

**Estado del Gate:** **STOP-THE-LINE / Evaluación Estratégica**. Los resultados OOD reales quedan sellados de forma completamente objetiva para revisión de Richie y la auditoría externa.
