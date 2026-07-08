# Roadmap

## v1.1
- OR-Bench integration (larger-scale over-refusal testing)
- McNemar's test and permutation tests for paired adapter comparison
- Multilingual safety prompt set

## v1.2
- Adaptive/optimization-based attacks (GCG, PAIR, TAP) as an opt-in "adversarial" mode
- Streaming evaluation support
- Domain-specific packs (healthcare, finance) as plugins

## v2.0
- Frozen public benchmark release with held-out leaderboard split
- Interactive dashboard
- Plugin API for third-party dataset/attack contributions

---

## Extensiones Detalladas del Equipo de Desarrollo (AegisBench)

### Planificación de Versión Corto Plazo (v1.1)
- **Soporte Multilingüe:** Implementación de un pipeline de traducción automática integrado para evaluar la robustez transfronteriza de los sistemas de gobernanza frente a ataques formulados en idiomas de bajos recursos.
- **Tests Estadísticos Comparativos:** Integración del test de McNemar para comparar si las diferencias en ASR u ORR entre dos adaptadores son estadísticamente significativas con muestras emparejadas.

### Planificación Adversarial (v1.2)
- **Ataques Optimizados de Caja Blanca:** Integración de ataques basados en optimización de gradientes como GCG (Greedy Coordinate Gradient) bajo un entorno sandbox controlado para simular atacantes persistentes con acceso al modelo de lenguaje subyacente.
- **Stress-Testing de Contexto Largo:** Pruebas de inyección de prompts indirectas ocultas en documentos de gran volumen (10k+ tokens).

### Visión de Lanzamiento de Producción (v2.0)
- **Infraestructura de Leaderboard:** Un portal web interactivo autohospedado donde investigadores de todo el mundo puedan subir sus adaptadores empaquetados para ser evaluados en una sandbox aislada contra el split de datos held-out oculto oficial de AegisBench.
