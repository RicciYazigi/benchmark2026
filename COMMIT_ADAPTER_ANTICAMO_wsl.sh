#!/usr/bin/env bash
# Commit del adapter extendido — EJECUTAR DESDE WSL. Rama main. Sin push.
set -euo pipefail
cd "$(dirname "$0")"
python3 -c "import ast; ast.parse(open('adapters_external/fourr2_adapter.py').read()); print('sintaxis OK')"
git add adapters_external/fourr2_adapter.py
git commit -m "feat(adapter): parámetros opt-in governance/anticamo/embedder/nli en FourR2Adapter

Solo configura el sistema bajo prueba; el scoring del benchmark NO cambia
(neutralidad preservada). Usado para validar la defensa anti-camuflaje de 4R2
en el split held-out (n=8, AUROC 1.000, 0 errores de veredicto, theta 0.46)."
echo "Commit listo en main. PUSH MANUAL cuando lo autorices."
