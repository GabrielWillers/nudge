# ADR-0006: Levar a aplicação a Kubernetes antes de automatizar o pipeline completo

## Status

Aceito — 2026-07-25

## Contexto

A sequência convencional é construir a verificação e a publicação
automatizadas primeiro, e só então usá-las para entregar em um ambiente. Ela é
convencional por um bom motivo: automatizar antes de fazer à mão evita
repetição manual e reduz erro humano.

O dono do projeto inverteu a ordem deliberadamente: Kubernetes primeiro, e a
plataforma amadurecendo em volta dele. O objetivo do projeto é aprender e
demonstrar Kubernetes; a integração contínua é meio.

A inversão tem uma consequência mecânica inescapável: sem publicação
automatizada, a imagem que vai para o cluster é construída e enviada da máquina
do operador. E tem um risco real: depurar manifesto de Kubernetes ao mesmo
tempo que se depura o aplicativo, sem rede de segurança, torna impossível
distinguir "o pod não sobe porque o manifesto está errado" de "o pod não sobe
porque o código está quebrado".

## Alternativas consideradas

- **Pipeline completo primeiro, depois Kubernetes** — a ordem convencional.
  Descartada por escolha do dono. Teria adiado o contato com Kubernetes por
  semanas, e a integração contínua construída antes de existir um destino de
  deploy tende a ser projetada no vazio.
- **Kubernetes primeiro, sem nenhuma verificação automatizada até a fase 9** —
  a leitura literal da inversão. Descartada pelo risco de ambiguidade de
  diagnóstico descrito acima.

## Decisão

Executar as fases nesta ordem: aplicação local → **verificação mínima** →
imagens à mão → cluster local → produção → sobreposições por ambiente →
infraestrutura como código → pipeline completo → convergência automática.

Duas salvaguardas acompanham a inversão:

1. **Verificação mínima antecipada (fase 3).** Uma configuração curta que roda
   apenas os testes dos dois componentes na proposta de mudança. Não é o
   pipeline: não há cobertura, varredura de vulnerabilidade, matriz de
   verificações nem publicação. É só a rede de segurança que permite depurar
   Kubernetes sabendo que o aplicativo está íntegro.
2. **Construção manual é registrada como transitória.** Enquanto durar,
   o identificador de build injetado na imagem mantém a rastreabilidade até o
   commit de origem, preservando a invariante do PRD. A fase 9 encerra a
   prática.

## Consequências

+ Contato com Kubernetes na primeira semana em vez de na quinta, que é o
  objetivo declarado do projeto.
+ O pipeline da fase 9 é projetado contra um destino de deploy que já existe e
  cujas necessidades são conhecidas, em vez de antecipadas.
+ Construir e publicar imagem à mão dezenas de vezes torna a automação da fase 9
  um alívio concreto e uma decisão informada, não um ritual copiado.
+ O histórico do repositório mostra a progressão manual → automatizada, que é
  uma narrativa mais convincente que um pipeline pronto no primeiro commit.
- Durante as fases 4 a 8, produção roda imagem construída em máquina de
  desenvolvimento: sem ambiente de build reprodutível e sujeita a "funciona na
  minha máquina".
- Publicação manual permite errar a versão, sobrescrever tag ou publicar código
  não commitado. Só o rigor do operador protege disso.
- A verificação mínima da fase 3 é trabalho que será substituído na fase 9 —
  descarte assumido, em troca de diagnóstico inequívoco enquanto se aprende
  Kubernetes.
- A ordem não é a que a maioria dos avaliadores espera; sem este ADR e o
  histórico para respaldá-la, pareceria descuido em vez de escolha.
