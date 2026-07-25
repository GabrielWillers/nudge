# ADR-0004: Congelar o escopo funcional do aplicativo ao fim da v1

## Status

Aceito — 2026-07-25

## Contexto

O modo de falha característico de projeto de portfólio com pretensão de DevOps
é conhecido: o esforço migra para as features do aplicativo, porque elas dão
retorno visível imediato, e a plataforma termina como um arquivo de
integração contínua adicionado no último commit. O resultado é um repositório
que não comprova o que se propôs a comprovar.

O aplicativo aqui é instrumento. Ele já exercita, na v1, tudo que a plataforma
precisa operar: banco relacional com migração, volume persistente, segredo,
sonda de saúde, dois serviços independentes e isolamento por usuário. Nenhuma
feature adicional de produto acrescentaria uma capacidade nova de
infraestrutura — lembrete recorrente, etiqueta ou busca textual não ensinam
nada sobre Kubernetes.

A versão inicial do roadmap previa notificação por worker agendado como fase
avançada, justamente para exercitar o ciclo. O dono do projeto retirou essa
fase e declarou o aplicativo como base fixa.

## Decisão

O escopo funcional do aplicativo encerra ao fim da fase 2 da plataforma. A
partir daí, mudança no diretório do aplicativo só é aceita por um destes
motivos:

1. Correção de defeito em comportamento já descrito por predicado no PRD.
2. Atualização de dependência.
3. Instrumentação exigida pela plataforma — métrica, log estruturado, sonda,
   exposição de identificador de build.
4. Ajuste necessário para o aplicativo rodar sob a plataforma (configuração,
   variável de ambiente, encerramento gracioso).

Feature nova de produto exige um ADR que substitua este.

Duas consequências entram como obrigação da fase 2, não como recomendação:

- **A suíte de testes é o corpus definitivo.** Como o código não vai crescer,
  os testes escritos na fase 2 serão os únicos por todas as fases seguintes.
  Uma suíte fraca torna decorativa toda a verificação automatizada do projeto.
- **O identificador de build é exposto na API e na interface.** Sem código
  mudando, nada distingue visualmente um deploy bem-sucedido de nenhum deploy.
  O identificador é o sinal observável que fecha o ciclo ponta a ponta.

## Consequências

+ O tempo do projeto vai inteiro para o objetivo declarado, e o histórico do
  repositório passa a registrar a plataforma amadurecendo em vez de features
  acumulando.
+ Superfície de teste estável: nenhuma fase posterior quebra por regressão de
  produto.
+ Cada capítulo de infraestrutura pode ser avaliado isoladamente, porque a
  variável "o app mudou" está eliminada.
+ Torna coerente a decisão de implementar identidade já na v1 (ADR-0003): não
  havendo v2, ela não teria outro momento para entrar.
- Um erro de escopo na v1 é permanente: o que faltar no PRD do aplicativo fica
  faltando, e corrigir isso custa um ADR substituto.
- O aplicativo isolado não impressiona como peça de produto; ele só faz sentido
  lido junto com a plataforma. O README precisa deixar isso explícito, senão
  quem avalia lê o repositório como um app pobre.
- Perde-se o exercício que a notificação daria: processo agendado, fila,
  entrega idempotente e um segundo tipo de carga no cluster ficam sem
  demonstração.
- A suíte de testes nunca cresce, então cobertura e tempo de pipeline param de
  evoluir — a partir da fase 9 não há mais o que otimizar ali.
