# Nudge

## Visão geral

Aplicativo web de lembretes usado como **carga de trabalho** de uma plataforma
DevOps de portfólio. Leia isto antes de qualquer coisa: **o aplicativo não é o
produto**. O entregável é a plataforma em volta dele — verificação automatizada,
artefato imutável, Kubernetes, convergência via GitOps, observabilidade e
continuidade de dados.

Duas consequências não-óbvias, ambas por ADR:

- **O escopo funcional está congelado** (`specs/adr/0004-congelar-escopo-funcional.md`).
  Feature nova de produto é mudança de decisão arquitetural, não tarefa.
- **O app é um serviço só, HTML renderizado no servidor, sem autenticação e sem
  usuários** (`specs/adr/0010-servico-unico-sem-autenticacao.md`), na forma do
  `KubeDev/kube-news`. Ele cabe em **no máximo 20 arquivos de código** — esse
  limite é o guarda-corpo contra o escopo voltar a crescer.

Os dados são fictícios e de demonstração. Não há usuário real, não há
compliance, e a produção pode ser destruída e recriada de propósito.

## Stack tecnológica

Fixa por ADR — **não substituir sem pedir**:

| camada | escolha | ADR |
|---|---|---|
| aplicação | Python 3.13, uv, FastAPI, **Jinja2** (HTML no servidor), Alembic, pydantic-settings | 0010 |
| acesso a dados | SQLAlchemy 2 **síncrono** + psycopg | 0010 |
| dados | PostgreSQL 17, StatefulSet + PVC no cluster | 0007 |
| métricas | instrumentador Prometheus para FastAPI | 0010 |
| análise estática | Ruff + mypy. **Só isso** — não há Node no repositório | 0010 |
| manifestos | Kustomize (base + overlays), **não Helm** | — |
| cluster | Kubernetes gerenciado na DigitalOcean (1 nó, 2 vCPU / 4 GB); kind local | 0005, 0008 |
| infraestrutura | Terraform | 0005 |
| automação | GitHub Actions; imagens no GHCR | 0005 |

Três coisas que é fácil reverter por hábito e **não devem ser revertidas**:

- **Nada de React, Vite, TypeScript, `package.json` ou npm.** O ADR-0002 previa
  isso e foi substituído. Node não existe neste repositório, e é isso que mantém
  uma cadeia de ferramentas só.
- **Nada de autenticação, JWT, hash de senha ou tabela de usuários.** O ADR-0003
  previa isso e foi substituído. A lista é compartilhada.
- **SQLAlchemy síncrono, não async.** Um app que renderiza página não ganha nada
  com assincronia.

## Estrutura de diretórios

O que existe hoje é a fase 2. O resto é o layout definido em
`specs/trd/plataforma-devops.md` e deve ser criado com esses nomes:

```
specs/          PRD, TRD e ADRs — fonte da verdade (existe)
app/            a aplicação inteira: FastAPI + Jinja2, uma imagem (existe)
  config.py     configuração por ambiente (pydantic-settings)
  db.py         engine, sessão por requisição, sonda do banco
  models.py     a única tabela
  timeutil.py   fronteira de fuso: entra e sai em UTC
  routes.py     as rotas de página
  main.py       composição, sondas, métricas, migração na partida
  templates/    base.html + index.html (escape automático sempre ligado)
  static/       um CSS, servido pelo próprio app
  migrations/   Alembic
tests/          suíte contra os predicados do PRD (existe)
Dockerfile      multi-estágio: dev (verificação) e runtime (execução) (existe)
compose.yaml    ambiente de desenvolvimento do app; NÃO valida manifesto (existe)
Makefile        todos os comandos, sempre em container (existe)
k8s/base/       recursos comuns aos dois ambientes
k8s/overlays/local/   sobreposição do cluster kind
k8s/overlays/prod/    sobreposição de produção — único caminho observado pelo
                      reconciliador GitOps (ADR-0001)
infra/          Terraform: cluster, node pool, DNS, firewall, volume
```

Contagem atual: **13 de 20** arquivos de código no app (`make files`).

## Modelo de domínio

**Uma tabela**: `reminders` (id, title ≤ 200, due_at, completed, created_at).
Não há tabela de usuários e não há coluna de dono. Contratos em
`specs/trd/nudge-app-v1.md`.

Regras que valem em todo fluxo:

- A lista é **única e compartilhada**. Não existe conceito de usuário.
- Todo instante é gravado e devolvido em **UTC**; a conversão vive só em
  `app/timeutil.py`. Entrada sem offset (é o que o campo `datetime-local`
  manda, e sem JavaScript o fuso do navegador não chega ao servidor) é
  interpretada em `APP_TIMEZONE`; entrada com offset é respeitada.
