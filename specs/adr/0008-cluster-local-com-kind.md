# ADR-0008: Usar kind como cluster local, espelhando os componentes da produção

## Status

Aceito — 2026-07-25

## Contexto

Aprender Kubernetes e depurar manifestos direto no cluster pago é lento e
caro: cada tentativa passa por construir imagem, publicar no registro e
esperar reagendamento, e o nó de 4 GB não tem folga para experimento. É
preciso um cluster local onde iterar de graça.

O valor do cluster local depende inteiramente de quanto ele se parece com a
produção. Divergência entre local e produção é a fonte clássica de "funcionava
localmente" — e um ambiente local que ensina o comportamento errado é pior que
nenhum.

Os pontos onde distribuições locais costumam divergir são exatamente os que
importam aqui: controlador de entrada, StorageClass e provisionamento de
serviço do tipo balanceador.

## Alternativas consideradas

- **k3d (k3s em Docker)** — foi a escolha inicial, quando a produção também
  seria k3s. Deixou de fazer sentido ao definir Kubernetes gerenciado como
  produção (ADR-0005): o k3s embute Traefik como entrada, um balanceador de
  serviço próprio e um provisionador de armazenamento local, nenhum dos quais
  existe no cluster gerenciado. Aprender contra esses componentes ensinaria
  comportamento que não transfere.
- **minikube** — funcional e popular, mas com camada de VM ou driver própria
  que adiciona divergência de rede e um modelo de acesso a imagem local
  particular.
- **Só o cluster de produção** — descartado por custo, lentidão de iteração e
  falta de memória livre para experimentar.
- **Docker Compose como ambiente de desenvolvimento único** — não é cluster e
  não valida manifesto nenhum. Permanece no projeto, mas para outro fim: laço
  rápido de desenvolvimento do aplicativo, com recarga automática.

## Decisão

Usar kind como cluster local. Sobre ele, instalar explicitamente os mesmos
componentes da produção — em especial o mesmo controlador de entrada — de modo
que a diferença entre os ambientes fique confinada às sobreposições de
configuração da fase 7, e não à natureza do cluster.

Os dois ambientes locais coexistem com papéis distintos e documentados:

- **Docker Compose** — desenvolvimento do aplicativo: build local, recarga
  automática, portas expostas. Não valida manifesto.
- **kind** — validação do estado declarado: os mesmos manifestos da produção,
  com a sobreposição local.

Diferenças aceitas e registradas: a StorageClass local é a padrão do kind, não
o volume de bloco do provedor, e não há emissão real de certificado no
ambiente local.

## Consequências

+ Iteração em manifesto sem custo e em segundos, sem passar pelo registro de
  imagens.
+ O mesmo controlador de entrada nos dois lados: regra de roteamento e
  anotação testadas localmente valem em produção.
+ Cluster local descartável e recriável, o que torna o próprio processo de
  instalação dos componentes um artefato repetível e versionado.
+ Papéis separados evitam a confusão comum de tratar Compose como se validasse
  o deploy.
- Dois ambientes locais para manter: o Compose e o kind podem divergir do
  aplicativo se ambos não forem exercitados.
- A divergência de StorageClass permanece: comportamento de volume de bloco —
  latência, expansão, tempo de anexação — não se reproduz localmente.
- kind não tem cloud-controller-manager, então serviço do tipo balanceador não
  é provisionado e o acesso local depende de mapeamento de porta do nó.
- Componentes que em produção vêm do provedor ou de um operador precisam ser
  instalados à mão no kind, e essa instalação é mais uma coisa a manter em
  sincronia.
