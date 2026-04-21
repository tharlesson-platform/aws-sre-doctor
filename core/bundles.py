from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from reporters.renderers import render_html, render_markdown


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def materialize_incident_bundle(
    *,
    bundle_dir: Path,
    report_name: str,
    input_path: Path,
    report: dict,
    region: str | None = None,
    profile: str | None = None,
    account_alias: str | None = None,
) -> Path:
    bundle_root = bundle_dir / report_name
    bundle_root.mkdir(parents=True, exist_ok=True)

    snapshot_target = bundle_root / input_path.name
    shutil.copyfile(input_path, snapshot_target)

    json_target = bundle_root / "diagnosis.json"
    markdown_target = bundle_root / "diagnosis.md"
    html_target = bundle_root / "diagnosis.html"
    manifest_target = bundle_root / "bundle-manifest.json"

    json_target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_target.write_text(render_markdown(report), encoding="utf-8")
    html_target.write_text(render_html(report), encoding="utf-8")

    manifest = {
        "tool": "aws-sre-doctor",
        "generated_at": _utc_now(),
        "report_name": report_name,
        "environment": report.get("environment", "unknown"),
        "workload": report.get("workload", {}),
        "severity": report.get("severity", "unknown"),
        "health_score": report.get("health_score"),
        "impact_classification": report.get("impact_classification"),
        "issues_found": report.get("summary", {}).get("issues_found", 0),
        "bundle_metadata": {
            "region": region,
            "profile": profile,
            "account_alias": account_alias,
        },
        "files": {
            "snapshot": snapshot_target.name,
            "json_report": json_target.name,
            "markdown_report": markdown_target.name,
            "html_report": html_target.name,
        },
    }
    manifest_target.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return bundle_root
