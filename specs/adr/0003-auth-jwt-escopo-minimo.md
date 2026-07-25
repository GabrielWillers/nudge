# ADR-0003: Autenticar com token JWT de acesso único e senha com hash Argon2

## Status

Aceito — 2026-07-25

## Contexto

A aplicação precisa de múltiplos usuários com isolamento de dados, porque
isolamento por dono é um dos comportamentos que a suíte de testes existe para
proteger. Isso exige identidade e sessão.

Identidade é, ao mesmo tempo, o maior bloco de código do escopo inicial e a
parte que menos contribui para o objetivo do projeto. Como o escopo funcional
congela na v1 (ADR-0004), não existe uma fase posterior para adicioná-la — ela
entra agora ou nunca. O risco concreto é o oposto: identidade completa
(refresh, revogação, recuperação de senha, verificação de e-mail) consumir
semanas e adiar indefinidamente a fase de Kubernetes, que é o ponto do
projeto.

Há uma restrição que fecha várias portas por si só: nenhum fluxo pode depender
de entregar mensagem a um ser humano, porque não há envio de e-mail em lugar
nenhum do sistema. Isso inviabiliza recuperação de senha e verificação de
e-mail independentemente de qualquer outra consideração.

## Alternativas consideradas

- **Provedor de identidade gerenciado (Auth0, Clerk, Supabase Auth)** —
  eliminaria o código de autenticação por completo. Descartado por dois
  motivos: adiciona dependência externa paga a um projeto com orçamento de
  US$ 30/mês, e move para fora do cluster um segredo e um fluxo que são bons
  objetos de demonstração.
- **Keycloak auto-hospedado** — resolveria identidade com padrão de mercado e
  seria uma carga interessante no cluster, mas consome sozinho mais memória que
  toda a aplicação no nó de 4 GB.
- **Sessão com cookie no servidor** — mais simples de revogar que JWT e
  imune a roubo de token por script. Descartado porque exigiria armazenamento
  de sessão compartilhado (mais um serviço no nó) e porque o frontend é uma
  aplicação de página única consumindo API.
- **Acesso único sem contas, protegido por senha no controlador de entrada** —
  seria o caminho mais curto, mas apagaria o isolamento por dono, que é o
  comportamento mais valioso da suíte de testes.

## Decisão

Implementar identidade própria, com escopo deliberadamente cortado:

- Registro e autenticação por e-mail e senha, senha com hash Argon2.
- Um único token de acesso JWT, assinado com segredo simétrico, com prazo de
  validade curto e explícito na resposta.
- Rotas de lembrete recusam requisição sem token válido; o dono é derivado do
  token, nunca aceito do cliente.
- Recusa de credencial inválida é indistinguível entre e-mail inexistente e
  senha errada.

Ficam explicitamente de fora: refresh token, revogação, logout no servidor,
recuperação de senha, verificação de e-mail, login social e papéis.

O segredo de assinatura é injetado por variável de ambiente e nunca tem valor
padrão embutido no código.

## Consequências

+ A fase de identidade cabe em horas, não semanas, e o cronograma da
  plataforma sobrevive.
+ Verificação de token sem consulta ao banco: nenhum armazenamento de sessão,
  nenhum serviço extra no nó.
+ O segredo de assinatura é um caso de uso real e concreto para demonstrar
  gestão de segredo no cluster e depois cifrado no repositório.
- **Não há como revogar um token emitido.** Vazamento de token dá acesso até o
  prazo expirar; a única mitigação é o prazo curto. Consequência assumida
  conscientemente, aceitável apenas porque os dados são fictícios.
- Trocar o segredo de assinatura invalida todas as sessões de uma vez.
- Usuário que esquecer a senha perde a conta: não existe recuperação, e não
  pode existir sem envio de e-mail.
- Prazo curto de token significa que o usuário é levado de volta à tela de
  entrada com alguma frequência, sem expiração deslizante para suavizar isso.
- Guardar o token no cliente é uma superfície de ataque que uma sessão com
  cookie de acesso restrito não teria.
