# Nudge

Lista compartilhada de lembretes — e, principalmente, a **carga de trabalho** de
uma plataforma DevOps de portfólio. O aplicativo não é o produto: o entregável é
a plataforma em volta dele (verificação automatizada, artefato imutável,
Kubernetes, GitOps, observabilidade e continuidade de dados).

Por isso ele é deliberadamente mínimo: um serviço, HTML renderizado no servidor,
sem autenticação e sem usuários ([ADR-0010](specs/adr/0010-servico-unico-sem-autenticacao.md)),
com escopo funcional congelado ([ADR-0004](specs/adr/0004-congelar-escopo-funcional.md)).

- **O quê e por quê:** [`specs/prd/`](specs/prd)
- **Como:** [`specs/trd/`](specs/trd)
- **Decisões e o que cada uma custou:** [`specs/adr/`](specs/adr)

## Subir o ambiente local

Único pré-requisito: Docker com Compose. **Não é preciso Python nem uv na
máquina** — todos os comandos rodam em container.

```bash
cp .env.example .env
docker compose up
```

A página fica em <http://localhost:8000>. Do zero até a página usável: **52 s**
medidos com build sem cache de camada (limite do PRD: 2 minutos).

O banco sobe junto e as migrações são aplicadas na partida do serviço, antes de
ele atender.

## Comandos

```bash
make help        # lista os alvos
make up          # sobe app e banco (cria o .env se faltar)
make down        # derruba (mantém o volume) | make clean derruba e apaga
make check       # o que o CI exige: lint + tipos + testes
make test        # pytest com cobertura (piso de 70%)
make lint        # ruff format --check + ruff check
make typecheck   # mypy estrito
make fmt         # formata e aplica correções automáticas
make migrate     # alembic upgrade head
make revision m="mensagem"
make build       # imagem de execução com APP_VERSION/APP_COMMIT injetados
make lock        # regera o uv.lock
make files       # conta os arquivos de código (teto de 20, ADR-0010)
```

## Rotas

| rota | efeito |
|---|---|
| `GET /` | a lista, ordenada por vencimento crescente |
| `POST /reminders` | cria; 303 para `/`, ou 422 com a mensagem na própria página |
| `POST /reminders/{id}/toggle` | alterna concluído; 303 para `/`, ou 404 |
| `POST /reminders/{id}/delete` | apaga; 303 para `/`, ou 404 |
| `GET /healthz` | vivacidade — **nunca** toca o banco |
| `GET /readyz` | prontidão — verifica o banco |
| `GET /metrics` | exposição para o coletor Prometheus |
| `GET /version` | versão e commit do build em execução |

`/healthz`, `/readyz` e `/metrics` não são publicados pelo controlador de
entrada: o orquestrador sonda o pod direto e o coletor raspa por dentro do
cluster.

## O que este aplicativo deliberadamente não tem

Cortes por ADR, não omissões — não os reintroduza sem substituir o ADR:

- **Autenticação, usuários e dono de lembrete.** A lista é única e
  compartilhada. Em produção, a escrita fica atrás de autenticação básica no
  controlador de entrada, não no aplicativo (ADR-0010).
- **JavaScript de aplicação, empacotador, `package.json`.** Node não existe
  neste repositório: uma cadeia de ferramentas só (ADR-0010).
- **API em JSON, paginação, busca, edição de lembrete, notificação.** Fora de
  escopo por PRD; o fluxo é criar, concluir e apagar.

## Estado atual

Fase 2 de 13 concluída (numeração em [`specs/prd/plataforma-devops.md`](specs/prd/plataforma-devops.md)):
o aplicativo está completo e testado localmente. As fases seguintes constroem a
plataforma — CI, imagem publicada, Kubernetes, produção, GitOps,
observabilidade e continuidade.
