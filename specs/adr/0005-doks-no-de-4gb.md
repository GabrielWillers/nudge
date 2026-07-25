# ADR-0005: Hospedar produção em Kubernetes gerenciado na DigitalOcean, com um nó de 4 GB

## Status

Aceito — 2026-07-25

## Contexto

A produção precisa ser um ambiente público e real: sem URL acessível, nada do
que o projeto se propõe fica demonstrado. O orçamento-alvo é de até
US$ 30/mês, mantido por um único operador.

O projeto tem Kubernetes como espinha dorsal por decisão do dono, e não apenas
como um destino de deploy entre outros. Isso muda o critério: o que importa é
que a experiência seja de Kubernetes de verdade — CSI provisionando volume,
cloud-controller-manager provisionando balanceador, upgrade de versão de
cluster — e não de uma aproximação.

Provedores foram comparados sob custo por GB de memória e sob quanto do
Kubernetes real eles entregam. A DigitalOcean é mais caro que a opção europeia
mais barata para a mesma memória, e o dono do projeto escolheu a DigitalOcean
conscientemente.

## Alternativas consideradas

- **k3s em VPS na Hetzner (~€7/mês por 8 GB)** — aproximadamente um quarto do
  custo pela mesma memória, e foi a recomendação inicial. Descartada por
  escolha do dono. Tem duas desvantagens técnicas reais: o control plane
  consome memória do mesmo nó que serve a aplicação, e k3s substitui
  componentes por versões próprias (balanceador de serviço, provisionador de
  armazenamento local), então o comportamento aprendido não transfere
  integralmente para Kubernetes gerenciado.
- **Plataforma como serviço (Render, Railway, Fly.io)** — deploy resolvido por
  `git push`. Descartada por eliminar exatamente a camada que o projeto existe
  para demonstrar. Além disso, os planos gratuitos hibernam a aplicação e
  expiram bancos, o que deixaria a demonstração fora do ar precisamente quando
  alguém abrisse o link.
- **EKS ou GKE** — Kubernetes gerenciado de referência, com cobrança pelo
  control plane e custo de ordem de grandeza superior ao orçamento.
- **Nó de 2 GB (~US$ 12/mês)** — caberia com folga no orçamento, mas não
  sustenta a pilha de observabilidade e o reconciliador simultaneamente.
  Descartado para evitar migração de nó no meio do projeto.

## Decisão

Provisionar um cluster de Kubernetes gerenciado na DigitalOcean com um único
node pool de um nó de 2 vCPU e 4 GB (~US$ 24/mês). Volume persistente pelo CSI
do provedor. DNS gerenciado pelo próprio provedor, o que também habilita
emissão de certificado por desafio de DNS (ADR-0009).

Imagens continuam no GitHub Container Registry, não no registro do provedor:
é gratuito para repositório público e mantém artefato e código no mesmo lugar.

A versão de Kubernetes é a mais recente oferecida pelo provedor no momento do
provisionamento, e fica declarada na descrição de infraestrutura.

Todo recurso pago é descrito por infraestrutura como código, e essa descrição
é antecipada para a fase 8 — antes da automação de integração contínua. A
razão é econômica, não estética: um cluster que custa por hora precisa ser
destrutível, e a destruição só é segura quando a recriação é confiável.

## Consequências

+ Control plane gerenciado sem custo: os 4 GB do nó ficam integralmente para as
  cargas.
+ Kubernetes upstream, não uma distribuição enxuta — CSI, cloud controller e
  upgrade de cluster comportam-se como em qualquer nuvem, e o que se aprende
  aqui transfere.
+ Provider de infraestrutura como código maduro, o que torna a fase 8 viável e
  o cluster genuinamente descartável.
+ Volume persistente sobrevive à morte do nó, ao contrário de armazenamento
  local em VPS.
- **Custo aproximadamente quatro vezes maior** que a alternativa em VPS para a
  mesma memória. Mitigação prevista: destruir o ambiente com a descrição de
  infraestrutura nos períodos sem uso, o que só é aceitável depois que a fase 13
  garantir backup e restauração confiáveis.
- Um nó significa **nenhuma alta disponibilidade**: perda do nó ou upgrade de
  versão derruba a aplicação. Réplica adicional não resolve, porque não há
  segundo nó onde agendá-la.
- 4 GB é teto apertado. A fase 12 vai exigir enxugar a pilha de
  observabilidade (retenção curta, sem redundância no alertador) ou expandir o
  node pool temporariamente, dobrando o custo naquele período. A decisão fica
  para um ADR próprio quando a medição existir.
- Volume de bloco é cobrado por GB e não é liberado pela destruição do cluster:
  a descrição de infraestrutura precisa contemplá-lo explicitamente, sob risco
  de cobrança por volume órfão.
- Ficar em um provedor pago torna o abandono do projeto uma decisão financeira
  ativa, não uma inércia.
