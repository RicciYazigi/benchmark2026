# -*- coding: utf-8 -*-
"""
Interfaz de línea de comandos (CLI) principal para AegisBench.
Construida sobre la librería click para proporcionar una experiencia de consola robusta.
"""

import json
import os
import sys
import time
from typing import List, Optional

import click

from aegisbench.adapters.registry import load_adapter
from aegisbench.attacks.transforms import ATTACK_TRANSFORMS, apply_transform
from aegisbench.core.runner import Runner
from aegisbench.datasets.loaders import (
    CACHE_DIR,
    LOCK_FILE_PATH,
    get_lock_config,
    load_dataset,
)
from aegisbench.interfaces.v1 import (
    GovernanceDecision,
    Message,
    Sample,
    ScenarioType,
)
from aegisbench.reports.renderers import write_reports
from aegisbench.stats.bootstrap import (
    calculate_advanced_metrics,
    calculate_bootstrap_ci,
    calculate_rates,
)


def _coerce_param(v: str):
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


@click.group()
def main() -> None:
    """AegisBench: Suite de evaluación y robustez para Sistemas de Gobernanza de IA."""
    pass


@main.command()
@click.option(
    "--adapter",
    "-a",
    required=True,
    help="Nombre del adaptador registrado (ej: 'dummy') o ruta de clase 'modulo:Clase'.",
)
@click.option(
    "--dataset",
    "-d",
    required=True,
    help="Nombre del dataset ('jailbreakbench', 'advbench', 'harmbench', 'agentharm', 'xstest') o 'all'.",
)
@click.option(
    "--n",
    "-n",
    type=int,
    default=None,
    help="Número máximo de muestras a evaluar por dataset.",
)
@click.option(
    "--seed",
    "-s",
    type=int,
    default=42,
    help="Semilla aleatoria para reproducibilidad de bootstrap y splits.",
)
@click.option(
    "--concurrency",
    "-c",
    type=int,
    default=1,
    help="Concurrencia de ejecución (número de hilos, ej. 1, 4, 16).",
)
@click.option(
    "--output",
    "-o",
    default="./reports",
    help="Directorio de salida donde guardar los reportes.",
)
@click.option(
    "--attack",
    type=click.Choice(list(ATTACK_TRANSFORMS.keys())),
    default=None,
    help="Aplicar opcionalmente una transformación de ofuscación sobre el dataset.",
)
@click.option(
    "--accept-agentharm-terms",
    is_flag=True,
    help="Aceptar explícitamente los términos de uso y licencia restringida de AgentHarm.",
)
@click.option(
    "--include-held-out",
    is_flag=True,
    help="Incluir el split held-out (20%) en la evaluación (uso avanzado).",
)
@click.option(
    "--strict-datasets",
    is_flag=True,
    help="Fallar (exit 1) si un dataset real no se puede descargar/validar, "
    "en vez de sustituir por datos sintéticos. Usar en runs oficiales/CI.",
)
@click.option(
    "--param",
    "params",
    multiple=True,
    help="Parámetro de constructor para el adaptador, formato clave=valor "
    "(repetible). Coerción automática: true/false, int, float; si no, str. "
    "Genérico para CUALQUIER adaptador; queda registrado en el reporte "
    "(adapter_version del propio adaptador debe reflejar su modo).",
)
def run(
    adapter: str,
    dataset: str,
    n: Optional[int],
    seed: int,
    concurrency: int,
    output: str,
    attack: Optional[str],
    accept_agentharm_terms: bool,
    include_held_out: bool,
    strict_datasets: bool,
    params: tuple = (),
) -> None:
    """Ejecuta una evaluación del benchmark para un adaptador contra datasets seleccionados."""
    click.echo(f"Iniciando evaluación con el adaptador: {adapter}")

    # 1. Instanciar el adaptador
    try:
        target_system = load_adapter(
            adapter,
            **{k: _coerce_param(v) for k, v in (p.split("=", 1) for p in params)},
        )
    except Exception as e:
        click.secho(f"Error cargando el adaptador: {e}", fg="red", err=True)
        sys.exit(1)

    # 2. Cargar datasets
    dataset_names = []
    if dataset.lower() == "all":
        dataset_names = [
            "jailbreakbench",
            "advbench",
            "harmbench",
            "agentharm",
            "xstest",
        ]
    else:
        dataset_names = [dataset.strip().lower()]

    all_samples: List[Sample] = []
    for dname in dataset_names:
        click.echo(f"Cargando dataset: {dname}...")
        try:
            samples = load_dataset(
                dname,
                include_held_out=include_held_out,
                accept_terms=accept_agentharm_terms,
                strict=strict_datasets,
            )
            if not samples and dname == "agentharm" and not accept_agentharm_terms:
                click.secho(
                    "Aviso: Saltando AgentHarm debido a que no se aceptaron los términos de licencia.",
                    fg="yellow",
                )
                continue

            # Limitar a N muestras si se especifica
            if n is not None and n > 0:
                samples = samples[:n]

            all_samples.extend(samples)
        except Exception as e:
            click.secho(f"Error cargando dataset {dname}: {e}", fg="red", err=True)
            if strict_datasets:
                click.secho(
                    "Modo --strict-datasets: abortando por fallo de dataset real.",
                    fg="red",
                    bold=True,
                    err=True,
                )
                sys.exit(1)

    if not all_samples:
        click.secho("No se cargaron muestras para evaluar. Abortando.", fg="yellow")
        sys.exit(0)

    # 3. Aplicar transformaciones de ataque si se solicita
    if attack:
        click.echo(f"Aplicando transformación de ataque: {attack}...")
        transformed_samples = []
        for sample in all_samples:
            try:
                # Solo aplicamos transformaciones si la muestra requiere bloqueo originalmente (es un ataque)
                # Para evitar alterar las muestras benignas de XSTest
                if sample.ground_truth_should_block:
                    transformed_samples.append(apply_transform(attack, sample))
                else:
                    transformed_samples.append(sample)
            except Exception as e:
                click.secho(
                    f"Error aplicando ataque a {sample.sample_id}: {e}",
                    fg="red",
                    err=True,
                )
                transformed_samples.append(sample)
        all_samples = transformed_samples

    click.echo(f"Total de muestras a evaluar: {len(all_samples)}")

    # 4. Correr la evaluación
    start_time = time.perf_counter()
    runner = Runner(target_system, all_samples, concurrency=concurrency, seed=seed)
    results = runner.run()
    end_time = time.perf_counter()

    total_time = (end_time - start_time) * 1000.0
    throughput = len(results) / (total_time / 1000.0) if total_time > 0 else 0.0

    click.echo("Evaluación finalizada. Procesando estadísticas...")

    # 5. Procesar estadísticas
    rates = calculate_rates(all_samples, results)
    ci = calculate_bootstrap_ci(all_samples, results, seed=seed)
    advanced = calculate_advanced_metrics(all_samples, results)

    # 6. Preparar estructura de reporte
    mean_lat = sum(r.latency_ms for r in results) / len(results) if results else 0.0
    summary = {
        "adapter_name": target_system.name,
        "adapter_version": target_system.version,
        "seed": seed,
        "total_samples": len(all_samples),
        "evaluated_samples": len(results),
        "mean_latency_ms": mean_lat,
        "total_time_ms": total_time,
        "throughput_samples_per_sec": throughput,
        "attack_applied": attack or "none",
    }

    n_synth = sum(1 for s in all_samples if s.metadata.get("synthetic"))
    summary["synthetic_fallback_samples"] = n_synth
    summary["synthetic_fallback"] = n_synth > 0
    if n_synth > 0:
        summary["synthetic_fallback_warning"] = (
            f"ADVERTENCIA: {n_synth}/{len(all_samples)} muestras provienen de "
            f"fallback SINTÉTICO local, no del dataset público declarado. "
            f"Las métricas NO son comparables con el dataset real."
        )

    sample_rows = []
    for s in all_samples:
        # Encontrar resultado
        res = next((r for r in results if r.sample_id == s.sample_id), None)
        if res:
            sample_rows.append(
                {
                    "sample_id": s.sample_id,
                    "dataset_source": s.dataset_source,
                    "decision": res.decision,
                    "confidence": res.confidence,
                    "latency_ms": res.latency_ms,
                    "ground_truth_should_block": s.ground_truth_should_block,
                    "synthetic_fallback": bool(s.metadata.get("synthetic", False)),
                }
            )

    # 7. Escribir reportes en disco
    write_reports(summary, rates, ci, advanced, sample_rows, output)

    # 8. Imprimir resumen
    click.secho("\n=== RESULTADOS DE EVALUACIÓN ===", fg="green", bold=True)
    if n_synth > 0:
        click.secho(summary["synthetic_fallback_warning"], fg="red", bold=True)
    click.echo(
        f"ASR: {rates['asr'] * 100:.2f}% (95% CI: [{ci['asr'][0] * 100:.2f}%, {ci['asr'][1] * 100:.2f}%])"
    )
    click.echo(
        f"ORR: {rates['orr'] * 100:.2f}% (95% CI: [{ci['orr'][0] * 100:.2f}%, {ci['orr'][1] * 100:.2f}%])"
    )
    click.echo(
        f"Escalation Rate: {rates['escalation_rate'] * 100:.2f}% (95% CI: [{ci['escalation_rate'][0] * 100:.2f}%, {ci['escalation_rate'][1] * 100:.2f}%])"
    )
    click.echo(f"Latencia promedio: {mean_lat:.2f} ms")
    click.echo(f"Rendimiento: {throughput:.2f} muestras/seg")
    click.echo(f"Reportes guardados exitosamente en: {os.path.abspath(output)}")


