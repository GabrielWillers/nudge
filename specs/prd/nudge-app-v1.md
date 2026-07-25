# PRD: Nudge App v1

## Contexto

Uma plataforma de DevOps só se prova contra uma carga de trabalho real. Um
"hello world" não exercita banco de dados, migração de schema, segredo,
volume persistente, sonda de saúde nem isolamento entre usuários — e são
exatamente essas as coisas que a plataforma precisa demonstrar que sabe
operar. Um aplicativo de lembretes com contas de usuário exercita todas elas
com o menor escopo funcional possível.

Nudge é esse aplicativo: um lugar onde uma pessoa registra o que precisa
fazer e até quando, e consulta o que está vencendo. Ele é o meio, não o fim.
Seu escopo funcional fecha na v1 e não cresce depois (ver ADR-0004), porque
todo esforço adicional pertence à plataforma em volta dele.

Hoje nada existe: nenhuma linha de código, nenhum dado, nenhum ambiente.

## Atores

- **Visitante** — pessoa sem conta; espera poder criar uma e entrar.
- **Usuário registrado** — pessoa autenticada; espera criar, consultar,
  alterar e apagar os próprios lembretes, e não ver os de mais ninguém.
- **Orquestrador de containers** — sonda a aplicação para decidir se aquela
  instância está apta a receber tráfego e se precisa ser reiniciada.
- **Suíte de testes automatizada** — exercita os predicados abaixo a cada
  proposta de mudança; é a única guardiã de regressão, já que o escopo
  congela e ninguém mais vai revisar este código manualmente.
- **Avaliador técnico** — abre a aplicação publicada para confirmar que ela
  funciona de verdade e que a versão no ar é a que o repositório diz.

## Predicados

### Identidade e sessão

- [ ] Dado um e-mail ainda não cadastrado e uma senha de ao menos 8
      caracteres, quando o visitante solicita registro, então a conta passa a
      existir e a resposta não contém a senha em nenhuma forma.
- [ ] Dado um e-mail já cadastrado, quando o visitante solicita registro,
      então a operação é rejeitada e continua existindo exatamente uma conta
      com aquele e-mail.
- [ ] Dada uma senha com menos de 8 caracteres, quando o visitante solicita
      registro, então a operação é rejeitada e nenhuma conta é criada.
- [ ] Dada uma credencial válida, quando o visitante autentica, então recebe
      um token de acesso acompanhado do seu prazo de validade.
- [ ] Dada uma credencial inválida, quando o visitante autentica, então a
      recusa é indistinguível entre "e-mail não existe" e "senha errada".
- [ ] Dado um token ausente, malformado ou expirado, quando se acessa
      qualquer recurso de lembrete, então a operação é recusada por falta de
      autenticação e nenhum dado de lembrete é retornado.
- [ ] Dado um usuário autenticado na interface, quando o token expira e ele
      executa uma ação, então é levado de volta à tela de entrada.

### Lembretes

- [ ] Dado um usuário autenticado, quando cria um lembrete com título e
      instante de vencimento, então o lembrete passa a existir vinculado a
      ele e é retornado com um identificador.
- [ ] Dado um usuário autenticado com lembretes, quando lista seus
      lembretes, então recebe apenas os próprios, ordenados por vencimento
      crescente.
- [ ] Dado um lembrete pertencente a outro usuário, quando se tenta ler,
      alterar ou apagar, então a resposta é idêntica à de um identificador
      inexistente.
- [ ] Dado um lembrete próprio, quando se altera título, vencimento ou
      estado de concluído, então a leitura seguinte reflete a alteração.
- [ ] Dado um lembrete próprio, quando se apaga, então ele desaparece da
      listagem e a leitura direta passa a responder "não encontrado".
- [ ] Dado um instante de vencimento informado com fuso horário, quando é
      gravado e lido de volta, então representa o mesmo instante absoluto,
      qualquer que seja o fuso de quem lê.
