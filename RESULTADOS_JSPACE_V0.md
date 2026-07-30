# Resultados de Fase 4 — J-Space v0 (Dataset Completo: 9,009 Turnos)

**TRACE_ID:** ARS-20260729-JSP0  
**Fecha de Ejecución:** 2026-07-29  
**Modelo Probeta:** `Qwen/Qwen2.5-0.5B` (Hidden states de la última capa con Mean Pooling sobre los 9,009 turnos completos de ATBench)  
**Protocolo:** Out-of-Fold (5-fold cross-validation) por trayectoria (supervisión débil por etiqueta de trayectoria), normalización por cuantiles y agregación temporal online.  
**Archivo de Evidencia Sellado:** `evidence/jspace_probe_Qwen_Qwen2.5-0.5B_20260729.json`  
**SHA-256:** `2a43cd5935d4309f29e63645c5afe550764e14530a144375b95044e85c960935`

> [!NOTE]
> **Aviso de Retractación de la Versión Preliminar (PARCIAL-RETIRADA):**  
> La ejecución preliminar sobre el subconjunto de 4,889 turnos (54% del dataset, 7 familias) queda oficialmente registrada como **PARCIAL-RETIRADA** debido a truncamiento del cache de entrada. El presente documento contiene la evaluación definitiva sobre las **1,000 muestras íntegras de ATBench (9,009 turnos completados, 8 familias de riesgo completas y N=198 eventos de inyección en `environment`)**.

---

## 1. Veredicto de las Hipótesis Pre-registradas (Alineado con Encabezado de Script)

| Hipótesis Pre-registrada | Planteamiento | Resultado Empírico (9,009 turnos) | Veredicto |
| :--- | :--- | :--- | :--- |
| **H-J1** | **Probe Latente vs Clasificador Textual:** El probe en $J$ supera al sensor textual/TF-IDF en AUROC de trayectoria. | Probe $J$ AUROC = **0.8210** vs Baseline TF-IDF sellado = **0.8760** ($\Delta = -0.0550$). | **FALSADA** *(Empírico)* |
| **H-J2** | **Ventaja de Acumulación Temporal en $J$:** CUSUM sobre $J$ supera a detectores reactivos sin memoria (Runmax). | CUSUM **0.8210** vs Runmax **0.8120** ($\Delta = +0.0088$, IC 95% = **[-0.0116, 0.0284]**; $P_{\text{mejora}} = 0.812$). Ganado en **5/8 familias** ($p = 0.36328$). | **FALSADA / NO SIGNIFICATIVA** *(IC incluye el 0)* |
| **H-J3** | **Localización Puntual de Inyecciones:** El argmax del score latente localiza el turno exacto de inyección en `environment`. | Acierto en `environment` ($N=198$): **17.68%** (vs Tasa aleatoria base: **34.60%**). | **FALSADA** *(Empírico)* |

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

## 3. Desglose por las 8 Familias de Riesgo (Mapeo Canónico de Datasets)

En **5 de 8 familias**, CUSUM superó a Runmax en el espacio latente, pero la ganancia global no alcanza significancia estadística unánime ($p = 0.36328$, prueba de signos unilateral).  
*Nota de Mapeo:* La etiqueta de risk_source `dummy_token` en el dataset crudo `atbench_test.jsonl` (61 trayectorias) corresponde formalmente a la categoría `malicious_user_instruction_or_jailbreak`.

| Familia de Riesgo (Dataset / Nombre Canónico) | AUROC CUSUM | AUROC Runmax | $\Delta$ (CUSUM - Runmax) | Estado |
| :--- | :--- | :--- | :--- | :--- |
| `malicious_tool_execution` | **0.8876** | 0.8646 | **+0.0230** | ✅ CUSUM gana |
| `indirect_prompt_injection` | 0.8451 | **0.8550** | **-0.0099** | ❌ Runmax gana |
| `dummy_token` (`malicious_user_instruction_or_jailbreak`) | 0.8312 | **0.8445** | **-0.0133** | ❌ Runmax gana |
| `inherent_agent_failures` | **0.8307** | 0.8081 | **+0.0225** | ✅ CUSUM gana |
| `unreliable_or_misinformation` | **0.8153** | 0.8092 | **+0.0061** | ✅ CUSUM gana |
| `corrupted_tool_feedback` | 0.8124 | **0.8143** | **-0.0019** | ❌ Runmax gana |
| `tool_description_injection` | **0.7732** | 0.7593 | **+0.0138** | ✅ CUSUM gana |
| `direct_prompt_injection` | **0.7646** | 0.7285 | **+0.0361** | ✅ CUSUM gana |

---

## 4. Análisis Crítico y Lección Metodológica

1. **Lección Metodológica: El Peligro de los Subconjuntos Truncados:**  
   En la corrida preliminar truncada a 4,889 turnos (54% del dataset), el incremento $\Delta$ del CUSUM mostraba un IC del 95% de `[+0.0004, +0.0567]` que parecía excluir el cero por un estrecho margen. Sin embargo, al completar la evaluación sobre los 9,009 turnos completos (incluyendo la familia `dummy_token` / jailbreak), el intervalo bootstrap se corrigió a **`[-0.0116, +0.0284]`**, demostrando empíricamente que la ventaja no es estadísticamente significativa en activaciones crudas. Este contraste constituye un caso de estudio metodológico de por qué los subconjuntos truncados inducen a falsos positivos.

2. **Ruido Espacial y Confounding en Activaciones de Última Capa (H-J1 Falsada):**  
   Las representaciones internas latentes de un LLM no entrenado específicamente para clasificación de seguridad contienen alta varianza atribuible a la longitud de la respuesta, patrones de sintaxis de herramientas y variabilidad temática. Un clasificador textual dedicado (como TF-IDF con AUROC 0.8760) actúa como un filtro de señal mucho más efectivo que una sonda lineal sobre activaciones crudas mean-pooled.

3. **Deriva Temporal vs Localización Puntual (H-J3 Falsada):**  
   Con los $N=198$ eventos de inyección en `environment` evaluados en el dataset completo, la tasa de localización puntual por argmax fue de apenas **17.68%** (frente a un azar del **34.60%**). La distorsión latente introducida por la herramienta no se concentra de manera aislada en el turno de entrada, sino que se propaga y diluye en los turnos de razonamiento y acción del agente.

---

## 5. Conclusión de la Fase 4 y Respaldo al Diseño del Producto

- **Retractación Transparente:** La versión preliminar de 4,889 turnos queda descartada y sustituida por las mediciones completas de 9,009 turnos documentadas en este informe.
- **Confirmación del Enfoque del Producto (`fuse-ai`):** Las sondas latentes en activaciones crudas no sustituyen a los sensores de seguridad textuales deducidos. La capa de contención agnóstica de `fuse-ai` debe ser alimentada primordialmente por clasificadores de seguridad calibrados sobre texto (donde CUSUM sí demuestra superioridad estadísticamente significativa de $p=0.0039$ e IC que excluye el cero).
