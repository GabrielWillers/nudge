# ADR-0002: Adotar React + TypeScript + Vite no frontend e FastAPI + PostgreSQL no backend

## Status

Aceito — 2026-07-25

## Contexto

A aplicação é a carga de trabalho da plataforma, não o produto (ADR-0004).
A escolha de stack precisa satisfazer três coisas, nesta ordem: ser rápida de
levar a "funcionando", exercitar os recursos que a plataforma tem de
demonstrar (banco relacional com migração, volume persistente, segredo, sonda
de saúde, imagem de container) e ser familiar ao operador para não consumir o
tempo que pertence à infraestrutura.

Não há requisito de escala, latência ou volume que empurre para uma escolha
menos convencional: o tráfego previsto é de demonstração.

## Alternativas consideradas

- **Renderização no servidor (Next.js, Remix)** — traria um runtime Node em
  produção e acoplaria frontend e backend em um só processo, reduzindo o número
  de cargas distintas no cluster. Justamente por isso é pior aqui: dois
  serviços independentes exercitam mais Kubernetes do que um.
- **Backend em Go** — binário estático produz imagem final minúscula e sem
  runtime, o que ajudaria no teto de memória. Descartado por familiaridade: o
  tempo de aprendizado sairia do orçamento da plataforma.
- **SQLite** — dispensaria um serviço e um volume, mas eliminaria exatamente as
  demonstrações mais valiosas: StatefulSet, PVC, migração e backup.
- **Django** — traz admin e ORM prontos, encurtando a fase 2. Descartado porque
  o admin embutido convidaria a expandir o escopo funcional que o ADR-0004
  congela.

## Decisão

Frontend em React com TypeScript em modo estrito, empacotado por Vite e servido
em produção como conteúdo estático por um servidor web dentro do container.
Estado de servidor gerenciado por uma biblioteca de cache de requisição, não por
um repositório de estado global — praticamente todo o estado da aplicação é
cache de API.

Backend em FastAPI sobre Python, com PostgreSQL como banco, acesso via ORM e
migrações versionadas em arquivo. Configuração exclusivamente por variável de
ambiente.

Frontend e backend são servidos no mesmo domínio, o frontend na raiz e a API
sob um prefixo. O frontend chama a API por caminho relativo.

## Consequências

+ Dois serviços independentes no cluster, com ciclos de vida, sondas e
  requisitos de recurso distintos — mais superfície de Kubernetes para
  demonstrar com o mesmo produto.
+ Servir tudo no mesmo domínio elimina o problema de embutir a URL da API no
  build do frontend: uma única imagem de frontend serve qualquer ambiente. Como
  efeito colateral, não há requisição entre origens e portanto nada de CORS.
+ Migração versionada em arquivo dá um artefato concreto para discutir evolução
  de schema em deploy.
+ Stack convencional o bastante para que qualquer avaliador leia o código sem
  esforço.
- Dois ecossistemas de dependência para manter atualizados, dois conjuntos de
  ferramentas de análise estática e dois Dockerfiles.
- O prefixo compartilhado de domínio transfere responsabilidade para o
  controlador de entrada: um erro de roteamento lá derruba os dois serviços de
  uma vez.
- Python em container é imagem maior e partida mais lenta que um binário
  estático, o que pesa num nó de 4 GB.
- Sem renderização no servidor, a aplicação depende de JavaScript no cliente e
  não tem valor de SEO — irrelevante aqui, mas é uma porta que fica fechada.
