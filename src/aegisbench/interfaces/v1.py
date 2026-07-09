# -*- coding: utf-8 -*-
"""
Módulo de interfaces versión 1 para AegisBench.
Define el contrato de datos y la clase base para los adaptadores.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

AEGISBENCH_INTERFACE_VERSION = "1.0.0"


class ScenarioType(str, Enum):
    """Tipos de escenarios de evaluación soportados por el benchmark.

    RESPONSE_GOVERNANCE representa escenarios donde 'turns' contiene al menos un
    Message(role="user", ...) seguido de un Message(role="assistant", ...),
    metadata['policy'] contiene la política que se debe cumplir, y
    ground_truth_should_block determina si la respuesta del assistant
    viola la política y por ende debe ser bloqueada/marcada.
    """

    SINGLE_TURN = "single_turn"
    AGENTIC_TOOL_USE = "agentic_tool_use"
    OVER_REFUSAL_CONTROL = "over_refusal_control"
    RESPONSE_GOVERNANCE = "response_governance"


class GovernanceDecision(str, Enum):
    """Decisiones de gobernanza devueltas por el sistema bajo prueba."""

    ALLOW = "allow"
    BLOCK = "block"
    ESCALATE = "escalate"  # ej., enrutado a revisión humana


@dataclass(frozen=True)
class Message:
    """Representa un mensaje individual dentro de una conversación."""

    role: str  # "user" | "assistant" | "tool"
    content: str


@dataclass(frozen=True)
class Sample:
    """Representa una muestra de evaluación individual."""

    sample_id: str
    scenario_type: ScenarioType
    turns: list[Message]
    dataset_source: str  # ej. "jailbreakbench", "xstest"
    harm_category: Optional[str]
    ground_truth_should_block: (
        bool  # True = ataque/inseguro, False = benigno/debería-permitirse
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    """Representa el resultado obtenido de evaluar una muestra en un adaptador."""

    sample_id: str
    decision: GovernanceDecision
    confidence: Optional[float]  # 0.0-1.0, None si el adaptador no expone confianza
    latency_ms: float
    adapter_name: str
    adapter_version: str
    raw_output: Optional[str] = (
        None  # opaco, no utilizado en puntuación, solo auditoría/reporte
    )


class TargetSystem:
    """Clase base que todo adaptador de sistema de gobernanza debe implementar."""

    name: str
    version: str

    def evaluate(self, sample: Sample) -> EvalResult:
        """Evalúa una muestra individual y devuelve el resultado de gobernanza."""
        raise NotImplementedError

    def supports_scenario(self, scenario_type: ScenarioType) -> bool:
        """
        Determina si el adaptador soporta un escenario específico.
        Los adaptadores pueden rechazar tipos de escenarios que no soporten; el ejecutor
        debe omitirlos y reportar N/A en lugar de fallar toda la ejecución.
        """
        raise NotImplementedError
