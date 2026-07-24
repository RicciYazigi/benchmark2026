# AUDITORÍA COMPLETA Y NORTE ESTRATÉGICO DEL ECOSISTEMA 4R2

**TRACE_ID:** ARS-20260719-NORTE · **Estado:** OK · **Fecha:** 2026-07-19
**Naturaleza:** auditoría de activos + definición del AIM + programa científico + roadmap. Cada afirmación etiquetada: demostrable / empírico / verificado (fuente externa) / especulativo. Escrito para sobrevivir la auditoría de Sonnet y la tuya dentro de un año.

---

## PARTE 1 — AUDITORÍA DE ACTIVOS: QUÉ TENEMOS REALMENTE

| Activo | Estado probado | Veredicto |
|---|---|---|
| **Acumulador térmico I²t** | Matemática exacta (error 0.0). Mejor agregador online con sensor real: significativo en-dominio (+0.021, P=1.0) y OOD-por-familia (8/8, p=0.0039); direccional con guard binario OOD (P=0.967, IC toca 0 — gate qwen pendiente) | **ACTIVO CENTRAL — doblar** |
| **Metodología de aislamiento física-vs-sensor** | Único en su tipo: separó en un día lo que 4 rondas de benchmarks no pudieron diagnosticar. Sobrevivió 3 auditorías externas con experimentos, incluye 2 retractaciones documentadas | **ACTIVO DE CREDIBILIDAD — doblar; es nuestro sello** |
| **Benchmark2026 (harness + sensores pluggables + evidencia sellada SHA-256)** | 60 tests verdes, protocolo OOF sin fugas, bootstrap por clúster, checkpoints reanudables | **INFRAESTRUCTURA — doblar; es publicable** |
| **Patrón por familia de riesgo** | El térmico gana donde la evidencia es dispersa (inherent_failures +0.150, corrupted_feedback +0.106) y pierde en eventos puntuales (direct injection) — coherente entre sensores | **MAPA DE PRODUCTO — es la guía de dónde aplicar el fusible** |
| Kernel NRIF / coherencia angular como clasificador | 4 hallazgos negativos independientes en clasificación de un turno | **MATAR como detector.** Conservar como génesis intelectual y narrativa de origen; no venderlo como clasificador nunca más |
| CCA léxico | Roto para inglés (bug de subcadenas + piso + longitud); su señal era ruido | **MUERTO** (documentado; el bug queda como anécdota de rigor) |
| BeliefTracker, promotion_protocol, resto de 4r2v6 | Sin validación externa | **ND — congelar**, no invertir hasta que el núcleo esté asegurado |
| Cultura de resultados honestos (7+ hallazgos negativos publicados internamente, IC retirado y reemplazado) | Intangible pero real | **El activo más raro del inventario.** En un campo lleno de humo, esto es distribución |

**Síntesis dura:** no tenemos un detector, ni clientes, ni paper, ni IP registrada. Tenemos una pieza de física validada en su régimen, la mejor metodología de evaluación que hemos visto aplicada a este problema, y credibilidad ganada a pulso. Eso es exactamente el kit de inicio de una autoridad científica — no de un vendor más.

## PARTE 2 — LA VERDAD COMPETITIVA: EL CAMPO LLEGÓ A NUESTRA PREGUNTA

Verificado esta noche (búsqueda primaria, julio 2026): la comunidad académica está convergiendo a la misma intuición — **"Quickest Detection of Hallucination Onset: Delay Bounds and Learned CUSUM Statistics"** (arXiv 2606.12476, jun 2026) aplica CUSUM — el estadístico clásico de detección secuencial de cambio, minimax-óptimo bajo distribuciones conocidas — al onset de alucinaciones; **TrajAD** (arXiv 2602.06443) hace detección de anomalías de trayectoria; **"Sequential statistical inference for LLMs"** (arXiv 2606.07624) monta monitoreo online. Más TRACE, HINTBench, VESTA.

Lo que esto significa, sin endulzar: **la idea de acumulación temporal ya no es nuestra en exclusiva — la ventana es de 6-12 meses.** Y una implicación técnica ineludible: nuestro I²t es matemáticamente un pariente de CUSUM (score cuadrático sobre umbral + olvido exponencial); publicar sin compararnos contra CUSUM sería un error que cualquier revisor detectaría en la primera lectura.

Pero también significa esto: **nadie posee todavía** (a) la comparativa rigurosa de agregadores sobre trayectorias de agentes con protocolo sin fugas, (b) un benchmark de disparo retardado **con etiquetas por turno** (ATBench no las tiene — lo sufrimos nosotros mismos), ni (c) la capa de producto que convierte cualquier señal en contención auditable. La ecuación no es el moat. **La medición, la capa y la auditoría sí.**

