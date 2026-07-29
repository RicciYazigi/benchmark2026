#!/usr/bin/env bash
# ============================================================================
# Fase 1 — Robustez del benchmark AegisBench (SOLO benchmark2026).
# CORRER EN WSL dentro del checkout (NO desde el sandbox de Claude: alli los
# archivos se leen truncados por desync). En WSL los archivos estan intactos.
# Local-first: esto COMMITEA local. El push se hace al final de todo.
# ============================================================================
set -e
cd "$(git rev-parse --show-toplevel)"

echo ">>> 0) Verificacion previa (debe salir verde, 49 passed)"
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -e ".[dev]" 2>/dev/null || pip install -q -e ".[dev]"
python3 -m ruff check src tests
python3 -m mypy --strict src/aegisbench/core src/aegisbench/interfaces
python3 -m pytest -q -m "not network"

echo ">>> 1) Staging SOLO los archivos de Fase 1"
git add src/aegisbench/datasets/loaders.py \
        src/aegisbench/cli/main.py \
        tests/test_datasets.py \
        tests/test_cli.py \
        REPRODUCIBILITY.md \
        AUDIT_FASE1_benchmark.md

echo ">>> 2) Commit (sin push)"
git commit -m "feat(robustez): descargas con retry+backoff, modo --strict-datasets y reproducibilidad

- download_file: reintentos x3 con backoff exponencial y Retry-After ante 429/5xx;
  fallo de integridad SHA256 sigue siendo fallo duro (sin reintento).
- load_dataset(strict=True) / CLI --strict-datasets: aborta (exit 1) si un dataset
  real no se puede obtener, en vez de sustituir por sintetico -> runs oficiales/CI.
- Aceptacion no-interactiva de AgentHarm via AEGISBENCH_ACCEPT_AGENTHARM=1.
- REPRODUCIBILITY.md (caché offline/air-gapped, dos modos) + AUDIT_FASE1_benchmark.md.
- +6 tests (retry, strict, env var, fallback, strict-CLI-abort). 49 passed, cov 89%,
  ruff y mypy --strict limpios. NO toca 4r2v6."

echo ">>> Hecho (local). git log:"
git log --oneline -3
echo ">>> El push se hace al final de todas las fases."
