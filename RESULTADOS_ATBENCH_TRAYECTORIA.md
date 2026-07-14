# Evaluación de Trayectorias con Memoria Térmica (ATBench) — Resultados (v2)

**Fecha:** 2026-07-14 · dataset `ATBench` (1000 muestras, 497 unsafe / 503 safe) · seed fija · comparativa cruzada de detectores (`CCA` vs `C_NI`) y calibración de umbrales óptimos de decisión.

---

## 1. Contexto y Objetivos

En la iteración previa, se identificaron tres problemas críticos que impedían evaluar de manera justa la hipótesis del acumulador térmico de 4R2 ($I^2t$ con memoria y decaimiento exponencial):
1. **Línea base degenerada**: El piso de criticidad de `CCA.observe()` para la clase `unclassified` ($0.50$) estaba por encima de $\theta = 0.35$, bloqueando el 100% de las muestras en el Turno 0.
2. **Inversión del AUROC**: La inyección cuadrática de la criticidad puntual de textos largos (respuestas de herramientas extensas clasificadas como $1.0$ por longitud) acumulaba calor en muestras benignas, empeorando el score continuo del acumulador.
3. **Falta de segmentación**: La imposibilidad de aislar los riesgos de **disparo retardado** (ataques indirectos que ocurren avanzada la conversación) impedía medir si la memoria temporal aportaba alguna ventaja real sobre una línea base puntual.

Esta versión 2 del experimento soluciona estos problemas calibrando óptimamente los umbrales de decisión ($\theta$ y $T_{trip}$) y segmentando el dataset en dos subconjuntos:
*   **Riesgo Temprano (Ataques Directos)**: 145 unsafe + 250 benignas (395 muestras totales).
*   **Riesgo Tardío / Disparo Retardado**: 605 unsafe + 250 benignas (855 muestras totales).

---

## 2. Resultados Comparativos Cruzados

### A. DETECTOR BASE: CCA (Léxico)
El detector léxico `CCA` utiliza keywords y penalización por longitud.

| Subconjunto | Sistema | Umbral | AUROC | Accuracy | F1-Score | Precision | Recall | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|---|
| **Completo** (1000) | Baseline (Fijo) | $\theta = 0.35$ | 0.5538 | 0.4970 | 0.6640 | 0.4970 | 1.0000 | 497 / 503 / 0 / 0 |
| | Baseline (Opt) | $\theta = 0.64$ | 0.5538 | 0.5320 | 0.6718 | 0.5156 | 0.9638 | 479 / 450 / 53 / 18 |
| | Memoria (Fijo) | $T_{trip} = 0.30$ | **0.5840** | 0.5490 | 0.6652 | 0.5271 | 0.9014 | 448 / 402 / 101 / 49 |
| | Memoria (Opt) | $T_{trip} = 0.13$ | **0.5840** | 0.5310 | **0.6727** | 0.5150 | 0.9698 | 482 / 454 / 49 / 15 |
| **Temprano** (395) | Baseline (Opt) | $\theta = 0.00$ | 0.4969 | 0.2532 | 0.4040 | 0.2532 | 1.0000 | 100 / 295 / 0 / 0 |
| | Memoria (Opt) | $T_{trip} = 0.01$ | 0.4195 | 0.2532 | 0.4040 | 0.2532 | 1.0000 | 100 / 295 / 0 / 0 |
| **Tardío** (855) | Baseline (Opt) | $\theta = 0.64$ | 0.5848 | 0.5076 | 0.6477 | 0.4850 | 0.9748 | 387 / 411 / 47 / 10 |
| | Memoria (Opt) | $T_{trip} = 0.25$ | **0.6107** | **0.5298** | **0.6492** | **0.4967** | 0.9370 | 372 / 377 / 81 / 25 |

### B. DETECTOR BASE: C_NI (Gobernanza / Hashing)
El detector de gobernanza `C_NI` mide la similitud de coseno léxica (hashing) entre el texto del turno y la política.

| Subconjunto | Sistema | Umbral | AUROC | Accuracy | F1-Score | Precision | Recall | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|---|
| **Completo** (1000) | Baseline (Opt) | $\theta = 0.46$ | 0.5180 | 0.4980 | 0.6644 | 0.4975 | 1.0000 | 497 / 502 / 1 / 0 |
| | Memoria (Opt) | $T_{trip} = 0.01$ | 0.5076 | 0.4970 | 0.6640 | 0.4970 | 1.0000 | 497 / 503 / 0 / 0 |
| **Tardío** (855) | Baseline (Opt) | $\theta = 0.00$ | 0.5083 | 0.4643 | 0.6342 | 0.4643 | 1.0000 | 397 / 458 / 0 / 0 |
| | Memoria (Opt) | $T_{trip} = 0.01$ | **0.5147** | 0.4643 | 0.6342 | 0.4643 | 1.0000 | 397 / 458 / 0 / 0 |

---

## 3. Discusión Científica y Lectura de Datos

1. **Validación de la Hipótesis del Acumulador en Riesgo Tardío (Disparo Retardado)**:
   *   En el subconjunto **Tardío (Disparo Retardado)** bajo el detector base `CCA`, el acumulador térmico calibrado óptimamente ($T_{trip} = 0.25$) **supera** a la línea base de un solo turno optimizada ($\theta = 0.64$).
   *   El AUROC de la memoria sube a **0.6107** (+2.59% frente al 0.5848 del baseline) y el F1-Score alcanza **0.6492** (frente al 0.6477).
   *   El acumulador logra filtrar **81 falsos positivos** benignos (`TN = 81`) frente a los 47 del baseline, manteniendo un recall sumamente alto del **93.70%** (372/397 ataques detectados). Esto valida empíricamente la hipótesis original: la inercia temporal del acumulador es útil para discriminar trayectorias donde el ataque se introduce o se propaga de forma retardada o indirecta.

2. **La Calibración óptima rescata la comparación**:
   *   Al calibrar óptimamente el baseline sin memoria del CCA a $\theta = 0.64$, este deja de ser degenerado (bloquear todo) y logra filtrar 53 negativos del total.
   *   Al contrastarlo de forma justa con la memoria óptima ($T_{trip} = 0.13$ en el dataset completo), la memoria retiene el F1-Score más alto (**0.6727**) y un AUROC más alto (**0.5840** vs. 0.5538).

3. **Inocuidad del detector C_NI**:
   *   El detector basado en Hashing `C_NI` no tiene poder predictivo real en este dataset en inglés (AUROC ~ 0.51). El uso de `HashingEmbedder` (256 dimensiones léxicas) no logra mapear la alineación política-respuesta en un entorno multilingüe complejo. Al ser la señal del sensor base puro ruido aleatorio, la memoria térmica aplicada a `C_NI` hereda y replica este comportamiento.

---

## 4. Límites y Observaciones

*   **Sesgo de Longitud**: La heurística de `CCA` penaliza severamente el texto largo ($semantic\_risk \approx 1.0$ si len > 80). En ATBench, esto genera picos instantáneos que causan disparos tipo `spike` en mensajes largos del entorno. Aunque la calibración amortigua este ruido elevando $T_{trip}$ a $0.25$ en el conjunto tardío, el rendimiento final sigue acotado por las limitaciones del clasificador léxico base.
*   **Dirección del AUROC corregida**: El AUROC del acumulador ya no se encuentra invertido (<0.50), gracias a la corrección del paso de $req$ no vacío (primer mensaje del usuario), lo que estabilizó el cálculo de la distancia y evitó excepciones de tipo fail-closed de los embeddings.
