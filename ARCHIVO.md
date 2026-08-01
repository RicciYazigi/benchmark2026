# ARCHIVO — qué se movió fuera de este repo y por qué

**Fecha:** 2026-07-30 · **TRACE_ID:** ARS-20260730-CANON-0001
**Destino:** `C:\Users\USER\Documents\informes y re organizacion antiguo y actual\`

AegisBench va a publicarse como open source. Un repo que se publica no lleva
volcados de conversación de 130-190 KB ni prompts de agente en la raíz: es lo
primero que ve quien llega, y da una señal equivocada sobre qué es el proyecto.

## Retirado — volcados de conversación (455 KB)

`MEGAFILE_SESION_4R2_20260719.md` (129 KB),
`Corrigiendo Evaluación de ATBench.md` (138 KB),
`Executing Guard Model OOD Evaluation.md` (187 KB),
`conversaciones antigravity/` → `50_CONVERSACIONES_Y_MEGAFILES/`.

## Retirado — prompts de agente ya ejecutados

`INSTRUCCIONES_ANTIGRAVITY*.md` (3), `INSTRUCCIONES_FASE_GUARD_MODEL.md`,
`PROMPT_ANTIGRAVITY_FASES_FINALES.md`, `PROMPT_ANTIGRAVITY_FASE_1_5.md`,
`PARA_SONNET_AUDITORIA_FINAL.md` → `40_PROMPTS_E_INSTRUCCIONES/`.

## Retirado — planes superados

`PLAN_ESTRATEGICO_4R2.md`, `ROADMAP.md` → `30_ROADMAPS_SUPERADOS/`.
Los reemplaza `INFORME_CANONICO_E2E_20260730.md` (repo maestro, copia en
`00_CANON_VIGENTE/`).

## Retirado — scripts de push por fase

`COMMIT_ADAPTER_ANTICAMO_wsl.sh`, `COMMIT_FASE1_benchmark_wsl.sh`,
`PUSH_ADAPTER_wsl.sh` → `60_SCRIPTS_PUSH_OBSOLETOS/`.
Los reemplaza **uno solo**: `PUSH_CANON_wsl.sh`.

## Retirado del control de versiones — caches

`evidence/guard_cache*.json` (3 archivos): son aceleradores locales de
inferencia, **no evidencia científica**. Vivían en `evidence/` y ensuciaban el
gate de cadena de evidencia. Ahora están en `.gitignore`.

## Se QUEDA (y por qué)

| Archivo | Razón |
|:--|:--|
| `RESULTADOS_*.md` (14) | El ledger científico, incluidos los hallazgos negativos. Es el activo de credibilidad |
| `AUDIT*.md`, `ANEXO_*.md`, `RESPUESTA_AUDITORIA_*.md` | Auditorías respondidas con experimentos: el historial que da confianza |
| `BALANCE_REAL_20260729.md`, `NORTE_UNA_PAGINA.md` | Estado vigente sin hype |
| `PLAN_PUBLICACION_APACHE.md`, `DATASET_LICENSES.md`, `REPRODUCIBILITY.md` | Necesarios para publicar |
| `fusible/` | **El producto.** No se toca |
