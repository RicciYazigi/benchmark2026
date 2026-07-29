# ATBench con Sensor Real por Turno — Resultados (2026-07-18)

**TRACE_ID:** ARS-20260718-SNR1 · **Estado:** OK
**Evidencia sellada:** `evidence/atbench_sensor_real_tfidf_20260718.json` (SHA-256 `7f9cb170…37dc`) y `evidence/atbench_sensor_real_tfidf_CAL_20260718.json` (SHA-256 `4bf99705…d1d`)
**Scripts:** `scripts/eval_atbench_sensor_real.py`, `scripts/eval_atbench_sensor_real_cal.py` · **Módulo nuevo:** `src/aegisbench/sensors/` · **Tests:** `tests/test_turn_sensors.py` (7/7 verdes)
**Invariante:** `core/` de 4r2v6 intacto. El acumulador se usa tal cual, sin cambios.

---

## Qué se hizo

Tras demostrar que el 100% del fracaso previo era del sensor (ver `RESULTADOS_FISICA_VS_SENSOR.md`), se construyó la pieza que faltaba: un **sensor de criticidad por turno con señal real** (`TfidfTurnSensor`: TF-IDF 1-2 gramas + regresión logística balanceada, supervisión débil con label de trayectoria propagado a turnos), evaluado con protocolo sin fuga: 5-fold estratificado **por trayectoria** (jamás se entrena y evalúa sobre la misma trayectoria), θ del acumulador calibrado por fold solo con train, bootstrap pareado.

## Resultados (OOF, N=1000, 497 unsafe / 503 safe)

| Agregación sobre el mismo sensor | AUROC [IC 95%] |
|---|---|
| Mejor detector de un turno (max score) | 0.8550 [0.8331, 0.8773] |
| Media simple de scores | **0.8986** [0.8804, 0.9173] |
| **Memoria térmica (max T, θ p90 train)** | 0.8764 [0.8566, 0.8970] |
| Memoria térmica calibrada (grid θ×τ train-only) | 0.8733 [0.8520, 0.8943] |

Deltas pareados (bootstrap 2,000, mismo remuestreo):

| Comparación | Δ AUROC | IC 95% | P(mejora) |
|---|---|---|---|
| Memoria vs. mejor un-turno | **+0.0214** | [+0.0134, +0.0301] | 1.000 |
| Memoria vs. media simple | −0.0223 | [−0.0348, −0.0101] | 0.0005 |

## Lectura honesta

1. **Primera evidencia positiva real de la tesis temporal.** Con un sensor que sí lee riesgo, agregar información a lo largo de la trayectoria le gana al mejor detector de un solo turno posible, con IC que excluye el cero y P(mejora)=1.0. La pregunta central del proyecto ("¿mirar la secuencia aporta sobre mirar el peor turno?") tiene por primera vez un **sí** medido sobre datos reales.
2. **Pero la forma térmica específica (I²t) todavía no demuestra valor único.** Una media aritmética — la agregación más tonta posible — supera al acumulador (Δ −0.025, significativo), y calibrar θ/τ no cierra la brecha. Interpretación técnica: con un sensor ruidoso, promediar cancela ruido; el acumulador descarta la señal sub-θ y penaliza cuadráticamente, lo que aquí pierde información. La ventaja teórica del I²t (sensibilidad al orden, a la persistencia y al timing) no se manifiesta en ATBench con este sensor — o el patrón no lo requiere, o el ruido del sensor domina.
3. **Reformulación falsable para la siguiente fase:** el terreno donde el I²t debería ganarle a la media es señal por turno **precisa pero débil** (deriva sostenida sub-umbral con picos benignos aislados — exactamente EXP B, donde la media también habría ganado poco). El guard model zero-shot (fuera de dominio, sin entrenar en ATBench) es el test limpio: instrucciones en `INSTRUCCIONES_FASE_GUARD_MODEL.md`.

## Límites

Sensor entrenado dentro del dominio ATBench (supervisión débil; generalización fuera de dominio: **ND**). El AUROC ~0.87-0.90 refleja en parte separabilidad léxica/temática del dataset, no capacidad de seguridad general. Grid de calibración evaluado con scores in-fold de train (optimismo residual en la selección, no en el test). Corrida única, seed 42.

| Etiqueta | Aplica a |
|---|---|
| empírico con límites | todos los AUROC y deltas de este documento |
| ND | comportamiento con sensor fuera de dominio (fase guard model) |

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal"). Dirección humana: Richie.*
