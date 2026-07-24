# PLAN MAESTRO ANTIGRAVITY — Post-Auditorías (2026-07-19)

**TRACE_ID:** ARS-20260719-PMA1 · **Este documento SUPERSEDE a `INSTRUCCIONES_ANTIGRAVITY.md`** (las Tareas 1-3 viejas quedan SUSPENDIDAS — se reubican como Fase 5 opcional, al final; no las ejecutes primero).
Contexto completo: `MEGAFILE_SESION_4R2_20260719.md` (v3, 128 KB — léelo entero antes de la Fase 1).

---

## REGLAS GLOBALES (inquebrantables, toda la sesión y las siguientes)

1. **NO modificar ningún archivo existente sin mostrar antes el diff propuesto y recibir aprobación explícita de Richie.** Crear archivos NUEVOS con los nombres exactos listados en cada fase está pre-autorizado; cualquier otro archivo nuevo, preguntar primero.
2. **No tocar `core/` de 4r2v6 jamás.** Solo lectura vía `FOURR2_REPO_PATH`.
3. **No `git push` nunca** salvo pedido explícito. Commit local solo al cerrar cada fase limpia, con el mensaje indicado.
4. **Verificar antes de afirmar**: cada gate termina con output real pegado (no descripciones de lo que "debería" pasar).
5. **Etiquetar todo**: demostrable / empírico con límites / plausible / ND.
6. Si la sesión se corta: dejar `CHECKPOINT_<FASE>.md` con fase en curso, último comando corrido y qué falta.
7. **Estadística**: cualquier IC por bootstrap debe respetar la estructura de dependencia (clúster por trayectoria si hay repetición — ver la retractación documentada en `RESULTADOS_CIERRE_AUDITORIA2.md`). AUROC siempre con corrección de empates.
8. Los resultados se reportan sea cual sea su signo. Un hallazgo negativo bien documentado cierra la fase igual que uno positivo.

---

## FASE 1 — GATE GUARD MODEL ZERO-SHOT (obligatoria, bloquea todo lo demás)

**Objetivo:** sensor fuera de dominio real (nunca vio ATBench, sin entrenamiento) alimentando el acumulador sin cambios. Es LA prueba que las tres auditorías dejaron como decisiva.

Sigue `INSTRUCCIONES_FASE_GUARD_MODEL.md` paso a paso (Pasos 0-4). Resumen operativo:

1. `ollama pull llama-guard3:1b` (o `:8b` si hay GPU) + verificación con los 2 prompts de prueba (pegar outputs).
2. Smoke test del adaptador `GuardModelHTTPSensor` con 3 turnos (pegar los 3 scores).
3. Corrida completa: `python scripts/eval_atbench_sensor_real.py guard` (~9,000 llamadas, 1-3 h CPU; cache reanudable en `evidence/guard_cache.json` — si se corta, relanzar el mismo comando).
4. **Gate 1-A:** pegar el JSON de resultados completo. Métricas mínimas: AUROC de single_max / single_mean / memory_maxT + deltas pareados.

**Después de la corrida base, análisis fino (archivos nuevos pre-autorizados):**

5. Crear `scripts/eval_guard_online.py` (adaptando `exp_streaming_online.py` para leer scores del guard cache en vez de tfidf): AUROC online de runmax/runmean/ewma/thermal + detección temprana a FPR 5%/10%. **Gate 1-B:** tabla pegada.
6. Crear `scripts/eval_guard_por_familia.py`: desglose por `risk_source` (8 familias) con los scores guard — SIN leave-family-out (el guard es zero-shot, no se entrena): AUROC térmico vs runmax por familia + test de signos + bootstrap por clúster (usar como referencia la lógica de `exp_lfo_cluster_bootstrap` documentada en el megafile). **Gate 1-C:** tabla por familia pegada.
7. Nota técnica: llama-guard3 da score binario 0/1 por turno (escalonado). Si ≥30% de los turnos salen con el mismo valor, correr la variante continua: `ollama pull qwen3:4b` y repetir con `GuardModelHTTPSensor(model='qwen3:4b')` (usa automáticamente el prompt numérico). Reportar ambas si aplica.
8. Crear `RESULTADOS_ATBENCH_GUARD.md` (estructura idéntica a `RESULTADOS_ATBENCH_SENSOR_REAL.md`: tablas, deltas, lectura honesta sea cual sea el signo, límites).

