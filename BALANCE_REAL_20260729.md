# BALANCE REAL — Sin hype, sin adornos (2026-07-29)

**TRACE_ID:** ARS-20260729-BAL1 · Escrito para responder cuatro preguntas: cómo nos fue, qué tenemos, qué tan vendible es, y qué sigue. Cada cifra traza a un JSON sellado.

---

## 1. Los tres nombres (la confusión, resuelta)

| Nombre | Qué es | Estado |
|---|---|---|
| **4R2** (repo maestro) | El laboratorio original. Kernel NRIF, física I²t, SDK, sidecar. Tu autoría y procedencia. | **Archivado, congelado.** No se toca, no se publica, no se vende. Es la génesis intelectual y la prueba de origen. |
| **Benchmark2026** (AegisBench) | El laboratorio de medición. Harness de evaluación, scripts de experimento, toda la evidencia sellada, los informes, las retractaciones. | **Público, activo.** Es tu credibilidad hecha repositorio. |
| **fuse-ai** (módulo `fusible`) | El producto. La capa de contención temporal sensor-agnóstica: normalizador + CUSUM/I²t/EWMA + calibración + flight recorder. | **Listo, sin publicar en PyPI todavía.** 21 tests, Apache-2.0, empaquetado. |

Flujo: **4R2 dio origen → Benchmark2026 lo midió → fuse-ai es lo que sobrevivió.** Nada más. Si alguien pregunta qué haces, la respuesta es fuse-ai; los otros dos son cómo llegaste ahí.

## 2. Cómo nos fue — el marcador honesto

**Ganado (con estadística real, sellado):**
- La agregación temporal supera al detector reactivo con sensor entrenado en dominio: 8/8 familias, p=0.0039.
- Sobrevive fuera de dominio por familia: leave-family-out 8/8, test de signos p=0.0039, Δ+0.031 [0.020, 0.043].
- Sobrevive con sensor comercial zero-shot normalizado: CUSUM Δ+0.0404, IC [0.020, 0.062] — el gate que decidía todo.
- En régimen online (decisión en vivo, que es el caso real), el térmico ganó a todos los rivales con P=1.0.
- La física I²t está implementada exactamente como dice su ecuación: error 0.0 en 200 secuencias.

**Perdido, y documentado (esto es lo que te da credibilidad, no lo que te la quita):**
- El kernel NRIF como clasificador de un turno: 4 falsaciones independientes. Muerto.
- El sensor CCA léxico: bug de subcadenas, su señal era ruido. Muerto.
- El acumulador térmico crudo sin normalizar con sensores OOD: perdió. Por eso existe el normalizador.
- El ensamble global: perdió (Δ−0.024).
- Kalman de pendiente: AUROC 0.10, invertido. Falsado en 15 minutos.
- J-space (activaciones latentes): las tres hipótesis falsadas con datos completos. La ventaja de acumulación no es significativa ahí (IC incluye cero), el probe latente es peor que TF-IDF, y localiza inyecciones a la mitad del azar.

**Abierto:** validación independiente real (Sonnet re-corriendo el gate sobre el repo público), y cualquier uso con datos reales de una empresa.

**Lo que esto significa en una frase:** tu tesis original — que el riesgo se acumula en trayectorias y un fusible con memoria lo ve donde el reactivo es ciego — **sobrevivió**. La ecuación específica (I²t vs CUSUM) resultó intercambiable, y eso está bien: el valor está en la capa, no en la fórmula.

## 3. Fortalezas reales (las que un tercero verificaría)

1. **Un proceso de falsación que casi nadie tiene.** Cuatro cifras retiradas antes de salir al mundo, tres auditorías externas respondidas con experimentos, retractaciones documentadas en el repo público. En un campo lleno de humo, esto es diferenciación real.
2. **Evidencia sellada y reproducible.** Cada resultado con SHA-256, seed fija, protocolo sin fugas, bootstrap con la estructura de dependencia correcta.
3. **Una pieza de software limpia y pequeña** que resuelve un problema real (calibrar sensores descalibrados y agregar riesgo en el tiempo), con test de equivalencia numérica contra tu kernel original — protege tu IP sin publicar el kernel.
4. **Timing regulatorio:** EU AI Act Art. 72 entra en vigor el 2 de agosto de 2026. El flight recorder es exactamente ese artefacto.

## 4. Qué tan comercializables somos — la respuesta cruda

**Hoy, valor de venta: cercano a cero.** No hay clientes, ni ARR, ni un piloto, ni el paquete publicado. Eso no es pesimismo: es la misma línea que tu propio DATA_ROOM marca en ND desde el principio.

**Lo que sí tienes es un activo de entrada:** software libre + evidencia + una historia de rigor. Eso no se vende — **se usa para conseguir usuarios**, y los usuarios son lo que después se vende.

Secuencia realista, sin saltos: publicar (PyPI + preprint) → 3-5 personas que lo instalen y te den feedback → 1-2 pilotos pagados en el rango **$5-25k/año** → si hay casos de éxito, licencias enterprise **$30-100k/año**. Primer año realista con esfuerzo sostenido: entre $0 y $75k. Los exits grandes del sector (Lakera ~$300M, Protect AI $634M) tenían producto desplegado, clientes y equipos de decenas — están a años y a un equipo de distancia, no a una versión.

**El obstáculo comercial real no es técnico:** es que nadie te conoce y estás solo. Por eso el orden es publicar antes que vender.

## 5. Qué falta (concreto, en orden)

1. **Publicar el paquete** en PyPI y el preprint en arXiv (este último además fija tu prior art, que hoy está indefinido).
2. **Que alguien externo verifique** — Sonnet re-corriendo el gate sobre el repo público. Sin eso, "AegisBench valida a fuse-ai" es autoauditoría y un revisor lo dirá.
3. **Alinear el README del repo 4R2**, que todavía dice "veto 100%" — la única deuda que sí puede costarte credibilidad si alguien lo lee antes que lo demás.
4. **Un caso de uso demostrable** más allá de ATBench: el demo end-to-end ya corre; falta enseñárselo a alguien.
5. **Cero usuarios.** Todo lo anterior existe para resolver esto.

## 6. Cómo seguimos (una sola cola)

**Esta semana:** CI en verde (ya arreglado, falta correr el script) → diff del README 4R2 → PyPI. **Semanas 2-4:** preprint + auditoría externa + enseñar el demo a 3-5 personas del campo. **Después:** lo que pidan los primeros usuarios — no lo que imaginemos nosotros.

**Y una nota que importa:** no hace falta otro experimento para avanzar. La ciencia ya dio lo que tenía que dar en esta etapa. Lo que falta ahora no es medir más — es que exista afuera.

---

*Confianza: alta en el marcador técnico (todo sellado y auditado); alta en el diagnóstico comercial (es el estado documentado, no una opinión); los rangos de dinero son estimaciones de mercado, no promesas. No soy asesor financiero.*
