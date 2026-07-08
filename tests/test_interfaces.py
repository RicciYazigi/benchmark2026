# -*- coding: utf-8 -*-
import pytest

from aegisbench.interfaces.v1 import (
    Message,
    Sample,
    ScenarioType,
    TargetSystem,
)


def test_message_creation():
    msg = Message(role="user", content="Hola")
    assert msg.role == "user"
    assert msg.content == "Hola"


def test_sample_creation():
    msg = Message(role="user", content="Hola")
    sample = Sample(
        sample_id="test_1",
        scenario_type=ScenarioType.SINGLE_TURN,
        turns=[msg],
        dataset_source="test_dataset",
        harm_category="benign",
        ground_truth_should_block=False,
    )
    assert sample.sample_id == "test_1"
    assert sample.scenario_type == ScenarioType.SINGLE_TURN
    assert len(sample.turns) == 1
    assert sample.ground_truth_should_block is False


def test_target_system_not_implemented():
    class TestSystem(TargetSystem):
        name = "test"
        version = "1.0.0"

    system = TestSystem()
    sample = Sample(
        sample_id="test_1",
        scenario_type=ScenarioType.SINGLE_TURN,
        turns=[],
        dataset_source="test_dataset",
        harm_category=None,
        ground_truth_should_block=False,
    )
    with pytest.raises(NotImplementedError):
        system.evaluate(sample)

    with pytest.raises(NotImplementedError):
        system.supports_scenario(ScenarioType.SINGLE_TURN)
