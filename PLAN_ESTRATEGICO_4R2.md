# Plan Estratégico 4R2 — ¿Guardrail, Pivote o Nicho? (2026-07-18)

**TRACE_ID:** ARS-20260718-EST1 · **Estado:** OK
**Naturaleza:** análisis estratégico fundamentado en (a) evidencia técnica propia sellada de esta sesión y (b) investigación de mercado con fuentes citadas. Etiquetas: verificado (fuente externa) / empírico (medido aquí) / especulativo (juicio estratégico).

---

## 1. Qué es lo que realmente tenemos (inventario honesto, post-ciclo)

Un **agregador temporal de riesgo validado en régimen online** (empírico): con el mismo sensor, el fusible térmico I²t supera a max reactivo, EWMA y media acumulada en decisión en vivo (AUROC 0.876, +26% de detección a FPR 5% vs. reactivo, P=1.0). No tenemos: un detector propio competitivo (el sensor es la pieza intercambiable), un producto, clientes, ni IP patentada. La honestidad del proceso (7 hallazgos negativos documentados y sellados) es en sí un activo de credibilidad técnica.

## 2. El mapa competitivo (verificado, julio 2026)

- **Detectores/plataformas guardrail**: campo saturado y ya consolidándose por adquisición — Lakera→Check Point (~$300M), Protect AI→Palo Alto ($634M), Prompt Security→SentinelOne, Aim→Cato, Apex→Tenable. Meta regala LlamaFirewall (PromptGuard, alignment checks, CodeShield); NVIDIA regala NeMo Guardrails. **Competir aquí de frente como "otro guardrail" es entrar tarde a una guerra de gigantes con producto gratis en la mesa.**
- **El hueco real está documentado** *(atribuciones corregidas 2026-07-19 tras auditoría externa)*: 88% de organizaciones con incidentes de agentes y solo **21% con visibilidad runtime** (Gravitee, encuesta 900+ — verificado); purpose binding en solo **37%** y kill switch en solo **40%** (**Kiteworks 2026 Forecast Report** — verificado; la nota de CSA sobre el governance gap describe la misma brecha cualitativamente, sin estas cifras). Es decir: sobran detectores, **falta la capa que convierte detecciones ruidosas en decisiones de contención en vivo**.
- **J-space (Anthropic, julio 2026, verificado)**: existe un espacio latente de trabajo ("Verbalizable Representations Form a Global Workspace in Language Models") sondeable con J-lens que emite señales internas por instante ("injection", "manipulation") aunque la salida se vea normal. Señal instantánea, ruidosa, sin agregación temporal publicada. **La intuición de moverse a ese terreno es correcta y es exactamente complementaria a lo nuestro.**

## 3. Opciones sobre la mesa (trade-offs explícitos)

**A. Ser un guardrail completo (detector + política + plataforma).** Descartado: campo saturado, incumbentes regalando el detector, y nuestra evidencia dice que el detector no es nuestra fortaleza. Especulativo pero de baja incertidumbre.

**B. Capa de agregación temporal sensor-agnóstica ("el fusible de contención") — RECOMENDADA.** No competimos con LlamaFirewall/Llama Guard/NeMo: **nos montamos encima de cualquiera de ellos**. Producto: librería OSS ligera (el acumulador + calibración + telemetría del turno de disparo) con adaptadores para los detectores populares, vendiendo después la capa enterprise (calibración por flota, kill-switch, auditoría del "por qué disparó y cuándo"). Ataca exactamente la brecha gobernanza→contención documentada. La evidencia técnica de esta sesión ES el pitch: "a FPR igualado, +26% de cobertura sobre el mismo detector que ya usas, decidiendo en vivo". Requiere: fase guard model (validación OOD, ya instruida) + 2-3 adaptadores + demo.

**C. Línea J-space: sondas latentes como sensor (el pivote de investigación, mediano plazo).** Sensores = probes lineales sobre activaciones de un modelo abierto local (Llama/Qwen); el acumulador integra esa señal ruidosa por instante en decisión de trayectoria. Nadie ha publicado agregación temporal sobre señales de interpretabilidad — hueco real y publicable. Límite: requiere acceso white-box (solo modelos abiertos o labs). No es el producto de corto plazo; es el diferenciador de mediano plazo y el paper fuerte. Especulativo, alto potencial.

