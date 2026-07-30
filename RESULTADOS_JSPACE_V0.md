# Resultados de Fase 4 — J-Space v0 (Dataset Completo: 9,009 Turnos)

**TRACE_ID:** ARS-20260729-JSP0  
**Fecha de Ejecución:** 2026-07-29  
**Modelo Probeta:** `Qwen/Qwen2.5-0.5B` (Hidden states de la última capa con Mean Pooling sobre los 9,009 turnos completos de ATBench)  
**Protocolo:** Out-of-Fold (5-fold cross-validation) por trayectoria (supervisión débil por etiqueta de trayectoria), normalización por cuantiles y agregación temporal online.  
**Archivo de Evidencia Sellado:** `evidence/jspace_probe_Qwen_Qwen2.5-0.5B_20260729.json`  
**SHA-256:** `2a43cd5935d4309f29e63645c5afe550764e14530a144375b95044e85c960935`

> [!NOTE]
> **Aviso de Retractación de la Versión Preliminar (PARCIAL-RETIRADA):**  
> La ejecución preliminar sobre el subconjunto de 4,889 turnos (54% del dataset, 7 familias) queda oficialmente marcada como **PARCIAL-RETIRADA** debido a truncamiento del cache de entrada. El presente documento contiene la evaluación definitiva sobre las **1,000 muestras íntegras de ATBench (9,009 turnos completados, 8 familias de riesgo completas y N=198 eventos de inyección en `environment`)**.

---

## 1. Veredicto de las Hipótesis Pre-registradas (Dataset Completo 9,009 Turnos)

| Hipótesis | Descripción | Resultado Empírico (9,009 turnos) | Veredicto |
| :--- | :--- | :--- | :--- |
| **H-J1** | **Acumulación Temporal en Espacio Latente $J$:** CUSUM sobre $J$ supera a detectores reactivos (Runmax). | CUSUM **0.8210** vs Runmax **0.8120** ($\Delta = +0.0088$, IC 95% = **[-0.0116, 0.0284]**; $P_{\text{mejora}} = 0.812$). Ganado en **5/8 familias** ($p = 0.36328$). | **FALSADA / NO ALCANZA SIGNIFICANCIA** *(IC incluye 0)* |
| **H-J2** | **Superioridad Absoluta de Representación $J$:** Los estados ocultos superan al sensor textual/TF-IDF. | Probe $J$ AUROC = **0.8210** vs Baseline TF-IDF sellado = **0.8760** ($\Delta = -0.0550$). | **FALSADA** *(Empírico)* |
| **H-J3** | **Localización Fina de Inyecciones:** El argmax del score latente identifica el turno exacto de inyección en `environment`. | Acierto en `environment` ($N=198$): **17.68%** (vs Tasa aleatoria base: **34.60%**). | **FALSADA** *(Empírico)* |

---

## 2. Métricas de Rendimiento Trayectoria (AUROC Online en $J$)

| Agregador Temporal | AUROC | $\Delta$ vs Runmax | IC 95% Bootstrap | $P_{\text{mejora}}$ |
| :--- | :--- | :--- | :--- | :--- |
| **CUSUM (Acumulativo)** | **0.8210** | **+0.0088** | **[-0.0116, 0.0284]** | **0.8120** |
| Runmax (Reactivo Baseline) | 0.8120 | 0.0000 | Ref. | — |
| Thermal ($I^2t$, $\tau=5$) | 0.8012 | -0.0112 | [-0.0212, -0.0019] | 0.0080 |
| EWMA ($\alpha=0.3$) | 0.7494 | -0.0626 | [-0.0915, -0.0310] | 0.0000 |
| Runmean (Promedio simple) | 0.7256 | -0.0864 | [-0.1180, -0.0520] | 0.0000 |

---

## 3. Desglose por las 8 Familias de Riesgo (CUSUM vs Runmax en $J$)

En **5 de 8 familias**, CUSUM superó ligeramente a Runmax, pero la ganancia global no alcanza significancia estadística unánime ($p = 0.36328$, prueba de signos unilateral):

| Familia de Riesgo | AUROC CUSUM | AUROC Runmax | $\Delta$ (CUSUM - Runmax) | Estado |
| :--- | :--- | :--- | :--- | :--- |
| `malicious_tool_execution` | **0.8876** | 0.8646 | **+0.0230** | ✅ CUSUM gana |
| `direct_prompt_injection` | **0.7646** | 0.7285 | **+0.0361** | ✅ CUSUM gana |
| `inherent_agent_failures` | **0.8307** | 0.8081 | **+0.0225** | ✅ CUSUM gana |
| `tool_description_injection` | **0.7732** | 0.7593 | **+0.0138** | ✅ CUSUM gana |
| `unreliable_or_misinformation` | **0.8153** | 0.8092 | **+0.0061** | ✅ CUSUM gana |
| `corrupted_tool_feedback` | 0.8124 | **0.8143** | **-0.0019** | ❌ Runmax gana |
| `indirect_prompt_injection` | 0.8451 | **0.8550** | **-0.0099** | ❌ Runmax gana |
| `malicious_user_instruction_or_jailbreak` | 0.8312 | **0.8445** | **-0.0133** | ❌ Runmax gana |

---

## 4. Análisis Crítico y Lección Científica Honesta

1. **H-J1 No Alcanza Significancia Estadística en Activaciones Crudas:**  
   Al evaluar el dataset completo de 9,009 turnos, la diferencia entre CUSUM (0.8210) y Runmax (0.8120) se reduce a $\Delta = +0.0088$. El intervalo de confianza bootstrap del 95% `[-0.0116, 0.0284]` incluye explícitamente el cero. Siguiendo nuestra regla estricta de rigurosidad (*"si el IC incluye cero, no se afirma victoria"*), declaramos H-J1 como **FALSADA / NO SIGNIFICATIVA** sobre activaciones latentes crudas sin filtrar.

2. **Ruido Espacial y Confounding en Activaciones de Última Capa (H-J2 Falsada):**  
   Las representaciones internas latentes de un LLM no entrenado específicamente para clasificación de seguridad contienen alta varianza atribuible a la longitud de la respuesta, patrones de sintaxis de herramientas y variabilidad temática. Un clasificador textual dedicado (como TF-IDF con AUROC 0.8760 o Llama Guard 3) actúa como un filtro de señal mucho más efectivo que una sonda lineal sobre activations crudas.

3. **Ceguera al Turno Puntual de Inyección (H-J3 Falsada):**  
   Con los $N=198$ eventos de inyección en `environment` evaluados en el dataset completo, la tasa de localización puntual por argmax fue de apenas **17.68%** (frente a un azar del **34.60%**). La distorsión latente introducida por la herramienta no se concentra de manera aislada en el turno de entrada, sino que se propaga y diluye en los turnos de razonamiento y acción del agente.

---

## 5. Conclusión de la Fase 4

- **Retractación Transparente:** Cumpliendo con el estándar de integridad científica del proyecto, la versión preliminar de 4,889 turnos queda descartada y sustituida por las mediciones completas de 9,009 turnos documentadas en este informe.
- **Confirmación del Enfoque del Producto (`fuse-ai`):** Las sondas latentes en activaciones crudas no sustituyen a los sensores de seguridad textuales deducidos. La capa de contención agnóstica de `fuse-ai` debe ser alimentada primordialmente por clasificadores de seguridad calibrados sobre texto (donde CUSUM sí demuestra superioridad estadísticamente significativa de $p=0.0039$ e IC que excluye el cero).
