# Tarea A — Cerrar cabo suelto: commitear el adapter (workspace: benchmark2026)

> ALCANCE: SOLO benchmark2026, rama `main`. Trabajo LOCAL. NO hagas push salvo
> que el humano lo autorice explícitamente. NO toques el scoring del benchmark
> (su neutralidad es un activo): el adapter solo CONFIGURA el sistema bajo prueba.

## Contexto
`adapters_external/fourr2_adapter.py` quedó MODIFICADO en el working-tree (añade
parámetros opt-in `governance/anticamo/embedder/nli_backend`) pero SIN commitear.
Fue el adapter usado para validar la defensa anti-camuflaje de 4R2 en el split
held-out. Hay que versionarlo para que la validación quede reproducible.

## Pasos (verificar antes de commitear)
```bash
# 1) Confirmar que SOLO cambió el adapter (no el core del benchmark)
git status --short
git diff --stat            # esperado: solo adapters_external/fourr2_adapter.py

# 2) Sintaxis intacta (anti-truncación)
python -c "import ast; ast.parse(open('adapters_external/fourr2_adapter.py',encoding='utf-8').read()); print('sintaxis OK')"

# 3) Confirmar que el SCORING del benchmark NO cambió
git diff -- src/aegisbench/stats/ src/aegisbench/core/   # DEBE salir vacío

# 4) Commit (LOCAL, sin push)
git add adapters_external/fourr2_adapter.py
git commit -m "feat(adapter): params opt-in governance/anticamo/embedder/nli en FourR2Adapter

Solo configura el sistema bajo prueba; el scoring del benchmark NO cambia
(neutralidad preservada). Usado para validar la defensa anti-camuflaje de 4R2
en el split held-out (n=8, AUROC 1.000, theta 0.46)."
git log --oneline -3
```
Si ya existe `COMMIT_ADAPTER_ANTICAMO_wsl.sh` en el repo, verifica que haga
exactamente esto y úsalo; si difiere, prevalece lo de arriba. NO `git push`.

## Qué NO hacer
- No modificar `src/aegisbench/` (scoring/datasets/stats). No push. No mezclar 4r2.
