from __future__ import annotations

from collections import OrderedDict
from datetime import UTC, datetime


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _dedupe_strings(values: list[str]) -> list[str]:
    return list(OrderedDict.fromkeys(item for item in values if item))


def _flatten_network_findings(network_assessment: dict) -> list[str]:
    findings: list[str] = []
    for section in ("route_findings", "security_group_findings", "nacl_findings", "dns_findings"):
        for item in network_assessment.get(section, []):
            if isinstance(item, dict):
                findings.append(item.get("summary", ""))
            elif isinstance(item, str):
                findings.append(item)
    return _dedupe_strings(findings)


def build_correlations(snapshot: dict, issues: list[dict], config: dict) -> dict:
    metadata = snapshot.get("metadata", {})
    alarm_events = metadata.get("alarm_events", [])
    deploy_events = metadata.get("deploy_events", [])
    network_assessment = metadata.get("network_assessment", {})

    anchor_time = _parse_timestamp(metadata.get("generated_at")) or datetime.now(tz=UTC)
    recent_change_window_minutes = int(config.get("correlation_recent_change_minutes", 180))
    quota_threshold = float(config.get("quota_hot_threshold", 0.9))

    categories = {item.get("category", "") for item in issues}
    active_alarms = [item for item in alarm_events if str(item.get("state", "")).upper() == "ALARM"]

    recent_deploys = []
    for event in deploy_events:
        event_time = _parse_timestamp(event.get("timestamp"))
        if event_time is None:
            recent_deploys.append(event)
            continue
        delta_minutes = abs((anchor_time - event_time).total_seconds()) / 60
        if delta_minutes <= recent_change_window_minutes:
            recent_deploys.append(event)

    quota_pressure = [
        quota
        for quota in snapshot.get("quotas", [])
        if float(quota.get("utilization", 0.0) or 0.0) >= quota_threshold
    ]
    network_findings = _flatten_network_findings(network_assessment)

    correlated_hypotheses: list[dict] = []
    if active_alarms:
        correlated_hypotheses.append(
            {
                "title": "Alarmes ativos reforçam a degradação observada",
                "detail": (
                    f"{len(active_alarms)} alarme(s) em estado ALARM foram encontrados para o workload, "
                    "o que fortalece a hipótese de impacto operacional em andamento."
                ),
                "confidence": "high",
            }
        )

    if recent_deploys:
        correlated_hypotheses.append(
            {
                "title": "Mudança recente merece validação imediata",
                "detail": (
                    f"{len(recent_deploys)} evento(s) de deploy ou mudança recente apareceram perto do momento da coleta. "
                    "Vale confirmar se a degradação começou após rollout, scaling ou alteração de configuração."
                ),
                "confidence": "medium",
            }
        )

    if active_alarms and recent_deploys:
        correlated_hypotheses.append(
            {
                "title": "Deploy recente pode estar correlacionado com os alarmes",
                "detail": (
                    "Há sinais simultâneos de mudança recente e alarmes ativos. "
                    "Essa combinação costuma ser um bom ponto de partida para validar causalidade antes de aprofundar o RCA."
                ),
                "confidence": "medium",
            }
        )

    if network_findings and categories.intersection({"network", "dependencies", "ecs", "eks", "efs"}):
        correlated_hypotheses.append(
            {
                "title": "Sinais de rede corroboram parte do impacto",
                "detail": (
                    "A coleta live encontrou indícios adicionais em subnets, security groups, NACLs ou DNS do VPC. "
                    "Isso aumenta a confiança em hipóteses ligadas a reachability e service discovery."
                ),
                "confidence": "medium",
            }
        )

    if quota_pressure and categories.intersection({"quotas", "ecs", "alb", "rds"}):
        quota_names = ", ".join(quota.get("name", "quota") for quota in quota_pressure[:3])
        correlated_hypotheses.append(
            {
                "title": "Pressão de quota pode amplificar a degradação",
                "detail": (
                    f"As quotas {quota_names} estão próximas do limite configurado. "
                    "Essa pressão pode bloquear scale-out, criação de recursos ou recuperação automática."
                ),
                "confidence": "medium",
            }
        )

    return {
        "alarm_events": active_alarms,
        "deploy_events": recent_deploys,
        "network_findings": network_findings,
        "quota_pressure": quota_pressure,
        "correlated_hypotheses": correlated_hypotheses,
    }
