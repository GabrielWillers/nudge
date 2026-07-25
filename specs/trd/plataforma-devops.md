# TRD: Plataforma DevOps

Deriva de `specs/prd/plataforma-devops.md`.

## Changelog

- 2026-07-25 — versão inicial.

## Escopo + NFRs

Recorte técnico: um repositório único que descreve integralmente a aplicação, o
estado do cluster e a infraestrutura paga; uma automação que verifica mudança e
publica artefato imutável; um cluster gerenciado de um nó que executa o estado
declarado; e a instrumentação que prova que tudo isso funciona.

> Como no TRD da aplicação, os números abaixo são alvos derivados do contexto
> (um operador, um nó de 4 GB, orçamento de US$ 30/mês) e não de medição
> prévia. Cada um é confirmado na fase em que passa a existir.

**Custo**

- Orçamento total ≤ US$ 30/mês em regime normal: nó ~US$ 24, volume de bloco
  ~US$ 1, armazenamento de objeto para backup ~US$ 5. Sem balanceador
  gerenciado (ADR-0009).
- Nenhum recurso pago fora da descrição de infraestrutura — a fatura do
  provedor é a verificação.

**Ciclo de entrega**

- Verificação de proposta de mudança: veredito em < 10 min, com os componentes
  verificados em paralelo.
- Publicação de versão (construção, varredura e envio das duas imagens):
  < 15 min.
- Convergência do cluster após alteração do estado declarado: < 5 min sem
  intervenção.
- Rollback para versão anterior: < 5 min, sem reconstruir imagem.
- Recriação completa da infraestrutura a partir do zero: < 60 min até a
  aplicação atender no domínio, incluindo restauração do backup.

**Disponibilidade**

- Sem compromisso formal de disponibilidade: um nó, sem redundância
  (ADR-0005).
- Janela de indisponibilidade aceitável durante atualização de imagem,
  atualização de versão do cluster e reagendamento de pod.
- Instância que não responde à sonda de prontidão deixa de receber tráfego em
  < 30 s.

**Segurança**

- Nenhum segredo em texto claro em nenhum commit do histórico.
- Limitação de taxa no controlador de entrada: 10 requisições por IP por
  minuto nas rotas de autenticação, 60 por minuto nas demais. Esta é a
  contrapartida de o aplicativo não implementar limitação própria — ver TRD da
  aplicação.
- TLS 1.2 ou superior; porta 80 responde exclusivamente redirecionamento.
- Certificado renovado automaticamente com pelo menos 30 dias de antecedência.
- Nenhum container roda como superusuário; sistema de arquivos raiz somente
  para leitura onde a carga permitir.
- Varredura de vulnerabilidade em sistema de arquivos e em imagem; achado de
  severidade alta ou crítica com correção disponível reprova a publicação.
- Credencial de acesso ao registro e ao provedor concedida por identidade
  federada onde o provedor suportar, evitando segredo de longa duração.

**Continuidade**

- Backup do banco a cada 24 h, retido por 7 dias, armazenado fora do cluster.
- Restauração exercitada de verdade ao menos uma vez, com tempo registrado.
- Objetivo de ponto de recuperação: até 24 h de perda de dados aceitável — os
  dados são de demonstração.

**Observabilidade**

- Métricas de latência, taxa de erro e saturação dos dois componentes, com pelo
  menos 7 dias de histórico.
- Coleta a cada 30 s.
- Alerta entregue em canal externo em < 5 min após a condição persistir pelo
  intervalo definido.
- Custo de memória da pilha de observabilidade ≤ 1,5 GB — o que exige
  configuração enxuta no nó de 4 GB.

## Arquitetura + Contratos

### Componentes e fluxo

