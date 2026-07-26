# ADR-0010: Reduzir o aplicativo a um serviço único, com HTML no servidor e sem autenticação

## Status

Substitui ADR-0002 e ADR-0003 — 2026-07-25

## Contexto

A primeira especificação do aplicativo previa dois serviços (aplicação de página
única em React/TypeScript e API em FastAPI), identidade própria com JWT e
Argon2, tabela de usuários e isolamento de dados por dono. Somava 20 predicados
de produto e cerca de 1.800 linhas de especificação.

O dono do projeto apontou que isso passou longe do que queria, e deu como
referência o `KubeDev/kube-news` — o aplicativo usado para ensinar Docker e
Kubernetes. Inspecionado, ele é:

- um serviço só, Express renderizando HTML com EJS, sem aplicação de página
  única e sem build de frontend;
- sem autenticação: uma lista compartilhada de posts, sem usuário e sem token;
- entre 10 e 15 arquivos de código;
- sem Dockerfile e sem manifestos no repositório — eles são o exercício, e o
  aplicativo é fixture;
- com exatamente dois pontos de contato com a plataforma: sondas de saúde e
  prontidão, e um endpoint de métricas.

A conclusão que importa: o valor daquele repositório como base de ensino não
está na linguagem, está na **forma**. Um container de aplicação e um banco, com
sondas e métricas desde o primeiro dia, e nada mais competindo por atenção.

Medido contra o objetivo declarado do projeto, o escopo anterior era peso morto:
autenticação, isolamento por dono e um segundo serviço com build próprio não
ensinam nada sobre Kubernetes, e consumiriam a maior parte do tempo antes da
primeira fase de infraestrutura.

A decisão de manter o arco de 13 fases da plataforma **não muda**. O que encolhe
é exclusivamente o aplicativo.

## Alternativas consideradas

- **Manter dois serviços, cortando só a autenticação** — preservaria mais
  superfície de Kubernetes para demonstrar (dois Deployments, duas imagens,
  roteamento por prefixo). Descartado: mantém duas cadeias de ferramentas, dois
  ecossistemas de dependência e um build de frontend, que é justamente o custo
  que o dono classificou como longe demais.
- **Manter React compilado dentro da mesma imagem**, servido como conteúdo
  estático pelo FastAPI — preservaria TypeScript no portfólio com um container
  só. Descartado por escolha do dono: ainda exige Node, `package.json` e um
  estágio de build, e some com a simplicidade que a referência tem.
- **Manter autenticação com escopo mínimo** (ADR-0003) — descartado porque é o
  maior bloco de código do projeto e o item que mais contradiz "algo mais
  simples". A referência não tem autenticação nenhuma.
- **Node/Express, copiando a referência literalmente** — descartado: a
  preferência de linguagem do dono é Python, e a forma é o que importa, não a
  linguagem.

## Decisão

O aplicativo passa a ser **um único serviço**:

- FastAPI renderizando HTML com Jinja2. Formulários HTML com POST e
  redirecionamento; nenhum JavaScript de aplicação, nenhum empacotador, nenhum
  `package.json` no repositório.
- **Sem autenticação e sem usuários.** Uma lista única e compartilhada de
  lembretes. A tabela de usuários deixa de existir, e com ela o isolamento por
  dono.
- Fluxo mínimo: criar, listar, marcar concluído, apagar. Alterar um lembrete
  existente fica fora de escopo.
- Acesso a dados com SQLAlchemy 2 em modo **síncrono** com psycopg. Sem
  assincronia: não há ganho num aplicativo que renderiza página, e o modo
  síncrono tem menos armadilhas.
- Persistem os quatro pontos de contato com a plataforma: `/healthz`, `/readyz`,
  `/metrics` e o identificador do build exposto na página.
- **A escrita em produção é protegida por autenticação básica no controlador de
  entrada**, não pelo aplicativo. Sem isso, uma lista compartilhada e pública
  fica aberta a qualquer visitante — e é uma demonstração de portfólio.

Limite explícito, na forma da referência: o aplicativo cabe em **no máximo 20
arquivos de código**. Passar disso é sinal de que o escopo voltou a crescer.

## Consequências

+ Uma cadeia de ferramentas só. Node sai inteiramente do repositório: um
  ecossistema de dependência, um conjunto de análise estática, um Dockerfile,
  uma imagem.
+ Um Deployment e um Service em vez de dois, e nenhum roteamento por prefixo no
  controlador de entrada — a parte de Kubernetes fica legível, que era o
  objetivo.
+ Sem build de frontend, some o problema de configuração em tempo de compilação
  e a possibilidade de divergência entre imagem e ambiente.
+ A fase de aplicação passa de semanas para horas, e a primeira fase de
  infraestrutura chega muito antes.
+ Sem autenticação, o teste de carga e o teste ponta a ponta ficam triviais de
  escrever: não há sessão para semear nem token para renovar.
- **TypeScript e React saem do portfólio.** O repositório deixa de demonstrar
  qualquer competência de frontend. Consequência assumida: o portfólio é de
  DevOps.
- **Qualquer visitante escreve na lista.** A mitigação vive fora do aplicativo,
  no controlador de entrada, o que significa que uma configuração errada de
  entrada expõe os dados diretamente — sem segunda linha de defesa no código.
- Duas demonstrações somem: isolamento de dados por usuário e um segundo serviço
  independente no cluster.
- A superfície de teste fica pequena. Como o escopo também está congelado
  (ADR-0004), a suíte será modesta para sempre, e cobertura alta será fácil
  demais para significar muita coisa.
- Renderização no servidor acopla apresentação e dados no mesmo processo:
  mudança de página exige novo deploy do serviço inteiro.

## Efeito sobre os outros ADRs

- **ADR-0002 e ADR-0003** — substituídos por este.
- **ADR-0004 (congelar escopo)** — permanece aceito, e o congelamento vale
  agora sobre um escopo menor. Duas premissas dele caem: "dois serviços
  independentes" e "isolamento por usuário" deixam de existir como demonstração.
  A decisão em si não muda, então o ADR não é substituído.
- **ADR-0007 (Postgres como StatefulSet)** — inalterado. O banco continua sendo
  a única carga com estado, e agora é a única companhia do aplicativo no
  cluster.
- **ADR-0005, 0006, 0008, 0009** — inalterados. Provedor, ordem das fases,
  cluster local e forma de exposição não dependem da forma do aplicativo.
- **ADR-0001 (monorepo)** — decisão inalterada. O repositório passa a ter um
  diretório de aplicação em vez de dois, o que só reforça a escolha; suas
  consequências sobre verificação de dois componentes deixam de se aplicar.
