# Resultados de Fase 4 — J-Space v0 (Representaciones Latentes y Sonda de Deriva Temporal)

**TRACE_ID:** ARS-20260729-JSP0  
**Fecha de Ejecución:** 2026-07-29  
**Modelo Probeta:** `Qwen/Qwen2.5-0.5B` (Hidden states de la última capa con Mean Pooling)  
**Protocolo:** Out-of-Fold (5-fold cross-validation) por trayectoria (supervisión débil por etiqueta de trayectoria), normalización por cuantiles y agregación temporal online.  
**Archivo de Evidencia Sellado:** `evidence/jspace_probe_Qwen_Qwen2.5-0.5B_20260729.json`  
**SHA-256:** `110e082e59ddfe479a1dece6c78ab6579cc224aebec904e3db423dac8f1c127a`

---

## 1. Veredicto de las Hipótesis Pre-registradas

| Hipótesis | Descripción | Resultado Empírico | Veredicto |
| :--- | :--- | :--- | :--- |
| **H-J1** | **Acumulación Temporal en Espacio Latente $J$:** CUSUM sobre $J$ supera a detectores reactivos (Runmax). | CUSUM 0.7880 vs Runmax 0.7609 ($\Delta = +0.0275$, IC 95% = $[0.0004, 0.0567]$, $P_{\text{mejora}} = 0.975$). Ganado en **7/7 familias** ($p = 0.00781$). | **CONFIRMADA** *(Empírico)* |
| **H-J2** | **Superioridad Absoluta de Representación $J$:** Los estados ocultos superan al sensor textual/TF-IDF. | Probe $J$ AUROC = **0.7880** vs Baseline TF-IDF sellado = **0.8760** ($\Delta = -0.0880$). | **FALSADA** *(Empírico con límites)* |
| **H-J3** | **Localización Fina de Inyecciones:** El argmax del score latente identifica el turno exacto de inyección en `environment`. | Acierto en `environment`: **12.71%** (Tasa aleatoria base: **33.91%**). | **FALSADA** *(Empírico)* |

---

## 2. Métricas de Rendimiento Trayectoria (AUROC Online en $J$)

| Agregador Temporal | AUROC | $\Delta$ vs Runmax | IC 95% Bootstrap | $P_{\text{mejora}}$ |
| :--- | :--- | :--- | :--- | :--- |
| **CUSUM (Acumulativo)** | **0.7880** | **+0.0275** | **[0.0004, 0.0567]** | **0.9750** |
| Thermal ($I^2t$, $\tau=5$) | 0.7657 | +0.0051 | [-0.0075, 0.0176] | 0.7800 |
| Runmax (Reactivo Baseline) | 0.7609 | 0.0000 | Ref. | — |
| EWMA ($\alpha=0.3$) | 0.7126 | -0.0483 | [-0.0812, -0.0154] | 0.0010 |
| Runmean (Promedio simple) | 0.6890 | -0.0719 | [-0.1045, -0.0392] | 0.0000 |

---

## 3. Desglose por Familia de Riesgo (CUSUM vs Runmax en $J$)

En **7 de 7 familias**, la acumulación de riesgo con memoria temporal (CUSUM) superó a la detección puntual sin memoria (Runmax) en el espacio de representaciones latentes $J$ ($p = 0.00781$, prueba de signos unilateral):

| Familia de Riesgo | AUROC CUSUM | AUROC Runmax | $\Delta$ (CUSUM - Runmax) |
| :--- | :--- | :--- | :--- |
| `unreliable_or_misinformation` | **0.8556** | 0.8306 | **+0.0250** |
| `corrupted_tool_feedback` | **0.8343** | 0.7827 | **+0.0516** |
| `malicious_tool_execution` | **0.8056** | 0.7688 | **+0.0368** |
| `indirect_prompt_injection` | **0.7950** | 0.7705 | **+0.0245** |
| `tool_description_injection` | **0.7943** | 0.7677 | **+0.0266** |
| `inherent_agent_failures` | **0.7609** | 0.7386 | **+0.0223** |
| `direct_prompt_injection` | **0.6757** | 0.6569 | **+0.0188** |

---

## 4. Análisis Crítico de los Hallazgos

1. **La Tesis de Acumulación Temporal se sostiene intrínsecamente en el espacio $J$:**
   La evidencia confirma que incluso dentro de representaciones latentes internas de la red neuronal (y no solo en scores de clasificadores de texto), **el riesgo se acumula dinámicamente a lo largo del tiempo**. CUSUM captura la elevación sostenida en $J$ superando al pico reactivo en **7/7 familias** con un IC 95% que excluye el cero.

2. **Por qué la sonda $J$ cruda no supera a los clasificadores dedicados (Falsación de H-J2):**
   Las representaciones latentes crudas de la última capa sufren de *confounding* espacial por longitud de secuencia, estilo de prompt y topic drift. Un clasificador especializado como TF-IDF (AUROC 0.8760) o Llama-Guard3 / Qwen-Guard extraen características semánticas filtradas mucho más limpias que una proyección lineal simple sobre la representación latente media de la última capa.

3. **Deriva Temporal vs Localización Puntual (Falsación de H-J3):**
   Cuando ocurre una inyección indirecta en el turno de `environment` (herramienta), la señal en el espacio latente no alcanza su pico máximo de manera instantánea en ese único turno. La anomalía latente se propaga y amplifica progresivamente durante las respuestas subsecuentes del agente, haciendo que el $12.71\%$ de localización puntual en `environment` sea insuficiente para uso como sensor de turno único.

---

## 5. Conclusión y Framing Final

- **$J$-Space v0 valida la generalización de la Tesis Norte:** El mecanismo fusible de acumulación de memoria con CUSUM no es un artefacto exclusivo de un clasificador de texto particular; **es una propiedad estructural fundamental de la seguridad en sistemas multi-turno**.
- La capa de contención agnóstica (`fuse-ai`) es el diseño correcto: recibe cualquier señal de riesgo continua (sea de sensores textuales, embeddings o sondas $J$) y aplica la memoria acumulativa temporal donde los detectores instantáneos fallan.
