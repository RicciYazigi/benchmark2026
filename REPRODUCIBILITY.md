# Reproducibilidad y ejecución offline — AegisBench

AegisBench busca métricas reproducibles. Los datasets reales se descargan de
fuentes públicas (GitHub/HuggingFace) y se validan por SHA256 contra
`datasets.lock.json`. Como esas fuentes pueden dar 429/403 transitorios, el
loader ahora es resiliente y auditable:

## Robustez de descarga
- **Reintentos con backoff:** `download_file` reintenta hasta 3 veces ante
  errores transitorios (HTTP 429/5xx y errores de red), respetando `Retry-After`.
  Un fallo de integridad SHA256 es fallo DURO (no se reintenta).
- **Caché local:** los archivos validados se guardan en `~/.aegisbench/cache`
  (configurable con `AEGISBENCH_CACHE_DIR`). Una vez cacheados, las corridas son
  offline y deterministas.

## Dos modos, elegir según el propósito
- **Desarrollo/offline (por defecto):** si un dataset real no se puede obtener,
  se cae a muestras SINTÉTICAS locales. Esto queda MARCADO de forma visible:
  `report.json` trae `summary.synthetic_fallback=true` +
  `synthetic_fallback_samples`, y `report.md/html` muestran una advertencia. Nunca
  se reportan métricas sintéticas como si fueran reales de forma silenciosa.
- **Oficial/CI (`--strict-datasets`):** si un dataset real falla, la corrida
  ABORTA con exit 1 en vez de sustituir por sintético. Usar SIEMPRE este modo
  para cualquier número que se vaya a publicar o comparar.

## Pre-cargar caché (air-gapped)
```bash
# En una máquina con red, poblar la caché:
export AEGISBENCH_CACHE_DIR=/ruta/portable/cache
python -m aegisbench.cli.main run --adapter dummy --dataset all \
    --accept-agentharm-terms --strict-datasets --output /tmp/warm
# Copiar /ruta/portable/cache a la máquina sin red y exportar la misma env var.
```

## AgentHarm (licencia restringida)
Aceptación no-interactiva para CI: exportar `AEGISBENCH_ACCEPT_AGENTHARM=1`
(equivale a la flag `--accept-agentharm-terms`). Sin aceptación, AgentHarm se
salta con aviso explícito.

## Determinismo
Bootstrap con `n_resamples=10000` y semilla fija `42`; split held-out 80/20 por
hash MD5 del `sample_id`. `aegisbench doctor` verifica determinismo en corridas
paralelas.