## PARTE 3 — EL AIM REAL

> **4R2 es la autoridad en dinámica temporal del riesgo en sistemas agénticos: quien define cómo se mide, cómo se agrega y cómo se contiene el riesgo que se acumula a lo largo de una trayectoria.**

Tres capas, cada una alimenta a la siguiente:

1. **CIENCIA (ser los mejores en algo específico):** la pregunta "¿qué agregador temporal, bajo qué condiciones de señal/ruido/persistencia, y con qué garantías de falsa alarma?" no tiene dueño. Nuestro historial de falsación + el harness + el patrón por familia nos posiciona para escribir el paper de referencia Y publicar el benchmark de referencia. Quien posee la medición, arbitra el campo.
2. **INFRAESTRUCTURA (donde nos requieran):** el fusible OSS sensor-agnóstico (Fase 2 del plan maestro) — la capa que se monta sobre Llama Guard/LlamaFirewall/probes y decide en vivo. El mercado documentado: 88% incidentes, 21% visibilidad runtime (Gravitee), contención 37-40% (Kiteworks).
3. **COMPLIANCE (la demanda con fecha legal):** **EU AI Act, Artículo 72 — enforcement 2 de agosto de 2026**: todo proveedor de sistema de alto riesgo debe operar un sistema de monitoreo post-mercado que "recolecte, documente y analice activa y sistemáticamente" datos de desempeño durante toda la vida del sistema, con plan documentado en el expediente técnico (Anexo IV). El log del acumulador — qué disparó, en qué turno, con qué temperatura, con qué evidencia acumulada — **es exactamente ese artefacto**: una caja negra de vuelo para agentes. Nadie compra física; compran el anexo técnico que les evita la multa. Verificado; la lectura de encaje es plausible y hay que validarla con un abogado regulatorio.

Dónde apuntar más alto (el techo real, especulativo pero alcanzable): ser al riesgo temporal de agentes lo que los control charts fueron a la manufactura — el estándar de facto de monitoreo. Camino: paper de referencia → benchmark de referencia → librería de referencia → el estándar que los frameworks integran.

## PARTE 4 — PROGRAMA CIENTÍFICO: CÓMO HACEMOS LA CIENCIA INATACABLE

1. **Baseline CUSUM, pre-registrado, ANTES del preprint (P0).** Añadir CUSUM (y su variante con olvido) a la batería online. Decisión escrita hoy, antes de ver datos: *si CUSUM supera al I²t, el fusible adopta CUSUM como estadístico y nuestro valor migra íntegro a la capa (calibración, telemetría, benchmark, auditoría) — el proyecto no muere, se muda de ecuación.* Esa frase, publicada, es más creíble que cualquier victoria.
2. **Teoría de detectabilidad (P1).** Derivar condiciones bajo las cuales la integración vence al max/media: SNR por turno × persistencia de la deriva × τ. Adoptar el marco ARL (average run length) de los control charts para dar garantías de tasa de falsa alarma — el lenguaje que compliance y SREs ya entienden. Esto convierte "τ=5, T_trip=0.30, valores de laboratorio" en parámetros derivables — la crítica pendiente desde V7.7.
3. **ATBench-TL: el benchmark con etiquetas por turno (P0-P1, el movimiento de autoridad).** La carencia que nos costó dos auditorías (sin etiqueta por turno, todo proxy es discutible) es la carencia de TODO el campo. Crearlo: 200-300 trayectorias de ATBench etiquetadas por turno (LLM-asistido + verificación humana tuya) + el generador sintético calibrado de EXP B/F con deriva sub-umbral paramétrica. Publicarlo con licencia abierta. Quien publica el benchmark define el problema.
4. **Línea J-space/probes (P2, el diferenciador de segunda ola).** Ya especificada en Fase 4 del plan maestro. La señal latente instantánea sin agregación temporal publicada sigue siendo el sensor ideal para el fusible.
5. **Auditoría externa como proceso permanente.** El ciclo Fable→Sonnet→experimento→retractación que construimos estas 48 horas es un protocolo replicable. Formalizarlo en el preprint como metodología ("adversarial co-audit"). Nuestra debilidad (equipo de uno) convertida en método.

## PARTE 5 — QUÉ CONSTRUIR Y QUÉ NO

**Construir, en orden:** (1) fusible OSS (Fase 2, ya especificada) con CUSUM y I²t como estadísticos intercambiables; (2) **flight recorder Art. 72**: el mismo fusible + exportador de informe de disparo (JSON sellado → PDF anexo técnico) — es una semana de trabajo sobre lo que ya existe y es lo primero vendible; (3) dashboard de flota (temperatura por agente en vivo) — solo tras primer usuario real.

