# -*- coding: utf-8 -*-
import os
import tempfile

import pytest
from click.testing import CliRunner

from aegisbench.cli.main import main


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_list_datasets(runner):
    result = runner.invoke(main, ["list-datasets"])
    assert result.exit_code == 0
    assert "xstest" in result.output
    assert "jailbreakbench" in result.output


def test_cli_list_attacks(runner):
    result = runner.invoke(main, ["list-attacks"])
    assert result.exit_code == 0
    assert "base64" in result.output
    assert "leetspeak" in result.output


def test_cli_validate_adapter_success(runner):
    result = runner.invoke(main, ["validate-adapter", "--adapter", "dummy"])
    assert result.exit_code == 0
    assert "cumple con la interfaz v1" in result.output


def test_cli_validate_adapter_failure(runner):
    result = runner.invoke(main, ["validate-adapter", "--adapter", "non_existent"])
    assert result.exit_code != 0


def test_cli_doctor(runner):
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "Diagnóstico AegisBench" in result.output


def test_cli_run_success(runner):
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            main,
            [
                "run",
                "--adapter",
                "dummy",
                "--dataset",
                "xstest",
                "--n",
                "3",
                "--output",
                tmpdir,
            ],
        )
        assert result.exit_code == 0
        assert "ASR:" in result.output
        assert "ORR:" in result.output

        # Verificar archivos generados
        assert os.path.exists(os.path.join(tmpdir, "report.json"))
        assert os.path.exists(os.path.join(tmpdir, "report.csv"))
        assert os.path.exists(os.path.join(tmpdir, "report.md"))
        assert os.path.exists(os.path.join(tmpdir, "report.html"))


def test_cli_report(runner):
    import json

    report_data = {
        "summary": {
            "adapter_name": "dummy",
            "adapter_version": "1.0.0",
            "seed": 42,
            "total_samples": 4,
            "evaluated_samples": 4,
            "mean_latency_ms": 0.05,
        },
        "metrics": {
            "rates": {"asr": 0.0, "orr": 0.5, "escalation_rate": 0.25},
            "confidence_intervals_95": {
                "asr": {"lower": 0.0, "upper": 0.0},
                "orr": {"lower": 0.0, "upper": 1.0},
                "escalation_rate": {"lower": 0.0, "upper": 0.75},
            },
            "advanced": {"auroc": "N/A - adapter does not expose confidence"},
        },
        "samples": [
            {
                "sample_id": "xs-1",
                "dataset_source": "xstest",
                "decision": "allow",
                "confidence": 0.5,
                "latency_ms": 0.02,
                "ground_truth_should_block": False,
            }
        ],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        input_json = os.path.join(tmpdir, "input.json")
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f)

        # Probar re-renderizado a HTML
        output_html = os.path.join(tmpdir, "out.html")
        result = runner.invoke(
            main,
            [
                "report",
                "--input",
                input_json,
                "--format",
                "html",
                "--output",
                output_html,
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists(output_html)

        # Probar re-renderizado a CSV
        output_csv = os.path.join(tmpdir, "out.csv")
        result = runner.invoke(
            main,
            [
                "report",
                "--input",
                input_json,
                "--format",
                "csv",
                "--output",
                output_csv,
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists(output_csv)


def test_cli_synthetic_fallback_report(runner, monkeypatch):
    import json

    from aegisbench.datasets import loaders

    # Mock download_file to always raise an exception
    def mock_download_file(*args, **kwargs):
        raise ValueError("Simulated download failure")

    monkeypatch.setattr(loaders, "download_file", mock_download_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            main,
            [
                "run",
                "--adapter",
                "dummy",
                "--dataset",
                "xstest",
                "--n",
                "2",
                "--output",
                tmpdir,
            ],
        )
        assert result.exit_code == 0

        # Verify CLI output has red warning
        assert "ADVERTENCIA:" in result.output

        # Verify files generated
        report_json_path = os.path.join(tmpdir, "report.json")
        assert os.path.exists(report_json_path)
        with open(report_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["summary"]["synthetic_fallback"] is True
        assert data["summary"]["synthetic_fallback_samples"] > 0
        assert "synthetic_fallback_warning" in data["summary"]

        # Verify that sample rows have synthetic_fallback == True
        samples = data.get("samples", [])
        assert len(samples) > 0
        for sample in samples:
            assert sample["synthetic_fallback"] is True
