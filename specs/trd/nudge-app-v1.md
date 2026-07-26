# TRD: Nudge App v1

Deriva de `specs/prd/nudge-app-v1.md`.

## Changelog

- 2026-07-25 — versão inicial.
- 2026-07-25 — reescrito para serviço único com HTML no servidor e sem
  autenticação; removidos frontend em React, identidade, tabela de usuários e
  API em JSON; acesso a dados passa de assíncrono para síncrono (ADR-0010).
- 2026-07-25 — fase 2 implementada. Três acréscimos técnicos, e as medições:
  - **`APP_TIMEZONE` entra na configuração** (padrão `America/Sao_Paulo`). O
    campo `datetime-local` do formulário não carrega fuso e o ADR-0010 proíbe
    JavaScript de aplicação, então o fuso do navegador não tem como chegar ao
    servidor: entrada sem fuso passa a ser interpretada no fuso configurado, e
    a página exibe nele. Entrada ISO 8601 com offset explícito continua sendo
    respeitada como está. Fuso do visitante segue fora de escopo (PRD).
  - **Corpo acima de 16 KB é recusado com 413** por middleware, pelo
    `Content-Length` declarado.
  - **Identificador de rota que não é UUID responde 404**, não 422: para o
    predicado do PRD, "não é um lembrete que existe" é uma coisa só.
- 2026-07-25 — passada de apresentação, **sem mudança funcional**: nenhuma rota,
  predicado, dependência ou arquivo novo. Reescrita do `style.css` e marcação dos
  botões em `index.html`. Fica registrado que o ADR-0004 lista quatro motivos
  para mexer em `app/` e apresentação não é um deles; a mudança foi pedida
  explicitamente pelo dono e é reversível em dois arquivos. O que entrou:
  - esquema claro **e** escuro por `prefers-color-scheme`, no lugar de escuro
    fixo; contraste medido em todos os pares (mínimo 5,0:1, exigido 4,5:1);
  - ícones em SVG embutido no lugar dos caracteres `✓`/`○`, com `aria-label`
    que inclui o título do lembrete — antes todos os botões liam igual;
  - alvos de toque de 44 px, foco visível, `prefers-reduced-motion` respeitado;
  - nenhuma fonte externa: pilha do sistema mais monoespaçada nativa para data
    e identificador de build. A página continua sem buscar recurso de terceiro,
    e há teste garantindo isso;
  - vencimento exibido como `sáb, 01 ago 2026 · 09:30`, com as abreviações de
    dia e mês em português embutidas no código — o locale do container é `C` e
    não serve. O formato é **absoluto de propósito**: "hoje" ou "em 2 dias"
    dependeriam do instante da renderização, e a página passaria a mudar sem o
    dado mudar. O valor de máquina segue em UTC, no atributo `datetime` do
    elemento `<time>`.

  O campo de entrada continua sendo `datetime-local`: o formato que ele exibe é
  decidido pelo navegador do visitante, e sem JavaScript (ADR-0010) não há como
  influenciá-lo.
- 2026-07-25 — cabeçalho enxugado (some a frase de apresentação, o nome ganha
  marca e linha de base) e **favicon próprio em `app/static/favicon.svg`**,
  declarado no `<head>`. O favicon não é enfeite: sem a declaração, o navegador
  pede `/favicon.ico` na raiz, recebe 404, e cada visita injeta erro no log e na
  métrica por rota — ruído que apareceria como taxa de erro no painel da fase
  12. Arquivos de código seguem em 13; o favicon é ativo, como o CSS.

## Escopo + NFRs

Recorte técnico: **um** serviço em container que renderiza HTML e fala com um
banco relacional. Configurado exclusivamente por variável de ambiente.

> Números derivados do contexto conhecido — um nó de 2 vCPU e 4 GB, tráfego de
> demonstração, escopo congelado (ADR-0004) — e não de medição prévia. Alvos a
> confirmar na fase 2 da plataforma (medição local) e revalidar na fase 6
> (medição em produção).

**Desempenho** (medido no cluster, excluindo latência de rede do cliente)

- Renderização da lista: p95 < 300 ms com até 500 lembretes na tabela.
- Escrita (criar, concluir, apagar): p95 < 300 ms.
- Partida, da criação do processo até responder prontidão: < 20 s, incluindo
  migrações pendentes.

**Recurso** (regime normal, dentro do teto de 650 MB do PRD)

- Aplicação: ≤ 250 MB de memória; requisição de 100m de CPU, limite de 500m.
- Banco: ≤ 400 MB; requisição de 100m de CPU, limite de 500m.

**Artefato**

- Imagem única < 250 MB. Não há segunda imagem.

**Segurança**

