# Guía de Creación de Adaptadores

> [!IMPORTANT]
> **Alineación con Tesis Congelada (2026-07-27)**
> AegisBench es el arnés de evaluación independiente de runtime governance (Apache 2.0). Los adaptadores representan sistemas bajo prueba (como `fuse-ai` / `fusible` o clasificadores de terceros).

Esta guía explica detalladamente cómo integrar cualquier sistema de gobernanza de IA (comercial, open-source o local) en AegisBench.

---

## 1. El Contrato de Datos

Cada sistema de gobernanza evaluado debe comunicarse utilizando la interfaz inmutable versión 1 de AegisBench (`src/aegisbench/interfaces/v1.py`). Tu adaptador debe heredar de `TargetSystem`:

```python
from aegisbench.interfaces.v1 import TargetSystem, Sample, EvalResult, GovernanceDecision, ScenarioType

class MiAdaptadorPersonalizado(TargetSystem):
    name: str = "mi_sistema_gobernanza"
    version: str = "1.0.0"

    def evaluate(self, sample: Sample) -> EvalResult:
        # Implementa tu lógica de evaluación de seguridad aquí
        pass

    def supports_scenario(self, scenario_type: ScenarioType) -> bool:
        # Indica si tu sistema soporta este tipo de escenario
        pass
```

### Reglas de Implementación

1. **`evaluate(self, sample: Sample) -> EvalResult`**
   - Debe ser hilo-seguro (thread-safe), ya que AegisBench puede ejecutarlo con concurrencia > 1.
   - Debe retornar un objeto `EvalResult` con el ID de la muestra original, la decisión tomada (`ALLOW`, `BLOCK` o `ESCALATE`), y la latencia calculada internamente en milisegundos (`latency_ms`).
   - Si tu sistema expone una puntuación continua de confianza, asígnala al atributo `confidence` (rango $0.0$ a $1.0$). Si no la expone, establécela en `None`. No inventes valores artificiales, ya que distorsionará el cálculo de AUROC/AUPRC.

2. **`supports_scenario(self, scenario_type: ScenarioType) -> bool`**
   - Si tu sistema no soporta evaluación de agentes multiturno (`ScenarioType.AGENTIC_TOOL_USE`) o control de sobrebloqueos (`ScenarioType.OVER_REFUSAL_CONTROL`), retorna `False`. El orquestador de AegisBench saltará limpiamente la muestra y la reportará como N/A sin fallar el proceso general.

---

## 2. Ejemplo Práctico de Adaptador

A continuación se muestra un adaptador mínimo que se conecta a una API de seguridad HTTP local:

```python
import time
import requests
from aegisbench.interfaces.v1 import TargetSystem, Sample, EvalResult, GovernanceDecision, ScenarioType

class HTTPShieldAdapter(TargetSystem):
    name = "http_shield"
    version = "1.2.0"

    def __init__(self, endpoint_url: str = "http://localhost:8080/check"):
        self.endpoint_url = endpoint_url

    def evaluate(self, sample: Sample) -> EvalResult:
        # Extraer el contenido del último turno del usuario
        user_prompt = sample.turns[0].content if sample.turns else ""
        
        start_time = time.perf_counter()
        
        try:
            response = requests.post(
                self.endpoint_url,
                json={"prompt": user_prompt},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Mapear decisión de la respuesta API
            api_decision = data.get("action")  # "allow", "block", "escalate"
            decision = GovernanceDecision(api_decision)
            confidence = data.get("confidence")  # Opcional, float o None
            
        except Exception as e:
            # Tolerancia a fallos: decidir bloquear o escalar en caso de error
            decision = GovernanceDecision.ESCALATE
            confidence = None
            
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        return EvalResult(
            sample_id=sample.sample_id,
            decision=decision,
            confidence=confidence,
            latency_ms=latency_ms,
            adapter_name=self.name,
            adapter_version=self.version,
            raw_output=str(data) if 'data' in locals() else f"Error: {e}"
        )

    def supports_scenario(self, scenario_type: ScenarioType) -> bool:
        # Este adaptador de API de texto simple solo soporta prompts de un único turno
        return scenario_type == ScenarioType.SINGLE_TURN
```

---

## 3. Ejecución del Adaptador en la CLI

Para evaluar tu adaptador en la CLI de AegisBench, no es obligatorio modificar el código fuente del benchmark. Puedes pasar la ruta calificada de tu módulo de Python directamente a través de la bandera `--adapter`:

```bash
# Validar el adaptador antes de correr el benchmark
aegisbench validate-adapter --adapter mi_modulo.mi_archivo:HTTPShieldAdapter

# Ejecutar la evaluación contra todos los datasets
aegisbench run --adapter mi_modulo.mi_archivo:HTTPShieldAdapter --dataset all --concurrency 4
```

> [!NOTE]
> Asegúrate de que el directorio que contiene tu módulo python (`mi_modulo`) se encuentre en tu variable de entorno `PYTHONPATH` para que la CLI pueda importarlo dinámicamente sin inconvenientes.

## Semántica de `confidence` (aclaración 2026-07-10, obligatoria)

`EvalResult.confidence` es la **confianza en la decisión tomada**, no un score
de riesgo. El cálculo de AUROC reconstruye el score continuo de bloqueo como
`conf` si la decisión es BLOCK/ESCALATE y `1 − conf` si es ALLOW. Si tu sistema
produce un score de riesgo r (mayor = más dañino), el mapeo correcto es:
`confidence = r` al bloquear/escalar y `confidence = 1 − r` al permitir.
Exponer `r` crudo viola el contrato y produce AUROC artefactual (caso real
documentado en RESULTADOS_4R2_OFICIAL_CLI.md §1).

## Parámetros de adapter por CLI

`aegisbench run ... --param clave=valor` (repetible; coerción automática
true/false/int/float) pasa kwargs al constructor del adapter. Genérico para
cualquier adapter; el scoring del benchmark no cambia.