**Adenda 2026-07-19d (tras corrida llama-guard3:1b):**
9. Con la variante continua (qwen), añadir a la comparación un **ensamble online barato**: score_k = promedio de rangos normalizados de runmax_k y thermal_k (calculados sobre safe_eval). Hipótesis falsable pre-registrada: el térmico gana donde la evidencia es dispersa (inherent_failures +0.150, corrupted_feedback +0.106 con llama-guard) y pierde donde el riesgo es un evento puntual (direct_injection, jailbreak) → un ensamble max+térmico debería dominar a ambos por separado. Reportar el ensamble con las mismas métricas (archivo nuevo pre-autorizado: `scripts/eval_guard_ensemble.py`, misma inferencia por clúster).
10. Si hay RAM/tiempo: repetir warming + gates con `llama-guard3:8b` (sigue binario, pero sensor mucho más fuerte que 1b — separa el efecto "sensor débil" del efecto "binario"). Opcional, no bloquea el cierre de Fase 1.

---

## FASE 1.5 — RESOLUCIÓN DEL STOP-THE-LINE (adenda 2026-07-19e, tras cierre de Fase 1)

**Contexto:** el gate OOD no validó la forma térmica: con qwen2.5:3b el térmico pierde con significancia (Δ−0.034 [−0.057, −0.012]); con llama-guard-1b gana sin significancia. Diagnóstico clave ANTES de concluir "la física falla OOD": **ambos sensores son casi ruido sobre ATBench** (mejor AUROC de cualquier agregador: 0.55 vs 0.85+ del sensor en-dominio) — cuando la señal ≈ 0, el ranking entre agregadores refleja la estructura del ruido, no la física. Además θ=p90 con qwen dio 0.95 (scores comprimidos en banda alta) → energía cuadrática ≈ 0.0025 máx/turno → térmico casi degenerado por calibración, segunda vez.

**Tres tareas, pre-registradas (archivos nuevos pre-autorizados):**

1. **Normalización de scores del sensor** (`src/aegisbench/sensors/normalize.py`): transformación por cuantiles contra buffer de referencia benigno (los turnos de safe_cal): score_norm = rango del score en la distribución benigna. Corrige compresión/descalibración de CUALQUIER sensor antes del acumulador. Re-correr Gates 1-B/1-C de qwen con scores normalizados.
2. **Baseline CUSUM** (añadir a `eval_guard_online.py` y al ensamble): estadístico CUSUM estándar (S_k = max(0, S_{k-1} + score_norm_k − k_ref)) con k_ref calibrado en safe_cal. Exigido por AUDITORIA_Y_NORTE (Parte 4.1) antes de cualquier preprint.
3. **Sensor fuerte:** warming + los 3 gates con `llama-guard3:8b` (cache separado `guard_cache_8b.json`). Es la única corrida que responde: "¿con un sensor OOD que SÍ tiene señal, reaparece la ventaja térmica que vimos en-dominio?"

**Hipótesis pre-registradas (no mover tras ver datos):** H1: con normalización por cuantiles, el térmico-qwen mejora pero no supera a EWMA (señal insuficiente). H2: con llama-guard-8b, el mejor agregador temporal (térmico o CUSUM) supera a runmax con IC excluyendo 0. H3: CUSUM ≥ térmico en al menos una variante (si pasa: el fusible adopta CUSUM como estadístico por defecto y el I²t queda como variante — decisión ya tomada en AUDITORIA_Y_NORTE, el valor vive en la capa).

**Regla de salida:** con los resultados de 1-3, CIERRE definitivo de Fase 1 en `RESULTADOS_ATBENCH_GUARD.md` (sección final "Veredicto del gate") y pase a Fase 2 con el estadístico ganador — la Fase 2 se construye estadístico-agnóstica (I²t/CUSUM/EWMA intercambiables) en cualquier escenario, así que NINGÚN resultado de Fase 1.5 la bloquea; solo decide el default.

**Criterios de decisión (definidos ANTES de ver resultados — no moverlos después):**
- Térmico > mejor un-turno online con IC excluyendo 0 → tesis temporal validada OOD real. Luz verde Fases 2-4.
- Térmico ≤ un-turno pero el patrón por familia muestra ventaja en inyecciones → luz amarilla: Fase 2 sí, Fase 4 (preprint) se replantea con ese hallazgo como centro.
- Térmico pierde en todo → hallazgo negativo mayor: STOP-THE-LINE, documentar, y la decisión estratégica vuelve a Richie con el cuadro completo. No avanzar a Fase 2 sin su OK.

**Commit local al cerrar:** `feat(guard): gate OOD zero-shot llama-guard3 — resultados en RESULTADOS_ATBENCH_GUARD.md`

---

## FASE 2 — LIBRERÍA "FUSIBLE" INSTALABLE (la pieza de producto)

**Objetivo:** extraer el valor validado a un paquete pip-instalable, sensor-agnóstico. NO se mueve código de 4r2v6: se crea un paquete nuevo dentro de benchmark2026 (o repo hermano si Richie prefiere — preguntar antes de crear el directorio raíz).

