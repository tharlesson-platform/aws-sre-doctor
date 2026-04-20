from __future__ import annotations

from collections import OrderedDict


PENALTIES = {"low": 5, "medium": 10, "high": 18, "critical": 28}


def issue(title: str, severity: str, impact: str, probable_causes: list[str], next_steps: list[str], evidence: dict) -> dict:
    return {
        "title": title,
        "severity": severity,
        "impact": impact,
        "probable_causes": probable_causes,
        "next_steps": next_steps,
        "evidence": evidence,
    }


def run_checks(snapshot: dict, config: dict) -> dict:
    issues: list[dict] = []
    ecs = snapshot.get("ecs", {})
    desired = int(ecs.get("service_desired_count", 0))
    running = int(ecs.get("service_running_count", 0))
    if desired and running < desired:
        issues.append(
            issue(
                "ECS service unhealthy",
                "critical" if running <= max(1, desired // 2) else "high",
                f"{desired - running} tasks indisponíveis",
                ["Capacity shortage", "Rolling deployment travado", "Target group reprovando health checks"],
                ["Validar eventos do service", "Revisar task definition", "Conferir target group e quotas"],
                {"desired": desired, "running": running},
            )
        )

    if ecs.get("task_failures"):
        issues.append(
            issue(
                "ECS task start failure",
                "high",
                "Novas tasks falham antes de estabilizar",
                ["Imagem inacessível no ECR", "ENI/IP insuficiente", "Erro de bootstrap do container"],
                ["Inspecionar stoppedReason", "Checar subnet/ENI", "Validar imagem, secret e IAM"],
                {"failures": ecs.get("task_failures", [])},
            )
        )

    if ecs.get("secrets_pull_errors") or snapshot.get("dependencies", {}).get("secrets_manager") != "ok":
        issues.append(
            issue(
                "Falha ao puxar secrets",
                "high",
                "Containers podem iniciar sem configuração crítica",
                ["Permission mismatch no Secrets Manager", "Secret ausente", "Network timeout para AWS API"],
                ["Validar IAM role", "Conferir nome/ARN do secret", "Testar reachability da API"],
                {"secret_errors": ecs.get("secrets_pull_errors", [])},
            )
        )

    dependency_failures = {name: status for name, status in snapshot.get("dependencies", {}).items() if status != "ok"}
    if dependency_failures:
        issues.append(
            issue(
                "Falha de rede para APIs AWS",
                "high",
                "Dependências de controle da AWS estão degradadas",
                ["NAT/route quebrada", "DNS privado falhando", "NACL/SG bloqueando egress"],
                ["Testar STS/ECR/SSM a partir do workload", "Revisar rotas", "Conferir VPC endpoints quando existirem"],
                dependency_failures,
            )
        )

    unhealthy_targets = [
        tg
        for tg in snapshot.get("alb", {}).get("target_groups", [])
        if int(tg.get("unhealthy_targets", 0)) > 0
    ]
    if unhealthy_targets:
        issues.append(
            issue(
                "ALB target unhealthy",
                "high",
                "Tráfego pode estar sendo derrubado ou concentrado em poucos targets",
                ["Health check path incorreto", "App devolvendo 5xx", "Security group bloqueando ALB -> target"],
                ["Validar path de health check", "Conferir security groups", "Revisar logs de aplicação"],
                {"target_groups": unhealthy_targets},
            )
        )

    mount_error = snapshot.get("efs", {}).get("mount_error")
    if mount_error:
        issues.append(
            issue(
                "EFS mount issue",
                "medium",
                "Workload pode falhar no startup por volume indisponível",
                ["Security group/NACL bloqueando 2049", "DNS da mount target falhando", "Mount targets ausentes na subnet"],
                ["Checar mount target por AZ", "Revisar TCP/2049", "Validar resolução DNS interna"],
                {"mount_error": mount_error},
            )
        )

    network = snapshot.get("network", {})
    if network.get("route_mismatch") or network.get("sg_mismatch") or network.get("nacl_mismatch"):
        issues.append(
            issue(
                "SG/NACL/route mismatch",
                "high",
                "Há indício de bloqueio de tráfego interno ou egress",
                ["Mudança recente de rede", "Subnet errada para o workload", "Regras inconsistentes entre tiers"],
                ["Comparar rota efetiva", "Conferir SG origem/destino", "Revisar NACL stateless"],
                network,
            )
        )

    iam = snapshot.get("iam", {})
    if iam.get("task_execution_role") or iam.get("irsa"):
        issues.append(
            issue(
                "IAM permission mismatch",
                "high",
                "Permissões atuais não atendem o caminho operacional do workload",
                ["Policy insuficiente", "Trust policy incorreta", "IRSA apontando para service account errada"],
                ["Revisar execution role e task role", "Checar trust relationship", "Comparar permissões com API falha"],
                iam,
            )
        )

    if snapshot.get("network", {}).get("dns_private_resolution") == "fail":
        issues.append(
            issue(
                "DNS interno / service discovery",
                "medium",
                "Resolução interna falhou para dependências privadas",
                ["Namespace privado inconsistente", "Resolver quebrado", "Security group bloqueando DNS"],
                ["Testar resolução de nomes internos", "Conferir Route53 Private Hosted Zone", "Validar kube-dns/CoreDNS quando aplicável"],
                {"dns_private_resolution": "fail"},
            )
        )

    hot_quotas = [quota for quota in snapshot.get("quotas", []) if float(quota.get("utilization", 0)) >= float(config.get("quota_hot_threshold", 0.9))]
    if hot_quotas:
        issues.append(
            issue(
                "Quotas relevantes em pressão",
                "medium",
                "Há risco de escala ou nova implantação falhar por limite",
                ["Fargate quota", "IPs/subnets próximos do limite", "Burst de incidentes concorrentes"],
                ["Abrir aumento de quota", "Revisar autoscaling", "Distribuir workloads por AZ/subnet"],
                {"quotas": hot_quotas},
            )
        )

    severity = "low"
    if any(item["severity"] == "critical" for item in issues):
        severity = "critical"
    elif any(item["severity"] == "high" for item in issues):
        severity = "high"
    elif any(item["severity"] == "medium" for item in issues):
        severity = "medium"

    health_score = max(0, 100 - sum(PENALTIES[item["severity"]] for item in issues))
    probable_causes = list(OrderedDict.fromkeys(cause for item in issues for cause in item["probable_causes"]))
    next_steps = list(OrderedDict.fromkeys(step for item in issues for step in item["next_steps"]))
    return {
        "title": "AWS SRE Doctor",
        "environment": snapshot.get("environment", "unknown"),
        "workload": snapshot.get("workload", {}),
        "health_score": health_score,
        "severity": severity,
        "summary": {
            "issues_found": len(issues),
            "diagnosis": "Operação estável" if not issues else "Há indícios fortes de degradação operacional",
        },
        "issues": issues,
        "possible_causes": probable_causes,
        "suggested_next_steps": next_steps,
    }
