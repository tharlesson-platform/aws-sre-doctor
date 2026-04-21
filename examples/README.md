# Examples

Use estes exemplos como ponto de partida antes de tentar montar um snapshot real do zero ou antes de partir para a coleta live via boto3.

## Ordem recomendada

1. Rode o caso saudavel para confirmar que a CLI esta instalada corretamente.
2. Rode o caso ECS degradado para ver o diagnostico classico de workload containerizado.
3. Rode os cenarios especificos de EC2, EKS, RDS, LB/TG e IAM.
4. Gere um snapshot proprio com `init-snapshot` ou use `collect-live`.

## Arquivos

- `incident_snapshot_healthy.json`
  - Cenario base sem falhas relevantes.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_healthy.json --environment prod --report-name healthy`
  - Saida esperada:
    - `artifacts/healthy.json`
    - `artifacts/healthy.md`
    - `artifacts/healthy.html`

- `incident_snapshot.json`
  - Cenario degradado com sinais em ECS, ALB, dependencias AWS, IAM, rede, quota e correlacao com alarme/deploy.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod --report-name degraded`
  - Saida esperada:
    - `artifacts/degraded.json`
    - `artifacts/degraded.md`
    - `artifacts/degraded.html`

- `incident_snapshot_ec2.json`
  - Cenario com instância EC2 degradada, CPU alta e indício de problema de segurança operacional.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_ec2.json --environment prod --report-name ec2`

- `incident_snapshot_eks.json`
  - Cenario com node group degradado, addon instável e problema de IRSA/OIDC.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_eks.json --environment prod --report-name eks`

- `incident_snapshot_rds.json`
  - Cenario com instância RDS em `modifying` e storage pressionado.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_rds.json --environment prod --report-name rds`

- `incident_snapshot_lb_target_group.json`
  - Cenario focado em load balancer e target group.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_lb_target_group.json --environment prod --report-name lb`

- `incident_snapshot_iam.json`
  - Cenario focado em roles, trust policy e falhas de permissao.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_iam.json --environment prod --report-name iam`

- `incident_snapshot_multi_service.json`
  - Cenario combinado para demo ou tabletop exercise, com alarmes ativos e eventos de mudanca recentes.
  - Comando:
    - `aws-sre-doctor analyze --input-path examples/incident_snapshot_multi_service.json --environment prod --report-name multi`
    - `aws-sre-doctor export-github-issue --report-path artifacts/multi.json --repo tharlesson-platform/aws-sre-doctor --preview-path artifacts/multi-github-issue.md --dry-run`

## Exemplo de colaboracao

Se alguem do time quiser criar um novo caso para treinamento:

```bash
aws-sre-doctor init-snapshot \
  --output-path examples/payments-stage.json \
  --environment stage \
  --workload-name payments-api \
  --cluster stage-apps
```

Depois basta editar o arquivo gerado e incluir apenas os sintomas que realmente interessam para o exercicio.

## Exemplo de coleta live

Quando voce ja tem o recurso em AWS e quer acelerar a montagem do snapshot:

```bash
aws-sre-doctor collect-live \
  --output-path incident_snapshot.live.json \
  --environment prod \
  --region us-east-1 \
  --workload-type ecs \
  --workload-name payments-api \
  --cluster prod-apps \
  --ecs-service payments-api
```

Depois rode:

```bash
aws-sre-doctor analyze --input-path incident_snapshot.live.json --environment prod
```

## Exemplo de handoff via GitHub Issue

Depois de gerar um relatorio JSON:

```bash
aws-sre-doctor export-github-issue \
  --report-path artifacts/degraded.json \
  --repo tharlesson-platform/aws-sre-doctor \
  --preview-path artifacts/degraded-github-issue.md \
  --dry-run
```
