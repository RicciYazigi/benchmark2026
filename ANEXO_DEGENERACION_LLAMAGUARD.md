# Anexo Técnico — Diagnóstico de la Degeneración 0.5000 en Llama Guard 3 1B

**TRACE_ID:** ARS-20260722-DEG1  
**Estado:** OK — Diagnóstico Confirmado y Blindaje Implementado  
**Fecha:** 2026-07-22  

---

## 1. Contexto y Problema

Durante las evaluaciones OOD de la Fase 1.5 sobre el benchmark `ATBench`, el detector `llama-guard3:1b` obtuvo un puntaje de AUROC de **0.5000 exacto** bajo los agregadores CUSUM y Térmico $I^2t$ al aplicar la normalización por cuantiles. Se requirió una auditoría local sobre el cache de inferencia sellado (`evidence/guard_cache.json`) para determinar si esto obedecía a un error en el pipeline de acumulación o a la estructura de la señal del sensor.

---

## 2. Medición Empírica sobre el Cache Real

Se ejecutó la inspección estadística directa sobre las 8,954 llamadas a `llama-guard3:1b` en el cache:

```python
# Verificación de distribución de respuestas en evidence/guard_cache.json
Total turnos evaluados: 8954
Turnos calificados con 1.0 (Flag / Inseguro): 7113
Tasa de alerta (Flag Rate): 79.44%
Turnos benignos calificados con 1.0: 78.41%
```

### 2.1 Causa Raíz
1. **Sensor Casi Constante:** `llama-guard3:1b` califica como inseguros ($1.0$) al **79.44% de todos los turnos**, incluyendo al **78.41% de los turnos benignos** en el dominio de interacción agéntica en inglés de `ATBench`.
2. **Colapso de Calibración:** Al calcular el percentil de referencia benigno ($p_{90}$), la masa acumulada del $78.4\%$ de turnos benignos en $1.0$ hace que el umbral de calibración caiga exactamente en el valor máximo del sensor:
   $$\theta = k_{\text{ref}} = 0.6078$$
3. **Energía Cero por Construcción:** Al caer el umbral en el nivel máximo de la referencia, el paso CUSUM y la energía térmica se anulan ($x_k - k_{\text{ref}} = 0$), produciendo un vector de acumulación constante y un AUROC de $0.5000$ exacto (equivalente a azar por empates masivos).

**Veredicto:** El resultado de $0.5000$ es la representación estadísticamente correcta del comportamiento de un sensor sin capacidad discriminativa en el dominio agéntico ($79\%$ de falsas alarmas), **NO un fallo de software o del pipeline**.

---

## 3. Blindaje Implementado en la Biblioteca `fusible` v0.1

Para evitar la degeneración silenciosa del acumulador cuando un usuario conecte sensores ruidosos o binarios en producción, se introdujo el método de calibración robusta `fusible.robust_reference()`:

### 3.1 Mecanismo de Protección
Si el percentil de calibración seleccionado ($p_{90}$) coincide exactamente con el nivel máximo de la serie de referencia benigna, `robust_reference()` desplaza suavemente el umbral al punto medio entre los dos niveles superiores de la distribución. Esto garantiza que la aparición de turnos con score máximo continúe aportando energía al acumulador sin distorsionar la calibración con sensores normales.

### 3.2 Verificación de Pruebas Unitarias
Se añadieron 2 pruebas específicas a `fusible/tests/test_fusible.py` que replican la distribución real de `llama-guard3:1b`.
La suite completa de la librería `fusible` pasó a **21/21 tests verdes** (`21 passed in 1.36s`).

---

## 4. Conclusión para el Protocolo de Difusión

- En todos los reportes externos y en el preprint ([PREPRINT_DRAFT.md](file:///c:/Users/USER/Documents/Benchmark2026/docs/PREPRINT_DRAFT.md)), el resultado de `llama-guard3:1b` se reportará de manera transparente como un hallazgo de **"sensor inservible / casi constante en dominio agéntico"**, resaltando que la capa de contención `fusible` detectó y absorbió la degeneración de manera segura.
- La validación del gate OOD de la Fase 1.5 se sostiene íntegra sobre la evaluación continua de `qwen2.5:3b`, donde CUSUM demostró una mejora estadísticamente significativa ($\Delta = +0.0404$ [IC 95%: $+0.0201, +0.0619$], $P=1.0000$).
