# Primer intento real de conectar 4R2 a AegisBench — veredicto honesto

**Lo mecánico funciona, el resultado numérico de hoy NO es confiable — y encontré por qué, no lo asumí.**

## Lo que sí está verificado y funciona

- Adaptador `adapters_external/fourr2_adapter.py` en tu repo Benchmark2026, usando la API pública real (`four_r2.Guardrail`), no el kernel interno.
- `aegisbench validate-adapter` → éxito, cumple el contrato v1.
- `selftest()` del kernel real → invariantes correctas (`perfect_c: 0.0`, `loss_correct_direction: True`).
- Corrida real contra los 5 datasets (97 muestras, seed 42): mecánicamente completa, sin errores, reportes generados.

## Por qué el número "ASR=100%" que salió NO significa que 4R2 falle

Hice la prueba de diagnóstico que faltaba antes de reportar el número, y encontré el problema:

4R2 (`Guardrail.evaluate`) necesita **tres** entradas distintas: política, petición, y **respuesta del agente**. AegisBench v1 solo tiene peticiones de un solo turno — no genera respuesta de ningún agente. Para poder correr algo, usé `response = request` (la misma muestra en ambos campos). Al probarlo a mano:

```
harmful (response=request) -> c_total=0.3322, C_RI=0.0
benign  (response=request) -> c_total=0.3219, C_RI=0.0
```

`C_RI` (coherencia representacional-informacional) sale **0.0 siempre**, dañino o benigno, porque comparo el texto contra sí mismo con el mismo embedder — la distancia es mecánicamente cero, no importa el contenido. Y `C_IF` queda fija en 0.5 porque nunca le doy verificabilidad real. Con dos de los tres ejes de NRIF anulados por construcción, `c_total` queda atrapado justo debajo de `theta=0.35` para prácticamente cualquier texto — dañino o no. Probé un mapeo alterno (petición fija + la muestra como respuesta) y pasa lo mismo en sentido opuesto: ahí *todo* sale FLAG, dañino o benigno, porque el eje que sí varía deja de tener relación con el daño real del contenido.

Verifiqué que el kernel SÍ discrimina bien cuando los tres campos son genuinamente distintos y semánticamente relacionados — el propio ejemplo de tu `quickstart.py` (política de viáticos, petición sobre límites, respuesta que transfiere dinero sin autorización) da `FLAG` correctamente. El problema no es 4R2 — es que **ninguna forma honesta de meter una sola muestra de AegisBench en un contrato de 3 entradas evita degenerar al menos un eje**, y sin los tres ejes vivos, NRIF no tiene con qué discriminar.

## Conclusión

**El resultado de hoy (ASR=100%, ORR=0%) es un artefacto del harness de prueba, no una medición real de la capacidad de defensa de 4R2.** Reportarlo como "4R2 falla" sería exactamente el tipo de afirmación no verificada que este proyecto existe para evitar. No lo voy a usar como dato.

## Hallazgo lateral confirmado (ya conocido, reconfirmado hoy)

En esta misma corrida, GitHub devolvió 429 (Too Many Requests) para advbench y harmbench — cayeron a datos sintéticos de fallback, visible en consola pero **sin rastro en report.json** (el campo `synthetic_fallback` que otra sesión de Claude afirmó haber agregado nunca llegó al repo real — lo confirmé revisando el commit `2c6b7a7`, no aparece). Sigue pendiente.

## Camino honesto hacia adelante (para decidir, no para asumir)

Para probar 4R2 de verdad necesitamos que cada muestra traiga una **respuesta real o simulada de forma no degenerada** de un agente, no solo la petición. Dos formas legítimas de conseguirlo:

1. **Extender AegisBench a "session-aware"**: que el `Sample` pueda traer `turns` con un segundo mensaje `role="assistant"` (respuesta real o generada por un LLM barato para el propósito del test). Esto es un cambio de diseño real en AegisBench (afecta el contrato v1), no un parche del adaptador.
2. **Usar un dataset que ya venga con pares petición+respuesta** (ej. transcripciones de jailbreak con la respuesta del modelo objetivo, como el propio JailbreakBench en su forma completa con "target model responses", si están disponibles) en vez de datasets de solo-petición.

No voy a avanzar con ninguna de las dos sin que la elijas — son decisiones de diseño reales, no un gap para "arreglar y seguir".
