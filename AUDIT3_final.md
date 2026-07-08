# AegisBench v1.0 — Verificación ronda 3 (post-fix de reports/ y JailbreakBench)

**Método:** instalación limpia (`pip install -e .`) en venv nuevo, ejecutado desde `/tmp` (fuera del repo, simulando un usuario real), contra el commit `2c6b7a7` publicado en GitHub.

## Veredicto: los dos P0/P1 de la ronda anterior están genuinamente resueltos

- `pip install -e .` desde el checkout limpio + `from aegisbench.cli.main import main` → **OK**, ya no hay `ModuleNotFoundError`. Confirmado también contra la API de GitHub: `src/aegisbench/reports/{__init__.py,renderers.py}` presentes en el árbol de `main`.
- `aegisbench run --adapter dummy --dataset <X> --n 5`, ejecutado desde `/tmp` (fuera del repo) para las 5 fuentes, todas cargan muestras reales y devuelven métricas con señal real (no todo-ceros):
  - jailbreakbench: 5 muestras, ASR 80%
  - advbench: 5 muestras, ASR 60%
  - harmbench: 5 muestras, ASR 100%
  - xstest: 5 muestras, ASR 0% (control de sobre-bloqueo, comportamiento esperado)
  - agentharm (con `--accept-agentharm-terms`): 5 muestras, ASR 100%
- `ruff check .` → All checks passed. `ruff format --check .` → limpio. `mypy --strict` en core/interfaces → limpio.
- 39 tests + 1 de red (deselecable) = 40, coincide con lo reportado. Cobertura 85.56-86% según cómo se redondee, consistente con el 86.95% reportado (variación menor, no relevante).
- `LOCK_FILE_PATH` ahora resuelto vía `os.path.dirname(__file__)` (portable) — confirmado, y el `CACHE_DIR` respeta `AEGISBENCH_CACHE_DIR` con default en `~/.aegisbench/cache`.

## 🟡 P2 nuevo, menor — `aegisbench doctor` da un falso negativo

`cli/main.py` línea 424 sigue comprobando `os.path.join(os.getcwd(), "configs", "datasets.lock.json")` — la ruta vieja, no la nueva `LOCK_FILE_PATH` empaquetada. Al correr `aegisbench doctor` desde fuera del repo (exactamente el escenario que este mismo fix debía soportar), imprime `✘ Archivo de bloqueo de datasets NO encontrado`, aunque todo funciona correctamente (la autoprueba de determinismo, justo debajo, pasa sin problema). No bloquea nada, pero el comando cuya función es "decir la verdad sobre el estado del entorno" está mintiendo en ese chequeo puntual. Fix: importar `LOCK_FILE_PATH` desde `aegisbench.datasets.loaders` en vez de recalcular con `getcwd()`.

## Nota menor de limpieza (no bloqueante)

Quedó un `configs/datasets.lock.json` duplicado (idéntico en contenido al nuevo `src/aegisbench/datasets/datasets.lock.json`) sin usarse por el código. No causa error, pero es una fuente potencial de confusión si alguien lo edita pensando que tiene efecto.

## Gate

**Gate B (funcional, con pulido pendiente).** Ya no hay bloqueantes P0/P1 verificados. Antes de Gate A (publicable sin reservas): corregir el `doctor` (P2, 1 línea) y opcionalmente eliminar el lock file duplicado.
