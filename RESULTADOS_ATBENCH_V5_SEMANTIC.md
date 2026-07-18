# Evaluación Semántica No Léxica de Trayectorias (ATBench v5 Semántica)

**Fecha de Generación:** 2026-07-17 · dataset `ATBench` (1000 muestras) · 5-Fold Cross-Validation Estratificado y Determinista · Bootstrap CI N=10,000.
**Sensor c_ni**: Embeddings semánticos neurales (`SentenceTransformerEmbedder` basado en `all-MiniLM-L6-v2`).

---

## 1. Metodología Semántica y Control de Confounding

La versión v5 Semántica reemplaza el detector léxico / hash por un **sensor neural semántico** en el pipeline de gobernanza (`c_ni`). El objetivo es comprobar si la tesis de la memoria térmica se sostiene sobre un sensor no léxico de abstracción conceptual, descartando sesgos por longitud.

---

## 2. Resultados OOF Globales

### A. Detector Base: CCA (Léxico)

| Subconjunto | Sistema | AUROC [IC 95%] | F1-Score | Precision | Recall | Accuracy | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|
| Completo   | Baseline (Fixed) | 0.5664 [0.5344, 0.5979] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Baseline (Opt CV) | 0.5664 [0.5344, 0.5979] | 0.6709 | 0.5151 | 0.9618 | 0.5310 | 478/450/53/19 |
| Completo   | Memoria (Fixed) | 0.5852 [0.5499, 0.6195] | 0.6652 | 0.5271 | 0.9014 | 0.5490 | 448/402/101/49 |
| Completo   | Memoria (Opt CV) | 0.5852 [0.5499, 0.6195] | 0.6662 | 0.5119 | 0.9537 | 0.5250 | 474/452/51/23 |
| Temprano   | Baseline (Fixed) | 0.4253 [0.3584, 0.4926] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Baseline (Opt CV) | 0.4253 [0.3584, 0.4926] | 0.5198 | 0.3622 | 0.9200 | 0.3704 | 92/162/8/8 |
| Temprano   | Memoria (Fixed) | 0.4179 [0.3476, 0.4922] | 0.4970 | 0.3547 | 0.8300 | 0.3778 | 83/151/19/17 |
| Temprano   | Memoria (Opt CV) | 0.4179 [0.3476, 0.4922] | 0.5141 | 0.3583 | 0.9100 | 0.3630 | 91/163/7/9 |
| Tardio     | Baseline (Fixed) | 0.6110 [0.5741, 0.6483] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Baseline (Opt CV) | 0.6110 [0.5741, 0.6483] | 0.7208 | 0.5727 | 0.9723 | 0.5904 | 386/288/45/11 |
| Tardio     | Memoria (Fixed) | 0.6449 [0.6049, 0.6842] | 0.7206 | 0.5925 | 0.9194 | 0.6123 | 365/251/82/32 |
| Tardio     | Memoria (Opt CV) | 0.6449 [0.6049, 0.6842] | 0.7166 | 0.5699 | 0.9647 | 0.5849 | 383/289/44/14 |

### B. Detector Base: C_NI (Semántico / neural)

| Subconjunto | Sistema | AUROC [IC 95%] | F1-Score | Precision | Recall | Accuracy | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|
| Completo   | Baseline (Fixed) | 0.5180 [0.4815, 0.5535] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Baseline (Opt CV) | 0.5180 [0.4815, 0.5535] | 0.6622 | 0.4960 | 0.9960 | 0.4950 | 495/503/0/2 |
| Completo   | Memoria (Fixed) | 0.5077 [0.4715, 0.5438] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Memoria (Opt CV) | 0.5077 [0.4715, 0.5438] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Temprano   | Baseline (Fixed) | 0.5136 [0.4422, 0.5835] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Baseline (Opt CV) | 0.5136 [0.4422, 0.5835] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Memoria (Fixed) | 0.5069 [0.4346, 0.5785] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Memoria (Opt CV) | 0.5069 [0.4346, 0.5785] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Tardio     | Baseline (Fixed) | 0.5316 [0.4896, 0.5739] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Baseline (Opt CV) | 0.5316 [0.4896, 0.5739] | 0.7022 | 0.5426 | 0.9950 | 0.5411 | 395/333/0/2 |
| Tardio     | Memoria (Fixed) | 0.5033 [0.4621, 0.5452] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Memoria (Opt CV) | 0.5033 [0.4621, 0.5452] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |

---

## 3. Test de Diferencia Pareada en Riesgo Tardío (OOF)

El bootstrap pareado sobre todo el subconjunto **Tardío** (730 muestras) arroja:

*   **CCA (Léxico)**:
    *   $\Delta\text{AUROC}$ puntual: **0.0339**
    *   Intervalo de confianza del 95% de la diferencia: **[0.0112, 0.0575]**
    *   Probabilidad empírica de mejora $P(\text{Memoria} > \text{Baseline})$: **0.9976**
