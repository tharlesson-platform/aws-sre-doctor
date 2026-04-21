from __future__ import annotations

import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from checks.catalog import run_checks
from core.config import load_environment_config
from core.live_collectors import AWSLiveCollector
from core.logging import configure_logging
from reporters.renderers import render_html, render_markdown
from core.snapshots import build_snapshot_template


app = typer.Typer(help="Operational troubleshooting CLI for AWS workloads.")
console = Console()


def run() -> None:
    app()


@app.command()
def version() -> None:
    console.print("0.1.0")


def _write_snapshot(output_path: Path, payload: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() in {".yaml", ".yml"}:
        rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False)
    else:
        rendered = json.dumps(payload, indent=2)
    output_path.write_text(rendered, encoding="utf-8")


@app.command()
def init_snapshot(
    output_path: Path = typer.Option(Path("incident_snapshot.json"), help="Path for the starter snapshot JSON/YAML."),
    environment: str = typer.Option("prod", help="Environment name."),
    workload_name: str = typer.Option("payments-api", help="Workload or service name."),
    workload_type: str = typer.Option("auto", help="auto|ecs|ec2|eks|rds|service"),
    cluster: str = typer.Option("prod-apps", help="Cluster or control plane name."),
    scenario: str = typer.Option(
        "healthy-baseline",
        help="healthy-baseline|ecs-degraded|ec2-degraded|eks-degraded|rds-degraded|lb-target-group-degraded|iam-degraded|multi-service-degraded",
    ),
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

    _write_snapshot(output_path, snapshot)

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
def collect_live(
    output_path: Path = typer.Option(Path("incident_snapshot.live.json"), help="Where the collected snapshot should be saved."),
    environment: str = typer.Option("prod", help="Environment name."),
    region: str = typer.Option("us-east-1", help="AWS region for collection."),
    profile: str | None = typer.Option(None, help="AWS profile name."),
    workload_type: str = typer.Option("service", help="ecs|ec2|eks|rds|service"),
    workload_name: str = typer.Option("payments", help="Logical workload or service name."),
    cluster: str = typer.Option("", help="Cluster or shared control plane name."),
    ecs_service: str | None = typer.Option(None, help="ECS service name to inspect."),
    eks_cluster_name: str | None = typer.Option(None, help="EKS cluster name to inspect."),
    ec2_instance_id: list[str] | None = typer.Option(None, help="EC2 instance id. Can be repeated."),
    rds_instance_id: list[str] | None = typer.Option(None, help="RDS instance id. Can be repeated."),
    load_balancer_arn: list[str] | None = typer.Option(None, help="Load balancer ARN. Can be repeated."),
    target_group_arn: list[str] | None = typer.Option(None, help="Target group ARN. Can be repeated."),
    iam_role_arn: list[str] | None = typer.Option(None, help="IAM role ARN. Can be repeated."),
    efs_file_system_id: list[str] | None = typer.Option(None, help="EFS file system id. Can be repeated."),
    collect_dependencies: bool = typer.Option(True, help="Probe STS, ECR, Secrets Manager, SSM and CloudWatch."),
    collect_quotas: bool = typer.Option(False, help="Keep placeholder metadata for quotas collection."),
) -> None:
    configure_logging()
    collector = AWSLiveCollector(region_name=region, profile=profile)
    snapshot = collector.collect_snapshot(
        environment=environment,
        workload_type=workload_type,
        workload_name=workload_name,
        cluster=cluster,
        ecs_service=ecs_service,
        eks_cluster_name=eks_cluster_name,
        ec2_instance_ids=ec2_instance_id,
        rds_instance_ids=rds_instance_id,
        load_balancer_arns=load_balancer_arn,
        target_group_arns=target_group_arn,
        iam_role_arns=iam_role_arn,
        efs_file_system_ids=efs_file_system_id,
        collect_dependencies=collect_dependencies,
        collect_quotas=collect_quotas,
    )
    _write_snapshot(output_path, snapshot)

    panel = Panel.fit(
        (
            f"snapshot={output_path.resolve()}\n"
            f"region={region}\n"
            f"workload={workload_name}\n"
            f"next=aws-sre-doctor analyze --input-path {output_path} --environment {environment}"
        ),
        title="AWS SRE Doctor Live Collection",
    )
    console.print(panel)
    console.print("Snapshot live coletado com boto3 e salvo para analise offline ou handoff.")


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
