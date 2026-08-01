<#
=============================================================================
  PUSH_CANON.ps1 - Benchmark2026 / AegisBench  (RicciYazigi/benchmark2026)
  TRACE_ID: ARS-20260730-CANON-0001

  Version PowerShell de PUSH_CANON_wsl.sh (misma logica, mismos 6 gates).

  USO:
     cd C:\Users\USER\Documents\Benchmark2026
     .\PUSH_CANON.ps1 -Dry     # solo gates
     .\PUSH_CANON.ps1          # gates + commit + push (pide confirmacion)

  Si Windows bloquea el script:
     powershell -ExecutionPolicy Bypass -File .\PUSH_CANON.ps1 -Dry
=============================================================================
#>
[CmdletBinding()]
param([switch]$Dry)

# 'Continue', no 'Stop': git escribe a stderr en operaciones normales y en
# PowerShell 5.1 eso se vuelve error terminante. Los codigos de salida se
# comprueban explicitamente con Chk en cada paso.
$ErrorActionPreference = 'Continue'
$ArchivoDir = 'C:\Users\USER\Documents\informes y re organizacion antiguo y actual'

function Paso($t) { Write-Host ""; Write-Host "-- $t --------------------------------------" -ForegroundColor Cyan }
function Ok($t)   { Write-Host $t -ForegroundColor Green }
function Morir($t){ Write-Host "ABORTADO: $t" -ForegroundColor Red; exit 1 }
function Chk($t)  { if ($LASTEXITCODE -ne 0) { Morir $t } }

function PyRun([string]$Code, [string]$ErrMsg) {
    $tmp = [System.IO.Path]::GetTempFileName() + '.py'
    [System.IO.File]::WriteAllText($tmp, $Code, (New-Object System.Text.UTF8Encoding $false))
    try {
        & $script:Py $tmp
        if ($LASTEXITCODE -ne 0) { Morir $ErrMsg }
    } finally { Remove-Item $tmp -ErrorAction SilentlyContinue }
}

# ------------------------------------------------------------ 0. contexto
Paso "0. Contexto"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Morir "git no esta en el PATH" }

$script:Py = $null
foreach ($cand in @('py','python','python3')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) {
        & $cand -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $script:Py = $cand; break }
    }
}
if (-not $script:Py) { Morir "no encuentro Python (probe py, python, python3)" }

git rev-parse --is-inside-work-tree *> $null; Chk "no estas dentro de un repo git"
$remoto = (git remote get-url origin).Trim()
if ($remoto -notmatch 'benchmark2026') { Morir "el remoto no es benchmark2026 (es '$remoto')" }
$rama = (git rev-parse --abbrev-ref HEAD).Trim()
if ($rama -ne 'main') { Morir "este script solo opera sobre main (estas en '$rama')" }

Write-Host "  repo   : $((git rev-parse --show-toplevel).Trim())"
Write-Host "  python : $script:Py"
Write-Host "  rama   : $rama"


# Candado de git huerfano: si una operacion anterior murio a medias, queda un
# .git/index.lock y TODO git falla. Si lleva mas de un minuto ahi, esta muerto.
$lock = Join-Path (git rev-parse --git-dir).Trim() 'index.lock'
if (Test-Path $lock) {
    $edad = (Get-Date) - (Get-Item $lock).LastWriteTime
    if ($edad.TotalSeconds -gt 60) {
        Remove-Item $lock -Force
        Write-Host "  (quitado un .git/index.lock huerfano de hace $([int]$edad.TotalMinutes) min)" -ForegroundColor Yellow
    } else {
        Morir "hay un .git/index.lock reciente: otro git esta corriendo. Espera y reintenta."
    }
}

