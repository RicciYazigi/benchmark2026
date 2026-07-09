# 4R2 via AegisBench — primer resultado real NO degenerado (response-governance)

**Fecha:** 2026-07-08 · **Estado:** hallazgo negativo honesto, reproducido de forma independiente.

## Setup (verificado por ejecucion)
- Sistema bajo prueba: 4R2 SDK `four_r2.Guardrail`, **Capa 1** (gate de coherencia NRIF), `theta=0.35`, `weights_profile=balanced`.
- Embedder: **HashingEmbedder por defecto (LEXICO, no semantico)**.
- Dataset: `policy_compliance` (curado, response-governance), 42 muestras de evaluacion, **21 violacion / 21 cumplimiento** (split held-out 80/20 aplicado sobre 50 curadas).
- Mapeo (NO degenerado, verificado eje por eje): `policy=metadata["policy"]`, `request=turno user`, `response=turno assistant`. Los tres textos son distintos por muestra.

## Verificacion de no-degeneracion (lo que fallo en el intento anterior)
| Eje | Violacion (ej.) | Cumplimiento (ej.) | Estado |
|-----|-----------------|--------------------|--------|
| C_NR | 0.468 | 0.420 | VIVO (varia) |
| C_RI | 0.337 | 0.370 | VIVO (varia, != 0) |
| C_IF | 0.500 | 0.500 | neutro fijo (AegisBench no aporta verificabilidad) |

El intento previo (response=request) colapsaba C_RI a 0.0; aqui C_RI varia. El resultado ya NO es un artefacto del harness.

## Resultado (CLI oficial de AegisBench, corroborado por script independiente)
| Metrica | Valor |
|---------|-------|
| ASR | 0.00% (CI95 [0,0]) |
| ORR (sobre-bloqueo) | 100.00% (CI95 [100,100]) |
| Escalation rate | 100.00% |
| AUROC | **0.358** |
| AUPRC | 0.424 |
| Precision / Recall / F1 | 0.50 / 1.00 / 0.667 |

**Lectura honesta:** 4R2 Capa-1 con embedder lexico **escala TODAS las muestras a FLAG** (violacion y cumplimiento por igual). `c_total` se agrupa en ~0.42-0.43, siempre por encima de `theta=0.35`. No discrimina: atrapa todas las violaciones (recall 1.0) solo porque marca todo, al costo de sobre-bloquear el 100% de las respuestas que cumplen. AUROC 0.358 < 0.5 = por debajo del azar en este set.

**Corroboracion independiente:** este resultado reproduce el hallazgo negativo de la Fase 1 de APEX (AUROC ~0.41) con **otra herramienta** (AegisBench, construida por Antigravity SIN conocer 4R2), **otros datos** (response-governance, no jailbreak), y un **mapeo no degenerado**. Dos mediciones distintas coincidiendo = evidencia solida de un hallazgo negativo real.

## Limites explicitos (que NO se puede concluir de esto)
1. Solo Capa 1 con embedder **lexico**. El tier semantico (sentence-transformers) quedo **ND** por espacio de disco del entorno — con embeddings semanticos C_NR/C_RI podrian separar mejor. Es la pregunta abierta principal.
2. C_IF fijo en 0.5 (AegisBench v1 no modela verificabilidad/grounding por muestra).
3. NO ejercita CCA / snapshot termico / Mario-Luigi-Arbiter (necesitan estado de sesion).
4. n=42, seed fija, un solo perfil de pesos, un solo theta. N pequeno.
5. `policy_compliance` es un set curado in-repo (CC0), NO un benchmark publico reconocido.

## Reproducir
```
export FOURR2_REPO_PATH=<raiz de 4r2v6>
export PYTHONPATH=<raiz benchmark2026>:<raiz benchmark2026>/src
python -m aegisbench.cli.main run \
  --adapter adapters_external.fourr2_adapter:FourR2Adapter \
  --dataset policy_compliance --output reports
```
