# PLAN DE PUBLICACIÓN — Apache-2.0 confirmado (2026-07-22)

**TRACE_ID:** ARS-20260722-PUB1 · **Estado:** OK · Decisión de Richie registrada: **núcleo Apache-2.0 + capa compliance propietaria futura**.
Este documento es la secuencia exacta post-gate-verde. Etapas A→D en orden; Antigravity ejecuta A-B, Richie hace los pasos marcados 👤, y el push (C) requiere autorización explícita de Richie por las reglas de sesión.

---

## AUDITORÍA PREVIA (hecha por Fable hoy, con acceso local — contexto para todos)

1. **Degeneración llama-guard 0.5000 — RESUELTA.** Causa raíz medida sobre el cache real: llama-guard3:1b flaggea el **79.4% de todos los turnos** (78.4% de los benignos). Con esa masa, el p90 benigno normalizado cae exactamente sobre el nivel del flag (0.6078) → θ = k_ref = nivel flag → energía y paso CUSUM = 0 por construcción → AUROC 0.5000 exacto. La hipótesis de empates de Sonnet era direccionalmente correcta; la causa profunda es un **sensor casi constante en este dominio** (sin información: su runmax 0.501 ya lo decía). Veredicto: caso cerrado como "sensor inservible en dominio agéntico", NO como bug del pipeline.
2. **Blindaje añadido al producto:** `fusible.robust_reference()` — si el percentil de calibración cae sobre el nivel máximo de la referencia, devuelve el punto medio entre los dos niveles superiores (el flag vuelve a aportar energía). Con sensores sanos es idéntico al percentil normal. **21/21 tests verdes** (2 nuevos, incluido el que reproduce la distribución real sellada).
3. **Matiz del ensamble (pedido por Sonnet, aceptado):** el hallazgo negativo (Δ−0.024, P=0.001) aplica a UNA regla de mezcla (promedio de rangos global). La hipótesis de apilado por familia/régimen queda abierta, no refutada. Así debe quedar redactado en todo material.
4. **Cache 8954 vs 8953:** +1 entrada por los smoke tests (turnos de prueba cacheados). Cosmético; documentado aquí, no requiere acción.
5. **Tasa de éxito global del proyecto** (todo sellado SHA-256): física exacta demostrada (error 0.0), pipeline sano (oráculo 0.97), en-dominio 8/8 familias p=0.0039, online en-dominio térmico primero con P=1.0, OOD real: CUSUM normalizado > runmax con IC [0.020, 0.062] excluyendo cero (gate VERDE legítimo), y 3 hallazgos negativos honestos documentados (térmico crudo OOD, kalman_slope, ensamble global). 21+60 tests verdes en las dos suites.

---

## ETAPA A — Cierres técnicos previos (Antigravity; archivos nuevos pre-autorizados)

1. Crear `ANEXO_DEGENERACION_LLAMAGUARD.md` con el diagnóstico del punto 1 de arriba + el output del comando de verificación (correr: fracción de 1.0 en cache, niveles normalizados, θ/k_ref — el script está en la transcripción de Fable de hoy). NO editar `RESULTADOS_ATBENCH_GUARD_FASE15.md` sin diff aprobado; si contiene la frase "el térmico logra ganar" sin matiz de IC, o generaliza el ensamble, proponer el diff a Richie.
2. Correr la suite completa una vez más y pegar: `cd fusible; python -m pytest tests/ -q` (esperado **21 passed**) y la suite del repo (esperado 60 passed).
3. Commit local: `fix(fusible): robust_reference blinda calibracion contra sensores degenerados (caso llama-guard 79% flag-rate) + anexo diagnostico`.

## ETAPA B — Licencia y paquete (Antigravity ejecuta, Richie decide el nombre)

