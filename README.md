# AWS SRE Doctor

CLI profissional para troubleshooting operacional em AWS, com foco em diagnóstico rápido, coleta live, correlação operacional e redução de MTTR.

## Problema que resolve

- Times de SRE perdem tempo consolidando sintomas espalhados entre ECS, EC2, EKS, RDS, ALB, IAM, quotas e rede.
- Incidentes recorrentes exigem hipóteses rápidas, severidade clara e próximos passos acionáveis.
- A ferramenta entrega um diagnóstico resumido e detalhado pronto para operação e handoff.

## Arquitetura

- CLI com Typer para execução local, coleta live via boto3, export para GitHub Issues e futura automação em pipeline.
- Checks desacoplados em `checks/` para evoluir troubleshooting por domínio.
- Reporters em markdown/json/html para operação, documentação e portfólio técnico.
- Engine de correlação para cruzar alarmes ativos, mudanças recentes, rede e pressão de quota.

## Estrutura do projeto

```text
.
|-- cli/
|-- core/
|-- checks/
|-- reporters/
|-- config/
|-- tests/
|-- examples/
|-- docs/
|-- pyproject.toml
|-- Makefile
|-- .github/workflows/ci.yml
|-- README.md
|-- LICENSE
|-- NOTICE
```

## Como executar

```bash
python -m pip install -e .[dev]
aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod
```

## Coleta live via boto3

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

## Incident bundle portatil

Agora o `analyze` tambem pode materializar um bundle portatil para handoff, postmortem ou ingestao por ferramentas irmas:

```bash
aws-sre-doctor analyze \
  --input-path examples/incident_snapshot.json \
  --environment prod \
  --report-name payments-prod \
  --bundle-dir bundles \
  --region us-east-1 \
  --profile platform \
  --account-alias prod-platform
```

Estrutura gerada:

```text
bundles/
  payments-prod/
    incident_snapshot.json
    diagnosis.json
    diagnosis.md
    diagnosis.html
    bundle-manifest.json
```

Agora a coleta live também consegue:

- coletar sinais extras de rede em `route tables`, `security groups`, `NACLs` e `DNS do VPC`
- capturar alarmes ativos relevantes em CloudWatch
- sintetizar sinais de deploy ou mudança recente
- coletar quotas relevantes por serviço quando `--collect-quotas` estiver habilitado

Exemplo com quotas:

```bash
aws-sre-doctor collect-live \
  --output-path incident_snapshot.live.json \
  --environment prod \
  --region us-east-1 \
  --workload-type ecs \
  --workload-name payments-api \
  --cluster prod-apps \
  --ecs-service payments-api \
  --collect-quotas
```

## Reproducao guiada

- Primeiro passo recomendado:
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_healthy.json --environment prod --report-name healthy`
- Segundo passo recomendado:
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod --report-name degraded`
- Terceiro passo recomendado:
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_ec2.json --environment prod --report-name ec2`
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_eks.json --environment prod --report-name eks`
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_rds.json --environment prod --report-name rds`
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_lb_target_group.json --environment prod --report-name lb`
  - `aws-sre-doctor analyze --input-path examples/incident_snapshot_iam.json --environment prod --report-name iam`
- Para reproduzir com mais seguranca:
  - consulte `examples/README.md`
  - siga `docs/reproduction-guide.md`

## Como gerar o incident_snapshot na prática

O caminho mais simples agora e gerar um snapshot-base e editar so o que esta acontecendo no incidente:

```bash
aws-sre-doctor init-snapshot \
  --output-path incident_snapshot.json \
  --environment prod \
  --workload-name payments-api \
  --cluster prod-apps
```

Isso cria um JSON "saudavel" com a estrutura certa. A partir dai voce altera apenas os sintomas observados.

Se quiser um exemplo ja degradado para demo ou treinamento:

```bash
aws-sre-doctor init-snapshot \
  --output-path incident_snapshot.demo.json \
  --environment prod \
  --workload-name payments-api \
  --cluster prod-apps \
  --scenario ecs-degraded
```

Agora tambem existem cenarios prontos para:

- `ec2-degraded`
- `eks-degraded`
- `rds-degraded`
- `lb-target-group-degraded`
- `iam-degraded`
- `multi-service-degraded`

Depois rode:

```bash
aws-sre-doctor analyze --input-path incident_snapshot.json --environment prod
```

Mapeamento pratico para preencher o snapshot com dados reais:

