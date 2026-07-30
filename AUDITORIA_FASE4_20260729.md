# Auditoría de la Fase 4 (J-Space v0) — Corrida completa 9,009 turnos

**TRACE_ID:** ARS-20260729-AUD4 · **Estado:** OK con dos correcciones de forma (ninguna cambia el veredicto)
**Auditor:** Fable 5, por ejecución propia sobre el workspace local (no por lectura del reporte).
**Evidencia auditada:** `evidence/jspace_probe_Qwen_Qwen2.5-0.5B_20260729.json` · SHA-256 recalculado **2a43cd5935d4309f29e63645c5afe550764e14530a144375b95044e85c960935** — coincide con el `.sha256` y con el reportado ✔

---

## 1. Integridad — RESUELTA, verificada de forma independiente

La ALERTA previa (corrida parcial) está **cerrada correctamente**:

| Verificación | Esperado | Medido | ✔ |
|---|---|---|---|
| Embeddings en el `.npz` | 9,009 | **9,009** | ✔ |
| Familias en el desglose | 8 | **8** | ✔ |
| N inyecciones con turno `environment` | ~198 | **198** | ✔ |
| Sellado SHA-256 | consistente | recalculado idéntico | ✔ |
| Retractación documentada en el informe | presente | 2 marcas PARCIAL/RETIRADA | ✔ |

La retractación siguió el protocolo del proyecto (misma disciplina que el IC retirado en la 3ª auditoría). Esta es la **cuarta cifra retirada antes de salir al mundo** — el proceso funciona.

## 2. Los veredictos son correctos y honestos (verificados a mano)

- **H-J1 — FALSADA / no significativa.** CUSUM 0.8210 vs runmax 0.8120; Δ+0.0088 con IC **[−0.0116, +0.0284]** que incluye el cero; 5/8 familias, test de signos p=0.363. **Bien reportado**: con el dataset completo la ventaja se desvanece. Nota de contraste importante para el preprint: en la corrida parcial el IC excluía cero por 0.0004 — es un caso de manual de por qué los subconjuntos truncados engañan, y vale documentarlo como lección metodológica.
- **H-J2 — FALSADA.** Probe latente 0.8210 vs TF-IDF sellado 0.8760. Las activaciones crudas mean-pooled tienen menos señal útil que un clasificador textual entrenado en dominio.
- **H-J3 — FALSADA, y es el hallazgo más interesante.** El argmax latente cae en el turno `environment` el **17.68%** de las veces contra un azar de 34.60% — **la mitad del azar**, y peor que el sensor textual (28.8%). No es solo "no localiza": está sistemáticamente *anti-correlacionado*, casi seguro porque el pico latente lo captura otra cosa (turnos largos de herramienta, cambios de estilo). Es una señal de que el pooling ingenuo de última capa no es la representación correcta — no de que la idea del J-space esté muerta.

## 3. Dos correcciones de forma (P2, no cambian ningún veredicto)

1. **Nombre de familia mal reportado.** El JSON contiene `dummy_token` (61 trayectorias), no `malicious_user_instruction_or_jailbreak`. Verificado contra el dataset crudo: `dummy_token` es literalmente la etiqueta de `risk_source` en `atbench_test.jsonl` para esas 61 muestras — el reporte de Antigravity la renombró al presentarla. La familia **sí está incluida** (el conteo cuadra: 44+39+61+77+135+25+52+64 = 497 ✔), pero el informe debe usar el nombre real del dataset o declarar el mapeo. Acción: corregir la tabla en `RESULTADOS_JSPACE_V0.md`.
2. **Nomenclatura de hipótesis inconsistente.** El script pre-registró J1/J2/J3 con estos significados: J1 = probe > tfidf, J2 = ventaja de acumulación se mantiene, J3 = localización. El informe las presenta como H-J1 = acumulación, H-J2 = superioridad. Los *resultados* son correctos y ninguna hipótesis quedó sin evaluar, pero el intercambio de etiquetas es exactamente el tipo de deriva que un revisor externo marcaría. Acción: alinear el informe con el orden pre-registrado en el encabezado del script, o declarar explícitamente el remapeo.

## 4. Lectura consolidada — qué queda probado tras las tres fases

| Sensor | Ventaja de la acumulación sobre lo reactivo | Evidencia |
|---|---|---|
| TF-IDF en dominio (OOF) | **SÍ, significativa** | 8/8 familias, p=0.0039; online +0.021 P=1.0 |
| Guard OOD zero-shot (qwen normalizado) | **SÍ, significativa** | Δ+0.0404, IC [0.0201, 0.0619] |
| Activaciones latentes crudas (Qwen-0.5B) | **NO significativa** | Δ+0.0088, IC [−0.0116, +0.0284], 5/8 |

Conclusión defendible (y la única citable): **la ventaja de la agregación temporal está demostrada sobre sensores que sí portan señal de riesgo calibrada, y no se sostiene sobre activaciones crudas sin refinar.** Eso refuerza —no debilita— el diseño sensor-agnóstico de `fuse-ai`: la capa vale sobre buenos sensores, y no pretende arreglar sensores malos. Lo contrario (afirmar universalidad) sería exactamente la sobreventa que este proyecto lleva un mes evitando.

## 5. Estado del push y qué falta

`git push` a `benchmark2026` reportado en commits `574a970` y `7018a0c`; **no verificable desde este entorno** (el fetch a github.com no devuelve contenido — ND, no es indicio de fallo). Pendiente de confirmar visualmente por Richie que ambos commits aparecen en la web y que el `.npz` de 17 MB subió completo.

**Acciones (todas P2, ninguna bloquea):** (1) corregir el nombre `dummy_token` en el informe; (2) alinear la nomenclatura J1/J2/J3 con el pre-registro; (3) añadir al informe la lección metodológica del contraste parcial-vs-completo (el IC que excluía cero por 0.0004 y luego no) — es material de primera para el preprint; (4) Richie confirma los commits en la web.

*Confianza: alta (verificación por ejecución propia sobre los artefactos locales; sellado recalculado). El único ND es el estado del repo remoto.*