```
   operador
      │ proposta de mudança
      ▼
 ┌──────────────────┐   verifica    ┌───────────────────────┐
 │   repositório    │──────────────►│ integração contínua   │
 │  (fonte única)   │               │ lint, tipos, teste,   │
 │                  │◄──────────────│ varredura, cobertura  │
 │  backend/        │  atualiza a   └───────────┬───────────┘
 │  frontend/       │  referência               │ publica por tag
 │  k8s/            │  de imagem                ▼
 │   ├─ base/       │               ┌───────────────────────┐
 │   └─ overlays/   │               │  registro de imagens  │
 │  infra/          │               │      (imutável)       │
 │  specs/          │               └───────────┬───────────┘
 └────────┬─────────┘                           │
          │ observa k8s/overlays/prod           │ baixa imagem
          ▼                                     │
 ┌──────────────────┐                           │
 │  reconciliador   │──── aplica estado ────────┼──┐
 └──────────────────┘                           │  │
                                                ▼  ▼
 ┌────────────────────────────────────────────────────────────┐
 │  cluster gerenciado — 1 nó, 2 vCPU / 4 GB                   │
 │                                                             │
 │   entrada (portas 80/443 no nó)  ──► frontend               │
 │        │                          ──► backend ──► postgres  │
 │        └─ TLS por desafio de DNS                  (volume)   │
 │                                                             │
 │   emissor de certificado    observabilidade    backup diário │
 └────────────────────────────────────────────────────────────┘
          ▲                                    │
          │ provisiona                         ▼ envia dump
 ┌──────────────────┐              ┌───────────────────────┐
 │ infraestrutura   │              │ armazenamento de      │
 │ como código      │              │ objeto (fora do       │
 │ (cluster, DNS,   │              │ cluster)              │
 │  volume, firewall)│             └───────────────────────┘
 └──────────────────┘
```

**Contrato central do ciclo:** o repositório é a única fonte de verdade. A
integração contínua nunca aplica estado no cluster — ela publica artefato e
atualiza a referência de imagem no estado declarado. Quem aplica é o
reconciliador. Essa separação é o que faz a divergência manual no cluster ser
detectável e reversível, e é a razão de o deploy não ser um passo do pipeline.

Antes da fase 10 não há reconciliador: o operador aplica o estado declarado à
mão. O contrato acima descreve o estado final; até lá, a fonte de verdade
continua sendo o repositório, aplicado manualmente.

### Interfaces

**Estrutura do repositório**

```
backend/            aplicação (ver TRD nudge-app-v1)
frontend/           aplicação (ver TRD nudge-app-v1)
k8s/
  base/             recursos comuns aos dois ambientes
  overlays/local/   sobreposição do cluster local
  overlays/prod/    sobreposição de produção — caminho observado pelo
                    reconciliador
infra/              descrição de infraestrutura do provedor
specs/              PRD, TRD, ADR
compose.yaml        ambiente de desenvolvimento do aplicativo (não valida
                    manifesto — ADR-0008)
```

**Gatilhos de automação**

| gatilho                      | efeito                                                        |
|------------------------------|---------------------------------------------------------------|
| proposta de mudança aberta   | verificação por componente em paralelo; bloqueia integração se falhar |
| integração na linha principal| verificação novamente; nenhuma publicação                     |
| marcação `v<major.minor.patch>` | constrói, varre e publica as duas imagens; atualiza a referência de imagem na sobreposição de produção |
| agenda diária                | varredura de dependência abre proposta de atualização          |
| agenda diária (no cluster)   | despejo do banco enviado ao armazenamento de objeto            |

**Identificação de imagem**

Cada imagem recebe, no mínimo, a versão semântica e o commit de origem. A
sobreposição de produção referencia **sempre a versão semântica**, nunca uma
tag móvel: é isso que faz o rollback ser a edição de uma linha e que garante a
invariante de imutabilidade. Uma versão já publicada nunca é republicada com
conteúdo diferente.

**Recursos no cluster**

| carga            | recurso do Kubernetes | exposição                       |
|------------------|-----------------------|---------------------------------|
| frontend         | Deployment            | Service interno; entrada em `/` |
| backend          | Deployment            | Service interno; entrada em `/api` |
| banco            | StatefulSet + PVC     | Service interno, sem exposição externa (ADR-0007) |
| backup           | CronJob               | nenhuma                         |
| entrada          | controlador com portas 80/443 no nó | público (ADR-0009) |
| certificado      | emissor com desafio de DNS | nenhuma                    |

Sondas: sonda de vivacidade contra `/healthz`, que não toca o banco, para que
uma indisponibilidade do banco não provoque reinício em laço do backend; sonda
de prontidão contra `/readyz`, que toca o banco, para tirar a instância do
tráfego. Sonda de partida cobrindo o tempo de migração declarado no TRD da
aplicação.

**Diferenças entre sobreposições**