**D. Nicho fuera de LLMs (fraude, insider threat, OT/ICS).** La física aplica (secuencias, deriva sub-umbral), los mercados son maduros… y por eso mismo tienen incumbentes de décadas (Splunk, Darktrace). Sin ventaja de distribución ni dominio, es más difícil que B. Mantener como opción si B encuentra tracción en un vertical específico.

## 4. Recomendación (una línea)

**No somos un guardrail y no hay que pivotar de problema: hay que reposicionar la pieza — 4R2 es la capa de contención temporal, sensor-agnóstica, que el mercado de detectores saturado no tiene; B ahora con la fase guard como gate, C como segunda ola.**

## 5. Secuencia ejecutable (90 días, gates falsables)

1. **Gate 1 (semanas 1-2)**: fase guard model OOD (`INSTRUCCIONES_FASE_GUARD_MODEL.md`). Si el térmico mantiene su ventaja online con sensor fuera de dominio → luz verde a todo lo demás. Si no → el hallazgo se documenta y B se re-evalúa con sensor híbrido antes de invertir más.
2. **Semanas 3-6**: extraer el acumulador + calibración a una librería instalable (`pip install`), con 3 adaptadores: Llama Guard (ollama), LlamaFirewall/PromptGuard, y webhook genérico. Demo reproducible con ATBench. README con las tablas de esta sesión.
3. **Semanas 7-10**: preprint corto (los resultados online + la metodología de aislamiento física-vs-sensor son publicables tal cual) + lanzamiento OSS. La credibilidad técnica es el canal de distribución de un fundador solo.
4. **Semanas 11-13**: experimento J-space v0 (probe lineal sobre Llama-3.2-1B local alimentando el acumulador, spec en sección 3.C) — decide si C se convierte en la tesis de producto de la siguiente etapa.

**Decisiones a confirmar contigo:** (1) ¿B como dirección oficial? (2) ¿OSS con licencia permisiva (Apache-2.0) o proteccionista (BSL)? (3) ¿El preprint lleva tu nombre/marca personal o marca de empresa?

## Fuentes

- [Galileo — Best AI Agent Guardrails 2026](https://galileo.ai/blog/best-ai-agent-guardrails-solutions) · [LlamaFirewall (arXiv)](https://arxiv.org/html/2505.03574v1) · [NeMo Guardrails (GitHub)](https://github.com/NVIDIA-NeMo/Guardrails)
- [Gravitee — State of AI Agent Security 2026](https://www.gravitee.io/state-of-ai-agent-security) · [Kiteworks — AI Agent Data Governance (cifras 37%/40%)](https://www.kiteworks.com/cybersecurity-risk-management/ai-agent-data-governance-why-organizations-cant-stop-their-own-ai/) · [CSA — AI Agent Governance Gap (cualitativo)](https://labs.cloudsecurityalliance.org/research/csa-research-note-ai-agent-governance-framework-gap-20260403/) · [VentureBeat — The enforcement gap](https://venturebeat.com/security/most-enterprises-cant-stop-stage-three-ai-agent-threats-venturebeat-survey-finds)
- [Check Point adquiere Lakera](https://www.checkpoint.com/press-releases/check-point-acquires-lakera-to-deliver-end-to-end-ai-security-for-enterprises/) · [GeekWire — Palo Alto/Protect AI](https://www.geekwire.com/2025/palo-alto-networks-to-acquire-seattle-cybersecurity-startup-protect-ai/)
- [DataScienceDojo — Anthropic J-Space](https://datasciencedojo.com/blog/anthropic-j-space-explained/) · [MindStudio — J-Space explained](https://www.mindstudio.ai/blog/what-is-anthropic-j-space-global-workspace-claude)

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal"). Dirección humana: Richie. Confianza: alta en evidencia propia; media en cifras de mercado de terceros; los juicios estratégicos son especulativos por naturaleza.*
