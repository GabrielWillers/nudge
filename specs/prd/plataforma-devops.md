# PRD: Plataforma DevOps

## Contexto

O objetivo deste projeto não é o aplicativo — é a plataforma em volta dele, e
a evidência verificável de competência em DevOps e Kubernetes que ela produz.

O padrão de mercado em repositório de portfólio é o inverso do que deveria
ser: um aplicativo com muitas features e, no último commit, um arquivo de CI
que roda um lint. Quem avalia não consegue distinguir isso de um pipeline que
funciona, porque nada no histórico mostra o ciclo em operação — não houve
ciclo, houve um arquivo adicionado no fim. O mesmo vale para infraestrutura:
um manifesto de Kubernetes no repositório não prova que algo já rodou em um
cluster.

Hoje não existe nada: nenhum repositório versionado, nenhum ambiente, nenhuma
automação. Toda operação seria manual, irreprodutível e invisível.

O que fecha essa lacuna é o inverso da ordem habitual: a carga de trabalho
nasce pequena e congela, e o histórico do repositório passa a ser o registro
de uma plataforma amadurecendo em cima dela — cada capítulo com sua decisão
registrada e seu efeito observável em produção.

## Atores

- **Operador** — dono do projeto, única pessoa com acesso; abre propostas de
  mudança, publica versões e opera o cluster. Trabalha em horas de fim de
  semana e espera que nenhuma etapa exija presença em horário determinado.
- **Serviço de integração contínua** — verifica cada proposta de mudança e
  produz artefatos versionados a partir das aprovadas.
- **Reconciliador de estado** — compara o estado declarado no repositório com
  o estado real do cluster e converge um para o outro.
- **Orquestrador de containers** — agenda as cargas, sonda a saúde delas,
  reinicia o que morre e mantém o tráfego longe do que não responde.
- **Registro de imagens** — guarda os artefatos publicados, imutáveis e
  endereçáveis por versão.
- **Provedor de nuvem** — fornece cluster, volume persistente, DNS e cobra por
  isso.
- **Autoridade certificadora** — emite e renova o certificado do domínio
  público.
- **Visitante do portfólio** — acessa a aplicação por uma URL pública e
  espera encontrá-la viva, em HTTPS, sem aviso de certificado.
- **Avaliador técnico** — lê o repositório esperando reconstituir cada decisão
  e a razão dela, e confirmar que o ciclo descrito de fato roda.

## Predicados

### Verificação de mudança

- [ ] Dada uma proposta de mudança aberta, quando ela é publicada, então
      formatação, análise estática, tipos e testes são verificados
      automaticamente e o resultado fica visível na própria proposta.
- [ ] Dada uma proposta cuja verificação falhou, quando se tenta integrá-la à
      linha principal, então a integração é bloqueada.
- [ ] Dada uma proposta de mudança, quando a verificação roda, então as
      checagens independentes rodam em paralelo, e o tempo total até o veredito
      fica abaixo de 10 minutos.
- [ ] Dada uma dependência com vulnerabilidade conhecida ou versão nova,
      quando a varredura periódica roda, então uma proposta de atualização é
      aberta automaticamente.

### Artefato

- [ ] Dada uma marcação de versão semântica publicada, quando o processo de
      release termina, então existe a imagem do serviço no registro
      identificada por aquela versão e pelo commit exato de origem.
- [ ] Dada uma versão já publicada no registro, quando se tenta publicar
      conteúdo diferente com a mesma identificação, então a publicação não
      substitui o conteúdo anterior.
- [ ] Dada uma imagem candidata, quando é publicada, então já passou por
      varredura de vulnerabilidade e o resultado está registrado junto à
      execução.
- [ ] Dada uma imagem em execução, quando se inspeciona o processo dentro
      dela, então ele não roda como superusuário.

### Convergência e produção

- [ ] Dado o estado declarado no repositório alterado, quando o reconciliador
      sincroniza, então o cluster converge para aquele estado sem nenhuma
      ação manual.
- [ ] Dada uma alteração introduzida manualmente no cluster, quando o
      reconciliador roda, então a divergência é reportada e desfeita.
- [ ] Dado um deploy concluído, quando se consulta a aplicação publicada,
      então o identificador de build que ela exibe corresponde ao commit da
      versão declarada no repositório.
- [ ] Dada uma versão anterior conhecida, quando ela é declarada de novo,
      então a produção volta a essa versão em menos de 5 minutos e sem
      reconstruir imagem.