1. 👤 **Richie verifica el nombre** (ND desde sandbox): abrir `https://pypi.org/project/fusible/` — si da 404, el nombre está libre; si existe, usar **`fusible-ai`**. Comunicar la decisión.
2. Crear `fusible/LICENSE` con el texto estándar Apache-2.0 (año 2026, titular: el nombre legal que Richie indique 👤 — persona o empresa futura; puede ser "Ricardo Yazigi" hoy y cederse a la empresa después).
3. Editar `fusible/pyproject.toml` (diff a aprobar): `license = {text = "Apache-2.0"}`, `name = "<nombre confirmado>"`, añadir `classifiers` (License :: OSI Approved :: Apache Software License, Python 3.10-3.12), `[project.urls]` al repo nuevo.
4. Añadir encabezado corto de licencia a los 5 archivos de `src/fusible/` (diff a aprobar; 2 líneas por archivo: copyright + SPDX-License-Identifier: Apache-2.0).
5. Añadir `NOTICE` (una línea: nombre del proyecto + copyright) y sección "Licencia" en el README (reemplaza el "pendiente de decisión" — diff a aprobar).
6. **Frontera OSS/propietario, explícita:** TODO lo que hoy vive en `fusible/` sale como Apache-2.0 (incluido el flight recorder básico — es el gancho). La capa de pago futura (plantillas de informe Art. 72 listas para expediente, dashboard de flota, calibración gestionada, SLA) se desarrollará en un repo PRIVADO separado (`fusible-enterprise`), nunca dentro de este.
7. Verificación de empaquetado local: `pip install build && python -m build` dentro de `fusible/` → debe producir wheel y sdist sin errores. Pegar output.

## ETAPA C — Repos y push (REQUIERE autorización explícita de Richie 👤)

1. 👤 Crear en GitHub el repo público nuevo (mismo nombre que el paquete), vacío.
2. Extraer `fusible/` a su propio repo local (`git init`, primer commit: "fusible v0.1.0 — temporal containment layer for agentic systems (Apache-2.0)"), añadir remote y push — **solo con el OK de Richie**.
3. Push de Benchmark2026 (todos los commits locales de Fase 1/1.5/2) — **solo con el OK de Richie**. Esto desbloquea la auditoría por ejecución propia de Sonnet (su pedido explícito: re-correr el gate 1.5-A completo y comparar contra los números sellados).
4. `4R2 repo maestro jul2026`: sin cambios, sin push. Sigue siendo el archivo maestro.
5. 👤 Publicación en PyPI (cuando Sonnet haya re-corrido y confirmado): crear cuenta PyPI + token; `pip install twine && twine upload dist/*`. Recomendado: primero `twine upload --repository testpypi dist/*` y probar `pip install -i https://test.pypi.org/simple/ <nombre>`.

## ETAPA D — Difusión (después de C, no antes)

1. Revisión del preprint (`docs/PREPRINT_DRAFT.md`) contra reglas duras: cero "aplastante"; cada cifra traza a un JSON sellado con su SHA; la degeneración llama-guard y el ensamble negativo REPORTADOS como hallazgos (los negativos honestos son la firma del proyecto); el resultado principal es el en-dominio relativo + el OOD de CUSUM; el térmico crudo OOD se reporta como está. Diffs a aprobar por Richie.
2. README del repo nuevo: quickstart + tabla de resultados con SHAs + ejemplo de integración con ollama/Llama Guard en 10 líneas.
3. Siguiente ciclo científico (ya en el norte): spec de **ATBench-TL** (etiquetas por turno) — el movimiento de autoridad. Fable la redacta en la próxima sesión.

## ORDEN Y GATES

A (cierres) → B (licencia/paquete, con nombre confirmado) → C (push, con OK explícito) → auditoría Sonnet por ejecución → PyPI → D (difusión). **Nada se publica sin que Sonnet haya podido re-correr el gate.** Ese es nuestro estándar y es también el pitch.

*Decisiones registradas hoy: licencia Apache-2.0 (núcleo) + enterprise propietario separado. Pendientes de Richie: nombre (fusible vs fusible-ai según PyPI), titular del copyright, y el OK de push.*