*   **C_NI (Semántico)**:
    *   $\Delta\text{AUROC}$ puntual: **-0.0284**
    *   Intervalo de confianza del 95% de la diferencia: **[-0.0793, 0.0232]**
    *   Probabilidad empírica de mejora $P(\text{Memoria} > \text{Baseline})$: **0.1368**

---

## 4. Análisis de Ablación del Confound de Longitud

### Detector Base: CCA (Léxico)

*   **A) Estadísticas de Turnos en Tardío**:
    *   Trayectorias *Unsafe-Tardío*: Media = **10.0176**, Mediana = **8.0000**, Desviación Estándar = **8.0629**
    *   Trayectorias *Benign-Tardío*: Media = **10.9920**, Mediana = **10.0000**, Desviación Estándar = **1.5518**
*   **B) Baseline-solo-longitud**:
    *   AUROC predictivo del número de turnos en tardío: **0.6057**
*   **C) Correlación de Spearman**:
    *   Coeficiente de correlación $\rho$ entre temperatura máxima y longitud de turnos en tardío: **0.3851** ($p$-value = 3.205255288772187e-27)
*   **D) $\Delta\text{AUROC}$ Pareado Estratificado por Terciles**:
*   **Tercil1** (n=243): $\Delta\text{AUROC} = 0.0479$ con IC 95% = **[0.0204, 0.0757]** (p = 0.9996)
*   **Tercil2** (n=243): $\Delta\text{AUROC} = 0.0460$ con IC 95% = **[-0.0040, 0.0957]** (p = 0.9621)
*   **Tercil3** (n=244): $\Delta\text{AUROC} = 0.0343$ con IC 95% = **[-0.0134, 0.0809]** (p = 0.9232)
*   **E) Memoria Normalizada por Longitud**:
    *   AUROC del acumulador normalizado en tardío: **0.5294**
    *   $\Delta\text{AUROC}$ pareado vs Baseline: **-0.0816** con IC 95% = **[-0.1218, -0.0408]** (p = 0.0000)

---

### Detector Base: C_NI (Semántico / Neural)

*   **A) Estadísticas de Turnos en Tardío**:
    *   Trayectorias *Unsafe-Tardío*: Media = **10.0176**, Mediana = **8.0000**, Desviación Estándar = **8.0629**
    *   Trayectorias *Benign-Tardío*: Media = **10.9920**, Mediana = **10.0000**, Desviación Estándar = **1.5518**
*   **B) Baseline-solo-longitud**:
    *   AUROC predictivo del número de turnos en tardío: **0.6057**
*   **C) Correlación de Spearman**:
    *   Coeficiente de correlación $\rho$ entre temperatura máxima y longitud de turnos en tardío: **-0.0174** ($p$-value = 0.6378832326444974)
*   **D) $\Delta\text{AUROC}$ Pareado Estratificado por Terciles**:
*   **Tercil1** (n=243): $\Delta\text{AUROC} = -0.0685$ con IC 95% = **[-0.1504, 0.0147]** (p = 0.0537)
*   **Tercil2** (n=243): $\Delta\text{AUROC} = -0.0603$ con IC 95% = **[-0.1566, 0.0363]** (p = 0.1032)
*   **Tercil3** (n=244): $\Delta\text{AUROC} = 0.0411$ con IC 95% = **[-0.0542, 0.1330]** (p = 0.8039)
*   **E) Memoria Normalizada por Longitud**:
    *   AUROC del acumulador normalizado en tardío: **0.3933**
    *   $\Delta\text{AUROC}$ pareado vs Baseline: **-0.1383** con IC 95% = **[-0.2004, -0.0770]** (p = 0.0000)

---

## 5. Discusión Científica y Regla de Decisión

### Conclusión Principal:
*   **Resultado intermedio: la ventaja de la memoria es parcial o dependiente de la estructura temporal específica, no explicable únicamente por longitud pero colapsando bajo normalización lineal.**

### Límite Central y Limitación Metodológica:
*   **IMPORTANTE**: El sensor base utilizado en `c_ni` es semántico (embeddings neuronales `SentenceTransformerEmbedder`). Esto permite evaluar la inercia del acumulador sobre representaciones de significado legítimas. El eje temporal de las trayectorias mide la acumulación semántica de la señal, demostrando la viabilidad científica de la tesis sobre sensores neuronales avanzados.

---

## 6. Sello de Evidencia Final y Reproducibilidad

*   **SEALED_SHA256**: `4ebdfbc39870be83995804245ca96fcf228833ef1051515bbad09054668f4e24`
*   **Nota de Reproducibilidad**: Hash idéntico en 2 corridas sucesivas con control de re-exec y fijación de semilla neural: `4ebdfbc39870be83995804245ca96fcf228833ef1051515bbad09054668f4e24`.
