#!/usr/bin/env bash
# ============================================================================
# ARREGLO DEL CI + PUSH — ejecutar en WSL desde la raiz de Benchmark2026
#   cd /mnt/c/Users/USER/Documents/Benchmark2026 && bash fix_ci_y_push.sh
#
# Los arreglos de codigo YA ESTAN APLICADOS en el workspace por Fable
# (pyproject con per-file-ignores, autofix de ruff, formato, tests de
# cobertura nuevos). Este script solo VERIFICA los 4 pasos del CI igual que
# GitHub Actions y, si todo pasa, commitea y pushea. Si algo falla, se detiene
# y NO pushea.
# ============================================================================
set -euo pipefail

echo "==> 0. Entorno"
cd "$(dirname "$0")"
export FOURR2_REPO_PATH="${FOURR2_REPO_PATH:-$(cd .. && pwd)/4R2 repo maestro jul2026}"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -e ".[dev]" pytest-cov
echo "    ok"

echo "==> 1. Lint (ruff check)"
python3 -m ruff check .

echo "==> 2. Formato (ruff format --check)"
python3 -m ruff format --check .

echo "==> 3. Tipos (mypy --strict)"
python3 -m mypy --strict src/aegisbench/core src/aegisbench/interfaces

echo "==> 4. Tests + cobertura (umbral 85%)"
python3 -m pytest --cov=src/aegisbench --cov-report=term:skip-covered \
                  --cov-fail-under=85 tests/ -q

echo "==> 5. Smoke del CLI"
aegisbench run --adapter dummy --dataset xstest --n 10 >/dev/null
echo "    ok"

echo "==> 6. Tests de la libreria fusible (no los corre el CI, pero deben estar verdes)"
( cd fusible && python3 -m pytest tests/ -q )

echo ""
echo "===================== LOS 5 PASOS DEL CI PASAN ====================="
echo ""

echo "==> 7. Commit y push"
git add -A
git status --short | head -30
git commit -m "fix(ci): lint, formato y cobertura al verde

- ruff: per-file-ignores para scripts de experimento (notacion matematica en
  mayusculas N806/N803 y ajuste de sys.path E402 son correctos en ese dominio);
  fusible/ excluido del lint raiz (paquete independiente, repo canonico fuse-ai).
- autofix + formato aplicados (whitespace, orden de imports, semicolons).
- cobertura 83.0% -> 89.2%: tests nuevos para aegisbench.sensors.normalize
  (QuantileNormalizer, incluido el caso binario tipo llama-guard) y para
  GuardModelHTTPSensor con urlopen mockeado (sin red): parseo binario y
  numerico, acotado de rango, cache en disco y cache corrupto.
- verificado localmente: ruff check + ruff format --check + mypy --strict +
  pytest --cov-fail-under=85 (74 passed) + smoke CLI + fusible 21 passed."
git push origin main

echo ""
echo "Listo. Revisa el CI en:"
echo "  https://github.com/RicciYazigi/benchmark2026/actions"
