# -*- coding: utf-8 -*-
"""Loader para el dataset ATBench.

Mapea las trayectorias de conversación multi-turno al formato de Sample de AegisBench.
"""

import json
from typing import List

from aegisbench.interfaces.v1 import Message, Sample, ScenarioType


def load_atbench(path: str = "data/atbench_test.jsonl") -> List[Sample]:
    """Carga el dataset ATBench desde un archivo JSONL y lo mapea a objetos Sample.

    Args:
        path: Ruta al archivo jsonl del dataset ATBench.

    Returns:
        List[Sample]: Lista de muestras mapeadas.
    """
    samples = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)

            # contents contiene una lista que tiene la trayectoria en su primer elemento
            raw_turns = row["contents"][0]

            turns = []
            for msg in raw_turns:
                role = msg.get("role")
                content = msg.get("content", "")

                if role == "user":
                    mapped_role = "user"
                elif role == "agent":
                    mapped_role = "assistant"
                    # Combinar pensamiento y acción si existen
                    thought = msg.get("thought", "")
                    action = msg.get("action", "")
                    parts = []
                    if thought:
                        parts.append(f"[THOUGHT] {thought}")
                    if action:
                        parts.append(f"[ACTION] {action}")
                    if not parts and content:
                        parts.append(content)
                    content = "\n".join(parts)
                elif role == "environment":
                    mapped_role = "tool"
                    content = msg.get("content", "")
                else:
                    mapped_role = str(role)

                turns.append(Message(role=mapped_role, content=content))

            samples.append(
                Sample(
                    sample_id=str(row["id"]),
                    scenario_type=ScenarioType.AGENTIC_TOOL_USE,
                    turns=turns,
                    dataset_source="atbench",
                    harm_category=row.get("risk_source"),
                    ground_truth_should_block=bool(row["label"]),
                    metadata={
                        "risk_source": row.get("risk_source"),
                        "failure_mode": row.get("failure_mode"),
                        "real_world_harm": row.get("real_world_harm"),
                        "reason": row.get("reason"),
                        "tool_used": row.get("tool_used"),
                    },
                )
            )
    return samples
