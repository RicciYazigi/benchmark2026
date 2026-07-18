# Evaluación de Trayectorias con Memoria Térmica (ATBench) — Resultados (v4)

**Fecha de Generación:** 2026-07-17 · dataset `ATBench` (1000 muestras) · 5-Fold Cross-Validation Estratificado y Determinista · Bootstrap CI N=10,000.

---

## 1. Metodología de la Evaluación (v4)

Esta versión 4 introduce un diseño experimental de máximo rigor para descartar el sobreajuste y los sesgos estadísticos:
1. **5-Fold Cross-Validation Estratificado**: El dataset original de 1000 muestras se divide de forma reproducible en 5 pliegues disjuntos, balanceando los 5 grupos de riesgo (directo vs indirecto, safe vs unsafe, y la clase de control benigna pura) con una variación menor a $\pm 2$ muestras.
2. **Evaluación Out-of-Fold (OOF)**: Los umbrales óptimos para baseline y memoria se calibran en cada pliegue $k$ utilizando los pliegues restantes ($dev$) y se usan para predecir en el pliegue held-out $ho$. Las métricas de exactitud, precisión, recall, F1 y matrices de confusión se reportan globalmente sobre las predicciones OOF.
3. **Manejo de Empates en AUROC**: Se implementa cálculo de la U de Mann-Whitney promediando rangos de empates mediante `scipy.stats.rankdata`.
4. **Test Pareado por Bootstrap**: Se realiza un remuestreo con reemplazo pareado ($N=10000$, semilla fija en 42) sobre las muestras del subconjunto **Tardío** para evaluar directamente la distribución de $\Delta\text{AUROC} = \text{AUROC}_{memoria} - \text{AUROC}_{baseline}$.

---

## 2. Resultados OOF Globales

### A. Detector Base: CCA (Léxico)

| Subconjunto | Sistema | AUROC [IC 95%] | F1-Score | Precision | Recall | Accuracy | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|
| Completo   | Baseline (Fixed ) | 0.5664 [0.5344, 0.5979] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Baseline (Opt CV) | 0.5664 [0.5344, 0.5979] | 0.6709 | 0.5151 | 0.9618 | 0.5310 | 478/450/53/19 |
| Completo   | Memoria  (Fixed ) | 0.5852 [0.5499, 0.6195] | 0.6652 | 0.5271 | 0.9014 | 0.5490 | 448/402/101/49 |
| Completo   | Memoria  (Opt CV) | 0.5852 [0.5499, 0.6195] | 0.6662 | 0.5119 | 0.9537 | 0.5250 | 474/452/51/23 |
| Temprano   | Baseline (Fixed ) | 0.4465 [0.3784, 0.5165] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Baseline (Opt CV) | 0.4465 [0.3784, 0.5165] | 0.5227 | 0.3651 | 0.9200 | 0.3778 | 92/160/10/8 |
| Temprano   | Memoria  (Fixed ) | 0.4349 [0.3625, 0.5091] | 0.4985 | 0.3562 | 0.8300 | 0.3815 | 83/150/20/17 |
| Temprano   | Memoria  (Opt CV) | 0.4349 [0.3625, 0.5091] | 0.5156 | 0.3597 | 0.9100 | 0.3667 | 91/162/8/9 |
| Tardio     | Baseline (Fixed ) | 0.5976 [0.5610, 0.6358] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Baseline (Opt CV) | 0.5976 [0.5610, 0.6358] | 0.7195 | 0.5710 | 0.9723 | 0.5877 | 386/290/43/11 |
| Tardio     | Memoria  (Fixed ) | 0.6334 [0.5941, 0.6729] | 0.7199 | 0.5916 | 0.9194 | 0.6110 | 365/252/81/32 |
| Tardio     | Memoria  (Opt CV) | 0.6334 [0.5941, 0.6729] | 0.7159 | 0.5691 | 0.9647 | 0.5836 | 383/290/43/14 |

### B. Detector Base: C_NI (Gobernanza / Hashing)

