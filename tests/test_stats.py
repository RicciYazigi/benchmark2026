# -*- coding: utf-8 -*-
import pytest

from aegisbench.interfaces.v1 import (
    EvalResult,
    GovernanceDecision,
    Message,
    Sample,
    ScenarioType,
)
from aegisbench.stats.bootstrap import (
    calculate_advanced_metrics,
    calculate_bootstrap_ci,
    calculate_rates,
)


@pytest.fixture
def base_data():
    samples = [
        Sample(
            sample_id="s1",
            scenario_type=ScenarioType.SINGLE_TURN,
            turns=[Message(role="user", content="atk")],
            dataset_source="test",
            harm_category="harm",
            ground_truth_should_block=True,
        ),
        Sample(
            sample_id="s2",
            scenario_type=ScenarioType.SINGLE_TURN,
            turns=[Message(role="user", content="atk")],
            dataset_source="test",
            harm_category="harm",
            ground_truth_should_block=True,
        ),
        Sample(
            sample_id="s3",
            scenario_type=ScenarioType.SINGLE_TURN,
            turns=[Message(role="user", content="ok")],
            dataset_source="test",
            harm_category=None,
            ground_truth_should_block=False,
        ),
        Sample(
            sample_id="s4",
            scenario_type=ScenarioType.SINGLE_TURN,
            turns=[Message(role="user", content="ok")],
            dataset_source="test",
            harm_category=None,
            ground_truth_should_block=False,
        ),
    ]

    results = [
        EvalResult(
            sample_id="s1",
            decision=GovernanceDecision.BLOCK,
            confidence=0.9,
            latency_ms=10.0,
            adapter_name="test",
            adapter_version="1.0",
        ),
        EvalResult(
            sample_id="s2",
            decision=GovernanceDecision.ALLOW,
            confidence=0.8,
            latency_ms=12.0,
            adapter_name="test",
            adapter_version="1.0",
        ),
        EvalResult(
            sample_id="s3",
            decision=GovernanceDecision.ALLOW,
            confidence=0.95,
            latency_ms=8.0,
            adapter_name="test",
            adapter_version="1.0",
        ),
        EvalResult(
            sample_id="s4",
            decision=GovernanceDecision.ESCALATE,
            confidence=0.7,
            latency_ms=15.0,
            adapter_name="test",
            adapter_version="1.0",
        ),
    ]
    return samples, results


def test_calculate_rates(base_data):
    samples, results = base_data
    rates = calculate_rates(samples, results)

    # s1 es blocked (correcto), s2 es allowed (ataque exitoso). ASR = 1/2 = 0.5
    assert rates["asr"] == 0.5

    # s3 es allowed (correcto), s4 es escalated (rechazo benigno). ORR = 1/2 = 0.5
    assert rates["orr"] == 0.5

    # s4 es escalated. Escalation rate = 1/4 = 0.25
    assert rates["escalation_rate"] == 0.25


def test_bootstrap_ci_determinism(base_data):
    samples, results = base_data

    # Probar que las llamadas con la misma semilla son deterministicas
    ci_1 = calculate_bootstrap_ci(samples, results, n_resamples=100, seed=42)
    ci_2 = calculate_bootstrap_ci(samples, results, n_resamples=100, seed=42)

    assert ci_1["asr"] == ci_2["asr"]
    assert ci_1["orr"] == ci_2["orr"]
    assert ci_1["escalation_rate"] == ci_2["escalation_rate"]


def test_advanced_metrics_with_confidence(base_data):
    samples, results = base_data
    metrics = calculate_advanced_metrics(samples, results)

    assert isinstance(metrics["auroc"], float)
    assert isinstance(metrics["auprc"], float)
    assert (
        metrics["precision"] == 0.5
    )  # tp=1 (s1), fp=1 (s4), fp=1 significa should_block=False pred=1
    assert metrics["recall"] == 0.5  # tp=1 (s1), fn=1 (s2)
    assert isinstance(metrics["f1"], float)


def test_advanced_metrics_missing_confidence(base_data):
    samples, results = base_data

    # Alterar un resultado para que no tenga confidence
    results_modified = list(results)
    results_modified[0] = EvalResult(
        sample_id="s1",
        decision=GovernanceDecision.BLOCK,
        confidence=None,  # Falta confianza
        latency_ms=10.0,
        adapter_name="test",
        adapter_version="1.0",
    )

    metrics = calculate_advanced_metrics(samples, results_modified)

    assert "N/A" in metrics["auroc"]
    assert "N/A" in metrics["auprc"]
    assert "N/A" in metrics["precision"]
