# AUDIT Fase 1 — benchmark2026 como benchmark independiente

**Método:** clon limpio del repo (HEAD 15b2b3b), ejecución real. Sin 4R2 en el alcance.

## Verificado sólido (no se tocó)
- Suite verde, `ruff` limpio, `mypy --strict` limpio (core+interfaces).
- 5 datasets reales cargan con hash SHA256 validado (advbench 411, harmbench 70,
  xstest 361, jailbreakbench ~79 eval, agentharm con términos); split held-out
  80/20 y bootstrap N=10000 seed 42 operativos.
- CLI completa (run, validate-adapter, list-datasets, list-attacks, report, doctor);
  4 ataques (base64/leetspeak/roleplay/translation) aplican end-to-end; determinismo OK.
- `synthetic_fallback` visible en reportes (fix previo verificado).

## Gaps encontrados y estado
| ID | Severidad | Hallazgo | Estado |
|----|-----------|----------|--------|
| P1-A | Robustez | `download_file` sin reintentos: un 429/403 transitorio tumbaba la descarga | **HECHO** — retry x3 con backoff + Retry-After; integridad = fallo duro |
| P1-B | Integridad | Único comportamiento ante fallo = sustituir por sintético (silencioso hasta el fix de visibilidad) | **HECHO** — modo `--strict-datasets` / `strict=True` aborta (exit 1) en runs oficiales |
| P2-C | Usabilidad | Aceptación de AgentHarm solo por flag CLI | **HECHO** — env var `AEGISBENCH_ACCEPT_AGENTHARM` para CI |
| P2-D | Cobertura | CLI 76%, rama de fallo de dataset sin test | **PARCIAL** — +test de strict-abort (CLI 78%); resto son ramas de error de bajo riesgo |
| P2-E | Reproducibilidad | Sin guía de caché offline/air-gapped | **HECHO** — `REPRODUCIBILITY.md` |
| P3 | Cosmético | Doc drift menor (docs dicen "rot13", la transform real es "translation"; "50" vs 42 tras held-out) | Pendiente, no bloqueante |

## Resultado tras Fase 1 (clon limpio)
- **49 tests passed** (+6 nuevos: retry, strict, env var, no-strict fallback, strict-CLI-abort).
- Cobertura **89%**; `ruff` y `mypy --strict` limpios.
- Archivos tocados (solo benchmark2026): `datasets/loaders.py`, `cli/main.py`,
  `tests/test_datasets.py`, `tests/test_cli.py`, `REPRODUCIBILITY.md`.

**Gate Fase 1:** benchmark robusto y honesto para runs oficiales (strict) y
resiliente en dev (retry + fallback visible). Listo para Fase 2 (probar 4R2).
Sin commit/push aún — trabajo local.
