# 4R2 × AegisBench — corrida OFICIAL por CLI, stack completo (2026-07-10)

**Estado: PASS · reproducido por el CLI oficial, seed 42, dataset `policy_compliance`.**
Sistema bajo prueba: `four_r2.Guardrail` (SDK público), embedder léxico
(HashingEmbedder). Sin cambios en el scoring del benchmark ni en el kernel 4R2.

## 1. El bug que bloqueaba la medición era del ADAPTER, no de 4R2 ni de AegisBench

AegisBench define `confidence` = *confianza en la decisión tomada* (stats hace
`score = conf` si BLOCK/ESCALATE, `score = 1 − conf` si ALLOW). El adapter
exponía `c_total` (score de riesgo) crudo — violaba ese contrato y el flip
destrozaba el ranking: governance daba AUROC 0.394 **artefactual** mientras el
C_NI del SDK, medido directo, da 0.7732. Fix (solo en `adapters_external/`):
`conf = riesgo` si bloquea/escala, `conf = 1 − riesgo` si permite → el score
continuo reconstruido por el benchmark es exactamente `c_total`.

**Verificación de imparcialidad:** con el fix, layer1 mantiene su AUROC 0.358
(el hallazgo negativo del kernel Capa-1 NO cambió — el fix no maquilla nada;
solo repara la semántica del contrato para cualquier adapter score-based).

## 2. Mejora de infraestructura del benchmark (genérica)

`aegisbench run` gana `--param clave=valor` (repetible, coerción automática)
para pasar parámetros de constructor a CUALQUIER adapter — los modos opt-in
eran inaccesibles desde runs oficiales. No toca scoring.

## 3. Resultados oficiales (dev n=42, 21/21, seed 42, θ=0.35 salvo indicado)

| Config (`--param`) | AUROC | AUPRC | ASR | ORR | Lectura |
|:--|:--:|:--:|:--:|:--:|:--|
| layer1 (kernel Capa-1) | 0.358 | 0.424 | 0% | 100% | Confirma hallazgo negativo previo: no rankea esta tarea |
| governance=true | **0.773** | 0.779 | 4.8% | 57.1% | Reproduce EXACTO la validación Fase 3 independiente |
| governance+anticamo | 0.687 | 0.660 | **0%** | 76.2% | Anticamo en datos limpios: peor ranking, mejor ASR (diseñado para camuflaje) |
| governance, θ=0.38 (calibrado) | 0.773 | — | 33.3% | 23.8% | Punto de operación validado: reproduce 33%/24% de Fase 3 |
| governance, θ=0.38, **held-out incluido** (n=50) | **0.802** | — | 32% | 24% | Generaliza al split no visto |

## 4. Lecturas honestas

1. **La cadena de validación cierra:** spec → validación independiente (0.773)
   → SDK real por CLI oficial (0.7732). Tres mediciones, dos implementaciones,
   mismo número.
2. **El kernel NRIF Capa-1 sigue sin discriminar cumplimiento de política**
   (0.358). El valor de gobernanza viene del modo governance (C_NI), opt-in.
   Mantener esta distinción en todo pitch.
3. **Anticamo no es gratis en datos limpios** (−0.086 AUROC vs governance
   puro). Es una defensa para condiciones adversariales (camuflaje); su
   evaluación justa requiere el dataset adversarial correspondiente
   (VALIDACION_ANTICAMUFLAJE en el repo 4R2). Recomendación de despliegue:
   governance para ranking/calibración, anticamo activado cuando el modelo de
   amenaza incluya evasión.
4. **Límites:** n pequeño (42 dev / 8 held-out), embedder léxico (tier
   semántico corre en host con sentence-transformers), un solo dataset curado
   (CC0, in-repo), C_IF neutro (AegisBench v1 no modela verificabilidad).

## 5. Reproducir

```bash
export FOURR2_REPO_PATH=<raiz 4r2v6>
export PYTHONPATH=<raiz benchmark>/src:<raiz benchmark>
python -m aegisbench.cli.main run -a adapters_external.fourr2_adapter:FourR2Adapter \
  -d policy_compliance -s 42 -o reports_gov \
  --param governance=true --param theta=0.38 --include-held-out
```
