# PRD: Nudge App v1

## Contexto

Uma plataforma de DevOps só se prova contra uma carga de trabalho real. Um
"hello world" não exercita banco de dados, migração de schema, volume
persistente, sonda de saúde nem métrica — e são essas as coisas que a
plataforma precisa demonstrar que sabe operar.

Nudge é o menor aplicativo que exercita todas elas: uma lista compartilhada de
lembretes, com o que fazer e até quando. Ele é o meio, não o fim. Seu escopo
funcional fecha na v1 e não cresce (ADR-0004), e sua forma é deliberadamente
mínima — um serviço, HTML renderizado no servidor, sem usuários e sem
autenticação (ADR-0010).

Hoje nada existe: nenhuma linha de código, nenhum dado, nenhum ambiente.

## Atores

- **Visitante** — qualquer pessoa com a URL. Consulta a lista e, quando
  autorizado pelo controlador de entrada, escreve nela. Não há conta nem sessão.
- **Orquestrador de containers** — sonda o serviço para decidir se a instância
  recebe tráfego e se precisa ser reiniciada.
- **Coletor de métricas** — raspa o endpoint de métricas periodicamente.
- **Suíte de testes automatizada** — exercita os predicados abaixo a cada
  proposta de mudança; como o escopo congela, é a única guardiã de regressão.
- **Avaliador técnico** — abre a aplicação publicada para confirmar que ela
  funciona e que a versão no ar é a que o repositório declara.

## Predicados

### Lembretes

- [x] Dado um título não vazio e um instante de vencimento válidos, quando o
      visitante submete o formulário de criação, então o lembrete passa a
      existir e aparece na lista.
- [x] Dados lembretes existentes, quando a lista é aberta, então todos aparecem
      ordenados por vencimento crescente.
- [x] Dado um lembrete não concluído, quando o visitante o marca como
      concluído, então a lista passa a exibi-lo como concluído; e marcá-lo de
      novo o devolve a não concluído.
- [x] Dado um lembrete existente, quando o visitante o apaga, então ele
      desaparece da lista e não volta ao recarregar.
- [x] Dado um título vazio, um título acima de 200 caracteres ou um vencimento
      em formato inválido, quando o formulário é submetido, então a operação é
      rejeitada com mensagem na própria página e nada é gravado.
- [x] Dado um instante de vencimento informado com fuso horário, quando é
      gravado e lido de volta, então representa o mesmo instante absoluto.
- [x] Dada nenhuma entrada na lista, quando a página é aberta, então há um
      estado vazio explícito, não uma tela em branco nem um erro.
- [x] Dado um identificador inexistente, quando se tenta concluir ou apagar,
      então a resposta é "não encontrado" e nada é gravado.

### Operabilidade

- [x] Dada a aplicação em execução, quando se consulta o endpoint de saúde,
      então responde sucesso e informa o identificador do build, **sem tocar o
      banco**.
- [x] Dada a aplicação sem conseguir alcançar o banco, quando o orquestrador
      consulta o endpoint de prontidão, então a resposta é falha.
- [x] Dada a aplicação em execução, quando o coletor raspa o endpoint de
      métricas, então há contagem de requisições, latência e erros por rota.
- [x] Dada uma versão implantada, quando a página é aberta, então o
      identificador do build está visível nela.
- [x] Dado o schema do banco em versão anterior, quando a aplicação sobe, então
      as migrações pendentes são aplicadas antes de ela atender.

## Invariantes

- A lista é única e compartilhada: nenhum lembrete tem dono, e não existe
  conceito de usuário no sistema.
- Todo instante gravado está em UTC.
- O endpoint de saúde nunca depende do banco — do contrário, uma
  indisponibilidade do banco provocaria reinício em laço.
- O identificador de build exposto corresponde ao código que está executando.
- Toda escrita passa por validação no servidor; nenhuma validação vive apenas
  no formulário.

## Restrições

- Escopo funcional congela ao fim da v1 (ADR-0004).
- Um serviço só, HTML renderizado no servidor. Sem aplicação de página única,
  sem empacotador, sem `package.json` no repositório (ADR-0010).
- Sem autenticação no aplicativo. A escrita em produção é protegida por
  autenticação básica no controlador de entrada (ADR-0010).
- Nenhum fluxo depende de entregar mensagem a um ser humano: não há envio de
  e-mail, push ou SMS em lugar nenhum.
- Título de lembrete máximo de 200 caracteres.
- Interface em português, língua única.
- Aplicação e banco dividem um nó de 4 GB com toda a plataforma: até 650 MB
  somados em regime normal.
- Sem paginação: volume de demonstração, dezenas de lembretes.
- **No máximo 20 arquivos de código** no aplicativo (ADR-0010). Passar disso é
  sinal de escopo crescendo.

## Fora de escopo

- Usuários, contas, autenticação, sessão, isolamento de dados por dono.
- Notificar alguém de qualquer forma — o app não avisa ninguém; lembretes são
  consultados. Inclui e-mail, push, SMS e alerta no navegador.
- Alterar um lembrete existente: o fluxo é criar, concluir e apagar.
- Lembretes recorrentes, subtarefas, etiquetas, prioridade, anexos, busca.
- Paginação, filtros e ordenação alternativa.
- JavaScript de aplicação, framework de frontend, TypeScript.
- Aplicativo móvel, PWA, uso offline.
- Internacionalização e escolha de fuso pelo visitante.
- API em JSON para consumo por terceiros.

## Critérios de aceite

- [x] Todo predicado acima tem ao menos um teste automatizado, e a suíte roda
      com um comando (`make test`): 25 testes.
- [x] Cobertura de linhas ≥ 70% — medida: 98%.
- [x] O aplicativo tem no máximo 20 arquivos de código, contados e registrados —
      13 (`make files`).
- [x] A partir do clone, copiar o arquivo de ambiente de exemplo e subir o
      ambiente local deixa a página usável em menos de 2 minutos, sem nenhum
      outro passo manual — 52 s com build sem cache.
- [ ] Um avaliador consegue, sem instruções: criar, concluir e apagar um
      lembrete pela página. *Os três fluxos foram exercidos pela HTTP real, mas
      este critério é sobre um humano descobrir a página sozinho: fica aberto
      até a fase 11, que o cobre em navegador de verdade.*
- [ ] Nenhum segredo no repositório, confirmado por varredura. *A varredura
      (Trivy) entra na fase 9 da plataforma, e o histórico completo é verificado
      na fase 13.*
- [x] O identificador do build aparece no endpoint de saúde e na página, e os
      dois coincidem.

## Fases

1. [x] Modelo de dados e migração inicial — depende de: —
2. [x] Rotas e templates: criar, listar, concluir, apagar, com validação e
   estado vazio — depende de: fase 1
3. [x] Sondas de saúde e prontidão, métricas e exposição do identificador de
   build — depende de: fase 1
4. [x] Suíte de testes cobrindo todos os predicados — depende de: fases 2 e 3

Concluídas em 2026-07-25. O escopo funcional está congelado a partir daqui
(ADR-0004).
