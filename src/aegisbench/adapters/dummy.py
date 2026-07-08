# -*- coding: utf-8 -*-
"""
Implementación de DummyAdapter para AegisBench.
Este es un adaptador básico, determinista y basado en palabras clave.
IMPORTANTE: Este adaptador sirve únicamente para validar el flujo del pipeline de evaluación
y no debe utilizarse como un sistema de defensa real.
"""

import re
import time
from typing import Optional

from aegisbench.interfaces.v1 import (
    EvalResult,
    GovernanceDecision,
    Sample,
    ScenarioType,
    TargetSystem,
)


class DummyAdapter(TargetSystem):
    """
    Un adaptador determinista e ingenuo basado en expresiones regulares para pruebas.
    """

    name = "dummy"
    version = "1.0.0"

    # Palabras clave sospechosas que causan bloqueo inmediato
    BLOCK_KEYWORDS = [
        r"jailbreak",
        r"bomba",
        r"bomb",
        r"matar",
        r"kill",
        r"destruir",
        r"destroy",
        r"hackear",
        r"hack",
        r"ilegal",
        r"illegal",
        r"armas",
        r"weapons",
    ]

    # Palabras clave que causan escalación a revisión humana
    ESCALATE_KEYWORDS = [
        r"humano",
        r"human",
        r"ayuda",
        r"help",
        r"escalar",
        r"escalate",
        r"soporte",
        r"support",
    ]

    def __init__(
        self,
        block_regexes: Optional[list[str]] = None,
        escalate_regexes: Optional[list[str]] = None,
    ):
        block_list = block_regexes if block_regexes is not None else self.BLOCK_KEYWORDS
        escalate_list = (
            escalate_regexes if escalate_regexes is not None else self.ESCALATE_KEYWORDS
        )

        self.block_pattern = (
            re.compile("|".join(block_list), re.IGNORECASE) if block_list else None
        )
        self.escalate_pattern = (
            re.compile("|".join(escalate_list), re.IGNORECASE)
            if escalate_list
            else None
        )

    def evaluate(self, sample: Sample) -> EvalResult:
        """
        Evalúa el contenido del Sample buscando coincidencia de palabras clave.
        """
        start_time = time.perf_counter()

        # Concatenar todos los turnos para el análisis
        full_text = " ".join([turn.content for turn in sample.turns])

        decision = GovernanceDecision.ALLOW
        confidence = 0.5  # Confianza base por defecto
        raw_output_parts = []

        # Comprobar reglas de bloqueo
        if self.block_pattern and self.block_pattern.search(full_text):
            decision = GovernanceDecision.BLOCK
            confidence = 0.95
            raw_output_parts.append(
                "Filtro de bloqueo activado por coincidencia de regex."
            )

        # Comprobar reglas de escalación (solo si no se bloqueó)
        elif self.escalate_pattern and self.escalate_pattern.search(full_text):
            decision = GovernanceDecision.ESCALATE
            confidence = 0.80
            raw_output_parts.append(
                "Filtro de escalación activado por coincidencia de regex."
            )

        else:
            raw_output_parts.append(
                "No se detectaron palabras clave de riesgo. Decisión: ALLOW."
            )

        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000.0

        return EvalResult(
            sample_id=sample.sample_id,
            decision=decision,
            confidence=confidence,
            latency_ms=latency_ms,
            adapter_name=self.name,
            adapter_version=self.version,
            raw_output=" | ".join(raw_output_parts),
        )

    def supports_scenario(self, scenario_type: ScenarioType) -> bool:
        """
        El DummyAdapter soporta todos los tipos de escenarios definidos en v1.
        """
        return scenario_type in (
            ScenarioType.SINGLE_TURN,
            ScenarioType.AGENTIC_TOOL_USE,
            ScenarioType.OVER_REFUSAL_CONTROL,
        )
