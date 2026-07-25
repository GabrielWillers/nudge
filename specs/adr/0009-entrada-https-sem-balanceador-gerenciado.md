# ADR-0009: Expor a entrada pela porta do nó e emitir certificado por desafio de DNS, sem balanceador gerenciado

## Status

Aceito — 2026-07-25

## Contexto

A produção precisa de uma URL pública em HTTPS com certificado válido e
renovação automática. O caminho padrão em Kubernetes gerenciado é um Service do
tipo `LoadBalancer`: o cloud-controller-manager provisiona um balanceador do
provedor, que recebe IP estável e encaminha para o controlador de entrada.

No provedor escolhido esse balanceador custa cerca de US$ 12/mês, sobre um nó
de ~US$ 24/mês. É metade do orçamento restante para um recurso que, em um
cluster de um nó só, não balanceia nada: encaminha tráfego para o único destino
possível.

Há ainda uma restrição de emissão de certificado. O desafio por HTTP exige a
porta 80 alcançável no endereço público. As portas de NodePort ficam em faixa
alta, então sem balanceador seria preciso publicar 80 e 443 direto no nó. Já o
desafio por DNS não depende de porta nenhuma — e o DNS do provedor, que é
gratuito e já está na infraestrutura como código (ADR-0005), pode ser
manipulado por API pelo emissor de certificado.

## Alternativas consideradas

- **Service do tipo `LoadBalancer` com balanceador gerenciado** — a escolha
  correta para produção séria: IP estável, terminação fora do nó, caminho para
  múltiplos nós. Descartada por ora apenas por custo. É a primeira coisa a
  religar se a fragilidade de IP incomodar ou se um segundo nó entrar.
- **Desafio de certificado por HTTP** — dispensaria credencial de API de DNS,
  mas exige a porta 80 pública e falha silenciosamente sempre que a entrada
  estiver indisponível, inclusive na renovação.
- **Certificado manual ou autoassinado** — quebra o predicado de renovação sem
  intervenção e coloca aviso de segurança na cara de quem avalia o portfólio.
- **Proxy externo gratuito à frente do cluster (Cloudflare Tunnel)** — daria
  HTTPS e esconderia o IP do nó sem custo, mas move a terminação e o roteamento
  para fora do cluster, retirando do escopo demonstrável justamente a camada de
  entrada do Kubernetes.

## Decisão

Instalar o controlador de entrada publicando as portas 80 e 443 diretamente na
interface do nó, sem Service do tipo `LoadBalancer`. O registro DNS do domínio
aponta para o IP público do nó, gerenciado pelo provedor e declarado na
infraestrutura como código.

Certificado emitido e renovado automaticamente por desafio de DNS, usando
credencial de API do provedor guardada como Secret no cluster. A porta 80
responde exclusivamente redirecionamento para HTTPS.

A migração para balanceador gerenciado é tratada como mudança de uma linha —
tipo do Service e registro de DNS — e ganhará ADR próprio quando for feita.

## Consequências

+ Economiza cerca de US$ 12/mês, mantendo a produção dentro do orçamento com
  margem para a expansão temporária de nó prevista na fase 12.
+ Desafio por DNS funciona mesmo com a entrada fora do ar, e permite emitir
  certificado curinga se vier a ser necessário.
+ Toda a camada de entrada permanece dentro do cluster e sob o estado
  declarado: nada de roteamento acontece em serviço externo invisível.
+ A ausência do balanceador é pedagógica: quando ele for religado, o efeito do
  cloud-controller-manager fica observável por contraste.
- **O IP do nó não é estável.** Recriar, redimensionar ou reciclar o nó troca o
  IP e derruba o domínio até o DNS ser atualizado. É a fragilidade central desta
  decisão, e ela colide de frente com a prática de destruir o ambiente para
  economizar (ADR-0005): a descrição de infraestrutura precisa reconciliar o
  registro DNS a cada recriação, senão a produção volta inacessível.
- A credencial de API do DNS vive no cluster e tem permissão de escrita na zona
  do domínio: um segredo mais sensível que o do banco, e um alvo real.
- Publicar porta privilegiada na interface do nó acopla a entrada a esse nó
  específico e não sobrevive a um segundo nó sem repensar a exposição.
- Sem balanceador não há verificação de saúde externa nem terminação de TLS
  fora do nó: o próprio nó é o ponto único de falha para tudo.
- O tempo de propagação do desafio de DNS torna a emissão mais lenta e mais
  ruidosa de depurar que o desafio por HTTP.
