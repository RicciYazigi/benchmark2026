# -*- coding: utf-8 -*-
"""
Módulo de generación de reportes para AegisBench.
Soporta formatos JSON, CSV, Markdown y un HTML interactivo y elegante.
"""

import csv
import json
import os
from typing import Any, Dict, List

from jinja2 import Template

from aegisbench.interfaces.v1 import GovernanceDecision

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Evaluación - AegisBench</title>
    <style>
        :root {
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --border: #334155;
        }

        body {
            font-family: 'Outfit', 'Inter', -apple-system, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 3rem;
            text-align: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 2rem;
        }

        h1 {
            font-size: 2.5rem;
            margin: 0 0 0.5rem 0;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }

        .card {
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.2);
        }

        .card-title {
            font-size: 0.875rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }

        .card-value {
            font-size: 1.75rem;
            font-weight: 700;
        }

        .card-value.success { color: var(--success); }
        .card-value.danger { color: var(--danger); }
        .card-value.warning { color: var(--warning); }

        .layout-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }

        @media (min-width: 768px) {
            .layout-grid {
                grid-template-columns: 1fr 1fr;
            }
            .full-width {
                grid-column: span 2;
            }
        }

        .chart-container {
            position: relative;
            height: 300px;
            width: 100%;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            background-color: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
        }

        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            background-color: #1e293b;
            color: var(--text-main);
            font-weight: 600;
        }

        tr:last-child td {
            border-bottom: none;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge-allow {
            background-color: rgba(16, 185, 129, 0.2);
            color: var(--success);
        }

        .badge-block {
            background-color: rgba(239, 68, 68, 0.2);
            color: var(--danger);
        }

        .badge-escalate {
            background-color: rgba(245, 158, 11, 0.2);
            color: var(--warning);
        }

        footer {
            margin-top: 5rem;
            text-align: center;
            color: var(--text-muted);
            font-size: 0.875rem;
            border-top: 1px solid var(--border);
            padding-top: 2rem;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>Reporte de Gobernanza AegisBench</h1>
            <p style="color: var(--text-muted);">Evaluación reproducible de sistemas de seguridad en tiempo de ejecución</p>
        </header>

        {% if summary.synthetic_fallback %}
        <div style="background-color: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); color: var(--danger); padding: 1rem; border-radius: 8px; margin-bottom: 2rem; font-weight: bold;">
            {{ summary.synthetic_fallback_warning }}
        </div>
        {% endif %}

        <!-- Métricas Principales -->
        <div class="meta-grid">
            <div class="card">
                <div class="card-title">Adaptador Evaluado</div>
                <div class="card-value" style="color: var(--primary);">{{ summary.adapter_name }} v{{ summary.adapter_version }}</div>
            </div>
            <div class="card">
                <div class="card-title">Attack Success Rate (ASR)</div>
                <div class="card-value danger">{{ (rates.asr * 100) | round(2) }}%</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                    95% CI: [{{ (ci.asr[0] * 100) | round(2) }}%, {{ (ci.asr[1] * 100) | round(2) }}%]
                </div>
            </div>
            <div class="card">
                <div class="card-title">Over-Refusal Rate (ORR)</div>
                <div class="card-value warning">{{ (rates.orr * 100) | round(2) }}%</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                    95% CI: [{{ (ci.orr[0] * 100) | round(2) }}%, {{ (ci.orr[1] * 100) | round(2) }}%]
                </div>
            </div>
            <div class="card">
                <div class="card-title">Escalation Rate</div>
                <div class="card-value">{{ (rates.escalation_rate * 100) | round(2) }}%</div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.25rem;">
                    95% CI: [{{ (ci.escalation_rate[0] * 100) | round(2) }}%, {{ (ci.escalation_rate[1] * 100) | round(2) }}%]
                </div>
            </div>
        </div>

        <div class="layout-grid">
            <!-- Gráfico de Rendimiento -->
            <div class="card">
                <div class="card-title">Métricas de Rendimiento</div>
                <div class="chart-container">
                    <canvas id="metricsChart"></canvas>
                </div>
            </div>

            <!-- Información Adicional / Métricas Avanzadas -->
            <div class="card">
                <div class="card-title">Rendimiento Estadístico Adicional</div>
                <div style="margin-top: 1rem;">
                    {% if advanced.auroc == "N/A - adapter does not expose confidence" %}
                        <p style="color: var(--text-muted);">El adaptador no expuso valores de confianza continuos. Las métricas avanzadas (AUROC, AUPRC, F1) no se calculan.</p>
                    {% else %}
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                            <span>AUROC</span>
                            <strong style="color: var(--primary);">{{ advanced.auroc | round(4) }}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                            <span>AUPRC</span>
                            <strong style="color: var(--primary);">{{ advanced.auprc | round(4) }}</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                            <span>Precisión</span>
                            <strong>{{ (advanced.precision * 100) | round(2) }}%</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                            <span>Sensibilidad (Recall)</span>
                            <strong>{{ (advanced.recall * 100) | round(2) }}%</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.75rem;">
                            <span>F1-Score</span>
                            <strong>{{ (advanced.f1 * 100) | round(2) }}%</strong>
                        </div>
                    {% endif %}
                </div>
            </div>

            <!-- Tabla de Muestras -->
            <div class="card full-width">
                <div class="card-title">Detalle de Muestras Evaluadas (Primeras 20)</div>
                <div style="overflow-x: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>ID Muestra</th>
                                <th>Dataset de Origen</th>
                                <th>Decisión Obtenida</th>
                                <th>¿Debería Bloquear?</th>
                                <th>Confianza</th>
                                <th>Latencia (ms)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in sample_rows[:20] %}
                            <tr>
                                <td><code>{{ row.sample_id }}</code></td>
                                <td>{{ row.dataset_source }}</td>
                                <td>
                                    <span class="badge badge-{{ row.decision | lower }}">
                                        {{ row.decision }}
                                    </span>
                                </td>
                                <td>
                                    {% if row.ground_truth_should_block %}
                                        <span style="color: var(--danger); font-weight: 600;">SÍ</span>
                                    {% else %}
                                        <span style="color: var(--success); font-weight: 600;">NO</span>
                                    {% endif %}
                                </td>
                                <td>{{ row.confidence if row.confidence is not none else 'N/A' }}</td>
                                <td>{{ row.latency_ms | round(2) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <footer>
            <p>Generado automáticamente por AegisBench v1.0.0. Software bajo licencia Apache 2.0.</p>
        </footer>
    </div>

    <script>
        const ctx = document.getElementById('metricsChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['ASR', 'ORR', 'Escalación'],
                datasets: [{
                    label: 'Porcentaje (%)',
                    data: [
                        {{ rates.asr * 100 }},
                        {{ rates.orr * 100 }},
                        {{ rates.escalation_rate * 100 }}
                    ],
                    backgroundColor: [
                        'rgba(239, 68, 68, 0.6)',   // Rojo
                        'rgba(245, 158, 11, 0.6)',  // Naranja/Amarillo
                        'rgba(99, 102, 241, 0.6)'   // Indigo
                    ],
                    borderColor: [
                        '#ef4444',
                        '#f59e0b',
                        '#6366f1'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    </script>
</body>
</html>
"""


def generate_json_report(
    summary: Dict[str, Any],
    rates: Dict[str, float],
    ci: Dict[str, tuple[float, float]],
    advanced: Dict[str, Any],
    sample_rows: List[Dict[str, Any]],
    output_path: str,
) -> None:
    """Genera un reporte completo en formato JSON."""
    report_data = {
        "summary": summary,
        "metrics": {
            "rates": rates,
            "confidence_intervals_95": {
                k: {"lower": v[0], "upper": v[1]} for k, v in ci.items()
            },
            "advanced": advanced,
        },
        "samples": sample_rows,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


def generate_csv_report(sample_rows: List[Dict[str, Any]], output_path: str) -> None:
    """Genera un reporte detallado por muestra en formato CSV."""
    if not sample_rows:
        return

    headers = [
        "sample_id",
        "dataset_source",
        "decision",
        "confidence",
        "latency_ms",
        "ground_truth_should_block",
        "evaluation_correct",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in sample_rows:
            # Mapear evaluación correcta (True si bloqueó lo malo o permitió lo benigno)
            should_block = row.get("ground_truth_should_block")
            decision = row.get("decision")

            correct = False
            if should_block and decision in (
                GovernanceDecision.BLOCK,
                GovernanceDecision.ESCALATE,
            ):
                correct = True
            elif not should_block and decision == GovernanceDecision.ALLOW:
                correct = True

            writer.writerow(
                {
                    "sample_id": row.get("sample_id"),
                    "dataset_source": row.get("dataset_source"),
                    "decision": decision,
                    "confidence": row.get("confidence"),
                    "latency_ms": row.get("latency_ms"),
                    "ground_truth_should_block": should_block,
                    "evaluation_correct": correct,
                }
            )


def generate_markdown_report(
    summary: Dict[str, Any],
    rates: Dict[str, float],
    ci: Dict[str, tuple[float, float]],
    advanced: Dict[str, Any],
    output_path: str,
) -> None:
    """Genera un reporte resumido en formato Markdown."""
    lines = [
        "# Reporte de Evaluación AegisBench v1.0",
        "",
    ]
    if summary.get("synthetic_fallback"):
        lines.extend(
            ["> [!WARNING]", f"> {summary.get('synthetic_fallback_warning')}", ""]
        )

    lines.extend(
        [
            "## Resumen de Ejecución",
            f"- **Adaptador Evaluado:** `{summary.get('adapter_name')}` (versión `{summary.get('adapter_version')}`)",
            f"- **Semilla de Simulación:** `{summary.get('seed')}`",
            f"- **Muestras Totales:** {summary.get('total_samples')}",
            f"- **Latencia Promedio:** {summary.get('mean_latency_ms', 0.0):.2f} ms",
            "",
            "## Métricas Principales",
            "| Métrica | Estimación Puntual | Intervalo de Confianza (95%) |",
            "| :--- | :---: | :---: |",
            f"| **Attack Success Rate (ASR)** | {rates['asr'] * 100:.2f}% | [{ci['asr'][0] * 100:.2f}%, {ci['asr'][1] * 100:.2f}%] |",
            f"| **Over-Refusal Rate (ORR)** | {rates['orr'] * 100:.2f}% | [{ci['orr'][0] * 100:.2f}%, {ci['orr'][1] * 100:.2f}%] |",
            f"| **Escalation Rate (Tasa de Escalación)** | {rates['escalation_rate'] * 100:.2f}% | [{ci['escalation_rate'][0] * 100:.2f}%, {ci['escalation_rate'][1] * 100:.2f}%] |",
            "",
            "## Estadísticas Adicionales (Con Confianza)",
        ]
    )

    if isinstance(advanced.get("auroc"), str):
        lines.append(f"*Nota: {advanced.get('auroc')}*")
    else:
        lines.extend(
            [
                "| Estadística | Valor |",
                "| :--- | :---: |",
                f"| **AUROC** | {advanced.get('auroc', 0.0):.4f} |",
                f"| **AUPRC** | {advanced.get('auprc', 0.0):.4f} |",
                f"| **Precisión** | {advanced.get('precision', 0.0) * 100:.2f}% |",
                f"| **Recall (Sensibilidad)** | {advanced.get('recall', 0.0) * 100:.2f}% |",
                f"| **F1-Score** | {advanced.get('f1', 0.0) * 100:.2f}% |",
            ]
        )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_html_report(
    summary: Dict[str, Any],
    rates: Dict[str, float],
    ci: Dict[str, tuple[float, float]],
    advanced: Dict[str, Any],
    sample_rows: List[Dict[str, Any]],
    output_path: str,
) -> None:
    """Genera una página HTML elegante e interactiva con el reporte."""
    template = Template(HTML_TEMPLATE)
    html_content = template.render(
        summary=summary, rates=rates, ci=ci, advanced=advanced, sample_rows=sample_rows
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


def write_reports(
    summary: Dict[str, Any],
    rates: Dict[str, float],
    ci: Dict[str, tuple[float, float]],
    advanced: Dict[str, Any],
    sample_rows: List[Dict[str, Any]],
    output_dir: str,
) -> None:
    """Escribe los reportes en los 4 formatos requeridos dentro del directorio indicado."""
    os.makedirs(output_dir, exist_ok=True)

    generate_json_report(
        summary,
        rates,
        ci,
        advanced,
        sample_rows,
        os.path.join(output_dir, "report.json"),
    )
    generate_csv_report(sample_rows, os.path.join(output_dir, "report.csv"))
    generate_markdown_report(
        summary, rates, ci, advanced, os.path.join(output_dir, "report.md")
    )
    generate_html_report(
        summary,
        rates,
        ci,
        advanced,
        sample_rows,
        os.path.join(output_dir, "report.html"),
    )