foreach ($t in @('ruff','mypy','pytest')) {
    & $script:Py -m $t --version *> $null
    if ($LASTEXITCODE -ne 0) { Morir "falta $t. Instala: $script:Py -m pip install -e `".[dev]`"" }
}
& $script:Py -c "import sklearn" 2>$null
if ($LASTEXITCODE -ne 0) { Morir "falta scikit-learn (extra 'sensors'). $script:Py -m pip install -e `".[dev]`"" }

# --------------------------------------------------- 1. finales de linea
Paso "1. Renormalizando finales de linea (.gitattributes)"
if (-not (Test-Path .gitattributes)) { Morir "falta .gitattributes" }
git add --renormalize . *> $null
Ok "  hecho"

# --------------------------------------------- 2. retirada de archivados
Paso "2. Retirando del repo lo archivado y los caches de evidencia"
$Retirar = @(
  'MEGAFILE_SESION_4R2_20260719.md',
  'Corrigiendo Evaluacion de ATBench.md',
  'Executing Guard Model OOD Evaluation.md',
  'INSTRUCCIONES_ANTIGRAVITY.md','INSTRUCCIONES_ANTIGRAVITY_ADAPTER_COMMIT.md',
  'INSTRUCCIONES_ANTIGRAVITY_PLAN_MAESTRO.md','INSTRUCCIONES_FASE_GUARD_MODEL.md',
  'PROMPT_ANTIGRAVITY_FASES_FINALES.md','PROMPT_ANTIGRAVITY_FASE_1_5.md',
  'PARA_SONNET_AUDITORIA_FINAL.md','PLAN_ESTRATEGICO_4R2.md','ROADMAP.md',
  'COMMIT_ADAPTER_ANTICAMO_wsl.sh','COMMIT_FASE1_benchmark_wsl.sh','PUSH_ADAPTER_wsl.sh'
)
if (-not (Test-Path $ArchivoDir)) { Morir "no encuentro la carpeta de archivo: $ArchivoDir" }
$n = 0
# nombres con acentos: resolvemos contra lo que git tiene realmente trackeado
$trackeados = (git ls-files) -split "`n"
foreach ($f in $Retirar) {
    $real = $trackeados | Where-Object { $_ -and ((Split-Path $_ -Leaf) -eq (Split-Path $f -Leaf)) } | Select-Object -First 1
    if (-not $real) { continue }
    $base = Split-Path $real -Leaf
    $copia = Get-ChildItem -Path $ArchivoDir -Recurse -Filter "*$base" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $copia) { Morir "no hay copia archivada de '$real' - no lo retiro" }
    if (-not $Dry) {
        git rm -q --cached $real *> $null
        Remove-Item $real -Force -ErrorAction SilentlyContinue
    }
    $n++
}
# carpeta completa de conversaciones
git ls-files --error-unmatch "conversaciones antigravity" *> $null
if ($LASTEXITCODE -eq 0 -and -not $Dry) {
    git rm -rq --cached "conversaciones antigravity" *> $null
    Remove-Item "conversaciones antigravity" -Recurse -Force -ErrorAction SilentlyContinue
    $n++
}
# caches: NO son evidencia (ya estan en .gitignore); salen del repo, quedan en disco
foreach ($c in @('evidence/guard_cache.json','evidence/guard_cache_llama.json','evidence/guard_cache_qwen.json')) {
    git ls-files --error-unmatch $c *> $null
    if ($LASTEXITCODE -ne 0) { continue }
    if (-not $Dry) { git rm -q --cached $c *> $null }
    $n++
}
Ok "  $n rutas a retirar (copias verificadas)"

# ------------------------------------------------------------- 3. GATES
Paso "3. Gates locales (identicos a GitHub Actions)"

Write-Host "  [1/6] ruff check..."
& $script:Py -m ruff check .; Chk "gate: ruff check"

Write-Host "  [2/6] ruff format --check..."
& $script:Py -m ruff format --check . *> $null; Chk "gate: formato (corrige con: $script:Py -m ruff format .)"

Write-Host "  [3/6] mypy --strict..."
& $script:Py -m mypy --strict src/aegisbench/core src/aegisbench/interfaces *> $null; Chk "gate: mypy"

Write-Host "  [4/6] pytest + cobertura >= 85%..."
& $script:Py -m pytest --cov=src/aegisbench --cov-fail-under=85 tests/ -q | Select-Object -Last 2
& $script:Py -m pytest --cov=src/aegisbench --cov-fail-under=85 tests/ -q *> $null; Chk "gate: tests o cobertura"

Write-Host "  [5/6] cadena de evidencia (cada .sha256 reproduce su artefacto)..."
& $script:Py scripts/verify_evidence_seals.py; Chk "gate: cadena de evidencia"

Write-Host "  [6/6] finales de linea..."
PyRun @'
import subprocess, sys, pathlib
EXCL = ("conversaciones antigravity/",)
EXCL_EXT = (".ps1", ".bat")
raw = subprocess.run(["git", "ls-files", "-z"], capture_output=True).stdout
malos = []
for b in raw.split(b"\0"):
    if not b:
        continue
    f = b.decode("utf-8", "surrogateescape")
    if f.startswith(EXCL) or f.endswith(EXCL_EXT):
        continue
    p = pathlib.Path(f)
    if not p.is_file():
        continue
    try:
        data = p.read_bytes()
    except OSError:
        continue
    # Un binario (.npz, imagen, zip) contiene 0x0D de forma legitima: no es un
    # final de linea. Se descarta por el byte NUL, heuristica estandar.
    if b"\0" in data:
        continue
    if b"\r" in data:
        malos.append(f)
if malos:
    print("CRLF detectado:")
    for m in malos[:20]:
        print("  ", m)
    print("Corrige con:  git add --renormalize .")
    sys.exit(1)
print("     OK")
'@ "gate: hay CRLF"

Ok "  LOS 6 GATES EN VERDE"

Write-Host "  smoke del CLI..."
& $script:Py -m aegisbench.cli.main run --adapter dummy --dataset xstest --n 10 *> $null
if ($LASTEXITCODE -ne 0) {
    & aegisbench run --adapter dummy --dataset xstest --n 10 *> $null
    Chk "gate: smoke del CLI"
}
Ok "  CLI OK"

if ($Dry) { Write-Host ""; Ok "-Dry: gates verificados. No se hizo commit ni push."; exit 0 }

# ------------------------------------------------------------- 4. commit
Paso "4. Commit"
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "  no hay cambios que commitear"
} else {
    $msg = @'
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
- Un solo PUSH_CANON (wsl.sh + .ps1) con los 6 gates antes de subir.

Nucleo de AegisBench y resultados cientificos SIN CAMBIOS.
'@
    $msgFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($msgFile, $msg, (New-Object System.Text.UTF8Encoding $false))
    git commit -q -F $msgFile; Chk "no pude crear el commit"
    Remove-Item $msgFile -ErrorAction SilentlyContinue
    Ok "  commit creado"
}

