# Nudge

Uma plataforma DevOps construída do zero, com uma aplicação pequena servindo de
carga de trabalho. **O aplicativo não é o produto** — o produto é tudo em volta
dele: verificação automatizada, artefato imutável, Kubernetes, convergência por
GitOps, observabilidade e continuidade de dados.

O repositório é o registro desse processo. Cada decisão difícil de reverter está
escrita em um ADR, com o que ela custou; cada fase tem critérios verificáveis
antes de ser considerada pronta.

---

## Por que existe

O padrão em repositório de portfólio de DevOps é o inverso do que deveria ser:
um aplicativo com muitas features e, no último commit, um arquivo de CI que roda
um lint. Quem avalia não consegue distinguir isso de um pipeline que funciona,
porque nada no histórico mostra o ciclo em operação — não houve ciclo, houve um
arquivo adicionado no fim.

Aqui a ordem é invertida de propósito. A carga de trabalho nasce pequena e
**congela na v1** ([ADR-0004](specs/adr/0004-congelar-escopo-funcional.md)), e o
histórico passa a registrar a plataforma amadurecendo em cima dela.

Consequência direta: o aplicativo tem 528 linhas de Python em 13 arquivos, e vai
continuar tendo. Isso não é falta de fôlego, é o contrato.

---

## O aplicativo

Uma lista compartilhada de lembretes: criar, listar, marcar como concluído,
apagar. Um serviço, HTML renderizado no servidor, sem autenticação e sem
usuários ([ADR-0010](specs/adr/0010-servico-unico-sem-autenticacao.md)).

```
                    ┌──────────────────────────┐
   navegador ─────► │  controlador de entrada  │  TLS + auth básica na escrita
                    └────────────┬─────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │  nudge (FastAPI+Jinja2)  │  1 imagem, 1 Deployment
                    └────────────┬─────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │       PostgreSQL 17      │  StatefulSet + PVC
                    └──────────────────────────┘
```

Ele existe para exercitar o que a plataforma precisa saber operar: banco
relacional com migração de schema, volume persistente, segredo, sonda de saúde,
sonda de prontidão, métricas e identificador de build. Um "hello world" não
exercitaria nada disso.

| camada | escolha |
|---|---|
| aplicação | Python 3.13, FastAPI, Jinja2, uv |
| dados | SQLAlchemy 2 síncrono, psycopg, Alembic, PostgreSQL 17 |
| verificação | Ruff, mypy estrito, pytest |
| artefato | imagem multi-estágio, base fixada por digest, usuário sem privilégio |

Sem Node, sem empacotador, sem `package.json`: uma cadeia de ferramentas só.

---

## Estado

Numeração de [`specs/prd/plataforma-devops.md`](specs/prd/plataforma-devops.md).

| # | fase | estado |
|---|---|---|
| 1 | Fundação: repositório, specs, ambiente local | concluída |
| 2 | Aplicação v1 completa e testada localmente | concluída |
| 3 | Verificação mínima na proposta de mudança | próxima |
| 4 | Imagens publicadas no registro com identificador de build | |
| 5 | Aplicação rodando em cluster local (kind) | |
| 6 | Produção: cluster gerenciado, HTTPS, domínio | |
| 7 | Base comum e sobreposições por ambiente (Kustomize) | |
| 8 | Infraestrutura como código (Terraform) | |
| 9 | Pipeline completo: análise estática, cobertura, varredura | |
| 10 | Convergência automática por GitOps | |
| 11 | Qualidade sob execução: ponta a ponta e carga | |
| 12 | Observabilidade: métricas, painel e alerta | |
| 13 | Continuidade: segredo cifrado, backup e restauração | |

---

## Decisões

Estão todas em [`specs/adr/`](specs/adr), com contexto, alternativas descartadas
e consequências — inclusive as ruins. As que mais moldaram o resultado:

**[Reduzir a aplicação a um serviço só, sem autenticação](specs/adr/0010-servico-unico-sem-autenticacao.md)**
A primeira spec previa React + TypeScript no frontend, API separada, JWT e
tabela de usuários. Foi tudo cortado: não ensina nada sobre Kubernetes e
consumiria a maior parte do tempo antes da primeira fase de infraestrutura.
O preço, assumido: o repositório deixa de demonstrar frontend.

**[Congelar o escopo funcional](specs/adr/0004-congelar-escopo-funcional.md)**
Feature nova de produto passa a exigir um ADR que substitua a decisão. Sem isso,
o esforço migra para o aplicativo — que é o modo de falha que este projeto
existe para evitar.

**[PostgreSQL como StatefulSet dentro do cluster](specs/adr/0007-postgres-statefulset-no-cluster.md)**
Em vez de banco gerenciado. Exercita volume persistente, `StorageClass` e sonda
com dependência externa. Em troca, backup e restauração passam a ser problema
meu — e a fase 13 é condição de aceite da decisão, não item opcional.

**[Entrada HTTPS sem balanceador gerenciado](specs/adr/0009-entrada-https-sem-balanceador-gerenciado.md)**
Porta do nó e certificado por desafio de DNS, para caber no orçamento de US$ 30
por mês. O IP do nó não é estável: reconciliar o DNS a cada recriação vira o
risco central da fase 8.

**[Kubernetes antes do pipeline completo](specs/adr/0006-kubernetes-antes-do-ci.md)**
Contra a ordem habitual. Automatizar um deploy que ainda não foi feito à mão é
automatizar um processo que ninguém entende.

---

## O que já está medido

Números de execução real, não estimativa:

| | alvo | medido |
|---|---|---|
| testes cobrindo os predicados do PRD | todos | 31 testes |
| cobertura de linhas | ≥ 70% | 98% |
| arquivos de código no aplicativo | ≤ 20 | 13 |
| tamanho da imagem | < 250 MB | 67,9 MB |
| clone até a página no ar | < 2 min | 52 s |
| contraste da interface | ≥ 4,5:1 | ≥ 5,0:1 |

Com o banco parado de propósito: `/healthz` responde 200, `/readyz` responde
503, o container não reinicia em laço e volta sozinho quando o banco retorna.

---

## O que ainda não está provado

Manter esta lista honesta é parte do exercício:

- **Não há CI.** Os dois PRs mergeados até aqui passaram por verificação local
  (`make check`), não por checagem automatizada. Isso é a fase 3.
- **Nada rodou em cluster ainda** — nem local nem gerenciado.
- **Latência e consumo de memória são alvos derivados**, não medições. Só a
  fase 11, com teste de carga, transforma isso em número.
- **A varredura de segredo é manual** até a fase 9; o histórico completo só é
  verificado na 13.
- **Migração de schema roda na inicialização do serviço.** Correto com uma
  réplica, quebra com duas. Está registrado como dívida no ADR-0007.

---

## Como ler o repositório

```
specs/prd/     o quê e por quê, com predicados verificáveis
specs/trd/     o como: arquitetura, contratos, NFRs, critérios de validação
specs/adr/     as decisões e o que cada uma tornou mais difícil
app/           a aplicação inteira
tests/         um teste por predicado do PRD
```

As specs são maiores que o código, e isso é intencional: elas descrevem a
plataforma de 13 fases, não a lista de lembretes. Quem quiser entender o projeto
em cinco minutos deve ler
[`specs/prd/plataforma-devops.md`](specs/prd/plataforma-devops.md) e os ADRs;
o resto é consequência.

Para rodar: `cp .env.example .env && docker compose up`. Os demais comandos
estão no `Makefile` — nada roda direto na máquina, tudo passa por container.