- [ ] Dado um container que morre ou é reagendado, quando ele volta, então os
      lembretes gravados continuam presentes.
- [ ] Dada uma instância que parou de responder, quando o orquestrador a
      sonda, então ela deixa de receber tráfego até responder de novo, e o
      serviço continua atendendo pelas instâncias sadias quando houver.
- [ ] Dado o ambiente local, quando se aplica a mesma declaração de estado com
      a sobreposição local, então a aplicação sobe em um cluster na máquina do
      operador usando o mesmo controlador de entrada da produção.

### Exposição e segredo

- [ ] Dado tráfego em texto claro chegando ao domínio público, quando ele é
      recebido, então é redirecionado para HTTPS.
- [ ] Dado o certificado do domínio aproximando-se do vencimento, quando
      ninguém intervém, então ele é renovado automaticamente e continua válido.
- [ ] Dado o repositório lido por um terceiro, quando ele procura segredos,
      então nenhum valor de segredo é recuperável a partir do conteúdo
      versionado, em nenhum ponto do histórico.
- [ ] Dada uma rota de escrita em produção, quando requisitada sem credencial,
      então é recusada pelo controlador de entrada — o aplicativo não tem
      autenticação própria (ADR-0010).
- [ ] Dado um segredo necessário à aplicação, quando o cluster é recriado do
      zero, então o segredo é reintroduzido por um procedimento documentado que
      não exige copiar valor de dentro do repositório.

### Infraestrutura reprodutível

- [ ] Dado nenhum recurso provisionado, quando se aplica a descrição de
      infraestrutura, então cluster, node pool, DNS e regras de firewall
      passam a existir com a mesma configuração da vez anterior.
- [ ] Dado o ambiente provisionado, quando se executa a destruição pela
      descrição de infraestrutura, então nenhum recurso cobrado permanece
      ativo.
- [ ] Dada a infraestrutura destruída e recriada, quando a aplicação volta,
      então ela atende de novo no mesmo domínio, com os dados restaurados do
      backup.

### Observação

- [ ] Dada a produção em operação, quando se abre o painel de
      observabilidade, então latência, taxa de erro e saturação de CPU e
      memória do serviço estão visíveis com histórico.
- [ ] Dada uma condição de indisponibilidade que persiste pelo intervalo
      definido, quando ela é detectada, então um alerta é entregue em um canal
      fora do cluster.
- [ ] Dado que a aplicação está de pé, quando se consulta o endpoint de
      métricas do serviço, então ele expõe contagem de requisições, latência e
      erros por rota.

### Qualidade sob execução

- [ ] Dado um ambiente descartável com o serviço e um banco, quando o teste
      ponta a ponta roda, então ele exercita criar, concluir e apagar um
      lembrete em um navegador real.
- [ ] Dado um perfil de carga definido, quando executado contra o ambiente
      descartável, então throughput sustentado, latência por percentil e o
      ponto de saturação ficam registrados no repositório.
- [ ] Dado um teste de carga ou ponta a ponta em execução, quando ele roda,
      então nenhum dado de produção é lido ou escrito.

### Continuidade de dados

- [ ] Dado o banco em produção, quando a rotina diária de backup roda, então
      existe um artefato de cópia armazenado fora do cluster.
- [ ] Dado um artefato de backup e um banco vazio, quando se executa o
      procedimento de restauração, então os dados voltam e o tempo gasto está
      registrado.

## Invariantes

- Nenhum segredo em texto claro no repositório, em nenhum commit do
  histórico.
- Uma identificação de versão no registro nunca aponta para dois conteúdos
  diferentes.
- Toda imagem em execução em produção é rastreável a um commit específico do
  repositório.
- O repositório é a única fonte de verdade do estado de produção: qualquer
  coisa aplicada fora dele é divergência a ser desfeita.
- Todo recurso pago no provedor de nuvem é descrito por infraestrutura como
  código.
- Nenhum dado trafega em texto claro: a única resposta possível em texto claro
  no domínio público é um redirecionamento para HTTPS.
- Os lembretes sobrevivem à destruição e recriação de qualquer container.
- Toda decisão difícil de reverter tem um ADR correspondente, e ADR aceito
  nunca é editado nem apagado.
- Nenhum processo de container roda como superusuário.

## Restrições

- Provedor: DigitalOcean, com Kubernetes gerenciado (ADR-0005). Orçamento-alvo
  de até US$ 30/mês em regime normal.
- Repositório e automação no GitHub; imagens no GitHub Container Registry.
- Um único ambiente de produção, mais o ambiente local do operador. Sem
  staging (ADR-0006 fixa também a ordem de execução).
