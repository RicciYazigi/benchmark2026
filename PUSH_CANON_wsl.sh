#!/usr/bin/env bash
# =============================================================================
#  PUSH_CANON_wsl.sh — Benchmark2026 / AegisBench  (RicciYazigi/benchmark2026)
#  TRACE_ID: ARS-20260730-CANON-0001
#
#  UN SOLO script. Reemplaza a COMMIT_ADAPTER_ANTICAMO / COMMIT_FASE1 /
#  PUSH_ADAPTER (archivados en "60_SCRIPTS_PUSH_OBSOLETOS/").
#
#  Este repo va a publicarse. El script corre EXACTAMENTE los mismos pasos que
#  GitHub Actions y solo sube si todos pasan.
#
#  USO (en WSL):
#     cd /mnt/c/Users/USER/Documents/Benchmark2026
#     bash PUSH_CANON_wsl.sh          # pide confirmacion antes de subir
#     bash PUSH_CANON_wsl.sh --dry    # solo gates
# =============================================================================
set -euo pipefail

DRY=0; [[ "${1:-}" == "--dry" ]] && DRY=1
ARCHIVO_DIR="/mnt/c/Users/USER/Documents/informes y re organizacion antiguo y actual"

rojo(){ printf '\033[0;31m%s\033[0m\n' "$*"; }
verde(){ printf '\033[0;32m%s\033[0m\n' "$*"; }
azul(){ printf '\033[0;36m%s\033[0m\n' "$*"; }
paso(){ echo; azul "── $* ─────────────────────────────────────────"; }
morir(){ rojo "ABORTADO: $*"; exit 1; }

# ---------------------------------------------------------------- 0. contexto
paso "0. Contexto"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || morir "no estas dentro de un repo git"
git remote get-url origin | grep -qi "benchmark2026" || morir "el remoto no es benchmark2026"
echo "  repo   : $(git rev-parse --show-toplevel)"
echo "  rama   : $(git rev-parse --abbrev-ref HEAD)"
[[ "$(git rev-parse --abbrev-ref HEAD)" == "main" ]] || morir "este script solo opera sobre main"

command -v ruff  >/dev/null || morir "falta ruff. Instala: pip install -e '.[dev]'"
command -v mypy  >/dev/null || morir "falta mypy. Instala: pip install -e '.[dev]'"
python3 -c "import sklearn" 2>/dev/null || morir "falta scikit-learn (extra 'sensors'). pip install -e '.[dev]'"

# ------------------------------------------------------- 1. finales de linea
paso "1. Renormalizando finales de linea (.gitattributes)"
[[ -f .gitattributes ]] || morir "falta .gitattributes"
git add --renormalize . >/dev/null 2>&1 || true
verde "  hecho"

# ------------------------------------------------- 2. retirada de archivados
paso "2. Retirando del repo lo archivado y los caches de evidencia"
RETIRAR=(
  "MEGAFILE_SESION_4R2_20260719.md"
  "Corrigiendo Evaluación de ATBench.md"
  "Executing Guard Model OOD Evaluation.md"
  "INSTRUCCIONES_ANTIGRAVITY.md"
  "INSTRUCCIONES_ANTIGRAVITY_ADAPTER_COMMIT.md"
  "INSTRUCCIONES_ANTIGRAVITY_PLAN_MAESTRO.md"
  "INSTRUCCIONES_FASE_GUARD_MODEL.md"
  "PROMPT_ANTIGRAVITY_FASES_FINALES.md"
  "PROMPT_ANTIGRAVITY_FASE_1_5.md"
  "PARA_SONNET_AUDITORIA_FINAL.md"
  "PLAN_ESTRATEGICO_4R2.md"
  "ROADMAP.md"
  "COMMIT_ADAPTER_ANTICAMO_wsl.sh"
  "COMMIT_FASE1_benchmark_wsl.sh"
  "PUSH_ADAPTER_wsl.sh"
)
[[ -d "$ARCHIVO_DIR" ]] || morir "no encuentro la carpeta de archivo: $ARCHIVO_DIR"
n=0
for f in "${RETIRAR[@]}"; do
  git ls-files --error-unmatch "$f" >/dev/null 2>&1 || continue
  if ! find "$ARCHIVO_DIR" -name "*$(basename "$f")" -print -quit | grep -q .; then
    morir "no hay copia archivada de '$f' — no lo retiro"
  fi
  [[ $DRY -eq 0 ]] && git rm -q --cached "$f" && rm -f "$f"
  n=$((n+1))
done
# carpeta completa de conversaciones
if git ls-files --error-unmatch "conversaciones antigravity" >/dev/null 2>&1; then
  [[ $DRY -eq 0 ]] && git rm -rq --cached "conversaciones antigravity" && rm -rf "conversaciones antigravity"
  n=$((n+1))
fi
# caches: NO son evidencia (ya estan en .gitignore)
for c in evidence/guard_cache.json evidence/guard_cache_llama.json evidence/guard_cache_qwen.json; do
  git ls-files --error-unmatch "$c" >/dev/null 2>&1 || continue
  [[ $DRY -eq 0 ]] && git rm -q --cached "$c"   # se queda en disco, sale del repo
  n=$((n+1))
