from __future__ import annotations

import json


def _render_section_list(items: list[str]) -> list[str]:
    if not items:
        return ["- nenhum item adicional"]
    return [f"- {item}" for item in items]


def render_markdown(report: dict) -> str:
    correlations = report.get("correlations", {})
    lines = [
        f"# {report['title']}",
        "",
        f"- environment: `{report['environment']}`",
        f"- workload: `{report['workload'].get('name', 'unknown')}`",
        f"- severity: `{report['severity']}`",
        f"- impact: `{report['impact_classification']}`",
        f"- health_score: `{report['health_score']}`",
        f"- correlated_signals: `{report['summary'].get('correlated_signals', 0)}`",
        "",
        "## Diagnóstico resumido",
        "",
        report["summary"]["diagnosis"],
        "",
        "## Possíveis causas",
        "",
    ]
    lines.extend(_render_section_list(report.get("possible_causes", [])))
    lines.extend(
        [
            "",
            "## Próximos passos sugeridos",
            "",
        ]
    )
    lines.extend(_render_section_list(report.get("suggested_next_steps", [])))

    if correlations.get("correlated_hypotheses"):
        lines.extend(
            [
                "",
                "## Hipóteses correlacionadas",
                "",
            ]
        )
        for item in correlations["correlated_hypotheses"]:
            lines.extend(
                [
                    f"### {item['title']}",
                    f"- confiança: `{item['confidence']}`",
                    f"- detalhe: {item['detail']}",
                    "",
                ]
            )

    if correlations.get("alarm_events"):
        lines.extend(
            [
                "## Alarmes ativos correlacionados",
                "",
            ]
        )
        for alarm in correlations["alarm_events"]:
            lines.extend(
                [
                    f"- `{alarm.get('name', 'unknown')}`: {alarm.get('reason', 'sem reason')}",
                ]
            )
        lines.append("")

    if correlations.get("deploy_events"):
        lines.extend(
            [
                "## Mudanças recentes",
                "",
            ]
        )
        for event in correlations["deploy_events"]:
            lines.extend(
                [
                    (
                        f"- `{event.get('source', 'unknown')}` / `{event.get('resource', 'unknown')}` "
                        f"em `{event.get('timestamp', 'n/a')}`: {event.get('summary', 'sem resumo')}"
                    ),
                ]
            )
        lines.append("")

    if correlations.get("network_findings"):
        lines.extend(
            [
                "## Sinais de rede coletados live",
                "",
            ]
        )
        lines.extend(_render_section_list(correlations["network_findings"]))
        lines.append("")

    lines.extend(
        [
        "## Achados",
        "",
        ]
    )
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
    correlations = report.get("correlations", {})
    issue_items = "".join(
        (
            f"<li><strong>{item['title']}</strong> ({item['severity']}/{item['confidence']})<br>"
            f"{item['impact']}<br><small>{json.dumps(item['evidence'], ensure_ascii=False)}</small></li>"
        )
        for item in report["issues"]
    )
    correlation_items = "".join(
        f"<li><strong>{item['title']}</strong><br>{item['detail']}</li>"
        for item in correlations.get("correlated_hypotheses", [])
    )
    alarm_items = "".join(
        f"<li><strong>{item.get('name', 'unknown')}</strong><br>{item.get('reason', 'sem reason')}</li>"
        for item in correlations.get("alarm_events", [])
    )
    deploy_items = "".join(
        (
            f"<li><strong>{item.get('source', 'unknown')}</strong> / {item.get('resource', 'unknown')}<br>"
            f"{item.get('timestamp', 'n/a')} - {item.get('summary', 'sem resumo')}</li>"
        )
        for item in correlations.get("deploy_events", [])
    )
    cause_items = "".join(f"<li>{item}</li>" for item in report.get("possible_causes", []))
    next_step_items = "".join(f"<li>{item}</li>" for item in report.get("suggested_next_steps", []))
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
        <p class="metric">Correlated signals: {report['summary'].get('correlated_signals', 0)}</p>
        <h2>Possíveis causas</h2>
        <ul>{cause_items}</ul>
        <h2>Próximos passos</h2>
        <ul>{next_step_items}</ul>
        <h2>Hipóteses correlacionadas</h2>
        <ul>{correlation_items or "<li>Nenhuma correlação adicional foi encontrada.</li>"}</ul>
        <h2>Alarmes ativos</h2>
        <ul>{alarm_items or "<li>Nenhum alarme ativo correlacionado.</li>"}</ul>
        <h2>Mudanças recentes</h2>
        <ul>{deploy_items or "<li>Nenhum evento de mudança recente foi correlacionado.</li>"}</ul>
        <h2>Achados</h2>
        <ul>{issue_items}</ul>
      </div>
    </body>
</html>
"""
