# AegisBench v1.0 — Auditoría independiente (contra-verificación del walkthrough de Antigravity)

**Fecha:** 2026-07-08
**Método:** ejecución real en entorno aislado (venv limpio, copia del repo), no relectura del reporte de Antigravity.

## Resumen ejecutivo

El walkthrough reporta éxito total. La auditoría confirma que **la parte de ingeniería de software (arquitectura, tests, tipado, CLI) es sólida y las cifras de tests/cobertura son exactas**, pero encuentra un **defecto estructural P0 no detectado ni reportado**: ninguno de los 5 datasets reales puede descargarse ni validarse jamás — el pipeline cae al fallback sintético (10 prompts hardcodeados) el 100% de las veces, no solo en este sandbox. Esto invalida la afirmación implícita de que el benchmark evalúa contra datos reales.

## Hallazgos verificados

### ✅ Confirmado como reportado
- 38/38 tests pasan (verificado en venv limpio, sin caché compartida).
- Cobertura total: 85.56% ((748-108)/748), coincide exactamente con el reporte.
- `mypy --strict` limpio en `core/` e `interfaces/` (alcance correcto según spec — no se pidió strict en todo el repo).
- Grep de términos prohibidos (4R2, NRIF, theta, LBB, kernel) en src/tests/docs/configs: **0 coincidencias**. Constraint duro respetado.
- Gating de AgentHarm (`--accept-agentharm-terms`) implementado y probado correctamente: sin la bandera devuelve 0 muestras.
- Split anti-gaming held-out (MD5, ~80/20) implementado y aplicado por defecto, tal como se especificó.
- Parsers de los 5 formatos de dataset (advbench/jailbreakbench/harmbench/xstest/agentharm) correctamente implementados y probados con fixtures sintéticos que replican el schema real de cada fuente.

### 🔴 P0 — No reportado por Antigravity, encontrado en esta auditoría
**Los 5 datasets están permanentemente rotos, no es un problema de red del sandbox:**

| Dataset | URL en `datasets.lock.json` | Resultado real (verificado con `requests` desde este entorno) |
|---|---|---|
| jailbreakbench | `.../jailbreakbench/main/src/jailbreakbench/data/jailbreakbench.csv` | **HTTP 404** — ruta no existe |
| xstest | `.../paul-rottger/exaggerated-safety/main/xstest_v2_prompts.csv` | **HTTP 404** — el repo real es `paul-rottger/xstest`, no `exaggerated-safety` |
| agentharm | `.../METR/agent-harm/main/agent_harm/dataset.jsonl` | **HTTP 404** — el repo `METR/agent-harm` no existe |
| advbench | `.../llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv` | HTTP 200, pero **SHA256 no coincide** (lock: `4e12e9b0...`, real: `6cd1a5c6...`) |
| harmbench | `.../centerforaisafety/HarmBench/main/data/behavior_datasets/harmbench_behaviors_text_val.csv` | HTTP 200, pero **SHA256 no coincide** (lock: `63d7a8d5...`, real: `7bfaaa5e...`) |

Consecuencia: `download_file()` siempre lanza excepción (404 o mismatch de hash) → `load_dataset()` siempre usa `get_synthetic_samples()` → **cada `aegisbench run` que se ha ejecutado hasta ahora, incluido el smoke test del walkthrough, evaluó 4-10 prompts de juguete hardcodeados, nunca los datasets reales.**

Esto también explica por qué el smoke test mostró "Total de muestras a evaluar: 4" con `--n 10`: xstest sintético solo tiene 5 muestras y el filtro held-out (~20%) descartó una, dejando 4 — no es un bug del runner, es la firma del fallback.

**Causa raíz probable:** las URLs y hashes de `configs/datasets.lock.json` fueron generadas por Antigravity sin verificación contra las fuentes reales (ni un `curl` de comprobación, ni un cálculo real de SHA256 antes de fijarlo en el lockfile). El test que existe (`test_load_dataset_synthetic_fallback`) prueba explícitamente el camino de fallback — nunca el de éxito — así que el defecto es invisible en `pytest`.

### 🟠 P1 — CI actualmente en rojo si se ejecuta hoy
- `ruff check .` → 2 errores reales en `tests/test_datasets.py` (import `json` sin usar, imports desordenados).
- `ruff format --check .` → 2 archivos necesitan reformateo (`test_adapters.py`, `test_datasets.py`).
- El workflow de GitHub Actions (`.github/workflows/ci.yml`) ejecuta ambos como paso obligatorio antes de tests → **el pipeline fallaría en el primer push**, contradiciendo la idea de "listo para GitHub".
- El paso "Smoke run" en CI no verifica que el dataset se haya descargado de verdad — pasaría en verde eternamente aunque el fallback sintético sea el único camino ejecutado (mismo blind spot que P0).

### 🟠 P1 — Atribución incorrecta de licencia (riesgo legal/IP)
`DATASET_LICENSES.md` atribuye AgentHarm a "METR". Según verificación externa (arXiv 2410.09024, dataset en Hugging Face), el publicador es el **UK AI Safety Institute** (`ai-safety-institute/AgentHarm`), no METR. Un documento cuyo propósito es guiar cumplimiento legal con la atribución equivocada es un defecto de por sí, no cosmético.

### 🟡 P2 — Comando `report` sin cobertura de test
Líneas 381-415 de `cli/main.py` (subcomando completo `aegisbench report`, especificado como parte del DoD) tienen 0% de cobertura — nunca se probó ni siquiera con datos sintéticos.

### 🟡 P2 — Portabilidad del CLI instalado
`CACHE_DIR` y `LOCK_FILE_PATH` en `datasets/loaders.py` se resuelven vía `os.getcwd()`. Un usuario que instale `aegisbench` via pip y lo ejecute fuera del directorio raíz del repo obtendrá `FileNotFoundError` en `get_lock_config()`. Debería resolverse relativo al paquete instalado o vía variable de entorno configurable.

## Gate

**Gate C (listo para publicar): NO CUMPLE.** El hallazgo P0 no es un detalle — es la funcionalidad central del proyecto ("benchmark de referencia con datasets reales, verificados por hash") la que está inoperante. Antes de anunciar v1.0 como funcional:

1. Recalcular y fijar los 5 pares URL/SHA256 reales (verificar con descarga real, no asumir rutas).
2. Añadir al menos un test de integración marcado `@pytest.mark.network` que descargue de verdad y valide contra el hash fijado (puede saltarse en CI sin red, pero debe existir y correrse manualmente antes de cada release).
3. Corregir `ruff` (2 fixes triviales, `--fix` los resuelve).
4. Corregir atribución de AgentHarm en `DATASET_LICENSES.md`.
5. Añadir test para el subcomando `report`.
