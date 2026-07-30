# -*- coding: utf-8 -*-
"""Cobertura de src/aegisbench/sensors: normalizador por cuantiles y adaptador
guard HTTP (mockeado, sin red). Cierra el hueco que dejaba el CI bajo el 85%:
`normalize.py` se probaba solo desde fusible/tests, y el adaptador HTTP no
tenia pruebas por depender de un servidor ollama local.
"""

import json
from unittest import mock

import numpy as np
import pytest

from aegisbench.sensors import GuardModelHTTPSensor, LexicalFixedSensor
from aegisbench.sensors.normalize import QuantileNormalizer


class TestQuantileNormalizer:
    def test_fit_transform_uniformiza_benignos(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0.9, 0.02, 4000)  # sensor comprimido (caso qwen)
        normed = QuantileNormalizer().fit_transform(ref)
        assert abs(float(np.percentile(normed, 90)) - 0.9) < 0.05
        assert 0.0 <= min(normed) and max(normed) <= 1.0

    def test_binario_usa_rango_medio(self):
        # caso llama-guard: 79% de flags en benignos -> sin rango medio, satura
        qn = QuantileNormalizer().fit([1.0] * 79 + [0.0] * 21)
        bajo, alto = qn.transform([0.0]), qn.transform([1.0])
        assert 0.0 < bajo[0] < alto[0] <= 1.0

    def test_transform_one_equivale_a_transform(self):
        qn = QuantileNormalizer().fit(np.linspace(0, 1, 500))
        assert qn.transform_one(0.42) == qn.transform([0.42])[0]

    def test_monotonia_preservada(self):
        qn = QuantileNormalizer().fit(np.random.default_rng(1).uniform(0, 1, 800))
        a, b, c = qn.transform([0.1, 0.5, 0.9])
        assert a < b < c

    def test_referencia_vacia_lanza(self):
        with pytest.raises(ValueError):
            QuantileNormalizer().fit([])

    def test_transform_sin_fit_lanza(self):
        with pytest.raises(RuntimeError):
            QuantileNormalizer().transform([0.5])


class TestLexicalFixedSensor:
    def test_fit_es_noop_y_devuelve_self(self):
        s = LexicalFixedSensor()
        assert s.fit(["x"], [0]) is s


def _fake_response(payload: str):
    """Contexto que imita urlopen() devolviendo el JSON de ollama."""
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps({"response": payload}).encode()
    ctx = mock.MagicMock()
    ctx.__enter__.return_value = resp
    return ctx


class TestGuardModelHTTPSensor:
    def test_llama_guard_binario(self):
        s = GuardModelHTTPSensor(model="llama-guard3:1b")
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response("unsafe\nS2")
        ):
            assert s.score(["transferir fondos sin permiso"]) == [1.0]
        s2 = GuardModelHTTPSensor(model="llama-guard3:1b")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response("safe")):
            assert s2.score(["el clima de hoy"]) == [0.0]

    def test_modelo_instruible_parsea_numero(self):
        s = GuardModelHTTPSensor(model="qwen2.5:3b")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response("0.73")):
            assert s.score(["texto"]) == [0.73]

    def test_respuesta_no_numerica_cae_a_neutro(self):
        s = GuardModelHTTPSensor(model="qwen2.5:3b")
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response("no lo se")
        ):
            assert s.score(["texto"]) == [0.5]

    def test_score_fuera_de_rango_se_acota(self):
        s = GuardModelHTTPSensor(model="qwen2.5:3b")
        with mock.patch("urllib.request.urlopen", return_value=_fake_response("7")):
            assert s.score(["texto"]) == [1.0]

    def test_cache_evita_segunda_llamada_y_persiste(self, tmp_path):
        cache = tmp_path / "guard_cache.json"
        s = GuardModelHTTPSensor(model="qwen2.5:3b", cache_path=str(cache))
        with mock.patch(
            "urllib.request.urlopen", return_value=_fake_response("0.42")
        ) as m:
            s.score(["mismo texto"])
            s.score(["mismo texto"])  # segunda vez: sale del cache
            assert m.call_count == 1
        assert cache.exists() and len(json.loads(cache.read_text())) == 1
        # una instancia nueva reutiliza el cache en disco, sin red
        s2 = GuardModelHTTPSensor(model="qwen2.5:3b", cache_path=str(cache))
        assert s2.score(["mismo texto"]) == [0.42]

    def test_cache_corrupto_no_rompe(self, tmp_path):
        cache = tmp_path / "corrupto.json"
        cache.write_text("{ esto no es json", encoding="utf-8")
        s = GuardModelHTTPSensor(model="qwen2.5:3b", cache_path=str(cache))
        with mock.patch("urllib.request.urlopen", return_value=_fake_response("0.1")):
            assert s.score(["t"]) == [0.1]

    def test_fit_es_zero_shot(self):
        s = GuardModelHTTPSensor()
        assert s.fit(["x"], [1]) is s
