from __future__ import annotations

from checks.base import build_issue


def run(snapshot: dict, _config: dict) -> list[dict]:
    network = snapshot.get("network", {})
    issues: list[dict] = []
    if network.get("route_mismatch") or network.get("sg_mismatch") or network.get("nacl_mismatch"):
        issues.append(
            build_issue(
                title="SG/NACL/route mismatch",
                severity="high",
                impact="Há indício de bloqueio de tráfego interno ou egress",
                probable_causes=[
                    "Mudança recente de rede",
                    "Subnet errada para o workload",
                    "Regras inconsistentes entre tiers",
                ],
                next_steps=[
                    "Comparar rota efetiva",
                    "Conferir SG origem/destino",
                    "Revisar NACL stateless",
                ],
                evidence=network,
                category="network",
            )
        )

    if network.get("dns_private_resolution") == "fail":
        issues.append(
            build_issue(
                title="DNS interno / service discovery",
                severity="medium",
                impact="Resolução interna falhou para dependências privadas",
                probable_causes=[
                    "Namespace privado inconsistente",
                    "Resolver quebrado",
                    "Security group bloqueando DNS",
                ],
                next_steps=[
                    "Testar resolução de nomes internos",
                    "Conferir Route53 Private Hosted Zone",
                    "Validar kube-dns/CoreDNS quando aplicável",
                ],
                evidence={"dns_private_resolution": "fail"},
                category="network",
                confidence="medium",
            )
        )
    return issues
