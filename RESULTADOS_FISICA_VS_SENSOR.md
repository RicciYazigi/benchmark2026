# Física vs. Sensor — Experimento Alterno de Aislamiento (2026-07-18)

**TRACE_ID:** ARS-20260718-FVS1 · **Estado:** OK
**Evidencia sellada:** `evidence/exp_fisica_vs_sensor_20260718.json` · SHA-256 `8b41bfcd5eabfa387ea997af203c28e62741c0efd48cb866654b9264b938d1f4`
**Script reproducible:** `scripts/exp_fisica_vs_sensor.py` · seed 42 · parámetros por defecto (θ=0.35, τ=5.0, T_trip=0.30)
**Invariante respetado:** `core/` de 4r2v6 sin tocar (solo lectura vía `FOURR2_REPO_PATH`).

---

## Pregunta

Si la matemática del acumulador térmico I²t está probada (tests unitarios verdes), ¿por qué no pasa ningún benchmark de texto? ¿Está mal la ecuación, el concepto, el pipeline, o el sensor? Este experimento separa las cuatro hipótesis y las falsa una por una, sin depender de ningún benchmark externo.

## Resultados por hipótesis

### H1 — ¿La implementación tiene un bug? **NO** (demostrable)

EXP A: 200 secuencias aleatorias (τ, T_trip, dt variables) comparadas contra la recurrencia T_t = T_{t−1}·e^(−Δt/τ) + max(0, c−θ)² calculada a mano de forma independiente, incluyendo la semántica de disparo y reset del fusible. **Error máximo absoluto: 0.0.** El código ES la ecuación declarada, exactamente.

### H2 — ¿La física no separa deriva de picos? **NO: separa perfectamente** (demostrable, señal sintética)

EXP B, diseño de máximo emparejado: ambas clases reciben exactamente un pico ~U(0.62, 0.70) en un turno aleatorio; la insegura además sostiene una meseta sub-pico (~0.55); la segura está en calma (<θ). El máximo por trayectoria es idéntico entre clases, así que **el mejor detector de un solo turno posible no puede separar por construcción** — esta es la formalización exacta del caso guardia-perro-ambulancia.

| Score | AUROC |
|---|---|
| Mejor detector de un turno (max criticality) | 0.4743 |
| Memoria térmica (max temperatura) | **1.0000** |

Controles adicionales: la disipación protege contra eventos espaciados (EXP C: max_T cae de 0.223 a 0.081 con dt=10), y con longitudes invertidas (segura de 30 turnos vs. insegura de 6, EXP D) la memoria mantiene **AUROC 1.0** mientras el predictor solo-longitud da 0.0 — con señal limpia, la memoria no mide longitud.

Nota de calibración: con parámetros por defecto la tasa de disparo binario sobre deriva genuina fue solo 0.75% (T_trip=0.30 es alto para meseta ~0.55). El score continuo separa perfecto; los umbrales binarios necesitan calibración cuando exista sensor real. Es un ajuste de constantes, no de física.

### H4 — ¿El pipeline sobre la estructura real de ATBench está roto? **NO** (demostrable)

EXP F: mismas 1,000 trayectorias reales (longitudes reales, labels reales, mismo balance 497/503), único cambio: la criticidad por turno la produce un oráculo limpio (riesgo plantado en turno aleatorio, meseta sostenida después; pico idéntico en ambas clases).

| Score | AUROC |
|---|---|
| Mejor un turno | 0.5137 |
| Memoria térmica | **0.9747** |

El mismo loader, el mismo acumulador, la misma estructura de datos que dio 0.58 con CCA da **0.97** con señal limpia. El pipeline está sano.

### H3 — ¿El sensor es el problema? **SÍ, y no es solo descalibración: hay un bug real** (empírico, N=9,009 turnos reales)

EXP E, autopsia de `CCA.observe()` sobre los 9,009 turnos de las 1,000 trayectorias reales:

