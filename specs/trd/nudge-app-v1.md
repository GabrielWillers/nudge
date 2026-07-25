# TRD: Nudge App v1

Deriva de `specs/prd/nudge-app-v1.md`.

## Changelog

- 2026-07-25 — versão inicial.

## Escopo + NFRs

Recorte técnico: dois serviços em container (API HTTP e conteúdo estático) e um
banco relacional, todos operáveis por um orquestrador de containers e
configurados exclusivamente por variável de ambiente.

> Os números abaixo são derivados do contexto conhecido — um nó de 2 vCPU e
> 4 GB, tráfego de demonstração, escopo funcional congelado (ADR-0004) — e não
> de medição prévia. São alvos a confirmar na fase 2 da plataforma (medição
> local) e revalidar na fase 6 (medição em produção), não requisitos de negócio.

**Desempenho** (medido dentro do cluster, excluindo latência de rede do cliente)

- Listagem de lembretes de um usuário: p95 < 300 ms com até 500 lembretes na
  tabela.
- Escrita de lembrete (criar, alterar, apagar): p95 < 300 ms.
- Autenticação: p95 < 800 ms. O limite é alto de propósito — a verificação de
  senha é deliberadamente custosa.
- Partida do backend, da criação do processo até responder prontidão: < 20 s,
  incluindo a aplicação de migrações pendentes.

**Recurso** (regime normal, somando ao teto de 1 GB da restrição do PRD)

- Backend: ≤ 300 MB de memória residente; requisição de 100m de CPU, limite de
  500m.
- Banco: ≤ 400 MB; requisição de 100m de CPU, limite de 500m.
- Frontend (servidor de conteúdo estático): ≤ 50 MB; requisição de 10m de CPU,
  limite de 100m.

**Artefato**

- Imagem do backend < 300 MB; imagem do frontend < 80 MB.
- Pacote JavaScript inicial < 300 KB comprimido.

**Segurança**

- Senha com hash Argon2id, parâmetros calibrados para custar entre 50 e 150 ms
  por verificação no nó de produção.
- Token de acesso JWT assinado em HS256, validade de 60 minutos, sem renovação
  (ADR-0003).
- Segredo de assinatura e credencial do banco vêm de variável de ambiente e não
  têm valor padrão no código: ausência de qualquer um deles impede a partida do
  processo.
- Título de lembrete limitado a 200 caracteres; corpo de requisição limitado a
  16 KB.
- **Limitação de taxa nas rotas de autenticação não é implementada no
  aplicativo.** Como o escopo do código está congelado e a aplicação fica
  publicamente exposta, ela é responsabilidade do controlador de entrada — 10
  tentativas por IP por minuto, especificado em `specs/trd/plataforma-devops.md`.
- Processo do container roda como usuário sem privilégio; sistema de arquivos
  raiz montado somente para leitura.

**Compatibilidade**

- Navegadores em versão corrente com suporte a ES2022. Sem suporte a navegador
  legado.

## Arquitetura + Contratos

### Componentes e fluxo

```
                    ┌──────────────────────────┐
   navegador ─────► │  controlador de entrada  │  (um domínio, TLS)
                    └────────┬─────────┬───────┘
                       /     │         │  /api
                             ▼         ▼
                    ┌────────────┐  ┌──────────────┐
                    │  frontend  │  │   backend    │
                    │  (estático)│  │  (API HTTP)  │
                    └────────────┘  └──────┬───────┘
                                           │ TCP 5432
                                           ▼
                                    ┌──────────────┐
                                    │  PostgreSQL  │
                                    └──────────────┘
```

Um único domínio serve os dois componentes: o frontend na raiz e a API sob
`/api` (ADR-0002). O frontend chama a API por caminho relativo, então não há URL
de API embutida no build nem requisição entre origens.

O frontend é conteúdo estático já compilado, servido por um servidor web dentro
da imagem. Ele não fala com o banco. Todo estado de servidor no cliente é cache
de requisição, invalidado por chave após escrita.

O backend não guarda estado em processo: autenticação é verificada pela
assinatura do token, sem consulta a armazenamento de sessão. Duas instâncias
seriam intercambiáveis do ponto de vista do tráfego — mas escalar exige antes
mover a migração para fora da inicialização (ADR-0007).

Migrações são aplicadas na partida do backend, antes de ele aceitar requisição.

### Endpoints / Interfaces

Todos sob o prefixo `/api`, exceto as sondas. Erro de validação responde 422 com
o campo inválido identificado. Toda resposta de erro segue um formato único
`{ "detail": ... }`.

