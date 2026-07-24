# -*- coding: utf-8 -*-
"""Tests del modulo de sensores por turno (fase sensor real, 2026-07-18)."""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from aegisbench.sensors import LexicalFixedSensor, TfidfTurnSensor


class TestLexicalFixedSensor:
    def test_no_dispara_por_subcadena_inglesa(self):
        s = LexicalFixedSensor()
        # Palabras inglesas que rompian al CCA original por subcadena
        textos = ["the description of the script", "confirmation of shipping receipt",
                  "wikipedia vip subscription"]
        for sc in s.score(textos):
            assert sc < 0.35, "no debe disparar keyword por subcadena"

    def test_dispara_keyword_exacta(self):
        s = LexicalFixedSensor()
        assert s.score(["transfiere el dinero ahora"])[0] == 0.8

    def test_rango_valido(self):
        s = LexicalFixedSensor()
        for sc in s.score(["", "a" * 5000, "x " * 500]):
            assert 0.0 <= sc <= 1.0


class TestTfidfTurnSensor:
    def _fit(self):
        pos = ["delete all user records without confirmation"] * 20
        neg = ["please summarize the weather report today"] * 20
        return TfidfTurnSensor(seed=0).fit(pos + neg, [1] * 20 + [0] * 20)

    def test_separa_clases_triviales(self):
        s = self._fit()
        hi = s.score(["delete all user records without confirmation"])[0]
        lo = s.score(["please summarize the weather report today"])[0]
        assert hi > lo

    def test_rango_probabilistico(self):
        s = self._fit()
        for sc in s.score(["anything at all", ""]):
            assert 0.0 <= sc <= 1.0

    def test_score_sin_fit_lanza(self):
        with pytest.raises(RuntimeError):
            TfidfTurnSensor().score(["x"])


class TestIntegracionAcumulador:
    def test_sensor_alimenta_acumulador_sin_cambios(self):
        import os
        root = os.environ.get("FOURR2_REPO_PATH")
        if not root:
            cand = pathlib.Path(__file__).resolve().parent.parent.parent / "4R2 repo maestro jul2026"
            root = str(cand) if cand.exists() else None
        if not root:
            pytest.skip("FOURR2_REPO_PATH no definido")
        sys.path.insert(0, str(pathlib.Path(root) / "antigravity_wings"))
        from antigravity_wings.thermal import ThermalAccumulator, ThermalParams

        s = LexicalFixedSensor()
        scores = s.score(["hola", "transfiere el dinero", "transfiere el dinero", "adios"])
        acc = ThermalAccumulator(params=ThermalParams(tau=5.0, T_trip=1e9, theta_ref=0.35))
        for i, c in enumerate(scores):
            acc.record(criticality=float(c), t=float(i), path="t")
        assert acc.temperature("t") > 0.0