1. **Bug de subcadenas (nuevo, no reportado antes).** El matching es `"ip" in texto` — subcadena, no palabra. En inglés dispara con: *description* (702 veces), *recipient*, *script*, *snippet*, *confirmation* (contiene "firma"), *zip*, *wikipedia*, *vip*, *shipping*, *receipt*, *subscription*, *multiple*… El **22.72% de TODOS los turnos** dispara keyword únicamente por subcadenas dentro de palabras inglesas — es decir, ~90% de los hits de keywords (25.21% total) son espurios.
2. **Piso `unclassified` = 0.50 > θ = 0.35.** El 74.79% de los turnos cae en `unclassified` e inyecta energía fija (0.15² = 0.0225) sin leer nada: calor proporcional al número de turnos, no al riesgo.
3. **`semantic_risk` = palabras/80.** El 12.37% de los turnos satura a criticidad 1.0 solo por ser largo (respuestas de herramientas).

Resultado neto: criticidad media en trayectorias seguras 0.6326 vs. inseguras 0.6725. **El sensor es prácticamente ciego al riesgo.**

**EXP G — control decisivo:** corrigiendo solo el bug (frontera de palabra) y quitando el piso sobre θ, los hits de keyword caen de 25.21% → 2.49% y el AUROC de la memoria cae de 0.592 → **0.5205**. Conclusión dura pero necesaria: la "ventaja" de la memoria reportada en las corridas previas de ATBench (0.585 global, Δ+0.034 en tardío) **no era detección de riesgo — era integración de ruido de subcadenas + piso + verbosidad**, que casualmente correlaciona débil con el label. Ese hallazgo previo queda reclasificado: de "primera validación externa" a "artefacto del sensor".

---

## Conclusión (una línea)

La ecuación es exacta, la física hace exactamente aquello para lo que fue diseñada (AUROC 1.0 sintético / 0.97 sobre estructura real con señal limpia, sin artefacto de longitud), el pipeline está sano — **el 100% del fracaso en benchmarks es atribuible al sensor de criticidad por turno, que sobre texto en inglés no mide riesgo, y su aparente señal previa era ruido.**

## Qué significa y qué sigue

La tesis del acumulador queda **validada en su propio terreno por primera vez** (nunca se había probado la física aislada), pero **sigue sin validación sobre lenguaje real**, porque ningún sensor disponible en el proyecto (CCA léxico, C_NI hash, C_NI MiniLM) produce señal de riesgo por turno sobre ATBench. La arquitectura correcta es explícita ahora: 4R2 no compite con los clasificadores de turno — es la **capa de agregación temporal encima de un sensor que sí funcione**. Próximos pasos (≤3):

1. Sensor por turno real: probar un guard model pequeño existente (p. ej. Llama Guard / ShieldGemma vía API o local) como productor de criticidad por turno, alimentando el acumulador sin cambios. Es la única pieza que falta.
2. Con ese sensor, repetir la corrida ATBench (el pipeline ya está probado con oráculo) y calibrar τ/T_trip sobre un split de desarrollo.
3. Corregir el matching por subcadenas del CCA (frontera de palabra) en la capa que corresponda — está en `core/` sellado, así que la corrección vive como decisión tuya, no de esta sesión.

## Límites

Señal sintética en EXP B/D/F diseñada para contener deriva sub-umbral: demuestra **capacidad** de la física, no que ATBench contenga ese patrón para un sensor real. Corrida única, seed 42, parámetros por defecto sin barrido. EXP G es una corrección mínima del léxico, no un sensor inglés serio.

| Etiqueta | Aplica a |
|---|---|
| demostrable | EXP A, C (matemática/mecánica exacta) |
| empírico con límites | EXP B, D, E, F, G (seed fija, corrida única) |
| ND | rendimiento con un sensor real por turno (paso 1 pendiente) |

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal") sobre un LLM. Dirección humana: Richie.*