- Escrita por `POST` seguido de redirecionamento 303 para a lista — nunca
  renderizar resposta direto de um POST, **nem no erro de validação**: a
  mensagem e o que foi digitado atravessam o redirecionamento no cookie
  `nudge_flash`, consumido na exibição seguinte.
- **Escape automático do Jinja2 nunca é desligado.** A entrada do visitante é
  reexibida na página; injeção de HTML é a superfície de ataque real deste app.
- `/healthz` **nunca** toca o banco (invariante do PRD). Se tocar, uma
  indisponibilidade do banco causa reinício em laço.

## Convenções de código

- Ruff (formatação e regras) + mypy. Sem `# type: ignore` sem comentário
  justificando.
- Configuração exclusivamente por variável de ambiente. **Segredo não tem valor
  padrão**: ausência de `DATABASE_URL` impede a partida do processo.
- Testes escritos contra os **predicados do PRD**, não contra a implementação.
  Cada predicado tem ao menos um teste.
- Imagens: build em múltiplos estágios, usuário sem privilégio, base fixada por
  digest, nunca tag móvel.
- `APP_VERSION` e `APP_COMMIT` entram como argumento de build e são expostos em
  `/healthz`, `/version` e no rodapé da página. **Não remover**: com o código
  congelado, é o único sinal observável de que um deploy aconteceu.

## Comandos

**Nada roda no host.** Não há Python nem uv instalados nesta máquina — todos os
comandos passam por Docker, e é isso que faz o ambiente ser o mesmo aqui e no
CI. Não sugira `pip install`, `python -m pytest` nem `uv run` direto.

| comando | efeito |
|---|---|
| `make check` | o portão antes de concluir tarefa: `lint` + `typecheck` + `test` |
| `make test` | pytest com cobertura (piso 70%); sobe o banco se preciso |
| `make lint` | `ruff format --check` + `ruff check` |
| `make typecheck` | mypy estrito |
| `make fmt` | formata e aplica correção automática |
| `make up` / `down` / `clean` | ambiente local (cria o `.env` se faltar) |
| `make migrate` / `revision m="..."` | Alembic |
| `make build` | imagem de execução com `APP_VERSION`/`APP_COMMIT` injetados |
| `make lock` | regera o `uv.lock` (única coisa que usa a imagem do uv) |
| `make files` | conta os arquivos de código do app (teto de 20) |

Detalhes que economizam tempo:

- A suíte exige **PostgreSQL de verdade** (`timestamptz` e `uuid` são o que
  precisa ser exercitado). Ela cria o banco de teste sozinha, a partir de
  `TEST_DATABASE_URL`.
- `pyproject.toml` tem `package = false`: o código é importado por `PYTHONPATH`,
  não instalado. Dependência nova exige `make lock` e commit do `uv.lock` — o
  build usa `uv sync --locked` e **reprova** com lock desatualizado, de
  propósito. `make lock` é o único comando que não roda no container de dev: o
  `uv.lock` de lá é a cópia assada no build, não o arquivo versionado.
- O ambiente virtual vive em `/opt/venv`, fora de `/app`, para que o bind mount
  de desenvolvimento não esconda as dependências.

## Specs (Spec Driven Development)

As specs são a fonte da verdade deste projeto. Leia antes de implementar:

- `specs/prd/nudge-app-v1.md` / `specs/prd/plataforma-devops.md` — o quê e o
  porquê, com predicados verificáveis
- `specs/trd/nudge-app-v1.md` / `specs/trd/plataforma-devops.md` — o como:
  arquitetura, endpoints, modelo de dados, NFRs, validação por fase
- `specs/adr/` — as decisões e o que cada uma tornou mais difícil. **0002 e 0003
  estão substituídos pelo 0010** — leia o 0010 antes de seguir qualquer um dos
  dois
- `specs/README.md` — índice e ADRs ainda previstos

**Antes de codar:** leia o PRD e o TRD da feature e os ADRs referenciados. Se
não existir spec para o que foi pedido, escreva a spec primeiro (skill
`spec-driven-dev`) e confirme com o usuário antes de implementar.

**Depois de mudar comportamento:** atualize a spec na mesma tarefa — TRD com
entrada no changelog para mudança técnica, PRD para mudança de escopo, novo ADR
para decisão arquitetural. **ADRs são imutáveis**: decisão revista vira um ADR
novo que substitui o anterior; o antigo só recebe a marca de substituído, nunca
é editado nem apagado.

