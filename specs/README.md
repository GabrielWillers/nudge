# Especificações

Este projeto segue Spec Driven Development: a especificação é o contrato entre
intenção e implementação, e é atualizada junto com o código. Mudou a
implementação, atualiza-se o TRD; tomou-se uma decisão difícil de reverter,
registra-se um ADR.

O projeto tem **duas features**, deliberadamente separadas: o aplicativo é a
carga de trabalho, e a plataforma é o entregável.

## PRD — o quê e o porquê

| documento | assunto |
|-----------|---------|
| [`prd/nudge-app-v1.md`](prd/nudge-app-v1.md) | O aplicativo: lista compartilhada de lembretes, um serviço, sem autenticação. Escopo congelado (ADR-0004) e forma mínima (ADR-0010). |
| [`prd/plataforma-devops.md`](prd/plataforma-devops.md) | A plataforma: verificação, artefato, cluster, convergência, observação e continuidade. É o objetivo do projeto. |

## TRD — o como

| documento | assunto |
|-----------|---------|
| [`trd/nudge-app-v1.md`](trd/nudge-app-v1.md) | Rotas, modelo de dados (uma tabela), stack e NFRs do aplicativo. |
| [`trd/plataforma-devops.md`](trd/plataforma-devops.md) | Fluxo do ciclo, estrutura do repositório, recursos no cluster e critérios de validação por fase. |

O aplicativo cabe em no máximo 20 arquivos de código (ADR-0010). Se a spec dele
ficar maior que o código, o corte foi no lugar errado.

## ADR — por que decidimos assim

ADRs são imutáveis: nunca edite a decisão de um ADR aceito nem o apague. Se a
decisão mudar, crie um novo com status "Substitui ADR-NNNN" e marque o antigo
como substituído.

| ADR | decisão | status |
|-----|---------|--------|
| [0001](adr/0001-monorepo-unico.md) | Repositório único para app, manifestos e infraestrutura | Aceito |
| [0002](adr/0002-stack-da-aplicacao.md) | ~~React + Vite no frontend, FastAPI no backend~~ | Substituído por 0010 |
| [0003](adr/0003-auth-jwt-escopo-minimo.md) | ~~Token JWT de acesso único e senha com Argon2~~ | Substituído por 0010 |
| [0004](adr/0004-congelar-escopo-funcional.md) | Congelar o escopo funcional do aplicativo ao fim da v1 | Aceito |
| [0005](adr/0005-doks-no-de-4gb.md) | Kubernetes gerenciado na DigitalOcean, um nó de 4 GB | Aceito |
| [0006](adr/0006-kubernetes-antes-do-ci.md) | Kubernetes antes do pipeline completo, com verificação mínima antecipada | Aceito |
| [0007](adr/0007-postgres-statefulset-no-cluster.md) | PostgreSQL no cluster como StatefulSet com volume do provedor | Aceito |
| [0008](adr/0008-cluster-local-com-kind.md) | kind como cluster local, espelhando a produção | Aceito |
| [0009](adr/0009-entrada-https-sem-balanceador-gerenciado.md) | Entrada pela porta do nó e certificado por desafio de DNS | Aceito |
| [0010](adr/0010-servico-unico-sem-autenticacao.md) | Serviço único, HTML no servidor, sem autenticação — **substitui 0002 e 0003** | Aceito |

### ADRs previstos, ainda não escritos

Decisões que só ficam maduras na fase em que são implementadas. Escrever cada
uma antes do trabalho da fase correspondente:

- Estratégia de cifra de segredo no repositório (fase 13).
- Configuração enxuta de observabilidade ou expansão do node pool, conforme a
  medição de memória (fase 12).
- Migração para balanceador gerenciado, se e quando a fragilidade de IP do nó
  justificar (substitui parcialmente o ADR-0009).
- Adoção de operador de banco de dados no lugar do StatefulSet cru
  (substituiria o ADR-0007).
- Extração da migração de schema da inicialização do serviço, pré-requisito para
  mais de uma réplica.

## Fases

A numeração canônica das fases é a de [`prd/plataforma-devops.md`](prd/plataforma-devops.md),
e é ela que os ADRs e os critérios de validação referenciam.