done
verde "  $n rutas a retirar (copias verificadas)"

# ------------------------------------------------------------- 3. LOS GATES
paso "3. Gates locales (identicos a GitHub Actions)"
echo "  [1/6] ruff check..."        ; ruff check .                || morir "gate: ruff check"
echo "  [2/6] ruff format --check..."; ruff format --check .       || morir "gate: formato"
echo "  [3/6] mypy --strict..."      ; mypy --strict src/aegisbench/core src/aegisbench/interfaces || morir "gate: mypy"
echo "  [4/6] pytest + cobertura >=85%..."
pytest --cov=src/aegisbench --cov-report=term-missing --cov-fail-under=85 tests/ 2>&1 | tail -3
pytest --cov=src/aegisbench --cov-fail-under=85 tests/ >/dev/null 2>&1 || morir "gate: tests o cobertura"
echo "  [5/6] cadena de evidencia (cada .sha256 reproduce su artefacto)..."
python3 scripts/verify_evidence_seals.py || morir "gate: cadena de evidencia"
echo "  [6/6] finales de linea..."
if git grep -Il $'\r' -- ':(exclude)conversaciones antigravity/**' ':(exclude)*.ps1' ':(exclude)*.bat' >/dev/null 2>&1; then
  morir "gate: hay CRLF. Corre: git add --renormalize ."
fi
verde "  LOS 6 GATES EN VERDE"
echo "  smoke del CLI..."; aegisbench run --adapter dummy --dataset xstest --n 10 >/dev/null || morir "gate: smoke del CLI"

if [[ $DRY -eq 1 ]]; then
  echo; verde "--dry: gates verificados. No se hizo commit ni push."; exit 0
fi

# ----------------------------------------------------------------- 4. commit
paso "4. Commit"
git add -A
if git diff --cached --quiet; then
  echo "  no hay cambios que commitear"
else
  git commit -q -F - <<'MSG'
canon(20260730): cierra la cadena de evidencia y deja el repo en estado publicable

CADENA DE EVIDENCIA (P0, cerrado)
- Causa raiz encontrada: 10 de 17 artefactos sellados llevaban ~3 semanas sin
  coincidir con su sidecar .sha256. NO era corrupcion ni una corrida sin
  READ_ONLY=1 (diagnostico anterior): era Path.write_text() en Windows
  traduciendo LF->CRLF DESPUES de hashear el payload en memoria.
- .gitattributes: LF forzado; evidence/, data/ y reports_* como binarios.
- Fix estructural en los 10 scripts de eval: write_bytes() en vez de
  write_text(), para el artefacto y para su sidecar. El hash del sidecar es
  ahora el hash de los bytes en disco en cualquier sistema operativo.
- scripts/verify_evidence_seals.py: gate nuevo + helper sellar() reutilizable.
- 5 artefactos que nunca tuvieron sidecar quedan sellados retroactivamente, con
  su procedencia declarada en evidence/SELLADO_RETROACTIVO_20260730.json
  (contenido ya commiteado; los experimentos NO se re-ejecutaron).
- CI: gates de sellos y de finales de linea.

DEPENDENCIAS
- scikit-learn estaba importado en src/aegisbench/sensors/ sin declararse en
  ninguna parte: los 3 tests de TfidfTurnSensor solo pasaban si el entorno ya lo
  tenia. Declarado en el extra 'sensors' y en 'dev'. 74/74 en verde.

HIGIENE PARA PUBLICAR
- 455 KB de volcados de conversacion, 7 prompts de agente, 2 planes superados y
  3 scripts de push por fase salen del repo (copia en
  "informes y re organizacion antiguo y actual"). Manifiesto en ARCHIVO.md.
- evidence/guard_cache*.json fuera del control de versiones: son aceleradores
  locales, no evidencia cientifica.
- Un solo PUSH_CANON_wsl.sh con los 6 gates antes de subir.

Nucleo de AegisBench y resultados cientificos SIN CAMBIOS.
MSG
  verde "  commit creado"
fi

# ------------------------------------------------------------------ 5. push
paso "5. Publicando"
echo "  Se va a subir main -> $(git remote get-url origin)"
read -r -p "  ¿Confirmas? [s/N] " ok
[[ "$ok" =~ ^[sSyY]$ ]] || morir "cancelado por el usuario (no se subio nada)"
git push origin main
verde "  publicado"

# ------------------------------------------------- 6. verificacion desde clon
paso "6. Verificando desde un clon limpio"
TMP=$(mktemp -d)
git clone -q --depth 1 "$(git remote get-url origin)" "$TMP/v" || morir "no pude clonar"
cd "$TMP/v"
python3 scripts/verify_evidence_seals.py | tail -3
cd - >/dev/null; rm -rf "$TMP"

echo
verde "════════════════════════════════════════════════════════════"
verde " LISTO. Comprueba los 3 jobs del CI (3.10/3.11/3.12) en verde."
verde "════════════════════════════════════════════════════════════"
echo " Siguiente gate del roadmap: publicar fuse-ai en PyPI y abrir"
echo " AegisBench en publico. Es el gate que lleva meses sin cruzarse."
