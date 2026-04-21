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
                "metadata": {"collection_mode": "boto3-live", "region": self.region_name},
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