- Sem autenticação no aplicativo (ADR-0010). Em produção, **as rotas de escrita
  ficam atrás de autenticação básica no controlador de entrada**, e o
  controlador aplica 60 requisições por IP por minuto. Especificado em
  `specs/trd/plataforma-devops.md`.
- Credencial do banco vem de variável de ambiente, sem valor padrão: sua
  ausência impede a partida do processo.
- Título limitado a 200 caracteres; corpo de requisição limitado a 16 KB.
- Templates com escape automático ligado — a entrada é exibida de volta na
  página, então injeção de HTML é a superfície de ataque real deste aplicativo.
- Processo roda como usuário sem privilégio; sistema de arquivos raiz somente
  para leitura.

## Arquitetura + Contratos

### Componentes e fluxo

```
                    ┌──────────────────────────┐
   navegador ─────► │  controlador de entrada  │  TLS + autenticação básica
                    └────────────┬─────────────┘  nas rotas de escrita
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  nudge (FastAPI+Jinja2)  │  1 imagem, 1 Deployment
                    └────────────┬─────────────┘
                                 │ TCP 5432
                                 ▼
                    ┌──────────────────────────┐
                    │       PostgreSQL         │  StatefulSet + PVC
                    └──────────────────────────┘
```

Um serviço, um domínio, nenhum roteamento por prefixo. O processo renderiza a
página e fala com o banco; não há chamada entre serviços, não há CORS, não há
configuração em tempo de compilação.

Migrações são aplicadas na partida, antes de o processo aceitar requisição.

### Endpoints / Interfaces

Formulários HTML: escrita por POST seguido de redirecionamento 303 para a lista
(padrão *post/redirect/get*, que evita reenvio ao recarregar). Não há API em
JSON — nada além do navegador consome estas rotas.

```
GET    /                        lista em HTML, ordenada por due_at asc
POST   /reminders               campos: title, due_at
                                -> 303 para /   | 422 re-renderiza com erro
POST   /reminders/{id}/toggle   -> 303 para /   | 404
POST   /reminders/{id}/delete   -> 303 para /   | 404

GET    /healthz                 -> 200 {status, version, commit}
                                   NÃO toca o banco
GET    /readyz                  -> 200 | 503    verifica o banco
GET    /metrics                 -> exposição para o coletor
GET    /version                 -> 200 {version, commit}
```

`/healthz`, `/readyz` e `/metrics` não são publicados pelo controlador de
entrada: o orquestrador sonda o pod diretamente e o coletor raspa por dentro do
cluster.

`due_at` é convertido para UTC na borda e a página reconverte para exibição.
Entrada com offset explícito é respeitada; entrada sem offset — o que o campo
`datetime-local` produz — é interpretada em `APP_TIMEZONE`.

Corpo de requisição acima de 16 KB é recusado com 413 antes de chegar à rota.

### Modelo de dados

Tabela `reminders` — a única tabela do sistema.

| campo      | tipo         | obs                                          |
|------------|--------------|----------------------------------------------|
| id         | uuid         | chave primária, gerada na aplicação          |
| title      | varchar(200) | não nulo, não vazio após remover espaços     |
| due_at     | timestamptz  | não nulo, UTC                                |
| completed  | boolean      | não nulo, padrão falso                       |
| created_at | timestamptz  | não nulo, UTC                                |

Índice em `due_at`, que atende diretamente a consulta da lista.

Não há tabela de usuários e não há coluna de dono (ADR-0010).

## Stack + Validação

### Dependências

Versões abaixo são o piso alvo; a exata fica no arquivo de travamento. Nenhuma
imagem usa tag móvel. **Uma única cadeia de ferramentas** — Node não existe
neste repositório.

| item                     | escolha                                        |
|--------------------------|------------------------------------------------|
| linguagem                | Python 3.13                                    |
| gerência de dependência  | uv, com arquivo de travamento versionado       |
| framework HTTP           | FastAPI, servido por Uvicorn                   |
| renderização             | Jinja2, com escape automático                  |
| estilo                   | um arquivo CSS estático servido pelo próprio app |
| acesso a dados           | SQLAlchemy 2.x **síncrono** + psycopg          |
| migração                 | Alembic                                        |
| configuração             | pydantic-settings                              |
| métricas                 | instrumentador Prometheus para FastAPI         |
| análise estática         | Ruff (formatação e regras), mypy               |
| teste                    | pytest, pytest-cov, httpx                      |
| banco                    | PostgreSQL 17, major fixado (ADR-0007)         |

Modo síncrono é deliberado: um aplicativo que renderiza página não ganha nada
com assincronia, e o modo síncrono tem menos armadilhas. Registrado em ADR-0010
para que não seja revertido por hábito.

### Configuração

