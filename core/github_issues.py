from __future__ import annotations

import json
from collections import OrderedDict
from typing import Callable
from urllib import error, request

from reporters.renderers import render_markdown


def build_issue_title(report: dict, prefix: str = "AWS SRE Doctor") -> str:
    severity = str(report.get("severity", "unknown")).upper()
    environment = report.get("environment", "unknown")
    workload = report.get("workload", {}).get("name", "unknown")
    return f"[{prefix}] {severity} {environment}/{workload}"


def build_issue_body(report: dict) -> str:
    correlation_titles = [
        item.get("title", "")
        for item in report.get("correlations", {}).get("correlated_hypotheses", [])
        if item.get("title")
    ]
    correlation_titles = list(OrderedDict.fromkeys(correlation_titles))

    lines = [
        "## Resumo executivo",
        "",
        f"- Severidade: `{report.get('severity', 'unknown')}`",
        f"- Impacto: `{report.get('impact_classification', 'unknown')}`",
        f"- Health score: `{report.get('health_score', 0)}`",
        f"- Diagnóstico: {report.get('summary', {}).get('diagnosis', 'n/a')}",
        "",
        "## Próximos passos sugeridos",
        "",
    ]
    next_steps = report.get("suggested_next_steps", [])
    if next_steps:
        lines.extend([f"- {step}" for step in next_steps])
    else:
        lines.append("- Revisar o relatório completo abaixo.")

    if correlation_titles:
        lines.extend(
            [
                "",
                "## Hipóteses correlacionadas",
                "",
            ]
        )
        lines.extend([f"- {title}" for title in correlation_titles])

    lines.extend(
        [
            "",
            "## Relatório completo",
            "",
            render_markdown(report).strip(),
            "",
            "_Issue gerada automaticamente pelo AWS SRE Doctor._",
        ]
    )
    return "\n".join(lines).strip() + "\n"


class GitHubIssuePublisher:
    def __init__(
        self,
        *,
        token: str,
        api_base_url: str = "https://api.github.com",
        opener: Callable[[request.Request], object] | None = None,
    ) -> None:
        self.token = token
        self.api_base_url = api_base_url.rstrip("/")
        self.opener = opener or request.urlopen

    def create_issue(self, *, repo: str, title: str, body: str, labels: list[str] | None = None) -> dict:
        if "/" not in repo:
            raise ValueError("Repo must follow the format owner/repository.")

        owner, repository = repo.split("/", 1)
        payload = {
            "title": title,
            "body": body,
            "labels": labels or [],
        }
        target_url = f"{self.api_base_url}/repos/{owner}/{repository}/issues"
        http_request = request.Request(
            target_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "aws-sre-doctor",
            },
            method="POST",
        )
        try:
            response = self.opener(http_request)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub issue creation failed: {detail}") from exc

        raw_payload = response.read()
        parsed = json.loads(raw_payload.decode("utf-8"))
        return {
            "number": parsed.get("number"),
            "html_url": parsed.get("html_url"),
            "title": parsed.get("title", title),
        }