| aspecto            | local (kind)                  | produção (gerenciado)        |
|--------------------|-------------------------------|------------------------------|
| referência de imagem | construída localmente        | versão semântica do registro |
| StorageClass       | padrão do kind                | volume de bloco do provedor  |
| TLS                | ausente                       | emitido por desafio de DNS   |
| domínio            | nome local                    | domínio público              |
| segredo            | valores de desenvolvimento    | cifrado no repositório        |
| réplicas           | 1                             | 1                            |

**Segredos**

Quatro segredos existem em produção: credencial do banco, segredo de assinatura
de token, credencial de API de DNS para o emissor de certificado e credencial do
armazenamento de objeto para o backup. Todos ficam cifrados no repositório
(fase 13) e decifrados no cluster. Até a fase 13, são aplicados manualmente e o
procedimento fica documentado — nunca versionados em texto claro.

Um recurso de Secret do Kubernetes é codificação, não cifra: por si só não
satisfaz a invariante de segredo do PRD.

## Stack + Validação

### Dependências

| camada                     | escolha                                              |
|----------------------------|------------------------------------------------------|
| hospedagem de código e automação | GitHub e GitHub Actions                        |
| registro de imagens        | GitHub Container Registry (ADR-0005)                 |
| provedor de nuvem          | DigitalOcean, Kubernetes gerenciado (ADR-0005)       |
| versão do Kubernetes       | a mais recente oferecida pelo provedor, fixada em `infra/` |
| cluster local              | kind (ADR-0008)                                      |
| composição de manifesto    | Kustomize, com base e sobreposições                  |
| controlador de entrada     | o mesmo nos dois ambientes, instalado explicitamente |
| certificado               | emissor no cluster com desafio de DNS (ADR-0009)     |
| infraestrutura como código | Terraform com o provider do provedor de nuvem        |
| convergência              | reconciliador de GitOps no cluster (fase 10)         |
| varredura de vulnerabilidade | Trivy, em sistema de arquivos e em imagem          |
| atualização de dependência | Dependabot, um ecossistema por diretório             |
| observabilidade           | Prometheus e Grafana, em configuração enxuta         |
| teste ponta a ponta       | Playwright, contra ambiente descartável              |
| teste de carga            | k6, contra ambiente descartável                      |
| armazenamento de backup   | armazenamento de objeto compatível com S3 do provedor |

Kustomize em vez de Helm: sem camada de template, nativo na ferramenta de linha
de comando, e mantém os manifestos das fases 5 e 6 legíveis como texto. Empacotar
com Helm só faria sentido para distribuir a aplicação a terceiros, o que não está
no escopo.

Imagens de container: construção em múltiplos estágios, imagem final sem
ferramenta de build, usuário sem privilégio, versão base fixada por digest.

### Critérios de validação

Agrupados pela fase que os torna verificáveis.

**Fase 3 — verificação mínima**
- [ ] Proposta com teste quebrado é bloqueada; a mesma proposta corrigida passa.

**Fase 4 — artefato**
- [ ] Imagem publicada carrega versão e commit, e o valor exibido pela
      aplicação em execução coincide com o commit de origem.
- [ ] Processo dentro da imagem confirmado rodando sem privilégio.

**Fase 5 — cluster local**
- [ ] Aplicação sobe no kind pelo estado declarado, atende pelo controlador de
      entrada e persiste dado através da exclusão do pod do banco.
- [ ] Sonda de prontidão retira a instância do tráfego quando o banco é
      derrubado, e a devolve quando ele volta, sem reinício em laço.

**Fase 6 — produção**
- [ ] Domínio público responde em HTTPS com certificado válido, avaliado por
      ferramenta externa.
- [ ] Requisição em texto claro é redirecionada, e nenhuma outra resposta em
      texto claro é possível.
- [ ] Limitação de taxa confirmada: décima primeira tentativa de autenticação
      no mesmo minuto é recusada pela entrada.

**Fase 8 — infraestrutura como código**
- [ ] `destroy` seguido de `apply` recria cluster, node pool, DNS e firewall, e
      a aplicação volta a atender no mesmo domínio; tempo registrado.
- [ ] Após `destroy`, a fatura do provedor não acusa recurso ativo — em
      particular, nenhum volume de bloco órfão.
- [ ] Registro de DNS é reconciliado automaticamente com o novo IP do nó após
      recriação (risco central do ADR-0009).

**Fase 9 — pipeline completo**
- [ ] Veredito de verificação em < 10 min, com paralelismo observável na
      execução.
- [ ] Achado de severidade alta com correção disponível reprova a publicação,
      comprovado com uma dependência vulnerável introduzida de propósito.
