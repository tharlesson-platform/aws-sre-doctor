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