**Se código e spec divergirem:** pare e reporte. Não conserte o código para
bater com a spec nem reescreva a spec para bater com o código sem confirmação.

A numeração canônica das fases é a de `specs/prd/plataforma-devops.md` (1 a 13).

## Git

- Branch padrão e de produção: `main`, publicada em
  `github.com/GabrielWillers/nudge`. **Não commitar nem mergear direto em
  `main`** — toda mudança nasce em branch própria e entra por PR. Exceção:
  hotfix com pedido explícito.
- Commits só quando o usuário pedir. Se estiver em `main`, criar branch antes.
- Conventional Commits no imperativo: `feat:`, `fix:`, `docs:`, `test:`,
  `refactor:`, `chore:`, `ci:`, com escopo opcional (`feat(app): ...`).
- **Release é tag semver** `vX.Y.Z` em `main`. Rollback é declarar a versão
  anterior na sobreposição de produção — nunca reconstruir imagem.
- **Nunca commitar segredo.** O invariante do PRD é "nenhum segredo em texto
  claro em nenhum commit do histórico" — um segredo commitado e depois removido
  já violou o invariante e exige reescrever o histórico e rotacionar o valor.
  Manter `.env.example` e `*.tfvars.example` atualizados.
- PR só integra com CI verde. Não desabilitar check para passar.
- Usar `gh` para operações no GitHub. Flags interativas (`rebase -i`, `add -i`)
  não funcionam aqui.
- Trailer obrigatório em commits gerados por agente:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## Regras de ouro

1. **Toda mudança de comportamento vai parar na spec.** PRD/TRD atualizado (com
   changelog) ou ADR aberto **na mesma tarefa**. Tarefa com spec desatualizada
   não está concluída.
2. **Não implemente feature sem spec.** Sem PRD/TRD para o pedido, escreva a
   spec e confirme antes de codar.
3. **Divergência entre código e spec é achado, não detalhe.** Reporte; não
   escolha um lado sozinho.
4. **Feature nova de produto no app está proibida por ADR-0004.** Só quatro
   motivos justificam mexer em `app/`: correção de defeito coberto por
   predicado, atualização de dependência, instrumentação exigida pela
   plataforma, ou ajuste para rodar sob a plataforma. Qualquer outra coisa exige
   um ADR que substitua o 0004 — pare e diga isso ao usuário.
5. **Não reintroduza o que o ADR-0010 removeu.** Frontend com build, TypeScript,
   autenticação, tabela de usuários, API em JSON: tudo isso foi cortado de
   propósito. Se a tarefa parecer exigir um deles, pare e diga.
6. **Pare e pergunte antes de** trocar item da stack, mexer em schema ou
   contrato de rota, afrouxar regra de segurança, criar superfície pública nova,
   ou provisionar recurso pago no provedor de nuvem.
7. **Validação sempre no servidor**, nunca só no formulário. Queries sempre
   parametrizadas. A proteção de escrita em produção vive no controlador de
   entrada (auth básica) — não a remova achando que o app se protege.
8. **Segredo só via ambiente**, jamais em manifesto, código ou log. Secret do
   Kubernetes é codificação, não cifra — não satisfaz o invariante sozinho.
9. **Lint, formatação, tipos e testes limpos** antes de concluir qualquer
   tarefa. Não marcar tarefa como pronta com verificação vermelha.
10. **Não introduzir biblioteca fora da stack** sem justificar e pedir
    confirmação. O nó tem 4 GB para app, banco, observabilidade e reconciliador.
11. **Reporte fielmente.** Teste falhou, diga com a saída. Passo pulado, diga
    qual. Não afirme que algo funciona sem ter rodado.

## Pendências conhecidas

- Domínio público ainda não registrado — bloqueia a fase 6.
- Números de NFR nos TRDs: a fase 2 mediu tamanho de imagem (67,9 MB) e partida
  do ambiente local (52 s). **Latência por percentil e consumo de memória
  continuam derivados, não medidos** — medição real só na fase 11 (carga) e
  revalidação na 6.
- Migração de schema roda na inicialização do serviço. Isso **quebra com mais de
  uma réplica** (ADR-0007): escalar exige extrair a migração antes.
- Proteção de escrita e limitação de taxa são responsabilidade do controlador
  de entrada, **não do app** — consequência do ADR-0010. Sem elas, a lista
  compartilhada fica aberta a qualquer visitante.
- IP do nó não é estável e o DNS precisa ser reconciliado a cada recriação
  (ADR-0009): é o risco central da fase 8.
