from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from checks.catalog import run_checks
from core.config import load_environment_config
from reporters.renderers import render_html, render_markdown
from core.snapshots import build_snapshot_template


app = typer.Typer(help="Operational troubleshooting CLI for AWS workloads.")
console = Console()


def run() -> None:
    app()


@app.command()
def version() -> None:
    console.print("0.1.0")


@app.command()
def init_snapshot(
    output_path: Path = typer.Option(Path("incident_snapshot.json"), help="Path for the starter snapshot JSON/YAML."),
    environment: str = typer.Option("prod", help="Environment name."),
    workload_name: str = typer.Option("payments-api", help="Workload or service name."),
    workload_type: str = typer.Option("ecs", help="ecs|eks|service"),
    cluster: str = typer.Option("prod-apps", help="Cluster or control plane name."),
    scenario: str = typer.Option("healthy-baseline", help="healthy-baseline|ecs-degraded"),
) -> None:
    try:
        snapshot = build_snapshot_template(
            environment=environment,
            workload_type=workload_type,
            workload_name=workload_name,
            cluster=cluster,
            scenario=scenario,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".yaml", ".yml"}:
        payload = yaml.safe_dump(snapshot, sort_keys=False, allow_unicode=False)
    else:
        payload = json.dumps(snapshot, indent=2)
    output_path.write_text(payload, encoding="utf-8")

    panel = Panel.fit(
        (
            f"snapshot={output_path.resolve()}\n"
            f"scenario={scenario}\n"
            f"workload={workload_name}\n"
            f"next=aws-sre-doctor analyze --input-path {output_path} --environment {environment}"
        ),
        title="AWS SRE Doctor Snapshot",
    )
    console.print(panel)
    console.print("Preencha somente os campos que representam o sintoma real do incidente.")


@app.command()
def analyze(
    input_path: Path = typer.Option(..., exists=True, help="Snapshot JSON/YAML to analyze."),
    environment: str = typer.Option("prod", help="Environment profile under config/environments."),
    output_dir: Path = typer.Option(Path("artifacts"), help="Directory for generated reports."),
    output_format: str = typer.Option("all", help="all|json|markdown|html"),
    report_name: str = typer.Option("diagnosis", help="Base name for generated files."),
) -> None:
    raw = input_path.read_text(encoding="utf-8")
    snapshot = json.loads(raw) if input_path.suffix.lower() == ".json" else yaml.safe_load(raw)
    config = load_environment_config(environment)
    report = run_checks(snapshot, config)

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_format in {"all", "json"}:
        (output_dir / f"{report_name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if output_format in {"all", "markdown"}:
        (output_dir / f"{report_name}.md").write_text(render_markdown(report), encoding="utf-8")
    if output_format in {"all", "html"}:
        (output_dir / f"{report_name}.html").write_text(render_html(report), encoding="utf-8")

    panel = Panel.fit(
        (
            f"health_score={report['health_score']}\n"
            f"severity={report['severity']}\n"
            f"impact={report['impact_classification']}\n"
            f"issues={len(report['issues'])}"
        ),
        title="AWS SRE Doctor",
    )
    console.print(panel)
    console.print(f"Relatórios gerados em {output_dir.resolve()}")
