# -*- coding: utf-8 -*-
"""Suite de fusible v0.1: equivalencia numérica con 4r2v6, estadísticos,
calibración, normalizador, fuse end-to-end y flight recorder."""
import os
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))

from fusible import (
    CusumStatistic,
    EwmaStatistic,
    FlightRecorder,
    Fuse,
    I2tStatistic,
    QuantileNormalizer,
    calibrate_threshold,
    make_statistic,
    select_best_statistic,
)


# ---------------------------------------------------------------------------
class TestEquivalenciaNumerica4r2:
    """La reimplementación limpia ES la misma ecuación que el kernel sellado."""

    def _get_legacy(self):
        root = os.environ.get("FOURR2_REPO_PATH")
        if not root:
            cand = pathlib.Path(__file__).resolve().parents[3] / "4R2 repo maestro jul2026"
            root = str(cand) if cand.exists() else None
        if not root:
            pytest.skip("FOURR2_REPO_PATH no definido")
        sys.path.insert(0, str(pathlib.Path(root) / "antigravity_wings"))
        from antigravity_wings.thermal import ThermalAccumulator, ThermalParams

        return ThermalAccumulator, ThermalParams

    def test_equivalencia_200_secuencias(self):
        ThermalAccumulator, ThermalParams = self._get_legacy()
        rng = np.random.default_rng(42)
        for _ in range(200):
            tau = float(rng.uniform(0.5, 20))
            theta = float(rng.uniform(0.1, 0.9))
            trip = float(rng.uniform(0.05, 3.0))
            n = int(rng.integers(3, 30))
            crits = rng.uniform(0, 1, n)
            dts = rng.uniform(0.1, 10, n - 1)

            legacy = ThermalAccumulator(params=ThermalParams(tau=tau, T_trip=trip, theta_ref=theta))
            mine = I2tStatistic(tau=tau, theta=theta, threshold=trip)
            t = 0.0
            for i, c in enumerate(crits):
                if i > 0:
                    t += dts[i - 1]
                req = legacy.record(criticality=float(c), t=t, path="p")
                v = mine.update(float(c), dt=1.0 if i == 0 else float(dts[i - 1]))
                legacy_temp = legacy.log[-1].temperature
                assert abs(v - legacy_temp) < 1e-6, f"divergencia: {v} vs {legacy_temp}"
                legacy_tripped = req is not None
                mine_tripped = v >= mine.threshold
                assert legacy_tripped == mine_tripped
                if mine_tripped:
                    mine.reset()  # legacy resetea internamente al disparar


# ---------------------------------------------------------------------------
class TestEstadisticos:
    def test_i2t_acumula_y_disipa(self):
        st = I2tStatistic(tau=5.0, theta=0.5, threshold=1e9)
        v1 = st.update(0.9)          # energía 0.16
        v2 = st.update(0.9)          # decae y suma
        assert v2 > v1 > 0
        for _ in range(50):
            v = st.update(0.0)       # sin energía: solo decae
        assert v < 0.01

    def test_cusum_deriva_negativa_en_benignos(self):
        st = CusumStatistic(k_ref=0.75, threshold=1e9)
        for _ in range(100):
            st.update(0.5)           # benigno típico normalizado
        assert st.value == 0.0       # nunca acumula bajo k_ref

    def test_cusum_acumula_riesgo_sostenido(self):
        st = CusumStatistic(k_ref=0.75, threshold=1e9)
        for _ in range(10):
            st.update(0.95)
        assert abs(st.value - 10 * 0.2) < 1e-9

    def test_ewma_primer_valor(self):
        st = EwmaStatistic(alpha=0.3)
        assert st.update(0.8) == 0.8

    def test_factory(self):
        for name in ("i2t", "cusum", "ewma"):
            assert make_statistic(name).name == name
        with pytest.raises(ValueError):
            make_statistic("inexistente")


# ---------------------------------------------------------------------------
class TestNormalizadorYCalibracion:
    def test_benignos_quedan_uniformes(self):
        rng = np.random.default_rng(0)
        ref = rng.normal(0.9, 0.02, 5000)  # sensor comprimido estilo qwen
        qn = QuantileNormalizer().fit(ref)
        normed = qn.transform(rng.normal(0.9, 0.02, 2000))
        # p90 de benignos normalizados debe estar cerca de 0.9 POR CONSTRUCCIÓN
        assert abs(np.percentile(normed, 90) - 0.9) < 0.05

    def test_binario_sin_sesgo(self):
        qn = QuantileNormalizer().fit([0.0] * 88 + [1.0] * 12)  # guard con 12% FP
        z, o = qn.transform([0.0])[0], qn.transform([1.0])[0]
        assert 0.3 < z < 0.6 and 0.85 < o <= 1.0  # rango medio, no saturado

    def test_monotonia(self):
        qn = QuantileNormalizer().fit(np.random.default_rng(1).uniform(0, 1, 1000))
        a, b = qn.transform([0.2, 0.7])
        assert a < b

    def test_calibrate_threshold_fpr(self):
        rng = np.random.default_rng(2)
        benign = [list(rng.uniform(0, 0.85, 10)) for _ in range(200)]
        h = calibrate_threshold(benign, "i2t", target_fpr=0.05, tau=5.0, theta=0.9)
        from fusible import peak_statistic

        fpr = np.mean([peak_statistic(tr, "i2t", tau=5.0, theta=0.9) >= h for tr in benign])
        assert fpr <= 0.06

    def test_select_best_statistic(self):
        rng = np.random.default_rng(3)
        benign = [list(rng.uniform(0, 0.8, 12)) for _ in range(100)]
        unsafe = [list(np.clip(rng.uniform(0.8, 1.0, 12), 0, 1)) for _ in range(100)]
        res = select_best_statistic(benign, unsafe)
        assert res["best"] in ("i2t", "cusum", "ewma")
        assert all(v > 0.9 for v in res["auroc"].values())  # caso separable: todos altos


