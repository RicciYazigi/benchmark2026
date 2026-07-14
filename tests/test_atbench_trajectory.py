# -*- coding: utf-8 -*-
"""Pruebas unitarias para el dataset ATBench y sus adaptadores de trayectoria."""

import pathlib
import sys

# Agregar rutas al sys.path
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parents[1] / "adapters_external")
)

from fourr2_singleturn_baseline_adapter import (
    FourR2SingleTurnBaselineAdapter,  # noqa: E402
)
from fourr2_trajectory_adapter import FourR2TrajectoryAdapter  # noqa: E402

from aegisbench.datasets.atbench_loader import load_atbench
from aegisbench.interfaces.v1 import GovernanceDecision


def test_load_atbench():
    samples = load_atbench("data/atbench_test.jsonl")
    assert len(samples) == 1000

    # Validar primera muestra
    s = samples[0]
    assert s.sample_id == "1"
    assert s.dataset_source == "atbench"
    assert s.ground_truth_should_block is True
    assert len(s.turns) > 0

    # Verificar mapeo de roles
    roles = [t.role for t in s.turns]
    assert "user" in roles
    assert "assistant" in roles
    assert "tool" in roles


def test_trajectory_adapter_evaluation():
    samples = load_atbench("data/atbench_test.jsonl")
    subsamples = samples[:5]

    adapter = FourR2TrajectoryAdapter(mode="cca")
    for s in subsamples:
        res = adapter.evaluate(s)
        assert res.sample_id == s.sample_id
        assert res.decision in (GovernanceDecision.ALLOW, GovernanceDecision.BLOCK)
        assert 0.0 <= res.confidence <= 1.0
        assert res.latency_ms > 0.0
        assert "verdict=" in res.raw_output


def test_singleturn_baseline_adapter_evaluation():
    samples = load_atbench("data/atbench_test.jsonl")
    subsamples = samples[:5]

    adapter = FourR2SingleTurnBaselineAdapter(mode="cca")
    for s in subsamples:
        res = adapter.evaluate(s)
        assert res.sample_id == s.sample_id
        assert res.decision in (GovernanceDecision.ALLOW, GovernanceDecision.BLOCK)
        assert 0.0 <= res.confidence <= 1.0
        assert res.latency_ms > 0.0
        assert "verdict=" in res.raw_output