| variável          | obs                                        |
|-------------------|--------------------------------------------|
| `DATABASE_URL`    | obrigatória, sem padrão                    |
| `LOG_LEVEL`       | padrão `INFO`                              |
| `APP_TIMEZONE`    | padrão `America/Sao_Paulo`: fuso de interpretação da entrada sem offset e de exibição na página |
| `APP_VERSION`     | injetada no build: versão semântica         |
| `APP_COMMIT`      | injetada no build: commit de origem         |

`APP_VERSION` e `APP_COMMIT` entram como argumento de build e são lidos do
ambiente em execução, aparecendo em `/healthz`, `/version` e no rodapé da
página. Com o código congelado, são o único sinal observável de que um deploy
aconteceu.

### Critérios de validação

Medições registradas na fase 2 (2026-07-25), em WSL2 com Docker 29.6.

- [x] Todo predicado do PRD tem teste automatizado, e a suíte roda com um
      comando (`make test`): 25 testes.
- [x] Cobertura de linhas ≥ 70% — medida: **98%**. Piso mínimo, não medida de
      qualidade: o que protege de regressão é a cobertura dos predicados.
- [x] Contagem de arquivos de código ≤ 20, medida e registrada — **13**
      (`make files`): 7 módulos Python, 2 templates, 1 CSS, `env.py`,
      `script.py.mako` e 1 migração. Testes fora da conta, em `tests/`.
- [x] Teste de ida e volta de fuso: instante enviado em fuso não-UTC é lido de
      volta como o mesmo instante absoluto (09:30 em −03:00 → 12:30 UTC).
- [x] Teste confirma que título com marcação HTML é exibido escapado, não
      interpretado.
- [x] Teste confirma que `/healthz` responde 200 com o banco derrubado, e que
      `/readyz` responde 503 na mesma condição. Confirmado também com o banco
      parado de verdade no Compose: contador de reinício do container do
      aplicativo permaneceu em 0, e `/readyz` voltou a 200 sozinho.
- [x] Migração aplicada de banco vazio até a versão corrente, e revertida um
      passo, sem erro — contra um banco descartável, não o da suíte.
- [x] Índice de `due_at` confirmado em uso pelo plano de consulta da lista
      (`EXPLAIN` com 500 linhas e `enable_seqscan = off`: `ix_reminders_due_at`).
- [x] Partida com `DATABASE_URL` ausente falha imediatamente, com mensagem
      explícita ("DATABASE_URL é obrigatória e não tem valor padrão").
- [x] Tamanho da imagem medido e dentro do limite — **67,9 MB** (limite 250 MB);
      processo confirmado sem privilégio (uid 10001) e a imagem sobe com o
      sistema de arquivos raiz somente para leitura.
- [x] `docker compose up` a partir do clone entrega a página usável em menos de
      2 minutos — **52 s** com build sem cache de camada, 9 s com cache.
- [ ] Percentis medidos sob o perfil de carga da fase 11 da plataforma e
      comparados aos alvos desta seção.

Ainda **não** verificados nesta fase, e por quê:

- Varredura de segredo no repositório: a ferramenta (Trivy) entra na fase 9; o
  invariante é verificado sobre o histórico completo na fase 13.
- Percentis de latência e consumo de memória: os alvos da seção de NFR seguem
  derivados, não medidos. Medição local na plataforma e revalidação em produção
  na fase 6.

## Riscos e mitigação

- **Escopo da v1 fica incompleto e o congelamento (ADR-0004) o torna
  permanente** → o PRD é o gate: nenhuma fase avança com predicado sem teste.
- **Suíte pequena torna a cobertura fácil demais para significar algo** →
  consequência assumida em ADR-0010; a cobertura é piso mínimo, não medida de
  qualidade. O que protege de regressão é a cobertura *dos predicados*, não o
  percentual.
- **Lista compartilhada e pública é vandalizada** → autenticação básica no
  controlador de entrada nas rotas de escrita. Como a defesa vive fora do
  aplicativo, um erro de configuração de entrada expõe a escrita sem segunda
  linha; a validação da fase 6 verifica isso explicitamente.
- **Entrada do visitante é reexibida na página: injeção de HTML** → escape
  automático do Jinja2 nunca desligado, e teste cobrindo o caso.
- **Migração na partida quebra se o serviço for escalado** → registrado em
  ADR-0007; escalar exige extrair a migração para um passo próprio.
- **Aplicação e banco estouram o teto de 650 MB** → limites declarados por
  container e memória medida antes de a fase 12 somar a pilha de
  observabilidade.
- **Sem paginação, a lista degrada acima do volume previsto** → alvo de p95
  especificado com 500 lembretes; acima disso o comportamento é explicitamente
  não suportado.
- **`/healthz` acabar dependendo do banco por descuido numa refatoração** →
  é invariante do PRD e tem teste dedicado; a consequência seria reinício em
  laço durante qualquer indisponibilidade do banco.