# ---------------------------------------------------------------------------
class TestFuseEndToEnd:
    def test_trayectoria_benigna_no_dispara(self):
        qn = QuantileNormalizer().fit(np.random.default_rng(4).uniform(0, 1, 1000))
        fuse = Fuse(statistic="cusum", normalizer=qn, threshold=2.0, k_ref=0.75)
        trips = [fuse.observe(0.3, t=float(k), path="a") for k in range(20)]
        assert all(t is None for t in trips)

    def test_deriva_sostenida_dispara_y_reporta_turno(self):
        qn = QuantileNormalizer().fit(np.random.default_rng(5).uniform(0, 1, 1000))
        fuse = Fuse(statistic="cusum", normalizer=qn, threshold=1.5, k_ref=0.75)
        trip_turn = None
        for k in range(30):
            trip = fuse.observe(0.97, t=float(k), path="b")
            if trip is not None:
                trip_turn = trip.turn_index
                break
        assert trip_turn is not None and trip_turn < 15
        assert len(trip.evidence_window) > 0

    def test_multi_path_aislado(self):
        fuse = Fuse(statistic="i2t", threshold=1e9, tau=5.0, theta=0.3)
        fuse.observe(0.9, t=0.0, path="x")
        assert fuse.value("x") > 0 and fuse.value("y") == 0.0

    def test_timestamp_no_monotono_lanza(self):
        fuse = Fuse(statistic="ewma")
        fuse.observe(0.1, t=5.0, path="z")
        with pytest.raises(ValueError):
            fuse.observe(0.1, t=1.0, path="z")


# ---------------------------------------------------------------------------
class TestFlightRecorder:
    def test_export_sellado_y_resumen(self):
        fuse = Fuse(statistic="cusum", threshold=0.5, k_ref=0.2)
        for k in range(5):
            fuse.observe(0.9, t=float(k), path="agente-1")
        payload = fuse.recorder.export()
        assert payload["n_trips"] >= 1 and len(payload["sha256"]) == 64
        summ = fuse.recorder.summary()
        assert summ["agentes_monitoreados"] == 1
        assert summ["disparos"][0]["estadistico"] == "cusum"


# ---------------------------------------------------------------------------
class TestKalmanSlope:
    def test_deriva_ascendente_da_pendiente_positiva(self):
        from fusible.statistics import KalmanSlopeStatistic
        import numpy as np
        rng = np.random.default_rng(6)
        st = KalmanSlopeStatistic(threshold=1e9)
        vals_rampa = [st.update(0.2 + 0.03 * k + rng.normal(0, 0.02)) for k in range(20)]
        st.reset()
        vals_plano = [st.update(0.5 + rng.normal(0, 0.02)) for _ in range(20)]
        assert max(vals_rampa[5:]) > max(vals_plano[5:]) * 2

    def test_deriva_descendente_no_dispara(self):
        from fusible.statistics import KalmanSlopeStatistic
        st = KalmanSlopeStatistic(threshold=1e9)
        vals = [st.update(0.9 - 0.04 * k) for k in range(15)]
        assert max(vals[5:]) == 0.0  # pendiente negativa -> clip a 0

    def test_en_factory(self):
        from fusible.statistics import make_statistic
        assert make_statistic("kalman_slope").name == "kalman_slope"


# ---------------------------------------------------------------------------
class TestRobustReference:
    def test_sensor_degenerado_llamaguard(self):
        """Reproduce el caso sellado 20260720: 78% de benignos en el nivel alto."""
        from fusible import robust_reference
        cal = [0.6078] * 784 + [0.1078] * 216   # distribucion real llama-guard normalizada
        theta = robust_reference(cal, 90)
        assert theta < 0.6078                    # ya no cae sobre el nivel de flag
        assert abs(theta - (0.6078 + 0.1078) / 2) < 1e-9
        # energia por flag vuelve a ser > 0:
        assert (0.6078 - theta) ** 2 > 0

    def test_sensor_sano_identico_al_percentil(self):
        from fusible import robust_reference
        import numpy as np
        cal = list(np.random.default_rng(7).uniform(0, 1, 5000))
        assert abs(robust_reference(cal, 90) - float(np.percentile(cal, 90))) < 1e-12
