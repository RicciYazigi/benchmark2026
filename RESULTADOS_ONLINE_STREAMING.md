# Régimen Online (Streaming) — El Terreno Donde el I²t Gana (2026-07-18)

**TRACE_ID:** ARS-20260718-STR1 · **Estado:** OK
**Evidencia sellada:** `evidence/exp_streaming_online_20260718.json` · SHA-256 `4e88f15b…50ec8f8`
**Script:** `scripts/exp_streaming_online.py` (reanudable, checkpoints por fold) · Protocolo OOF 5-fold por trayectoria, seed 42, sensor tfidf-logreg-v1 · `core/` intacto.

---

## Pregunta

En retrospectiva (trayectoria completa disponible), la media simple ganó al acumulador (`RESULTADOS_ATBENCH_SENSOR_REAL.md`). Pero un guardrail real decide **en vivo, turno a turno, sin conocer el futuro** — la media de trayectoria completa no existe en producción hasta que ya es tarde. ¿Quién gana cuando todos los métodos juegan con las reglas reales?

## Resultados (todos los estadísticos 100% online)

| Detector online | AUROC | TPR @ FPR 5% | TPR @ FPR 10% |
|---|---|---|---|
| **Térmico I²t (τ=5)** | **0.8764** | **0.5392** | **0.5996** |
| Térmico I²t (τ=2) | 0.8684 | 0.4769 | 0.5976 |
| Max acumulado (reactivo) | 0.8550 | 0.4266 | 0.5292 |
| EWMA (α=0.3) | 0.8348 | 0.3219 | 0.4809 |
| Media acumulada | 0.7854 | 0.2394 | 0.3400 |

Deltas pareados (bootstrap 2,000, mismos remuestreos): térmico vs. max acumulado **+0.0214** [+0.0135, +0.0297], P(mejora)=1.0; térmico vs. EWMA **+0.0417** [+0.0271, +0.0572], P(mejora)=1.0.

## Lectura honesta

1. **En el régimen online, el acumulador térmico es el mejor agregador de todos los probados, con significancia plena.** La ventaja de la media simple era un artefacto de la evaluación retrospectiva: al pasar a decisión en vivo, la media acumulada colapsa (0.899 → 0.785, y TPR 24% a FPR 5%) porque los primeros turnos benignos diluyen la señal que llega después. El térmico retiene el calor de la deriva sin dejar que el pasado benigno lo lave.
2. **A tasa de falsos positivos igualada (5%), el térmico detecta un 26% más de trayectorias inseguras que el mejor detector reactivo** (53.9% vs. 42.7%) y más del doble que la media online. Ese es el número de producto: mismo costo de fricción, sustancialmente más cobertura.
3. **El térmico detecta más tarde dentro de la trayectoria que la media (fracción 0.69 vs. 0.28) — pero la media casi no detecta** (TPR 24%): detecta temprano solo lo trivialmente obvio. La comparación honesta de "cuándo" solo tiene sentido entre métodos con TPR comparable; contra el max reactivo (0.61 vs. 0.69 de fracción), el térmico paga un retraso pequeño a cambio de +11 puntos de TPR.
4. Implicación arquitectónica: la tesis original del proyecto (fusible por acumulación con disipación, decidiendo en línea) queda **validada empíricamente en su régimen de diseño** por primera vez, sobre datos reales y contra rivales online justos.

## Límites

Sensor en dominio (tfidf entrenado en ATBench vía OOF); la fase guard model (fuera de dominio) sigue siendo el test limpio pendiente — instrucciones ya entregadas. Umbrales de operación elegidos sobre el pool global de trayectorias seguras, idéntico para todos los métodos (comparación relativa válida; cifras absolutas de TPR/FPR requieren calibración con datos propios de despliegue). Corrida única, seed 42.

| Etiqueta | Aplica a |
|---|---|
| empírico con límites | todas las cifras de este documento |
| ND | régimen online con sensor fuera de dominio |

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal"). Dirección humana: Richie.*