- [ ] Tentativa de republicar uma versão existente com conteúdo diferente não
      substitui o conteúdo anterior.

**Fase 10 — convergência**
- [ ] Alteração no estado declarado converge em < 5 min sem ação manual.
- [ ] Alteração aplicada manualmente no cluster é reportada como divergência e
      desfeita.
- [ ] Rollback pela declaração da versão anterior concluído em < 5 min, com o
      identificador de build na tela voltando ao valor antigo; tempo registrado.

**Fase 11 — qualidade sob execução**
- [ ] Teste ponta a ponta exercita registro, entrada e ciclo de vida de
      lembrete em navegador real, contra ambiente descartável.
- [ ] Teste de carga registra throughput sustentado, latência por percentil e o
      ponto de saturação; percentis comparados aos alvos do TRD da aplicação.
- [ ] Confirmado que nenhum teste alcança o banco de produção.

**Fase 12 — observabilidade**
- [ ] Painel apresenta latência, taxa de erro e saturação dos dois componentes,
      com 7 dias de histórico.
- [ ] Alerta disparado em teste deliberado e entregue em canal externo em
      < 5 min.
- [ ] Memória total da pilha de observabilidade medida e dentro do teto, ou o
      node pool expandido com a decisão registrada em ADR.

**Fase 13 — continuidade**
- [ ] Nenhum segredo em texto claro recuperável em nenhum commit do histórico,
      confirmado por varredura do histórico completo.
- [ ] Backup diário produz artefato fora do cluster, com retenção de 7 dias
      efetivamente observada.
- [ ] Restauração executada em banco vazio, dados conferidos, tempo registrado.

**Transversal**
- [ ] Custo mensal real medido e registrado, dentro do orçamento.
- [ ] Toda decisão difícil de reverter tomada durante o projeto tem ADR, e
      nenhum ADR aceito foi editado ou apagado.
- [ ] Terceiro sobe o ambiente local em < 15 min seguindo apenas o README.

## Riscos e mitigação

- **IP do nó muda ao recriar e derruba o domínio** (ADR-0009, agravado pela
  prática de destruir o ambiente para economizar) → o registro de DNS é
  gerenciado pela descrição de infraestrutura e reconciliado no mesmo `apply`
  que cria o nó; a validação da fase 8 verifica isso explicitamente. Enquanto a
  fase 8 não existir, destruir o ambiente não é uma prática segura.
- **Teto de 4 GB estoura na fase 12** → configuração enxuta de observabilidade
  como NFR quantificado; se não couber, expandir o node pool temporariamente e
  registrar em ADR, com o efeito no custo medido.
- **Custo escapa do orçamento sem ninguém notar** → alerta de faturamento no
  provedor configurado na fase 6, antes de qualquer prática de destruir e
  recriar.
- **Volume de bloco órfão continua sendo cobrado após destruir o cluster** →
  volume descrito explicitamente na infraestrutura como código e verificado na
  fatura após o primeiro `destroy`.
- **Reconciliador observando o mesmo repositório do código reage a commit
  irrelevante** (ADR-0001) → o reconciliador observa exclusivamente
  `k8s/overlays/prod`.
- **Publicação manual de imagem nas fases 4 a 8 permite enviar código não
  commitado** → o identificador de build é derivado do commit, e a construção
  aborta com a árvore de trabalho suja.
- **Filtro por caminho na verificação deixa passar proposta não verificada**
  (ADR-0001) → a verificação da linha principal roda sem filtro; o filtro
  existe apenas na proposta.
- **Perda de dado antes de a fase 13 existir** → até lá o dado de produção é
  tratado como descartável e a aplicação não é divulgada como serviço utilizável.
- **Um nó é ponto único de falha para tudo, inclusive para a entrada e o
  certificado** → limitação aceita e declarada (ADR-0005); a mitigação é
  reprovisionar rápido, o que é exatamente o que a fase 8 torna possível.
- **Segredo de API de DNS no cluster tem permissão de escrita na zona do
  domínio** → escopo da credencial restrito à zona usada; segredo cifrado no
  repositório e rotacionado se o cluster for exposto.
- **Projeto perde tração antes da fase 13 e a produção fica no ar pagando sem
  backup** → a ordem das fases coloca infraestrutura como código na 8, de modo
  que interromper o projeto seja um `destroy` e não uma fatura recorrente
  esquecida.