# --------------------------------------------------------------- 5. push
Paso "5. Publicando"
Write-Host "  main -> $remoto"
$ok = Read-Host "  Confirmas? [s/N]"
if ($ok -notmatch '^[sSyY]$') { Morir "cancelado por el usuario (no se subio nada)" }
git push origin main; Chk "fallo el push"
Ok "  publicado"

# ------------------------------------------- 6. verificacion desde clon
Paso "6. Verificando desde un clon limpio"
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("bench_" + [guid]::NewGuid().ToString('N').Substring(0,8))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
$aqui = Get-Location
try {
    git clone -q --depth 1 $remoto "$tmp\v"; Chk "no pude clonar"
    Set-Location "$tmp\v"
    & $script:Py scripts/verify_evidence_seals.py | Select-Object -Last 3
    if ($LASTEXITCODE -eq 0) { Ok "  clon limpio: sellos verificados" }
    else { Write-Host "  AVISO: los sellos NO verifican en el clon" -ForegroundColor Red }
} finally {
    Set-Location $aqui
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Ok "============================================================"
Ok " LISTO. Comprueba los 3 jobs del CI (3.10/3.11/3.12) en verde."
Ok "============================================================"
Write-Host " Siguiente gate del roadmap: publicar fuse-ai en PyPI y abrir"
Write-Host " AegisBench en publico. Es el gate que lleva meses sin cruzarse."
