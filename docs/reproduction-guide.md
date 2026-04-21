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

### 3. Criar um snapshot proprio

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

## Como preencher um snapshot sem sofrer

- Use o comando `init-snapshot` para nunca comecar de um arquivo vazio.
- Preencha apenas os sintomas confirmados.
- Evite marcar `route_mismatch`, `sg_mismatch` ou `nacl_mismatch` como `true` sem evidencia.
- Use o guia [snapshot-generation.md](snapshot-generation.md) para mapear AWS CLI em campos do snapshot.

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

## Fluxo recomendado para colaboradores

1. Executar o caso saudavel.
2. Executar o caso degradado.
3. Ler `artifacts/*.md` para entender a estrutura do diagnostico.
4. Criar um snapshot proprio com `init-snapshot`.
5. Versionar novos cenarios em `examples/` quando forem uteis para treino ou onboarding.
