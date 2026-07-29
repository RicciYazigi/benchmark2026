#!/usr/bin/env bash
# Correr en WSL dentro del checkout de benchmark2026. Push del puente 4R2 (solo benchmark2026).
set -e
cd "$(git rev-parse --show-toplevel)"
git add adapters_external/fourr2_adapter.py adapters_external/__init__.py \
        RESULTADOS_4R2_RESPONSE_GOVERNANCE.md
git commit -m "feat(adapter): puente 4R2 response-governance + primer resultado real no-degenerado

Adaptador AegisBench->4R2 (Capa 1, lexico) con mapeo no degenerado
policy/request/response (C_NR y C_RI vivos, C_IF neutro declarado).
Primer run real: AUROC=0.358, ORR=100%, escala todo a FLAG -> no discrimina.
Corrobora de forma independiente el hallazgo negativo de APEX Fase 1 (AUROC~0.41).
No toca el repo 4r2v6. Ver RESULTADOS_4R2_RESPONSE_GOVERNANCE.md."
echo ">>> commit listo. Para subir:  git push origin main"