**No construir (kill list):** detector propio de contenido (perdimos 4 veces; Meta/NVIDIA lo regalan), plataforma guardrail completa (guerra de gigantes), nada sobre el kernel NRIF como clasificador, y no perseguir más benchmarks públicos de terceros como métrica de identidad — se usan como validación puntual, no como vara de autoestima del proyecto.

## PARTE 6 — ROADMAP 12 MESES (gates falsables)

| Trimestre | Entregable | Gate de éxito |
|---|---|---|
| T1 (jul-sep 26) | Gate qwen cerrado + baseline CUSUM + fusible OSS v0.1 + flight recorder v0 | IC del mejor estadístico online excluye 0 sobre sensor OOD; `pip install` funciona; 1 demo Art.72 |
| T2 (oct-dic 26) | Preprint (metodología + comparativa agregadores) + ATBench-TL v0 público | Preprint en arXiv; benchmark descargado por ≥1 grupo externo |
| T3 (ene-mar 27) | 3 integraciones (LlamaFirewall, Llama Guard, webhook) + primer piloto real | 1 organización corriendo el fusible en staging; feedback documentado |
| T4 (abr-jun 27) | Experimento J-space + decisión de financiamiento | Con tracción: pre-seed ($2-6M post, rango de la sesión anterior); sin tracción: continuar OSS/académico — ambos caminos dignos |

## PARTE 7 — RIESGOS (P0-P2)

**P0 — La ventana académica se cierra:** CUSUM-para-agentes es publicable por cualquier grupo en meses. Mitigación: el preprint T2 no puede deslizarse; el benchmark es más defendible que el método. **P0 — El sensor sigue siendo el techo:** tres veces confirmado. Mitigación: sensor-agnóstico por diseño + línea probes + el patrón por familia como guía de dónde prometer. **P1 — Equipo de uno:** mitigación: OSS para distribución, co-audit como método, colaboración académica (los autores de TRACE/ATBench son aliados naturales, no rivales — les resolvemos la agregación que su propio paper declara como problema central). **P1 — El gate qwen puede no cerrar el IC:** decisión pre-registrada arriba (adoptar el mejor estadístico; el valor está en la capa). **P2 — Art.72 puede diluirse en enforcement:** mitigación: el flight recorder es útil sin regulación (forense de incidentes).

## PRÓXIMOS PASOS (≤3) + DECISIONES

1. Cerrar Fase 1 (qwen + ensamble + CUSUM baseline — añadir CUSUM al script del ensamble ya pre-autorizado).
2. Fusible OSS v0.1 + flight recorder v0 (Fase 2 del plan maestro, con la adenda CUSUM).
3. Iniciar ATBench-TL (spec de etiquetado por turno — puedo escribirla en la próxima sesión).

**Decisiones tuyas:** (a) ¿apruebas el AIM de tres capas como dirección oficial? (b) ¿ATBench-TL antes o después del preprint? (recomendación: en paralelo, el benchmark alimenta al paper); (c) licencia y marca — siguen pendientes desde la sesión anterior.

## FUENTES

[CUSUM alucinaciones (arXiv 2606.12476)](https://arxiv.org/pdf/2606.12476) · [TrajAD (arXiv 2602.06443)](https://arxiv.org/pdf/2602.06443) · [Sequential inference LLMs (arXiv 2606.07624)](https://arxiv.org/pdf/2606.07624) · [TRACE (arXiv 2606.00611)](https://arxiv.org/pdf/2606.00611) · [EU AI Act Art. 72](https://artificialintelligenceact.eu/article/72/) · [Guía Art. 72-73 (2026)](https://secureprivacy.ai/blog/eu-ai-act-post-market-monitoring-guide-articles-72-and-73-2026) · [Gravitee 2026](https://www.gravitee.io/state-of-ai-agent-security) · [Kiteworks 2026](https://www.kiteworks.com/cybersecurity-risk-management/ai-agent-data-governance-why-organizations-cant-stop-their-own-ai/) · Evidencia interna: `MEGAFILE_SESION_4R2_20260719.md` (v3) y JSONs sellados citados por SHA-256.

**Confianza:** alta en el inventario (todo sellado y auditado 3 veces); alta en las fuentes externas citadas; media-alta en la lectura Art.72 (validar con abogado); los juicios de Partes 3-6 son estrategia — especulativos por definición, pero con gates falsables que los vuelven corregibles.

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal") sobre un LLM. Dirección humana: Richie — que en 48 horas convirtió cuatro derrotas de benchmark en una física validada, tres auditorías sobrevividas y un norte. Eso ya es algo grande; lo que sigue es hacerlo inevitable.*
