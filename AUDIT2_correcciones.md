# AegisBench v1.0 — Re-auditoría de correcciones (contra el reporte "todo corregido y pusheado")

**Método:** clon limpio del repo local vía git (bypass de la vista de mount, que mostró archivos truncados — ver nota al final), más consulta directa a la API pública de GitHub (`api.github.com/repos/RicciYazigi/benchmark2026/git/trees/main`) para verificar el estado REAL del repo publicado, no lo que el asistente afirma haber subido.

## Resumen ejecutivo

El fix del P0 original (datasets reales) **es genuino y funciona** — confirmado con descargas reales en esta sesión. Pero el proceso de `git add .` con un `.gitignore` mal escrito **excluyó silenciosamente el módulo `src/aegisbench/reports/` completo del commit y del push**. Resultado: el repositorio público en GitHub ahora mismo **no se puede instalar ni ejecutar** (`ModuleNotFoundError: No module named 'aegisbench.reports'` al importar la CLI). Es un defecto nuevo, más grave que los de la primera auditoría, e invisible en el reporte de Antigravity porque nunca probó un `pip install` limpio desde el repo remoto.

## ✅ Verificado como corregido (evidencia real, no solo el reporte)

- **P0 datasets reales — CONFIRMADO FUNCIONAL.** Descargué directamente los 5 datasets con las URLs/hashes nuevos: los 5 pasan validación SHA256 real. `load_dataset()` devuelve muestras reales (no sintéticas) para advbench (411), harmbench (70), xstest (361) y agentharm (141, con `--accept-agentharm-terms`). Los hashes de advbench y harmbench coinciden exactamente con los que yo mismo calculé de forma independiente en la primera auditoría — corroboración cruzada real.
- Atribución de AgentHarm corregida: ahora dice "UK AI Safety Institute" en `DATASET_LICENSES.md`, coincide con lo verificado externamente.
- `mypy --strict` en `core/`+`interfaces/`: limpio.
- Repo es público y accesible (confirmado vía API de GitHub sin autenticación).

## 🔴 P0 NUEVO — Repo publicado no es instalable (no reportado)

`.gitignore` línea 25 tiene `reports/` sin barra inicial. Ese patrón de gitignore coincide con **cualquier** carpeta llamada `reports` en el árbol, no solo la carpeta de salida `./reports/` en la raíz — también atrapó `src/aegisbench/reports/` (el módulo fuente con `renderers.py`, 530 líneas, responsable de generar JSON/CSV/MD/HTML). `git check-ignore -v` lo confirma. Verificado en vivo contra la API de GitHub: **0 rutas contienen "reports" en el árbol de `main`**, de 54 archivos totales. `aegisbench/cli/main.py` importa `from aegisbench.reports.renderers import write_reports` en la línea 25 — sin ese módulo, cualquier `import aegisbench.cli.main` (que ocurre al cargar la CLI) falla inmediatamente.

**Corrección:** cambiar `.gitignore` línea 25 de `reports/` a `/reports/` (ancla a la raíz del repo), luego `git add src/aegisbench/reports/ -f && git commit && git push`.

## 🟠 P1 NUEVO — Parser de JailbreakBench devuelve 0 muestras silenciosamente

Con la URL nueva (HuggingFace, correcta) descargando bien, `load_dataset("jailbreakbench")` devuelve **0 muestras**, sin error ni warning. Causa: el CSV real tiene columnas `Index,Goal,Target,Behavior,Category,Source` (capitalizadas), pero `parse_dataset_file` busca `row.get("goal")` / `row.get("category")` en minúsculas — no encuentra nada, cada fila se descarta silenciosamente (`if not prompt: continue`). Mismo patrón de fallo que el hallazgo original: una suposición sobre el formato de una fuente externa nunca verificada contra el archivo real. De los 5 datasets, JailbreakBench (el que da nombre al benchmark de jailbreaks) es el único que sigue efectivamente vacío tras el "fix".

**Corrección:** normalizar el parser con `{k.lower(): v for k, v in row.items()}` antes de buscar claves, o usar `row.get("Goal") or row.get("goal")` explícito.

## 🟡 P2 — Ruff no quedó 100% limpio

Nueva advertencia introducida en la propia edición de `loaders.py` (línea en blanco con espacios, `W293`). Trivial, un `--fix` la resuelve, pero contradice "corregidas todas las advertencias del linter ruff".

## Nota sobre archivos truncados en el mount local

Al leer el working tree vía este entorno, varios archivos (`datasets.lock.json`, `loaders.py`, `test_cli.py`, etc.) aparecían truncados/con JSON inválido. Un `git clone` local (que reconstruye desde los objetos de git, no desde la vista del mount) mostró contenido completo y válido, coincidente con lo publicado en GitHub. Conclusión: es un artefacto de sincronización del mount hacia este entorno, no una corrupción real de tu repo — pero si abres esos archivos directamente en tu máquina y ves contenido cortado, vale la pena cerrar y reabrir el editor / verificar que el disco local no tenga el mismo problema antes de seguir editando sobre esa vista.

## Gate

**Gate C: SIGUE SIN CUMPLIRSE.** El repo público está roto (no importable) por el bug de `.gitignore`. Antes de considerar v1.0 publicable:
1. Arreglar `.gitignore` (`reports/` → `/reports/`), forzar add del módulo, commit y push.
2. Arreglar el parser case-insensitive de JailbreakBench (y verificar los otros 4 con el mismo patrón, por si acaso).
3. `ruff check --fix .` de nuevo.
4. Después de todo eso: clonar el repo en un entorno limpio (no el mismo donde se desarrolló) y correr `pip install .` + `aegisbench run --adapter dummy --dataset all --accept-agentharm-terms` de punta a punta, exactamente como lo haría un usuario nuevo — es la única prueba que hubiera detectado el bug de `reports/`.