- Cluster de um nó: sem alta disponibilidade, e janelas de indisponibilidade
  durante upgrade de versão são aceitáveis.
- Um só operador, trabalhando em horas de fim de semana: nenhuma etapa pode
  exigir intervenção em horário determinado nem plantão.
- O nó de 4 GB hospeda aplicação, banco, observabilidade e reconciliador
  simultaneamente; qualquer carga nova precisa caber nesse teto ou
  justificar a expansão do node pool.
- A plataforma não pode depender de nenhuma feature nova do aplicativo, cujo
  escopo está congelado (ver PRD `nudge-app-v1` e ADR-0004).
- O aplicativo é um serviço único, sem autenticação (ADR-0010): proteger a
  escrita é responsabilidade do controlador de entrada, não do código.
- Kubernetes entra antes da automação completa de integração contínua
  (ADR-0006).

## Fora de escopo

- Alta disponibilidade: múltiplos nós, múltiplas regiões, failover, tolerância
  a perda de nó.
- Staging, ambiente por proposta de mudança, deploy canário ou blue/green.
- Banco de dados gerenciado pelo provedor.
- Autoscaling horizontal, políticas de rede, service mesh, mTLS interno,
  orçamento de interrupção de pods — todos ficam como extensões posteriores,
  fora desta iteração.
- Rastreamento distribuído e agregação centralizada de logs com retenção
  longa.
- SLO formal com orçamento de erro.
- Conformidade regulatória (LGPD, SOC 2): os dados são fictícios e de
  demonstração.
- Plano de recuperação de desastre com RTO e RPO contratados.
- Gestão de múltiplos operadores, papéis ou acesso de terceiros ao cluster.

## Critérios de aceite

- [ ] Uma URL pública serve a aplicação em HTTPS com certificado válido, e um
      terceiro consegue registrar-se e usá-la sem instrução.
- [ ] Um commit trivial atravessa proposta → verificação → versão → produção
      sem nenhum passo manual fora do repositório, e o identificador de build
      exibido na tela muda ao fim.
- [ ] Rollback para a versão anterior executado de verdade e cronometrado em
      menos de 5 minutos, com o resultado registrado no repositório.
- [ ] Destruição e recriação completa da infraestrutura executada ao menos uma
      vez, com o tempo gasto registrado e a aplicação voltando no mesmo
      domínio.
- [ ] Restauração de backup executada ao menos uma vez, com tempo registrado.
- [ ] Painel de observabilidade cobrindo latência, erro e saturação, e um
      alerta disparado ao menos uma vez em teste deliberado.
- [ ] Resultado de um teste de carga registrado, com o ponto de saturação
      identificado.
- [ ] Custo mensal real medido e registrado, dentro do orçamento-alvo.
- [ ] Toda decisão difícil de reverter tomada durante o projeto tem ADR.
- [ ] O README permite a um terceiro subir o ambiente local em menos de 15
      minutos.

## Fases

1. Fundação: repositório versionado, especificações, instruções de projeto e
   ambiente local de desenvolvimento — depende de: —
2. Aplicação v1 completa e testada localmente — depende de: fase 1 e do PRD
   `nudge-app-v1`
3. Verificação mínima automatizada na proposta de mudança (apenas testes) —
   depende de: fase 2
4. Imagens construídas e publicadas manualmente no registro, com identificador
   de build injetado — depende de: fase 2
5. Aplicação rodando em cluster local, com estado declarado em manifestos —
   depende de: fase 4
6. Produção: cluster gerenciado no provedor, entrada HTTPS, domínio e primeiro
   deploy público — depende de: fase 5
7. Declaração de estado organizada em base comum e sobreposições por ambiente
   — depende de: fases 5 e 6
8. Infraestrutura como código: provisionamento e destruição reprodutíveis do
   ambiente de produção — depende de: fase 6
9. Verificação e publicação automatizadas: pipeline completo com análise
   estática, cobertura, varredura de vulnerabilidade e release por versão —
   depende de: fases 3, 4 e 7
10. Convergência automática: reconciliador aplicando o estado declarado, fim do
    deploy manual — depende de: fases 7 e 9
11. Qualidade sob execução: testes ponta a ponta e de carga contra ambiente
    descartável — depende de: fases 9 e 10
12. Observabilidade: métricas, painel e alerta — depende de: fase 10
13. Continuidade: segredos cifrados no repositório, backup diário e drill de
    restauração — depende de: fases 8 e 12
