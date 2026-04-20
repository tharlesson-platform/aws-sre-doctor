import json
from pathlib import Path

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