```
POST   /api/auth/register   corpo {email, password} -> 201 {id, email}
                            409 e-mail já em uso | 422 validação
POST   /api/auth/login      corpo {email, password} -> 200 {access_token,
                            token_type, expires_in}
                            401 credencial inválida (mensagem única para
                            e-mail inexistente e senha errada) | 422
GET    /api/auth/me         -> 200 {id, email} | 401

GET    /api/reminders       -> 200 [reminder], ordenado por due_at asc | 401
POST   /api/reminders       corpo {title, due_at} -> 201 reminder | 401 | 422
GET    /api/reminders/{id}  -> 200 reminder | 401 | 404
PATCH  /api/reminders/{id}  corpo parcial {title?, due_at?, completed?}
                            -> 200 reminder | 401 | 404 | 422
DELETE /api/reminders/{id}  -> 204 | 401 | 404

GET    /api/version         -> 200 {version, commit}   (público, sem auth)
```

Sondas, servidas pelo backend e **não** publicadas pelo controlador de entrada:

```
GET    /healthz   -> 200 {status, version, commit}   não toca o banco
GET    /readyz    -> 200 | 503                       verifica o banco
GET    /metrics   -> exposição de métricas            (introduzido na fase 12
                                                       da plataforma)
```

Contratos de comportamento que valem para todas as rotas de lembrete:

- O dono é sempre derivado do token. `user_id` enviado pelo cliente é ignorado.
- Recurso de outro usuário responde 404, nunca 403 — a existência do
  identificador não é revelada.
- `due_at` é aceito em formato ISO 8601 com fuso e devolvido sempre em UTC com
  sufixo `Z`.

### Modelo de dados

Tabela `users`

| campo         | tipo        | obs                                        |
|---------------|-------------|--------------------------------------------|
| id            | uuid        | chave primária, gerada na aplicação        |
| email         | text        | não nulo, único, normalizado em minúsculas |
| password_hash | text        | não nulo, Argon2id; nunca serializado      |
| created_at    | timestamptz | não nulo, UTC                              |

Tabela `reminders`

| campo      | tipo         | obs                                             |
|------------|--------------|-------------------------------------------------|
| id         | uuid         | chave primária, gerada na aplicação             |
| user_id    | uuid         | não nulo, referencia `users.id`, cascata ao apagar |
| title      | varchar(200) | não nulo, não vazio após remover espaços        |
| due_at     | timestamptz  | não nulo, UTC                                   |
| completed  | boolean      | não nulo, padrão falso                          |
| created_at | timestamptz  | não nulo, UTC                                   |
| updated_at | timestamptz  | não nulo, UTC, atualizado a cada escrita        |

Índices: único em `users.email`; composto em `reminders (user_id, due_at)`, que
atende diretamente a consulta de listagem.

A unicidade de e-mail é garantida por índice no banco, não apenas por
verificação na aplicação — a verificação antecipada existe para dar mensagem de
erro, e a restrição do banco é a que sustenta a invariante sob concorrência.

Fuso horário: todo instante é gravado e devolvido em UTC. Conversão para o fuso
do leitor acontece exclusivamente na formatação do frontend.

## Stack + Validação

### Dependências

Versões abaixo são o piso alvo; a versão exata fica fixada em arquivo de
travamento no repositório. Nenhuma imagem usa tag móvel.

**Backend**

| item                     | escolha                                  |
|--------------------------|------------------------------------------|
| linguagem                | Python 3.13                              |
| gerência de dependência  | uv, com arquivo de travamento versionado |
| framework HTTP           | FastAPI, servido por Uvicorn             |
| acesso a dados           | SQLAlchemy 2.x em modo assíncrono + asyncpg |
| migração                 | Alembic                                  |
| validação e configuração | Pydantic 2 e pydantic-settings           |
| token                    | PyJWT                                    |
| hash de senha            | pwdlib com backend Argon2                |
| análise estática         | Ruff (formatação e regras), mypy         |
| teste                    | pytest, pytest-asyncio, pytest-cov, httpx |

Escolhas deliberadas de biblioteca: `PyJWT` e `pwdlib` no lugar de
`python-jose` e `passlib`, ambos sem manutenção ativa. Registrado aqui para que
a decisão não seja revertida por hábito.

**Frontend**

| item                | escolha                                       |
|---------------------|-----------------------------------------------|
| runtime de build    | Node 22 LTS                                   |
| linguagem           | TypeScript 5 em modo estrito                  |
| biblioteca de UI    | React 19                                      |
| empacotador         | Vite                                          |
| estado de servidor  | TanStack Query                                |
| navegação           | React Router                                  |
| estilo              | Tailwind CSS                                  |
| análise estática    | Biome (formatação e regras em uma ferramenta) |
| teste               | Vitest, Testing Library, MSW                  |
| serviço em produção | servidor de conteúdo estático em imagem enxuta |

