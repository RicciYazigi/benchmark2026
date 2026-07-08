# -*- coding: utf-8 -*-
import pytest

from aegisbench.attacks.transforms import (
    Base64Transform,
    LeetspeakTransform,
    RoleplayTransform,
    TranslationTransform,
    apply_transform,
)
from aegisbench.interfaces.v1 import Message, Sample, ScenarioType


@pytest.fixture
def base_sample():
    return Sample(
        sample_id="test_s",
        scenario_type=ScenarioType.SINGLE_TURN,
        turns=[Message(role="user", content="Hola amigo")],
        dataset_source="test",
        harm_category="benign",
        ground_truth_should_block=False,
    )


def test_base64_transform(base_sample):
    transformer = Base64Transform()
    transformed = transformer.transform(base_sample)
    assert transformed.sample_id == "test_s-base64"
    assert "Base64" in transformed.turns[0].content
    assert transformed.metadata["transform"] == "base64"
    assert transformed.metadata["original_content"] == "Hola amigo"


def test_leetspeak_transform(base_sample):
    transformer = LeetspeakTransform()
    transformed = transformer.transform(base_sample)
    assert transformed.sample_id == "test_s-leetspeak"
    # 'Hola amigo' -> 'H0l4 4m190'
    assert transformed.turns[0].content == "H0l4 4m190"
    assert transformed.metadata["transform"] == "leetspeak"


def test_roleplay_transform(base_sample):
    transformer = RoleplayTransform()
    transformed = transformer.transform(base_sample)
    assert transformed.sample_id == "test_s-roleplay"
    assert "fines dramáticos" in transformed.turns[0].content
    assert "Hola amigo" in transformed.turns[0].content


def test_translation_transform(base_sample):
    transformer = TranslationTransform()
    transformed = transformer.transform(base_sample)
    assert transformed.sample_id == "test_s-translation_rot13"
    assert "ROT13" in transformed.turns[0].content
    # 'Hola amigo' en ROT13 es 'Ubyn nzvtb'
    assert transformer._rot13("Hola amigo") == "Ubyn nzvtb"


def test_apply_transform_success(base_sample):
    t1 = apply_transform("base64", base_sample)
    assert t1.metadata["transform"] == "base64"


def test_apply_transform_invalid(base_sample):
    with pytest.raises(ValueError):
        apply_transform("invalid_transform_name", base_sample)