| Subconjunto | Sistema | AUROC [IC 95%] | F1-Score | Precision | Recall | Accuracy | TP / FP / TN / FN |
|---|---|---|---|---|---|---|---|
| Completo   | Baseline (Fixed ) | 0.5180 [0.4815, 0.5535] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Baseline (Opt CV) | 0.5180 [0.4815, 0.5535] | 0.6622 | 0.4960 | 0.9960 | 0.4950 | 495/503/0/2 |
| Completo   | Memoria  (Fixed ) | 0.5077 [0.4715, 0.5438] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Completo   | Memoria  (Opt CV) | 0.5077 [0.4715, 0.5438] | 0.6640 | 0.4970 | 1.0000 | 0.4970 | 497/503/0/0 |
| Temprano   | Baseline (Fixed ) | 0.5125 [0.4405, 0.5844] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Baseline (Opt CV) | 0.5125 [0.4405, 0.5844] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Memoria  (Fixed ) | 0.4875 [0.4154, 0.5588] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Temprano   | Memoria  (Opt CV) | 0.4875 [0.4154, 0.5588] | 0.5405 | 0.3704 | 1.0000 | 0.3704 | 100/170/0/0 |
| Tardio     | Baseline (Fixed ) | 0.5318 [0.4902, 0.5741] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Baseline (Opt CV) | 0.5318 [0.4902, 0.5741] | 0.7022 | 0.5426 | 0.9950 | 0.5411 | 395/333/0/2 |
| Tardio     | Memoria  (Fixed ) | 0.5119 [0.4704, 0.5540] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |
| Tardio     | Memoria  (Opt CV) | 0.5119 [0.4704, 0.5540] | 0.7045 | 0.5438 | 1.0000 | 0.5438 | 397/333/0/0 |

---

## 3. Test de Diferencia Pareada en Riesgo Tardío

Para dirimir la efectividad del acumulador de memoria frente a la línea base instantánea en el subconjunto **Tardío / Disparo Retardado** (730 muestras), el bootstrap pareado arroja los siguientes resultados:

*   **CCA (Léxico)**:
    *   $\Delta\text{AUROC}$ puntual: **0.0358**
    *   Intervalo de confianza del 95% de la diferencia: **[0.0129, 0.0591]**
    *   Probabilidad empírica de mejora $P(\text{Memoria} > \text{Baseline})$: **0.9992**
*   **C_NI (Gobernanza)**:
    *   $\Delta\text{AUROC}$ puntual: **-0.0199**
    *   Intervalo de confianza del 95% de la diferencia: **[-0.0720, 0.0308]**
    *   Probabilidad empírica de mejora $P(\text{Memoria} > \text{Baseline})$: **0.2225**

---

## 4. Discusión Científica y Conclusiones

### Conclusión Principal:
*   Para el clasificador **CCA** en riesgo tardío: **ventaja de la memoria en riesgo tardio, estadisticamente distinguible (ΔAUROC=0.0358, IC=[0.0129, 0.0591], p=0.9992). Primera evidencia externa real de la tesis I2t, condicionada al sensor actual.**

### Límite Central y Limitación Metodológica:
*   **IMPORTANTE**: El sensor base utilizado para medir la criticidad del turno es léxico (CCA es-ES) o hashing (C_NI, que rinde en torno a ~0.5 AUROC, es decir, nivel azar). El eje temporal de las trayectorias se mide sobre una señal de criticidad no semántica. Por ende, un AUROC >0.5 en esta evaluación refleja que el acumulador realiza una inercia de señal útil y geométricamente robusta a lo largo del tiempo, no que el sensor base esté calibrado semánticamente.

---

## 5. Sello de Evidencia Final y Reproducibilidad

*   **SEALED_SHA256**: `01db4604bb77208ff7b0b8ab2f4c6282b0e09e94d683676dd007f3c770f2547b`
*   **Nota de Reproducibilidad**: Hash idéntico en 2 corridas sucesivas: `01db4604bb77208ff7b0b8ab2f4c6282b0e09e94d683676dd007f3c770f2547b`.
