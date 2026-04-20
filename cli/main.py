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


app = typer.Typer(help="Operational troubleshooting CLI for AWS workloads.")
console = Console()


def run() -> None:
    app()


@app.command()
def version() -> None:
    console.print("0.1.0")


@app.command()
def analyze(
    input_path: Path = typer.Option(..., exists=True, help="Snapshot JSON/YAML to analyze."),
    environment: str = typer.Option("prod", help="Environment profile under config/environments."),
    output_dir: Path = typer.Option(Path("artifacts"), help="Directory for generated reports."),
) -> None:
    raw = input_path.read_text(encoding="utf-8")
    snapshot = json.loads(raw) if input_path.suffix.lower() == ".json" else yaml.safe_load(raw)
    config = load_environment_config(environment)
    report = run_checks(snapshot, config)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "diagnosis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "diagnosis.md").write_text(render_markdown(report), encoding="utf-8")
    (output_dir / "diagnosis.html").write_text(render_html(report), encoding="utf-8")

    panel = Panel.fit(
        f"health_score={report['health_score']}\nseverity={report['severity']}\nissues={len(report['issues'])}",
        title="AWS SRE Doctor",
    )
    console.print(panel)
    console.print(f"Relatórios gerados em {output_dir.resolve()}")
