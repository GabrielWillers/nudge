# ADR-0001: Manter frontend, backend, manifestos e infraestrutura em um repositório único

## Status

Aceito — 2026-07-25

## Contexto

O projeto tem quatro corpos de artefato: aplicação web (TypeScript), API
(Python), declaração de estado do cluster e descrição de infraestrutura. Um só
operador mantém todos. O objetivo do projeto é demonstrar o ciclo completo, o
que exige que uma mudança de código e a mudança de infraestrutura que a
acompanha sejam legíveis juntas.

Repositórios separados por componente são a norma em times grandes porque
isolam donos e cadências de release. Aqui não há times, não há donos distintos
e a cadência é uma só.

## Alternativas consideradas

- **Um repositório por componente (app, manifestos, infra)** — obrigaria a
  versionar contratos entre repositórios e duplicar a automação de verificação
  três vezes. Para um operador só, o custo de coordenação não compra nada.
- **Repositório separado apenas para os manifestos** (padrão comum em GitOps,
  para evitar que o reconciliador reaja a commits de código) — resolve um
  problema real de laço de realimentação, mas cria dois históricos que precisam
  ser lidos em paralelo para reconstituir uma mudança. Mitigável com
  sobreposições por ambiente e um caminho vigiado pelo reconciliador.

## Decisão

Usar um repositório único, `nudge`, com `backend/`, `frontend/`, `k8s/`,
`infra/` e `specs/` como diretórios de primeiro nível. A automação de
verificação roda por componente dentro do mesmo repositório, filtrando por
caminho alterado quando isso reduzir tempo de execução.

## Consequências

+ Uma mudança de código e a mudança de manifesto correspondente cabem na mesma
  proposta de mudança e no mesmo commit — exatamente o que um avaliador precisa
  ler.
+ Uma única configuração de verificação, de varredura de dependências e de
  publicação de versão.
+ Uma tag de versão descreve o sistema inteiro, sem matriz de compatibilidade
  entre repositórios.
- O reconciliador de GitOps observa o mesmo repositório onde o código muda:
  será preciso restringi-lo a um caminho para ele não reagir a commits
  irrelevantes.
- A verificação dispara para os dois componentes mesmo quando só um mudou, a
  menos que filtros por caminho sejam mantidos — e filtro por caminho é uma
  fonte conhecida de proposta que passa sem ter sido de fato verificada.
- Versão semântica única acopla os componentes: publicar correção só do
  frontend ainda incrementa a versão do sistema todo.
