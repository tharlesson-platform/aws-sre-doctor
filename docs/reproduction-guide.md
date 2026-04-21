# Guia de reproducao

Este guia existe para facilitar a primeira execucao do `aws-sre-doctor` por novos colaboradores.

## Pre-requisitos

- Python 3.11+
- ambiente virtual opcional
- dependencias instaladas com `python -m pip install -e .[dev]`

## Caminho mais rapido

### 1. Validar a instalacao

```bash
aws-sre-doctor analyze --input-path examples/incident_snapshot_healthy.json --environment prod --report-name healthy
```

O comando deve gerar:

- `artifacts/healthy.json`
- `artifacts/healthy.md`
- `artifacts/healthy.html`

### 2. Ver um caso com falhas reais

```bash
aws-sre-doctor analyze --input-path examples/incident_snapshot.json --environment prod --report-name degraded
```

Esse cenario e o melhor ponto de partida para demo, onboarding e testes de handoff.

### 3. Rodar cenarios especificos por servico

```bash
aws-sre-doctor analyze --input-path examples/incident_snapshot_ec2.json --environment prod --report-name ec2
aws-sre-doctor analyze --input-path examples/incident_snapshot_eks.json --environment prod --report-name eks
aws-sre-doctor analyze --input-path examples/incident_snapshot_rds.json --environment prod --report-name rds
aws-sre-doctor analyze --input-path examples/incident_snapshot_lb_target_group.json --environment prod --report-name lb
aws-sre-doctor analyze --input-path examples/incident_snapshot_iam.json --environment prod --report-name iam
```

### 4. Criar um snapshot proprio

```bash
aws-sre-doctor init-snapshot \
  --output-path incident_snapshot.json \
  --environment prod \
  --workload-name payments-api \
  --cluster prod-apps
```

Depois edite apenas os campos que representam o incidente real e rode:

```bash
aws-sre-doctor analyze --input-path incident_snapshot.json --environment prod
```

### 5. Coletar um snapshot live com boto3

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

Esse comando acelera muito o bootstrap do diagnostico quando voce ja sabe quais recursos quer observar em AWS.

### 6. Ver a correlacao operacional e gerar issue preview

```bash
aws-sre-doctor analyze --input-path examples/incident_snapshot_multi_service.json --environment prod --report-name multi
aws-sre-doctor export-github-issue --report-path artifacts/multi.json --repo tharlesson-platform/aws-sre-doctor --preview-path artifacts/multi-github-issue.md --dry-run
```

Esse fluxo e o mais util para mostrar:

- correlacao entre alarmes e mudancas recentes
- seccao de hipoteses correlacionadas no markdown/html
- issue pronta para handoff ou backlog

## Como preencher um snapshot sem sofrer

- Use o comando `init-snapshot` para nunca comecar de um arquivo vazio.
- Use `collect-live` quando o recurso ja existe e voce quer partir de dados reais.
- Preencha apenas os sintomas confirmados.
- Evite marcar `route_mismatch`, `sg_mismatch` ou `nacl_mismatch` como `true` sem evidencia.
- Use o guia [snapshot-generation.md](snapshot-generation.md) para mapear AWS CLI em campos do snapshot.
- Use o guia `docs/live-collection.md` para comandos boto3/CLI prontos por servico.

## O que revisar no resultado

- `health_score`
- `severity`
- `impact_classification`
- `possible_causes`
- `suggested_next_steps`

## Erros comuns

- Rodar com um `input-path` inexistente.
- Misturar `.yaml` com sintaxe JSON.
- Usar valores muito genericos em `dependencies` e depois esperar uma classificacao precisa.
- Criar snapshots grandes demais com campos que nao agregam ao diagnostico.
- Rodar `collect-live` sem credenciais AWS validas e esperar um snapshot completo.
- Coletar live sem informar ids/arns relevantes e depois assumir que o snapshot cobriu todo o incidente.

## Fluxo recomendado para colaboradores

1. Executar o caso saudavel.
2. Executar o caso degradado.
3. Executar pelo menos um cenario de `EC2`, `EKS` ou `RDS`.
4. Ler `artifacts/*.md` para entender a estrutura do diagnostico.
5. Criar um snapshot proprio com `init-snapshot`.
6. Testar `collect-live` em um workload controlado.
7. Gerar um preview de GitHub Issue para entender o formato de handoff.
8. Versionar novos cenarios em `examples/` quando forem uteis para treino ou onboarding.