@main.command("validate-adapter")
@click.option(
    "--adapter",
    "-a",
    required=True,
    help="Nombre o ruta de clase del adaptador a validar.",
)
def validate_adapter(adapter: str) -> None:
    """Valida el cumplimiento del contrato del adaptador con muestras sintéticas."""
    click.echo(f"Validando adaptador: {adapter}...")
    try:
        target_system = load_adapter(adapter)
    except Exception as e:
        click.secho(f"Error cargando adaptador: {e}", fg="red", err=True)
        sys.exit(1)

    # Validar atributos básicos
    if not hasattr(target_system, "name") or not target_system.name:
        click.secho(
            "Fallo: El adaptador no expone el atributo 'name' correcto.",
            fg="red",
            err=True,
        )
        sys.exit(1)
    if not hasattr(target_system, "version") or not target_system.version:
        click.secho(
            "Fallo: El adaptador no expone el atributo 'version' correcto.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    # Evaluar muestra de prueba
    test_sample = Sample(
        sample_id="validate-test-1",
        scenario_type=ScenarioType.SINGLE_TURN,
        turns=[Message(role="user", content="prueba de validación de sistema")],
        dataset_source="validation",
        harm_category=None,
        ground_truth_should_block=False,
    )

    try:
        if not target_system.supports_scenario(ScenarioType.SINGLE_TURN):
            click.secho(
                "Advertencia: El adaptador declara no soportar SINGLE_TURN.",
                fg="yellow",
            )
        else:
            result = target_system.evaluate(test_sample)
            if not isinstance(result.decision, GovernanceDecision):
                click.secho(
                    "Fallo: El retorno de evaluate no contiene una decision de tipo GovernanceDecision válida.",
                    fg="red",
                    err=True,
                )
                sys.exit(1)
            if result.sample_id != test_sample.sample_id:
                click.secho(
                    "Fallo: El sample_id devuelto no coincide con el evaluado.",
                    fg="red",
                    err=True,
                )
                sys.exit(1)
            if result.confidence is not None and not (0.0 <= result.confidence <= 1.0):
                click.secho(
                    "Fallo: El valor de confidence devuelto está fuera del rango [0.0, 1.0].",
                    fg="red",
                    err=True,
                )
                sys.exit(1)

        click.secho(
            f"Éxito: El adaptador '{target_system.name}' (v{target_system.version}) cumple con la interfaz v1 de AegisBench.",
            fg="green",
        )
    except Exception as e:
        click.secho(
            f"Fallo durante la evaluación de validación del adaptador: {e}",
            fg="red",
            err=True,
        )
        sys.exit(1)


@main.command("list-datasets")
def list_datasets() -> None:
    """Muestra información sobre los datasets configurados en el benchmark."""
    try:
        config = get_lock_config()
        click.secho(
            f"{'Dataset':<18} | {'Licencia':<45} | {'Restringido':<12} | {'Hash SHA256 bloqueado':<64}",
            bold=True,
        )
        click.echo("-" * 147)
        for name, info in config.items():
            rest = "SÍ" if info.get("restricted") else "NO"
            lic = info.get("license") or "MIT"
            if len(lic) > 42:
                lic = lic[:39] + "..."
            click.echo(f"{name:<18} | {lic:<45} | {rest:<12} | {info.get('sha256')}")
    except Exception as e:
        click.secho(f"Error listando datasets: {e}", fg="red", err=True)
        sys.exit(1)


@main.command("list-attacks")
def list_attacks() -> None:
    """Muestra las transformaciones de ataque por ofuscación disponibles."""
    click.secho("Transformaciones de Ataque Disponibles:", bold=True)
    for name in ATTACK_TRANSFORMS.keys():
        click.echo(f"- {name}")


@main.command()
@click.option(
    "--input",
    "-i",
    required=True,
    help="Ruta al archivo JSON de reporte original (report.json).",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "csv", "md", "html"]),
    required=True,
    help="Formato en el cual regenerar/exportar el reporte.",
)
@click.option(
    "--output",
    "-o",
    required=True,
    help="Archivo o directorio de destino del reporte exportado.",
)
def report(input: str, format: str, output: str) -> None:
    """Exporta o re-renderiza un reporte existente a otro formato."""
    if not os.path.exists(input):
        click.secho(f"El reporte de entrada {input} no existe.", fg="red", err=True)
        sys.exit(1)

    with open(input, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    metrics = data.get("metrics", {})
    rates = metrics.get("rates", {})
    ci_raw = metrics.get("confidence_intervals_95", {})
    advanced = metrics.get("advanced", {})
    samples = data.get("samples", [])

    # Reconstruir tuplas de CIs
    ci = {}
    for k, v in ci_raw.items():
        ci[k] = (v.get("lower", 0.0), v.get("upper", 0.0))

    if format == "json":
        write_reports(summary, rates, ci, advanced, samples, os.path.dirname(output))
    elif format == "csv":
        from aegisbench.reports.renderers import generate_csv_report

        generate_csv_report(samples, output)
    elif format == "md":
        from aegisbench.reports.renderers import generate_markdown_report

        generate_markdown_report(summary, rates, ci, advanced, output)
    elif format == "html":
        from aegisbench.reports.renderers import generate_html_report

        generate_html_report(summary, rates, ci, advanced, samples, output)

    click.echo(f"Reporte exportado exitosamente a: {output}")


@main.command("doctor")
def doctor() -> None:
    """Verifica la integridad del entorno y del benchmark."""
    click.echo("=== Diagnóstico AegisBench ===")

    # 1. Comprobar archivos del sistema
    lock_file = LOCK_FILE_PATH
    if os.path.exists(lock_file):
        click.secho(
            f"[OK] Archivo de bloqueo de datasets encontrado: {lock_file}", fg="green"
        )
    else:
        click.secho(
            f"[ERROR] Archivo de bloqueo de datasets NO encontrado en {lock_file}",
            fg="red",
        )

    # 2. Comprobar directorio de cache
    click.echo(f"Ruta de caché local: {CACHE_DIR}")
    if os.path.exists(CACHE_DIR):
        click.secho("[OK] Directorio de caché local disponible.", fg="green")
    else:
        click.echo(
            "[INFO] Directorio de caché no creado aún (se creará al descargar datasets)."
        )

    # 3. Auto-prueba de consistencia y determinismo con DummyAdapter
    click.echo("\nEjecutando auto-prueba de consistencia y determinismo...")
    try:
        target = load_adapter("dummy")
        test_samples = [
            Sample(
                sample_id="doctor-s1",
                scenario_type=ScenarioType.SINGLE_TURN,
                turns=[Message(role="user", content="prueba de ataque bomba")],
                dataset_source="doctor",
                harm_category="harm",
                ground_truth_should_block=True,
            ),
            Sample(
                sample_id="doctor-s2",
                scenario_type=ScenarioType.SINGLE_TURN,
                turns=[Message(role="user", content="hola mundo seguro")],
                dataset_source="doctor",
                harm_category=None,
                ground_truth_should_block=False,
            ),
        ]

        # Ejecutar dos veces para asegurar determinismo
        runner1 = Runner(target, test_samples, concurrency=1, seed=42)
        res1 = runner1.run()

        runner2 = Runner(target, test_samples, concurrency=1, seed=42)
        res2 = runner2.run()

        # Validar determinismo
        if len(res1) == len(res2) == 2:
            match = True
            for r1, r2 in zip(res1, res2):
                if r1.decision != r2.decision or r1.confidence != r2.confidence:
                    match = False
            if match:
                click.secho(
                    "[OK] Auto-prueba de consistencia y determinismo exitosa.",
                    fg="green",
                )
            else:
                click.secho("[ERROR] Falló el determinismo del DummyAdapter.", fg="red")
        else:
            click.secho("[ERROR] Resultados de auto-prueba incompletos.", fg="red")

    except Exception as e:
        click.secho(f"[ERROR] En la auto-prueba: {e}", fg="red")


if __name__ == "__main__":
    main()
