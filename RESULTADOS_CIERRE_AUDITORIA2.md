# Cierre de la Segunda Auditoría — P2a Des-confundido + OOD Leave-Family-Out (2026-07-19)

**TRACE_ID:** ARS-20260719-AUD2 · **Estado:** OK
**Evidencia sellada:** `evidence/exp_cierre_auditoria2_20260719.json` · SHA-256 `582ac8b4…d59`
**Script:** `scripts/exp_cierre_auditoria2.py` (checkpoints reanudables en `evidence/lfo_ckpt/`)

---

## Objeciones de la segunda auditoría y qué se hizo con cada una

**1. Atribución Kiteworks/CSA — aceptada y corregida.** Las cifras 37% (purpose binding) / 40% (kill switch) son del Kiteworks 2026 Forecast Report, no de CSA. Corregido en `PLAN_ESTRATEGICO_4R2.md` y `RESPUESTA_AUDITORIA_20260719.md` con nota de corrección explícita. Las cifras Gravitee (88% incidentes, 21% visibilidad runtime, 900+ encuestados) fueron confirmadas independientemente por la propia auditoría.

**2. Circularidad tema-`reason` en P2a — aceptada como riesgo real, y puesta a prueba.** El argumento: si el sensor detecta tema (~59% de su señal) y `reason` describe la trayectoria con vocabulario temático, el proxy Jaccard no es independiente y el "2× azar" podría ser la misma fuga medida dos veces.

**Control ejecutado:** se recalculó toda la localización **excluyendo del proxy las 12,728 palabras que el sensor pondera positivamente** (todo su vocabulario de riesgo — el canal exacto de la circularidad), más un control de longitud.

| Métrica (496→482 trayectorias inseguras) | Original (con confound) | **Des-confundido** | Azar |
|---|---|---|---|
| Top-1 acierto (argmax sensor = turno proxy) | 0.2520 | **0.2054** | 0.1303 |
| Rango normalizado medio del turno de riesgo | 0.7158 | **0.6704** | 0.5 |
| % trayectorias con Δ positivo vs. vecinos | 0.7419 | **0.6805** | 0.5 |
| Argmax del sensor = turno más largo | 0.1371 | 0.1411 | — |
| Top-1 cuando el proxy NO es el turno más largo | 0.2466 | 0.2061 | ~0.13 |

**Veredicto honesto:** la circularidad existía y explicaba parte del efecto (top-1 cae de 25.2% a 20.5%) — la auditoría acertó en señalarla. Pero la localización **sobrevive al des-confounding**: 1.6× azar sin ninguna palabra del vocabulario del sensor, rango 0.67 vs. 0.5, y no es artefacto de longitud (el sensor solo elige el turno más largo el 14% de las veces). La frase correcta ya no es "el sensor localiza parcialmente la conducta" a secas, sino: **"la localización parcial persiste tras remover el canal de circularidad señalado; es débil (1.6× azar) pero no es un artefacto del confound temático."**

**3. Necesidad de evidencia OOD — adelantada hasta donde lo local permite.** El gate guard-model zero-shot sigue siendo tuyo (requiere ollama en tu máquina). Pero se ejecutó la aproximación OOD ejecutable hoy: **leave-family-out sobre `risk_source`** — por cada una de las 8 familias de riesgo, el sensor se entrena **sin ver ninguna trayectoria insegura de esa familia** y se evalúa sobre ella (+50% de seguras jamás usadas en train). OOD por construcción respecto al tipo de riesgo.

| Agregador online | AUROC macro (8 familias) |
|---|---|
| **Térmico I²t (τ=5)** | **0.8581** |
| Max acumulado | 0.8266 |
| EWMA (α=0.3) | 0.8099 |
| Media acumulada | 0.7716 |

**El térmico gana en las 8 familias de 8** — incluidas las tres de inyección donde el diagnóstico previo mostró que el sensor NO localiza el turno culpable: indirect_prompt_injection (0.848 vs. 0.803 del max), tool_description_injection (0.858 vs. 0.806), corrupted_tool_feedback (0.903 vs. 0.876). Lectura fina: justo donde la señal por turno es más débil y difusa (inyecciones que el sensor no sabe localizar), la integración temporal aporta su mayor ventaja — que es exactamente la tesis del acumulador.

**CORRECCIÓN DE INFERENCIA (2026-07-19c, tercera auditoría).** El delta pareado sobre el pool originalmente reportado (+0.0344 [0.0278, 0.0414]) queda **RETIRADO por inválido**: las 252 trayectorias seguras se repetían 8 veces en el pool (2,513 puntos tratados como independientes sin serlo), estrechando el IC artificialmente — detectado por auditoría externa. Lo reemplaza la inferencia válida (`evidence/exp_lfo_cluster_bootstrap_20260719.json`, SHA-256 `4d22d6ac…cc23`): **bootstrap por clúster de trayectoria** (cada segura arrastra sus 8 scores juntos; inseguras remuestreadas dentro de su familia): macro-Δ **+0.0312 [+0.0198, +0.0428]**, P(mejora)=1.0 — IC más ancho, como corresponde, y sigue excluyendo el cero con holgura. Además, **test de signos sobre las 8 familias independientes**: 8/8 victorias, p unilateral = **0.0039**. Deltas por familia: todos positivos, de +0.017 (misinformation) a +0.052 (tool_description_injection). El resultado defendible externamente es: *8/8 familias, test de signos p=0.0039, macro-Δ por clúster +0.031 [0.020, 0.043]*.

## Estado consolidado tras dos rondas de auditoría

Sobreviven con evidencia reforzada: la física validada aislada, la superioridad **relativa** online del térmico (ahora también bajo OOD-por-familia, 8/8), y el hallazgo negativo P2b (aceptado por la auditoría sin reservas). Corregidos: atribución Kiteworks, interpretación de P2a (de "localiza" a "localización débil que sobrevive al des-confounding"). Pendiente e inmutable: **el gate guard-model zero-shot en tu máquina** (`INSTRUCCIONES_FASE_GUARD_MODEL.md`) — ninguna decisión estratégica externa (licencia, marca, pitch) antes de ese resultado.

## Límites

LFO es OOD respecto a la familia de riesgo, no respecto al dataset (vocabulario de dominio agentic compartido entre familias; las seguras de test son comunes a las 8 evaluaciones — comparación relativa entre agregadores válida, cifras absolutas no comparables con las corridas 5-fold). El proxy de localización sigue siendo imperfecto incluso des-confundido. Corrida única, seed 42.

| Etiqueta | Aplica a |
|---|---|
| empírico con límites | EXP-1 y EXP-2 completos |
| verificado | corrección de atribución (Kiteworks/CSA/Gravitee) |
| ND | comportamiento con guard model zero-shot (gate pendiente, obligatorio) |

*Salida de un pipeline orquestado ("ARQ Orchestrator – Modo Arsenal"). Dirección humana: Richie.*
