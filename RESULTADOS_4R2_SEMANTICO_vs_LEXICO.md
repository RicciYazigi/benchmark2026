# 4R2 léxico vs semántico — la pregunta abierta, resuelta

**Fecha:** 2026-07-08 · dataset `policy_compliance` (42 muestras, 21/21) · seed fija.
Medición local, sin tocar 4r2v6.

## Pregunta
El primer run de 4R2 (embedder LÉXICO por defecto) dio AUROC 0.358 (no separa
violación de cumplimiento). Quedaba la duda: ¿es el kernel, o solo el embedder
léxico? Se probó el embedder SEMÁNTICO real de 4R2 (`SentenceTransformerEmbedder`,
all-MiniLM-L6-v2, dim 384).

## Resultado
| Embedder | AUROC | c_total viol / cumpl | C_NR vivo | C_RI vivo | C_IF |
|----------|-------|----------------------|-----------|-----------|------|
| Léxico (Hashing) | **0.358** | 0.417 / 0.432 | sí (sd 0.048) | sí (sd 0.060) | fijo 0.5 |
| Semántico (MiniLM) | **0.281** | 0.365 / 0.379 | sí (sd 0.046) | sí (sd 0.049) | fijo 0.5 |
| **Δ (sem − léx)** | **−0.077** | — | — | — | — |

## Conclusión (honesta)
El embedder semántico **NO rescata** la discriminación; incluso empeora
levemente. Ambos ejes activos (C_NR, C_RI) varían pero no rankean las violaciones
por encima de los cumplimientos. La duda queda cerrada: **el problema no es el
embedder** — es que el gate de coherencia (Capa 1), tal como está formulado, no
es un buen clasificador de gobernanza de respuestas para tareas de cumplimiento
de política.

## Implicación para calibración (Fase 3)
- **AUROC es independiente del umbral `theta`.** Recalibrar theta NO cambia esto:
  solo mueve el punto de operación (cambia ASR↔ORR), no mejora el ranking. El
  lever "subir/bajar theta" no arregla la discriminación.
- El problema es de **separación de la señal**, no de umbral. Opciones reales de
  Fase 3: re-formular/reponderar los ejes NRIF, aportar el eje C_IF
  (verificabilidad) que aquí está muerto, o aceptar que Capa 1 no es la
  herramienta para este tipo de tarea y medir 4R2 donde sí aporta (CCA/térmico/
  sesión), que este benchmark de un turno no ejercita.

## Límites
N=42 (IC amplio); AUROC<0.5 sugiere posible inversión débil, no señal fuerte.
Solo Capa 1, un perfil de pesos (balanced), C_IF neutro. Corrobora e independiza
el hallazgo negativo de APEX Fase 1.
