from __future__ import annotations

import json


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['title']}",
        "",
        f"- environment: `{report['environment']}`",
        f"- workload: `{report['workload'].get('name', 'unknown')}`",
        f"- severity: `{report['severity']}`",
        f"- impact: `{report['impact_classification']}`",
        f"- health_score: `{report['health_score']}`",
        "",
        "## Diagnóstico resumido",
        "",
        report["summary"]["diagnosis"],
        "",
        "## Achados",
        "",
    ]
    for item in report["issues"]:
        lines.extend(
                [
                    f"### {item['title']}",
                    f"- severidade: `{item['severity']}`",
                    f"- categoria: `{item['category']}`",
                    f"- confiança: `{item['confidence']}`",
                    f"- impacto: {item['impact']}",
                    f"- causas prováveis: {', '.join(item['probable_causes'])}",
                    f"- próximos passos: {', '.join(item['next_steps'])}",
                    f"- evidências: `{json.dumps(item['evidence'], ensure_ascii=False)}`",
                    "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def render_html(report: dict) -> str:
    issue_items = "".join(
        f"<li><strong>{item['title']}</strong> ({item['severity']}/{item['confidence']})<br>{item['impact']}</li>"
        for item in report["issues"]
    )
    return f"""<!doctype html>
<html lang="pt-BR">
  <head>
    <meta charset="utf-8">
    <title>{report['title']}</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 32px; background: #f6f8fb; color: #1f2937; }}
      .card {{ background: white; border-radius: 16px; padding: 24px; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08); }}
      .metric {{ display: inline-block; margin-right: 24px; font-weight: bold; }}
    </style>
  </head>
  <body>
      <div class="card">
        <h1>{report['title']}</h1>
        <p class="metric">Severity: {report['severity']}</p>
        <p class="metric">Impact: {report['impact_classification']}</p>
        <p class="metric">Health score: {report['health_score']}</p>
        <h2>Achados</h2>
        <ul>{issue_items}</ul>
      </div>
    </body>
</html>
"""
