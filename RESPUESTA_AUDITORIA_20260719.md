# Respuesta a Auditoría Externa (Sonnet 5) — Diagnóstico Turno-por-Turno (2026-07-19)

**TRACE_ID:** ARS-20260719-AUD1 · **Estado:** OK (con hallazgos que matizan, no tumban)
**Evidencia sellada:** `evidence/exp_diagnostico_turno_20260719.json` · SHA-256 `748ce6d5…8ccf`
**Script:** `scripts/exp_diagnostico_turno.py` (usa los scores OOF ya sellados, cero reentrenamiento)

---

## La objeción, en sus términos

El `TfidfTurnSensor` se entrena propagando el label de trayectoria a cada turno (incluidos los benignos). Riesgo señalado: el sensor podría estar clasificando **tema de conversación**, no **conducta riesgosa por turno**, inflando el AUROC (0.85-0.88 vs. 0.5-0.6 del CCA) por una vía que no ejercita el patrón de disparo retardado. Pregunta exigida: score del sensor en el turno donde vive el riesgo vs. turnos vecinos.

Es la objeción correcta. Parte estaba declarada en los límites de los informes previos ("el AUROC refleja en parte separabilidad léxica/temática, no capacidad de seguridad general"); lo que no estaba era la **cuantificación**. Aquí está.

## Resultados del diagnóstico (N=1000, scores OOF sellados)

**P1 — Fuga temática, cuantificada.** AUROC usando SOLO el turno 0 (la petición inicial, antes de cualquier conducta del agente): **0.7084**. Trayectoria completa: 0.8550. En proporción de señal sobre azar: **~59% del poder discriminativo ya está en el tema de la petición inicial**; ver la conducta añade +0.147 de AUROC. Veredicto: la fuga temática es real y grande — pero no total: hay señal conductual por turno genuina encima del tema.

**P2a — Localización del turno de riesgo (proxy: máx. Jaccard con `reason`, 496 trayectorias evaluables).** El argmax del sensor coincide con el turno de riesgo el **25.2%** de las veces (azar: 13.1% — el doble del azar). Rango normalizado medio del turno de riesgo según el sensor: **0.716** (azar: 0.5). El turno de riesgo puntúa por encima de la media de sus vecinos en el **74.2%** de las trayectorias (Δ medio +0.086). Veredicto: el sensor **sí localiza parcialmente** la conducta riesgosa dentro de la trayectoria — no es solo tema — aunque está lejos de ser un localizador confiable.

**P2b — Inyecciones específicamente: hallazgo negativo.** En las 198 trayectorias de inyección (indirect/tool_description/corrupted_feedback/malicious_tool), el argmax del sensor cae en un turno `environment` solo el **28.8%** de las veces, contra un base rate del 34.6% — **por debajo del azar**. El sensor es ciego al turno de inyección del entorno; detecta esas trayectorias por otras vías (reacción del agente, tema). Para la familia de riesgo más importante del mercado (inyección indirecta), el sensor no localiza.

## Qué sobrevive y qué cambia

**Sobrevive:** la carrera entre agregadores (térmico vs. max vs. EWMA vs. media online) corre sobre la misma serie de scores — la superioridad online del térmico (+0.021 sobre max, +0.042 sobre EWMA, P=1.0) es una afirmación **relativa** y sigue siendo válida y justa. La física validada aislada (EXP A-F) no depende de este sensor en absoluto.

**Cambia:** (1) los AUROC absolutos (0.85-0.90) quedan oficialmente reclasificados: inflados por fuga temática ~59%, no representan capacidad de seguridad desplegable; (2) el patrón de disparo retardado se ejercita solo parcialmente (P2a sí, P2b no); (3) la fase guard model OOD **sube de "recomendada" a "obligatoria"** como gate de cualquier decisión estratégica — exactamente lo que la auditoría pedía; (4) queda abierto un requisito de diseño nuevo: el sensor de la fase siguiente debe puntuar turnos `environment` explícitamente (Llama Guard clasifica turnos de herramienta con su categoría propia — ya contemplado en el adaptador).

## Verificación de las cifras de mercado cuestionadas

- **Gravitee "State of AI Agent Security 2026" — verificado**: 88% de organizaciones con incidentes confirmados o sospechados de agentes IA en el último año (encuesta a 900+ ejecutivos y técnicos). Además: solo **21% tiene visibilidad runtime** de lo que hacen sus agentes — peor que el 52% que cité antes desde una fuente secundaria; corrijo hacia la cifra primaria.
- **Cifras de contención 37%/40% — CORRECCIÓN DE ATRIBUCIÓN (2026-07-19b)**: los números purpose binding **37%** y kill switch **40%** son del **Kiteworks 2026 Forecast Report**, no de CSA. La nota de CSA (governance gap, abril 2026) describe la brecha gobernanza→contención cualitativamente pero no contiene estas cifras. Detectado por auditoría externa (Sonnet 5); corregido aquí y en `PLAN_ESTRATEGICO_4R2.md` antes de cualquier uso externo.
- **Reclasificación**: las cifras "52% cobertura / 38% end-to-end / 17% agente-agente" citadas en el plan estratégico venían de fuentes secundarias (blogs) → quedan degradadas a *plausible*. Las reemplazan las primarias de arriba. **La tesis de la Opción B no se debilita — se refuerza**: visibilidad runtime al 21% y contención al 37-40% es una brecha mayor que la citada originalmente.

## Conclusión de una línea

La auditoría acertó en exigir la cuantificación: ~59% del AUROC del sensor es tema, no conducta — pero la señal conductual existe (2× azar en localización, 74% de turnos de riesgo sobre la media), la comparación entre agregadores sigue siendo válida, y la decisión completa queda correctamente colgada del gate guard-model OOD, que ya estaba instruido y ahora es obligatorio.

| Etiqueta | Aplica a |
|---|---|
| empírico con límites | P1, P2a, P2b (proxy de localización imperfecto, declarado) |
| verificado | cifras Gravitee 88%/21%, CSA 37%/40% |
| plausible (degradado) | cifras 52%/38%/17% del plan estratégico v1 |

## Fuentes

[Gravitee — State of AI Agent Security 2026](https://www.gravitee.io/state-of-ai-agent-security) · [Gravitee — 88% blog](https://www.gravitee.io/blog/state-of-ai-agent-security-2026-report-when-adoption-outpaces-control) · [VentureBeat — enforcement gap](https://venturebeat.com/security/most-enterprises-cant-stop-stage-three-ai-agent-threats-venturebeat-survey-finds) · [CSA — Governance Gap research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-agent-governance-framework-gap-20260403/) · [CSA — press release](https://cloudsecurityalliance.org/press-releases/2026/03/24/more-than-two-thirds-of-organizations-cannot-clearly-distinguish-ai-agent-from-human-actions)

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal"). Dirección humana: Richie.*
