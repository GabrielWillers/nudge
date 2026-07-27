# Estado declarado do cluster

```
base/               recursos comuns aos dois ambientes
overlays/local/     cluster kind (ADR-0008)
overlays/prod/      produção — único caminho observado pelo reconciliador (ADR-0001)
```

Aplicar:

```sh
kubectl apply -k k8s/overlays/local
```

## O segredo, antes de qualquer coisa

Nenhum manifesto deste diretório contém segredo — só referências a um Secret
chamado `nudge-db`. Ele é criado à mão até a fase 13 introduzir segredo cifrado
no repositório, e **nunca** é versionado:

```sh
kubectl create secret generic nudge-db \
  --from-literal=postgres-password='<senha>' \
  --from-literal=database-url='postgresql+psycopg://nudge:<senha>@nudge-db:5432/nudge'
```

A senha aparece duas vezes porque o Postgres a consome solta em
`POSTGRES_PASSWORD` e a aplicação a consome embutida na URL de conexão. Os dois
valores têm de concordar.

Um Secret do Kubernetes é codificação em base64, não cifra: por si só não
satisfaz a invariante de segredo do PRD. É a fase 13 que fecha isso.

## O que ainda não está aqui

- **Domínio e TLS** (fase 6): o host da entrada em produção é marcador; o
  domínio público ainda não foi registrado.
- **Proteção de escrita** (fase 6): o ADR-0010 tirou a autenticação do
  aplicativo, então a lista compartilhada depende de autenticação básica na
  entrada. Sem ela, qualquer visitante escreve.
- **Supressão de `/healthz`, `/readyz` e `/metrics` na entrada**: exige
  configuração do controlador, não anotação — ver comentário em
  `base/ingress.yaml`.
- **Controlador de entrada e emissor de certificado**: cargas instaladas no
  cluster, não recursos deste repositório.
