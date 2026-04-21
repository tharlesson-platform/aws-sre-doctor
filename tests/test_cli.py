import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app


def test_analyze_generates_reports() -> None:
    runner = CliRunner()
    fixture = Path("examples/incident_snapshot.json")
    result = runner.invoke(
        app,
        ["analyze", "--input-path", str(fixture), "--environment", "prod", "--report-name", "doctor-output"],
    )
    assert result.exit_code == 0, result.stdout
    assert Path("artifacts/doctor-output.json").exists()
    assert "AWS SRE Doctor" in result.stdout


def test_init_snapshot_generates_template_json(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "incident_snapshot.json"
    result = runner.invoke(
        app,
        [
            "init-snapshot",
            "--output-path",
            str(output_path),
            "--environment",
            "stage",
            "--workload-name",
            "billing-api",
            "--cluster",
            "stage-apps",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["environment"] == "stage"
    assert payload["workload"]["name"] == "billing-api"
    assert payload["workload"]["cluster"] == "stage-apps"
    assert payload["dependencies"]["sts"] == "ok"
    assert "next=aws-sre-doctor analyze" in result.stdout


def test_init_snapshot_supports_rds_scenario(tmp_path: Path) -> None:
    runner = CliRunner()
    output_path = tmp_path / "incident_snapshot.yaml"
    result = runner.invoke(
        app,
        [
            "init-snapshot",
            "--output-path",
            str(output_path),
            "--environment",
            "prod",
            "--workload-name",
            "payments-db",
            "--cluster",
            "",
            "--scenario",
            "rds-degraded",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
    assert payload["workload"]["type"] == "rds"
    assert payload["rds"]["instances"][0]["status"] == "modifying"


def test_collect_live_generates_snapshot_with_mocked_collector(tmp_path: Path, monkeypatch) -> None:
    class FakeCollector:
        def __init__(self, *, region_name: str, profile: str | None = None) -> None:
            self.region_name = region_name
            self.profile = profile

        def collect_snapshot(self, **kwargs) -> dict:
            return {
                "environment": kwargs["environment"],
                "workload": {"type": kwargs["workload_type"], "name": kwargs["workload_name"], "cluster": kwargs["cluster"]},
                "metadata": {
                    "collection_mode": "boto3-live",
                    "region": self.region_name,
                    "generated_at": "2026-04-20T12:00:00+00:00",
                    "alarm_events": [],
                    "deploy_events": [],
                    "network_assessment": {
                        "route_findings": [],
                        "security_group_findings": [],
                        "nacl_findings": [],
                        "dns_findings": [],
                    },
                },
                "ecs": {"service_desired_count": 2, "service_running_count": 1, "deployments_in_progress": 1, "task_failures": [], "secrets_pull_errors": []},
                "ec2": {"instances": []},
                "eks": {"nodegroups": [], "addons": []},
                "rds": {"instances": []},
                "alb": {"load_balancers": [], "listeners": [], "target_groups": []},
                "dependencies": {"sts": "ok", "ecr": "ok", "secrets_manager": "ok", "ssm": "ok", "cloudwatch": "ok"},
                "efs": {"mount_error": "", "file_systems": []},
                "network": {"route_mismatch": False, "sg_mismatch": False, "nacl_mismatch": False, "dns_private_resolution": "unknown"},
                "iam": {"task_execution_role": "ok", "task_role": "ok", "irsa": "ok", "roles": []},
                "quotas": [],
            }

    monkeypatch.setattr("cli.main.AWSLiveCollector", FakeCollector)
    runner = CliRunner()
    output_path = tmp_path / "incident_snapshot.live.json"
    result = runner.invoke(
        app,
        [
            "collect-live",
            "--output-path",
            str(output_path),
            "--environment",
            "prod",
            "--region",
            "us-east-1",
            "--workload-type",
            "ecs",
            "--workload-name",
            "payments-api",
            "--cluster",
            "prod-apps",
            "--ecs-service",
            "payments-api",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["metadata"]["collection_mode"] == "boto3-live"
    assert payload["workload"]["name"] == "payments-api"
    assert "AWS SRE Doctor Live Collection" in result.stdout


def test_export_github_issue_supports_dry_run_preview(tmp_path: Path) -> None:
    runner = CliRunner()
    report_path = tmp_path / "report.json"
    preview_path = tmp_path / "issue.md"
    report_path.write_text(
        json.dumps(
            {
                "title": "AWS SRE Doctor",
                "environment": "prod",
                "workload": {"name": "payments-api"},
                "health_score": 47,
                "severity": "critical",
                "impact_classification": "customer-visible",
                "summary": {
                    "issues_found": 2,
                    "diagnosis": "Há falha crítica com potencial de impacto direto ao cliente",
                    "categories": ["ecs", "network"],
                    "correlated_signals": 2,
                },
                "issues": [],
                "possible_causes": ["IAM permission mismatch"],
                "suggested_next_steps": ["Revisar execution role"],
                "correlations": {
                    "alarm_events": [{"name": "payments-api-5xx", "reason": "5xx above threshold"}],
                    "deploy_events": [{"source": "ecs", "resource": "payments-api", "timestamp": "2026-04-20T12:00:00+00:00", "summary": "Rollout in progress"}],
                    "network_findings": [],
                    "quota_pressure": [],
                    "correlated_hypotheses": [{"title": "Deploy recente pode estar correlacionado com os alarmes", "detail": "Há sinais simultâneos.", "confidence": "medium"}],
                },
            }
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "export-github-issue",
            "--report-path",
            str(report_path),
            "--repo",
            "tharlesson-platform/aws-sre-doctor",
            "--preview-path",
            str(preview_path),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert preview_path.exists()
    assert "Preview gerado sem criar issue remota." in result.stdout