Estructura pre-autorizada (`fusible/` dentro de Benchmark2026):
```
fusible/
  pyproject.toml            # nombre tentativo: "fusible-termico" — CONFIRMAR CON RICHIE
  src/fusible/__init__.py
  src/fusible/accumulator.py   # reimplementación limpia del I²t (misma ecuación,
                               # misma semántica trip/reset; NO copiar texto de core/,
                               # escribir desde la spec matemática + tests de equivalencia)
  src/fusible/calibration.py   # theta por percentil de benignos, grid τ/T_trip train-only
  src/fusible/sensors/base.py  # el contrato TurnSensor
  src/fusible/sensors/ollama.py  # adaptador guard local (port de GuardModelHTTPSensor)
  src/fusible/sensors/webhook.py # sensor genérico vía HTTP POST
  tests/                       # equivalencia numérica vs ThermalAccumulator de 4r2v6
                               # (mismo input → misma temperatura, error < 1e-9),
                               # + tests de calibración y adaptadores
  README.md                    # tablas de resultados del megafile + quickstart
```

**Gates:** 2-A: test de equivalencia numérica pegado (esto protege la propiedad intelectual de Richie: la librería pública no contiene código del kernel sellado, y la equivalencia está demostrada). 2-B: `pip install -e . && pytest` verde pegado. 2-C: demo end-to-end de 10 trayectorias ATBench con el sensor ollama, output pegado.

**Decisiones que requieren a Richie antes de ejecutar:** nombre del paquete, licencia (Apache-2.0 vs BSL — pendiente de la sesión anterior), y si `fusible/` vive en benchmark2026 o repo aparte.

---

## FASE 3 — MATERIALES DE EVIDENCIA EXTERNA (preprint + pitch)

Solo con Fase 1 en verde o amarillo. Archivos nuevos pre-autorizados:

1. `docs/PREPRINT_DRAFT.md`: estructura de paper corto (6-8 págs): (i) aislamiento física-vs-sensor como metodología, (ii) resultados online + OOD por familia + guard zero-shot, (iii) retractaciones documentadas como fortaleza metodológica. Solo redacción — cero números nuevos: cada cifra debe trazar a un JSON sellado del megafile (citar SHA-256 en cada tabla).
2. `docs/ONE_PAGER_PITCH.md`: el argumento de producto (capa de contención temporal sensor-agnóstica; brecha 21% visibilidad runtime / 37-40% contención, **con la atribución Kiteworks/Gravitee corregida** — copiar de `PLAN_ESTRATEGICO_4R2.md`, nunca de versiones previas).
3. **Gate 3-A:** ambos documentos listos para revisión de Richie y de la auditoría externa (Sonnet). No se publica nada — son borradores internos.

---

## FASE 4 — EXPERIMENTO J-SPACE v0 (solo si hay hardware; si no, dejar especificado)

**Requiere:** GPU o CPU potente + `transformers` + un modelo abierto pequeño (Llama-3.2-1B o Qwen2.5-1.5B). Si la máquina no puede, crear solo `docs/SPEC_JSPACE_V0.md` con este diseño y marcar ND.

Diseño: (1) correr el modelo abierto sobre cada turno de ATBench capturando activaciones de capa intermedia (última capa antes de la cabeza, mean-pooled); (2) entrenar un probe lineal de riesgo sobre esas activaciones con el MISMO protocolo OOF 5-fold por trayectoria y leave-family-out del megafile; (3) alimentar el acumulador con el score del probe; (4) mismas métricas online + por familia + bootstrap por clúster. Pregunta falsable: ¿la señal latente (j-space casero) localiza mejor los turnos `environment` de inyección donde el sensor textual fue ciego (28.8% vs 34.6% azar)? **Gate 4-A:** esa cifra específica, comparada.

---

## FASE 5 — (OPCIONAL, AL FINAL, PREVIA APROBACIÓN) Tareas viejas de INSTRUCCIONES_ANTIGRAVITY.md

Las Tareas 1-3 antiguas (visibilidad de fallback sintético en reportes, escenario response_governance, limpieza/push) SOLO si Richie las reactiva explícitamente. La Tarea 3 incluía push — regla 3 aplica: sin push.

---

## PROTOCOLO DE REPORTE (cada fase)

Al cerrar cada fase, entregar a Richie un bloque con: fase y gates cumplidos (outputs pegados), archivos creados (lista exacta), diffs propuestos pendientes de aprobación (si los hay), hallazgos etiquetados, y la decisión que le toca a él (si aplica). Formato de los informes de resultados: idéntico a `RESULTADOS_ATBENCH_SENSOR_REAL.md`.

**Orden estricto: Fase 1 → (decisión Richie) → 2 → 3 → 4. Nada en paralelo con la Fase 1: es el gate de todo.**

*Plan emitido por el pipeline orquestado ("ARQ Orchestrator – Modo Arsenal") tras tres rondas de auditoría externa. Dirección humana: Richie.*
