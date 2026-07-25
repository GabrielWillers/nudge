# ADR-0007: Rodar o PostgreSQL dentro do cluster como StatefulSet com volume do provedor

## Status

Aceito — 2026-07-25

## Contexto

A aplicação precisa de um banco relacional persistente. Onde ele roda é uma
decisão de porta estreita: migrar banco depois de haver dado em produção é a
operação mais arriscada do projeto.

A recomendação de engenharia usual para produção é banco gerenciado — o
provedor cuida de backup, atualização e disponibilidade. Aqui há duas forças
contrárias. A primeira é custo: banco gerenciado no provedor escolhido custa
sozinho mais que o nó inteiro, estourando o orçamento de US$ 30/mês. A segunda
é que carga com estado é justamente o que há de mais instrutivo em Kubernetes:
StatefulSet, PersistentVolumeClaim, StorageClass, ordem de inicialização e
sonda de prontidão dependente de dependência externa. Um banco gerenciado
apagaria toda essa demonstração e deixaria o cluster com duas cargas sem
estado.

O volume vem do CSI do provedor (ADR-0005), não de armazenamento local do nó,
o que muda materialmente o perfil de risco: o dado sobrevive à destruição do
nó.

## Alternativas consideradas

- **Banco gerenciado do provedor** — a escolha correta para um sistema com
  usuários reais. Descartada por custo e por eliminar a demonstração de carga
  com estado. Se este projeto ganhasse usuários reais, esta decisão seria a
  primeira a ser substituída.
- **Camada gratuita de Postgres gerenciado de terceiro (Neon, Supabase)** —
  custo zero, mas adiciona dependência externa fora da infraestrutura como
  código e, de novo, retira o estado do cluster.
- **Operador de banco de dados (CloudNativePG)** — entrega backup contínuo,
  recuperação a ponto no tempo e failover, e é a resposta madura para Postgres
  em Kubernetes. Descartado **por ora**: consome memória relevante no nó de
  4 GB e esconde, atrás de uma abstração, exatamente os primitivos que a fase 5
  existe para ensinar. Candidato natural a extensão futura, com ADR próprio.
- **PostgreSQL como Deployment com PVC** — funciona com uma réplica, mas
  StatefulSet é o recurso correto para identidade estável e volume por
  instância; usar o recurso errado de propósito ensinaria a coisa errada.

## Decisão

PostgreSQL roda no cluster como StatefulSet de uma réplica, com
PersistentVolumeClaim servido pela StorageClass de volume de bloco do provedor.
Versão de imagem fixada em major explícito, nunca em tag móvel.

Credenciais vêm de Secret, jamais de valor embutido em manifesto. A sonda de
prontidão do backend depende de conseguir alcançar o banco, para que uma
instância sem banco não receba tráfego.

Migrações de schema são aplicadas na inicialização do backend, antes de ele
começar a atender.

A fase 13, com backup diário fora do cluster e um drill de restauração
efetivamente executado e cronometrado, é **condição de aceite desta decisão**,
não um item opcional de roadmap.

## Consequências

+ Exercita os primitivos com estado de Kubernetes: StatefulSet, PVC,
  StorageClass, Secret e sonda de prontidão com dependência externa.
+ Custo marginal baixo: apenas os centavos por GB do volume de bloco.
+ Todo o estado do sistema fica descrito no mesmo repositório que o resto.
+ O volume sobrevive à recriação do pod e à destruição do nó.
- **Volume persistente não é backup.** Exclusão acidental de PVC, corrupção
  lógica ou `DROP TABLE` levam o dado embora, e o backup da fase 13 é a única
  defesa. Até ela existir, o dado de produção é descartável — e o projeto tem
  de tratá-lo assim.
- Uma réplica significa indisponibilidade do banco durante qualquer
  atualização de imagem ou reagendamento de pod. A aplicação inteira fica fora
  do ar nessas janelas.
- Migração na inicialização do backend é correta com uma réplica e **quebra com
  mais de uma**: duas instâncias subindo em paralelo tentariam migrar
  simultaneamente. Escalar o backend exige, antes, mover a migração para um
  passo separado — dívida registrada aqui.
- Upgrade de versão major do PostgreSQL passa a ser trabalho manual de despejar
  e restaurar, sem automação do provedor.
- Volume de bloco não é liberado ao destruir o cluster: a fase 8 precisa
  gerenciá-lo explicitamente, sob risco de cobrança por volume órfão.