- `ecs.service_desired_count` e `ecs.service_running_count`: saem de `aws ecs describe-services`
- `ecs.task_failures`: use `stoppedReason`, eventos do service ou erros recorrentes das tasks
- `ecs.secrets_pull_errors`: registre erros como `AccessDeniedException`, `ResourceNotFoundException` ou timeout
- `alb.target_groups[*].healthy_targets` e `unhealthy_targets`: saem de `aws elbv2 describe-target-health`
- `dependencies`: marque `ok`, `timeout`, `access_denied` ou outro estado observavel para STS, ECR, Secrets Manager, SSM e CloudWatch
- `efs.mount_error`: copie a mensagem real do mount quando existir
- `network.route_mismatch`, `sg_mismatch`, `nacl_mismatch`: marque `true` apenas quando voce confirmar inconsistencia
- `network.dns_private_resolution`: use `ok` ou `fail`
- `iam.task_execution_role` e `iam.irsa`: descreva o problema encontrado ou mantenha `ok`
- `quotas`: adicione apenas quotas perto do limite, por exemplo utilizacao acima de 85%
- `metadata.alarm_events`: use quando quiser enriquecer o snapshot com alarmes relevantes
- `metadata.deploy_events`: use para marcar rollout, change window ou alteração recente

Um fluxo bem pratico fica assim:

1. Gere a base com `init-snapshot`
2. Olhe ECS/ALB/AWS CLI e preencha somente os sintomas reais
3. Rode `analyze`
4. Use o markdown/html gerado para handoff ou postmortem

Guia detalhado com comandos AWS CLI: `docs/snapshot-generation.md`

Guia de coleta live via boto3: `docs/live-collection.md`

Guia de export para GitHub Issues: `docs/github-issues.md`

## Exemplos reais

- `aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod`
- `AWS_REGION=us-east-1 AWS_PROFILE=platform aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment dev`
- `aws-sre-doctor init-snapshot --output-path incident_snapshot.yaml --environment stage --workload-name billing-api --cluster stage-apps`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_healthy.json --environment prod --report-name healthy`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_ec2.json --environment prod --report-name ec2`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_eks.json --environment prod --report-name eks`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_rds.json --environment prod --report-name rds`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_lb_target_group.json --environment prod --report-name lb`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_iam.json --environment prod --report-name iam`
- `aws-sre-doctor analyze --input-path examples/incident_snapshot_multi_service.json --environment prod --report-name multi`
- `aws-sre-doctor collect-live --output-path incident_snapshot.live.json --environment prod --region us-east-1 --workload-type eks --workload-name payments-cluster --eks-cluster-name payments-eks-prod`
- `aws-sre-doctor export-github-issue --report-path artifacts/multi.json --repo tharlesson-platform/aws-sre-doctor --preview-path artifacts/multi-github-issue.md --dry-run`

## Como isso ajuda SREs no dia a dia

- Acelera triagem inicial quando ECS, EC2, EKS, RDS, ALB e dependências AWS falham em conjunto.
- Padroniza diagnóstico resumido, causas prováveis e próximos passos para reduzir MTTR.
- Permite partir de dados reais com coleta live via boto3 quando o incidente ja esta acontecendo.
- Ajuda a cruzar alarmes, mudanças recentes, rede e quota sem depender só de memória operacional.
- Cria artefatos reutilizáveis em postmortems, runbooks e demos técnicas.
- Facilita abrir issues com contexto suficiente para follow-up do incidente.

## Roadmap entregue nesta versão

- Coleta live enriquecida com sinais de rede e quotas.
- Correlação automática com eventos de deploy e alarmes.
- Export de diagnóstico para GitHub Issues.

## Próximas evoluções sugeridas

- Incluir coleta opcional de eventos de deploy a partir de GitHub Actions ou CodePipeline.
- Exportar achados diretamente para Slack ou Jira.
- Adicionar correlação temporal mais fina com janela ajustável por ambiente.

## Licença

Este projeto está licenciado sob a Apache License 2.0. Consulte o arquivo `LICENSE` para mais detalhes.

## Atribuição

Este projeto foi desenvolvido e publicado por **Tharlesson**.
Caso você utilize este material como base em ambientes internos, estudos, adaptações ou redistribuições, preserve os créditos de autoria e os avisos de licença aplicáveis.

## Créditos e Uso

Este repositório foi criado com foco em automação, padronização operacional e melhoria da rotina de profissionais de SRE, DevOps, Cloud e Plataforma.

Você pode:
- estudar
- reutilizar
- adaptar
- evoluir este projeto dentro do seu contexto

Ao reutilizar ou derivar este material:
- mantenha os avisos de licença
- preserve os créditos de autoria quando aplicável
- documente alterações relevantes feitas sobre a base original

## Autor

**Tharlesson**  
GitHub: https://github.com/tharlesson
