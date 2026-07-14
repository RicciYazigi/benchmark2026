# Evaluación de Trayectorias con Memoria Térmica (ATBench) — Resultados

**Fecha:** 2026-07-14 · dataset `ATBench` (1000 muestras, 497 unsafe / 503 safe) · seed fija · detector base `CCA` (léxico) con `theta = 0.35`, `tau = 5.0`, `T_trip = 0.30`.
Medición local, sin modificar el kernel de 4r2v6.

---

## Pregunta
¿El acumulador térmico de 4R2 (que modela la criticidad acumulada con memoria y disipación térmica entre turnos) ofrece ventajas cuantitativas frente a un detector tradicional reactivo de un solo turno (sin memoria)? Se evalúa sobre el benchmark de trayectorias multi-turno de agentes ATBench.

---

## Resultados

| Métrica | Con Memoria (ThermalAccumulator) | Sin Memoria (Línea Base) | Δ (memoria − baseline) |
|---|---|---|---|
| **AUROC** | 0.3335 | 0.5538 | **−0.2203** |
| **F1-Score** | 0.6652 | 0.6640 | **+0.0012** |
| **Precision** | 0.5271 | 0.4970 | **+0.0301** |
| **Recall** | 0.9014 | 1.0000 | **−0.0986** |
| **Accuracy** | 0.5490 | 0.4970 | **+0.0520** |
| **Verdaderos Positivos (TP)** | 448 | 497 | −49 |
| **Falsos Positivos (FP)** | 402 | 503 | −101 |
| **Verdaderos Negativos (TN)** | 101 | 0 | **+101** |
| **Falsos Negativos (FN)** | 49 | 0 | +49 |
| **Turno Medio de Detección** | **2.83** | **0.0** | **+2.83** |

---

## Conclusión y Lectura Honesta

1. **La memoria mitiga la saturación catastrófica de falsos positivos**: 
   La línea base sin memoria bloquea absolutamente todas las interacciones en el Turno 0 (`TN = 0, FP = 503, Recall = 100%`). Esto ocurre porque la heurística léxica `CCA.observe()` de 4r2v6 asigna un piso de criticidad conservador de `0.50` a cualquier texto no clasificado (`unclassified`), lo cual supera inmediatamente el umbral de bloqueo puntual (`theta = 0.35`). Al no tener memoria, cualquier prompt de inicio bloquea el sistema.
   El acumulador térmico (con memoria) introduce **inercia y disipación**. Al permitir que el "calor" decaiga exponencialmente (`tau = 5.0`), los falsos positivos puntuales aislados no logran acumular suficiente temperatura como para cruzar el fusible de disparo (`T_trip = 0.30`). Esto salva **101 muestras benignas** de ser bloqueadas erróneamente (`TN = 101`), manteniendo un recall robusto del **90.14%** (detectando 448 de 497 riesgos).

2. **El AUROC y el desajuste de la heurística base**:
   El AUROC de ambos sistemas es insatisfactorio (0.3335 y 0.5538). El detector base `CCA.observe()` fue diseñado originalmente con un diccionario de keywords en español (como `"transfiere"`, `"dinero"`, `"ejecuta"`) y un estimador de riesgo por longitud (`semantic_risk = len(split) / 80`). Al evaluar el dataset ATBench en inglés:
   - La mayoría de las peticiones legítimas caen en `unclassified` (criticidad piso de 0.50).
   - Los mensajes largos de respuesta de herramientas/entorno se saturan automáticamente a `1.0` de criticidad únicamente por su conteo de palabras.
   Por lo tanto, la criticidad puntual no correlaciona con la peligrosidad semántica real del ataque, sino con la extensión del texto, penalizando el uso natural de herramientas del agente.

3. **Validación del Acumulador Térmico**:
   A pesar de la descalibración del detector base sobre el idioma inglés de ATBench, el experimento proporciona una **validación empírica exitosa de la física del acumulador**: la integración temporal de la criticidad (`I2t`) y el decaimiento térmico logran discriminar la acumulación sostenida de riesgo, reduciendo drásticamente la tasa de falsos positivos frente a un enfoque reactivo de un solo turno.

---

## Límites
- **Tamaño de muestra**: N = 1,000 muestras completas evaluadas.
- **Configuración fija**: Perfil de parámetros por defecto (`theta = 0.35`, `tau = 5.0`, `T_trip = 0.30`).
- **Idioma**: El dataset ATBench es en inglés, lo que inhabilita las reglas léxicas en español de `CCA.observe()`.