- [ ] Dado um título vazio, um título acima de 200 caracteres ou um
      vencimento em formato inválido, quando se cria ou altera, então a
      operação é rejeitada indicando o campo inválido e nada é gravado.
- [ ] Dado um usuário sem nenhum lembrete, quando abre a interface, então vê
      um estado vazio explícito e não uma tela em branco ou um erro.

### Operabilidade

- [ ] Dada a aplicação em execução, quando se consulta o endpoint de saúde,
      então responde sucesso e informa o identificador do build em execução.
- [ ] Dada a aplicação sem conseguir alcançar o banco de dados, quando o
      orquestrador consulta o endpoint de prontidão, então a resposta é
      falha.
- [ ] Dada uma versão implantada, quando um usuário abre a interface, então o
      identificador do build está visível na tela.
- [ ] Dado o schema do banco em qualquer versão anterior, quando a aplicação
      sobe, então as migrações pendentes são aplicadas antes de ela começar a
      atender.

## Invariantes

- Todo lembrete tem exatamente um dono, e esse dono nunca muda.
- Nenhum usuário observa dado de outro usuário, em nenhum fluxo.
- Senha nunca é gravada nem devolvida em forma recuperável.
- Todo e-mail é único no sistema.
- Todo instante gravado está em UTC.
- O identificador do build exposto pela aplicação corresponde ao código que
  ela está de fato executando.
- A interface nunca apresenta estado autenticado sem um token válido em mãos.

## Restrições

- O escopo funcional congela ao fim da v1: nenhuma feature nova de produto
  entra depois (ADR-0004).
- Nenhum fluxo pode depender de entregar mensagem a um ser humano: não há
  envio de e-mail, push ou SMS em lugar nenhum do sistema.
- Senha mínima de 8 caracteres; título de lembrete máximo de 200 caracteres.
- Interface em português, língua única.
- Aplicação e banco dividem um nó de 4 GB com toda a plataforma: a soma de
  memória em regime normal fica em até 1 GB.
- Sem paginação: a interface e a API assumem volume de demonstração
  (dezenas de lembretes por usuário, não milhares).

## Fora de escopo

- Notificar o usuário de qualquer forma — o app não avisa ninguém; lembretes
  são consultados. Isto inclui e-mail, push, SMS e alerta no navegador.
- Refresh token, revogação de sessão, logout no servidor, expiração
  deslizante.
- Recuperação de senha e verificação de e-mail.
- Login social, OAuth, SSO.
- Lembretes recorrentes, subtarefas, etiquetas, prioridade, anexos, busca
  textual.
- Compartilhar lembrete com outra pessoa; papéis, permissões, administração.
- Aplicativo móvel, PWA, uso offline.
- Internacionalização e escolha de fuso horário pelo usuário.
- Exclusão de conta e exportação de dados.

## Critérios de aceite

- [ ] Todo predicado acima tem ao menos um teste automatizado
      correspondente, e a suíte inteira roda com um comando.
- [ ] Cobertura de linhas do backend ≥ 70%.
- [ ] A partir do clone, copiar o arquivo de ambiente de exemplo e subir o
      ambiente local deixa a interface usável em menos de 2 minutos, sem
      nenhum outro passo manual.
- [ ] Um avaliador consegue, pela interface e sem instruções: registrar-se,
      entrar, criar, alterar, concluir e apagar um lembrete.
- [ ] Nenhum segredo presente no repositório, confirmado por varredura
      automatizada.
- [ ] O identificador do build aparece tanto no endpoint de saúde quanto na
      interface, e os dois coincidem.

## Fases

1. Modelo de dados e migração inicial — depende de: —
2. Identidade: registro, autenticação e proteção de rota — depende de: fase 1
3. Lembretes: ciclo de vida completo com isolamento por dono — depende de:
   fase 2
4. Endpoints de saúde e prontidão, com exposição do identificador de build —
   depende de: fase 3
5. Interface: entrada, registro, listagem, formulário e estado vazio —
   depende de: fase 3
6. Suíte de testes cobrindo todos os predicados — depende de: fases 4 e 5
