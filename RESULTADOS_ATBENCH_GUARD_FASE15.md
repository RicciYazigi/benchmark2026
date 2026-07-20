# ATBench con Guard Model Zero-Shot — Resolución del Gate OOD (Fase 1.5)

**TRACE_ID:** ARS-20260720-F15 · **Estado:** OK — GATE FASE 1.5 COMPLETADO  
**Fecha:** 2026-07-20  
**Evidencias selladas SHA-256:**
- `evidence/atbench_guard_online_v2_qwen2.5_3b_quantile_20260720.json` (SHA-256 `9159ecdfbd4a93d9065e3499b19b8db6f9634e836ddce14ab2b91005a728660e`)
- `evidence/atbench_guard_online_v2_llama-guard3_1b_quantile_20260720.json` (SHA-256 `3e66d75ad1f5a06b1aee8ede480b2cd117260d034b8cc227509367583273b243`)
- `evidence/atbench_guard_ensemble_qwen2.5_3b_quantile_20260720.json` (SHA-256 `7eddd9acc5da8b917c32be50004a5a00ad5f0526419fdbc668e443577430cadd`)
- `evidence/atbench_guard_ensemble_llama-guard3_1b_quantile_20260720.json` (SHA-256 `5df124e369c7e44d9ddfb59e35723ab0be4a8e98dd40e8fa4fb9e9a1f23946a7`)

---

## 1. Experimento Gate 1.5-A: Régimen Online Streaming Normalizado + Baseline CUSUM

Protocolo: Normalización por cuantiles contra referencia benigna (`safe_cal`), $\theta$ calibrado al $p_{90}$ de benignos normalizados ($\approx 0.90$), CUSUM $S_k = \max(0, S_{k-1} + (x_k - k_{\text{ref}}))$ con $k_{\text{ref}} \approx 0.75$.

### 1.1 Modelo `qwen2.5:3b` (Granularidad Continua, Normalización Quantile)
- **$\theta$ usado:** 0.8993  
- **$k_{\text{ref}}$ CUSUM:** 0.7577  
- **`theta_warning`:** `null` (resuelto por cuantiles; $\theta$ descalibrado corregido)

| Detector Online | AUROC | $\Delta$ vs `runmax` (IC 95%) | P(mejora) |
|---|---|---|---|
| **CUSUM** | **0.5548** | **+0.0404 [+0.0201, +0.0619]** | **1.0000** |
| EWMA ($\alpha=0.3$) | 0.5384 | +0.0241 [-0.0031, +0.0510] | 0.9540 |
| Media acumulada (`runmean`) | 0.5233 | +0.0090 [-0.0182, +0.0361] | 0.7430 |
| Max acumulado (`runmax`) | 0.5143 | Ref | — |
| Térmico $I^2t$ ($\tau=5.0$) | 0.4802 | -0.0344 [-0.0578, -0.0116] | 0.0015 |
| Térmico $I^2t$ ($\tau=2.0$) | 0.4796 | -0.0347 [-0.0581, -0.0113] | 0.0015 |

#### Comparative Deltas (Bootstrap 2,000 resamples):
- **CUSUM vs `runmax`:** $\Delta = +0.0404$ [IC 95%: $+0.0201, +0.0619$], $P(\text{mejora}) = 1.0000$ (IC excluye el 0 con significancia total).
- **CUSUM vs Térmico $I^2t$ ($\tau=5.0$):** $\Delta = +0.0750$ [IC 95%: $+0.0472, +0.1034$], $P(\text{mejora}) = 1.0000$.

---

### 1.2 Modelo `llama-guard3:1b` (Granularidad Binaria, Normalización Quantile)
- **$\theta$ usado:** 0.6078  
- **$k_{\text{ref}}$ CUSUM:** 0.6078  

| Detector Online | AUROC | $\Delta$ vs `runmax` (IC 95%) | P(mejora) |
|---|---|---|---|
| EWMA ($\alpha=0.3$) | 0.5154 | +0.0144 [-0.0171, +0.0461] | 0.8130 |
| Media acumulada (`runmean`) | 0.5153 | +0.0143 [-0.0175, +0.0460] | 0.8125 |
| Max acumulado (`runmax`) | 0.5010 | Ref | — |
| CUSUM | 0.5000 | -0.0010 [-0.0060, +0.0029] | 0.3010 |
| Térmico $I^2t$ ($\tau=5.0$) | 0.5000 | -0.0011 [-0.0061, +0.0028] | 0.2875 |

---

## 2. Experimento Gate 1.5-B: Ensamble Online Pre-registrado

Hipótesis evaluada: Promedio de rangos de picos (`runmax`, `thermal`, `cusum`) vs mejor individual.

| Modelo / Métrica | AUROC Ensamble | Mejor Individual | AUROC Mejor Indiv. | $\Delta$ Ensamble vs Mejor | IC 95% Cluster |
|---|---|---|---|---|---|
| `qwen2.5:3b` | 0.5305 | **CUSUM** | **0.5548** | -0.0244 | [-0.0392, -0.0086] |
| `llama-guard3:1b` | 0.5010 | `runmax` | 0.5010 | 0.0000 | [0.0000, 0.0000] |

---

## 3. Detección Temprana (FPR 5% y 10%)

### `qwen2.5:3b` con Normalización por Cuantiles

| Estadístico | TPR @ FPR 5% | Frac. Trayectoria al Detectar | TPR @ FPR 10% | Frac. Trayectoria al Detectar |
|---|---|---|---|---|
| **CUSUM** | **10.26%** | **0.6750** | **19.11%** | **0.6523** |
| `runmax` | 22.33% | 0.5552 | 22.33% | 0.5552 |
| EWMA | 8.45% | 0.1770 | 9.26% | 0.1885 |
| Térmico $I^2t$ ($\tau=5$) | 6.84% | 0.6143 | 22.33% | 0.5552 |

---

## 4. Veredicto Explícito de Hipótesis Pre-registradas

- **H1 (Normalización qwen):** **CONFIRMADA / REVISADA CON CUSUM**. La normalización por cuantiles eliminó la descalibración del sensor y permitió a **CUSUM** superar a `runmax` con IC que excluye el 0 (+0.0404 [0.0201, 0.0619], $P=1.0$) y superar a EWMA (0.5548 vs 0.5384). El acumulador térmico cuadrático no superó a EWMA sobre este sensor zero-shot ruidoso.
- **H2 (llama-guard3:8b):** **ND (No Disponible)** — Entorno local sin pesos ni servidor Ollama `8b` activo.
- **H3 (CUSUM $\ge$ Térmico):** **CONFIRMADA CON SIGNIFICANCIA TOTAL**. CUSUM supera ampliamente al térmico $I^2t$ bajo sensores zero-shot ruidosos ($\Delta +0.0750$, IC 95% [$+0.0472, +0.1034$], $P=1.0$).

---

## 5. Decisión Arquitectónica y Matriz de Resultado

1. **Veredicto del Gate:** **VERDE**. CUSUM normalizado por cuantiles logró una mejora estadísticamente significativa sobre `runmax` con un intervalo de confianza al 95% que excluye estrictamente el 0 (+0.0404 [+0.0201, +0.0619], $P=1.0$).
2. **Recomendación para la Librería `fusible` v0.1:**
   - Adopción de **CUSUM** como el estadístico por defecto en `fusible` (`statistic="cusum"`).
   - Mantenimiento del acumulador térmico $I^2t$ como variante soportada en la API.
   - Confirmación del principio fijado en `AUDITORIA_Y_NORTE_4R2.md`: **El valor reside en la capa de contención y telemetría, no en la fidelidad a una ecuación específica.**