**Dados**

PostgreSQL 17, versão major fixada explicitamente (ADR-0007).

### Configuração

Toda configuração por variável de ambiente, sem valor padrão para segredo:

| variável           | componente | obs                                   |
|--------------------|------------|---------------------------------------|
| `DATABASE_URL`     | backend    | obrigatória                            |
| `JWT_SECRET`       | backend    | obrigatória, sem padrão                |
| `JWT_TTL_MINUTES`  | backend    | padrão 60                              |
| `LOG_LEVEL`        | backend    | padrão `INFO`                          |
| `APP_VERSION`      | ambos      | injetada no build: versão semântica    |
| `APP_COMMIT`       | ambos      | injetada no build: commit de origem    |

`APP_VERSION` e `APP_COMMIT` entram como argumento de build da imagem. No
frontend são incorporados ao pacote em tempo de compilação; no backend são lidos
do ambiente em tempo de execução. Os dois componentes de uma mesma versão são
construídos do mesmo commit, portanto os valores coincidem — e o critério de
aceite do PRD verifica isso.

### Critérios de validação

- [ ] Todo predicado do PRD tem teste automatizado correspondente, e a suíte
      inteira roda com um comando.
- [ ] Cobertura de linhas do backend ≥ 70%, medida na execução da suíte.
- [ ] Isolamento por dono coberto por teste que autentica dois usuários
      distintos e confirma resposta 404 no acesso cruzado em leitura,
      alteração e exclusão.
- [ ] Teste confirma que credencial inválida por e-mail inexistente e por senha
      errada produzem resposta byte a byte idêntica.
- [ ] Teste de ida e volta de fuso horário: instante enviado em fuso não-UTC
      é lido de volta como o mesmo instante absoluto.
- [ ] Teste confirma que a serialização de usuário não contém `password_hash`
      em nenhuma rota.
- [ ] Migração aplicada de banco vazio até a versão corrente, e revertida um
      passo, sem erro.
- [ ] Índice composto confirmado em uso pelo plano de consulta da listagem.
- [ ] Partida com `JWT_SECRET` ausente falha imediatamente, com mensagem
      explícita, e não sobe servidor.
- [ ] `/readyz` responde 503 com o banco indisponível, verificado derrubando o
      banco no ambiente local.
- [ ] Tamanho das duas imagens medido e dentro do limite; processo confirmado
      rodando sem privilégio.
- [ ] `docker compose up` a partir do clone entrega interface usável em menos
      de 2 minutos.
- [ ] Percentis de latência medidos sob o perfil de carga da fase 11 da
      plataforma e comparados aos alvos desta seção.

## Riscos e mitigação

- **Escopo da v1 fica incompleto e o congelamento (ADR-0004) o torna
  permanente** → o PRD é o gate: nenhuma fase avança com predicado sem teste, e
  a revisão de aceite acontece antes da fase 3 da plataforma.
- **Suíte de testes fraca torna decorativo todo o pipeline** → cobertura mínima
  é critério de aceite, e a suíte é escrita contra os predicados, não contra a
  implementação.
- **Argon2 calibrado alto demais estoura o limite de CPU do nó e faz a
  autenticação expirar** → parâmetros calibrados por medição, não copiados de
  exemplo: primeiro na máquina de desenvolvimento (fase 2) e **revalidados no nó
  de produção na fase 6**, que é quando o hardware alvo passa a existir. O
  limite de 500m de CPU é verificado sob autenticação concorrente.
- **Sem limitação de taxa no aplicativo, a rota de autenticação fica exposta a
  força bruta** → limitação no controlador de entrada, especificada no TRD da
  plataforma. Enquanto ela não existir, a produção não deve ser divulgada
  publicamente.
- **Migração na partida quebra se o backend for escalado** → registrado em
  ADR-0007; escalar exige antes extrair a migração para um passo próprio.
- **Token sem revogação: vazamento dá acesso até expirar** → validade curta;
  consequência assumida em ADR-0003.
- **Aplicação e banco juntos estouram o teto de 1 GB do nó** → limites de
  recurso declarados por container e memória medida em regime normal antes de
  a fase 12 adicionar a pilha de observabilidade.
- **Sem paginação, a listagem degrada se o volume crescer além do previsto** →
  alvo de p95 especificado com 500 lembretes; acima disso o comportamento é
  explicitamente não suportado.
