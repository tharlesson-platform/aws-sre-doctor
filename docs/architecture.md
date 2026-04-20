# AWS SRE Doctor Architecture

## Visão geral

CLI orientada a troubleshooting operacional com pipeline simples: snapshot -> checks desacoplados -> score -> relatórios terminal/markdown/json/html.

## Fluxo

- A CLI recebe snapshot JSON/YAML do incidente ou um dump preparado pelo time de plataforma.
- O catálogo de checks aplica regras independentes para ECS, ALB, AWS APIs, IAM, quotas e rede.
- Os reporters produzem material para operação, handoff e portfólio técnico.

## Extensões futuras

- Adicionar coleta live via boto3 para ECS, ELBv2, STS e Service Quotas.
- Publicar resumo no Slack e abrir GitHub Issue opcionalmente.
- Gerar timeline de hipóteses baseada em evidências e eventos de deploy.
