# Assinatura da empresa (Admin › Assinatura)

**Dono:** arquiteto · **Versão:** 14 out 2026 (T-183) · **App:** `plataforma` (lê e grava no `public`, servido no host da empresa) · **Regras:** PLT-01, PLT-02, PLT-03, PLT-04, PLT-05, AUT-13, tabela de estados da empresa · **ADR:** 0007, 0023 · **Telas:** Admin-Assinatura (desktop e celular)

Decisão do dono em 14 out 2026: a tela `Admin-Assinatura` entra inteira no MVP. Este contrato completa o que `GET /api/assinatura/` (`plataforma.md`, "Do lado da empresa") ainda não entregava, levantado na T-170: mudar e comparar planos, forma de pagamento, faturas, dados da nota fiscal, o cartão do plano Completo e a data da 1ª fatura. "Cancelar assinatura" (`PLT-06`, tela `Admin-Cancelar`) e pausar estão com o produto e **não** fazem parte deste contrato.

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (itens 2 e 3 e apoio do `public`).

> **Pontos que dependem do produto.** Onde a regra não diz, o contrato marca **[D-n]** e segue a opção recomendada, para backend e frontend poderem começar. As perguntas estão no fim ("Decisões pedidas ao produto") e no backlog, seção da T-183. Se o produto escolher outra opção, muda só o trecho marcado.

---

## Quem usa

- `GET /api/assinatura/` continua para **todos os perfis** (as telas de Filiais, Usuários e Veículos leem o `uso`). Os blocos novos do administrador (`forma_pagamento`, `dados_fiscais`, `oferta`, `acoes`) vêm **ausentes** para os outros perfis, como o bloco do vendedor em `veiculos.md`.
- Todas as outras rotas deste contrato são **só do administrador** (tabela de perfis: "Administração ... assinatura"). Outro perfil: 403 `{ "codigo": "permissao", "mensagem": "Só o administrador mexe na assinatura" }`.
- Suporte Giro dentro da empresa (`PLT-07`): só lê. Nenhuma escrita deste contrato aceita token de suporte, nem com "ver e editar" (dinheiro e dados fiscais da empresa são decisão do administrador): 403 `{ "codigo": "PLT-07", "mensagem": "O suporte não mexe na assinatura da empresa" }`.

### Estado da empresa e o que cada rota aceita

`somente_leitura` (empresa `suspensa`, `pausada` ou `cancelada`) faz todo endpoint de escrita responder 403 `empresa_sem_operacao` (`plataforma.md`). **Exceção:** a empresa `suspensa` precisa conseguir pagar para voltar a `ativa` na hora (tabela de estados), então estas rotas continuam abertas para ela: `PUT forma-pagamento/`, `POST faturas/{codigo}/pagar/` e `PATCH dados-fiscais/`. A exceção fica numa lista explícita na permissão de `somente_leitura`, com teste.

| Rota | `em_teste` | `ativa` | `inadimplente` | `suspensa` | `pausada`, `cancelada` |
| --- | --- | --- | --- | --- | --- |
| ler (`GET`) | sim | sim | sim | sim | sim |
| mudar de plano | sim | sim | não [D-5] | não [D-5] | não |
| forma de pagamento | sim | sim | sim | sim | não |
| pagar fatura | sim | sim | sim | sim | não |
| dados fiscais | sim | sim | sim | sim | não |

Fora da tabela: 409 `{ "codigo": "transicao_empresa", "mensagem": "<texto do caso>" }`, com os textos de cada rota abaixo.

---

## GET /api/assinatura/ (campos novos)

Os campos de hoje (`plano`, `status`, `teste`, `faixa_aviso`, `uso`, `somente_leitura`) não mudam. Entram:

```json
{
  "plano": { "id": 2, "nome": "Profissional", "preco_contratado_centavos": 44900, "ciclo": "mensal" },
  "status": "em_teste",
  "teste": { "inicio": "2026-10-07", "fim": "2026-10-21", "dias_restantes": 14 },
  "proxima_fatura": { "vencimento": "2026-10-22", "valor_centavos": 44900, "descricao": "Plano Profissional · 22 out a 21 nov" },
  "plano_proximo": null,
  "faixa_aviso": null,
  "uso": { "...": "como hoje" },
  "somente_leitura": false,

  "forma_pagamento": {
    "forma": null,
    "situacao": { "codigo": "sem_forma", "rotulo": "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso.", "tom": "alerta" },
    "cartao": null,
    "prazo": "2026-10-21"
  },
  "dados_fiscais": {
    "razao_social": "Moto Rápida Locações Ltda",
    "cnpj": "12345678000195",
    "email_cobranca": "financeiro@motorapida.com.br"
  },
  "oferta": {
    "plano": { "id": 3, "nome": "Completo" },
    "recursos_a_mais": ["dominio_proprio", "api_integracoes", "suporte_prioritario"],
    "sem_limite": ["veiculos", "filiais", "usuarios"]
  },
  "acoes": { "mudar_plano": true, "escolher_forma_pagamento": true, "editar_dados_fiscais": true, "cancelar": false }
}
```

- `teste.inicio` é novo (a tabela de faturas mostra a linha do teste com essa data). `teste` é `null` fora de `em_teste`.
- **`proxima_fatura`** é o que a tela mostra em "R$ 449,00 por mês, a partir de …". A 1ª fatura vence **no dia seguinte ao fim do teste** (`PLT-01`): Moto Rápida, teste de 07 a 21 out, vence em **22 out**. A referência diz "a partir de 21 out" e erra: vale a regra (a tela mostra `proxima_fatura.vencimento`, correção pedida ao design-system). Com um downgrade agendado, `valor_centavos` já é o do plano menor. `null` em `pausada` e `cancelada`. A descrição segue o período da fatura [D-2].
- **`plano_proximo`**: `{ "id", "nome", "vale_em": "2026-11-22" }` quando há downgrade agendado (`PLT-04`); senão `null`. A tela mostra "Muda para Essencial em 22 nov" com `vale_em`.
- **`forma_pagamento`**:
  - `forma`: `cartao`, `pix_automatico`, `boleto` ou `null`.
  - `cartao`: `{ "bandeira": "visa", "final": "4242" }` quando já há cartão guardado no parceiro; senão `null`. O Giro nunca tem o número do cartão (ADR 0023).
  - `situacao.codigo`, na ordem (a primeira que valer):

    | `codigo` | Quando | `rotulo` (exemplo) | `tom` |
    | --- | --- | --- | --- |
    | `sem_forma` | `forma` nula | "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso." (em teste; fora dele, "Nenhuma cadastrada.") | `alerta` |
    | `aguardando_autorizacao` | Pix automático pedido e ainda não autorizado no banco | "Autorize o Pix automático no app do seu banco." | `alerta` |
    | `cartao_recusado` | a última cobrança no cartão foi recusada (`PLT-02`) | "O cartão foi recusado. Tentamos de novo amanhã." | `perigo` |
    | `cartao_na_primeira_fatura` | cartão escolhido e ainda sem cartão guardado [D-6] | "Você cadastra o cartão ao pagar a primeira fatura." | `info` |
    | `ativa` | resto | "Cartão Visa final 4242 · cobrança automática todo mês", "Pix automático autorizado", "Boleto enviado por e-mail 5 dias antes" [D-7] | `sucesso` |
  - `prazo`: último dia para escolher sem perder o acesso = `teste.fim` em `em_teste` [D-1]; `null` fora do teste.
- **`dados_fiscais`**: ver `PATCH /api/assinatura/dados-fiscais/`. CNPJ só com dígitos.
- **`oferta`** é o cartão "Precisa de NF-e ou domínio próprio?": o primeiro plano ativo acima do atual pela `ordem`, com os `recursos` dele que o atual não tem e os limites que ele não tem (`sem_limite`). `null` quando a empresa já está no plano mais alto (Completo) ou não há plano acima. O texto do cartão é montado só com o que vier aqui; a referência cita "emissão de notas" e "portal do cliente", que não existem nos recursos, e "assinatura digital", que já é do Profissional (`contrato_digital`) [D-10].
- **`acoes`** já cruza perfil, estado da empresa e a tabela acima; o frontend mostra só o que vier `true`. `cancelar` fica `false` até o contrato da `PLT-06` (produto): o link "Cancelar assinatura" fica como a T-170 deixou.

Caso do seed: Moto Rápida em 07 out → `proxima_fatura` 22 out, 44900, `forma` nula com `sem_forma` e prazo 21 out, `oferta` Completo, `acoes` todas `true` menos `cancelar`.

---

## GET /api/assinatura/planos/

Administrador. "Mudar de plano" e "Comparar planos" abrem a mesma lista. Sem paginação.

```json
{ "ciclo_atual": "mensal",
  "resultados": [
    { "id": 1, "nome": "Essencial", "ordem": 1, "atual": false,
      "preco_mensal_centavos": 19900, "preco_anual_centavos": 199000,
      "limite_veiculos": 30, "limite_filiais": 1, "limite_usuarios": 3,
      "recursos": ["locacoes_vistoria", "contas_receber"],
      "mudanca": "downgrade",
      "cabe": false,
      "excede": { "veiculos": { "usado": 86, "limite": 30 }, "usuarios": { "usado": 5, "limite": 3 } } },
    { "id": 2, "nome": "Profissional", "ordem": 2, "atual": true, "...": "...", "mudanca": null, "cabe": true, "excede": {} },
    { "id": 3, "nome": "Completo", "ordem": 3, "atual": false,
      "preco_mensal_centavos": 89900, "preco_anual_centavos": 899000,
      "limite_veiculos": null, "limite_filiais": null, "limite_usuarios": null,
      "recursos": ["...todos..."], "mudanca": "upgrade", "cabe": true, "excede": {} }
  ] }
```

- Só planos `ativo=true`, mais o plano atual mesmo se desativado (`PLT-05`: quem já assina continua).
- Preço mostrado é o de **tabela**; o atual mostra também `preco_contratado_centavos` (pode ser diferente, `PLT-05`).
- `mudanca`: `upgrade` se o plano tem `ordem` maior, `downgrade` se menor, `null` no atual. `cabe` e `excede` usam a mesma contagem do `uso` (`PLT-03`, `PLT-04`): Moto Rápida não cabe no Essencial (86 de 30 veículos, 5 de 3 usuários; 1 filial cabe).
- Os rótulos dos `recursos` são os mesmos da `Compra-Planos`, no frontend (lista fechada em `plataforma.md`, "Planos").

## POST /api/assinatura/mudanca-plano/simular/

Administrador. Não grava nada (ADR 0005). Corpo: `{ "plano_id": 3, "ciclo": "mensal" }`.

200:
```json
{ "tipo": "upgrade", "vale_em": "2026-10-07",
  "preco_novo_centavos": 89900,
  "diferenca_centavos": 0,
  "fatura_diferenca": null,
  "proxima_fatura": { "vencimento": "2026-10-22", "valor_centavos": 89900, "descricao": "Plano Completo · 22 out a 21 nov" },
  "mensagem": "O plano Completo vale agora. A primeira fatura, em 22 out, fica em R$ 899,00." }
```

- **Upgrade** (`PLT-04`): vale na hora.
  - Em `em_teste`: não há cobrança; muda o plano, o `preco_contratado_centavos` passa ao preço de tabela do plano novo (`PLT-05`: é assinatura nova) e a 1ª fatura (ainda `aberta`, sem cobrança no parceiro ou com a cobrança refeita) passa ao valor novo.
  - Em `ativa`: cobra a diferença proporcional [D-3]. Recomendação: `(preço novo − preço contratado) × dias que faltam no período ÷ dias do período`, contando o dia da mudança, `ROUND_HALF_UP` no centavo (ADR 0009), numa **fatura avulsa** (`tipo = diferenca_plano`) que vence em 3 dias, cobrada pela forma cadastrada (no cartão, cobra na hora). Ex. com essa opção: período de 22 out a 21 nov (31 dias), mudança de Profissional para Completo em 01 nov → 45000 × 21 ÷ 31 = 30483,87 → **30484** (R$ 304,84). `fatura_diferenca` traz `{ "valor_centavos": 30484, "vencimento": "2026-11-04" }`.
- **Downgrade** (`PLT-04`): só se o uso couber; vale na próxima fatura. Não cabe → 422 (abaixo). Cabe → `tipo: "downgrade"`, `vale_em` = vencimento da próxima fatura, `diferenca_centavos: 0`, `mensagem` "O plano Essencial vale a partir de 22 nov. Até lá, você continua no Profissional." Em `em_teste`, o downgrade vale na hora (não há fatura paga a respeitar) e a 1ª fatura passa ao valor novo [D-3].
- **Ciclo** diferente do atual (mensal ↔ anual): 422 `{ "codigo": "mudanca_ciclo", "mensagem": "Para mudar entre mensal e anual, fale com o suporte." }` até o produto decidir [D-4].
- Mesmo plano e ciclo: 422 `{ "codigo": "mesmo_plano", "mensagem": "Este já é o seu plano." }`.
- Plano inativo (que não é o atual): 404.

## POST /api/assinatura/mudanca-plano/

Administrador. Mesmo corpo do simular, mais `"confirmar_valor_centavos"` = `diferenca_centavos` do simular (se o valor mudou entre simular e confirmar, 409 `{ "codigo": "valor_mudou", "detalhes": { "diferenca_centavos": ... } }` e nada é gravado).

200: o corpo de `GET /api/assinatura/` já atualizado.

Erros:
- 422 `{ "codigo": "PLT-04", "mensagem": "Seu uso não cabe no plano Essencial. Desative veículos ou usuários antes de mudar.", "detalhes": { "veiculos": { "usado": 86, "limite": 30 }, "usuarios": { "usado": 5, "limite": 3 } } }`.
- 409 `transicao_empresa` "Pague a fatura em atraso antes de mudar de plano." (`inadimplente`, `suspensa`) [D-5].
- 422 `mudanca_ciclo`, `mesmo_plano` como no simular.

Serviço único `plataforma.services.mudar_plano(empresa, plano, ciclo, por, motivo=None)`, o mesmo da ação `mudar-plano` do painel da plataforma (`plataforma.md`, "Ações sobre a empresa"). Trava a `Empresa` e o `UsoEmpresa` (`SELECT ... FOR UPDATE`) para a conta do uso e a mudança serem da mesma foto. Downgrade grava `plano_proximo`; a tarefa da virada da fatura aplica. Auditoria `empresa.mudar_plano` no `public` (categoria cobrança) e na auditoria da empresa (categoria configurações), com plano antigo, novo, ciclo e a diferença.

## DELETE /api/assinatura/mudanca-plano/

Administrador. Desfaz o downgrade agendado (`plano_proximo` → nulo) [D-5]. 200 com o corpo de `GET /api/assinatura/`. Sem downgrade agendado: 404.

---

## PUT /api/assinatura/forma-pagamento/

Administrador. Corpo: `{ "forma": "cartao" | "pix_automatico" | "boleto" }`. Os dados do cartão **nunca** passam pelo Giro (ADR 0023); não há campo de cartão neste corpo.

200:
```json
{ "forma_pagamento": { "forma": "pix_automatico", "situacao": { "codigo": "aguardando_autorizacao", "...": "..." }, "cartao": null, "prazo": "2026-10-21" },
  "proximo_passo": { "tipo": "autorizar_pix", "pix_copia_e_cola": "000201...", "expira_em": "2026-10-08T15:00:00Z" } }
```

`proximo_passo` por forma:

| Forma | O que o backend faz | `proximo_passo` |
| --- | --- | --- |
| `boleto` | grava a forma. O boleto de cada fatura é criado no parceiro N dias antes do vencimento e vai para o `email_cobranca` [D-7]. | `null` |
| `pix_automatico` | cria a autorização recorrente na conta principal (`criar_autorizacao_recorrente`, frequência do ciclo, valor = `preco_contratado_centavos`). A forma fica `aguardando_autorizacao` até o webhook confirmar. | `{ "tipo": "autorizar_pix", "pix_copia_e_cola", "expira_em" }`; o frontend desenha o QR a partir do copia e cola (como na T-029). |
| `cartao` | grava a forma. O cartão é digitado **na página do parceiro**, ao pagar uma fatura; o parceiro guarda o cartão, e as faturas seguintes são cobradas nele sem passar pela tela [D-6]. Se há fatura `aberta` ou `atrasada` agora, devolve o link dela. | `{ "tipo": "pagina_parceiro", "url": "https://...", "fatura": "FAT-0001" }` ou `null` (em teste, com a 1ª fatura ainda longe [D-6]) |

- Trocar de forma cancela a anterior no parceiro: autorização do Pix automático cancelada (`cancelar_autorizacao`) e token do cartão esquecido. Cobranças já emitidas de faturas abertas continuam valendo até o vencimento; a próxima sai pela forma nova.
- `em_teste` → `ativa` quando a forma fica cadastrada [D-1]. Com boleto, na hora; com Pix automático, quando o banco autoriza; com cartão, como decidido em [D-6].
- Parceiro fora do ar: 503 `{ "codigo": "parceiro_indisponivel", "mensagem": "Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos." }` (o mesmo da T-029), nada gravado. Parceiro recusou: 422 `parceiro_recusou` com o motivo.
- Auditoria `assinatura.forma_pagamento` (forma antiga e nova; nunca token nem dado do cartão), nos dois lugares.

---

## GET /api/assinatura/faturas/

Administrador. Lista da tabela "Faturas", da mais nova para a mais antiga, 25 por página. `?status=aberta|paga|atrasada|cancelada`.

```json
{ "resultados": [
    { "tipo": "fatura", "codigo": "FAT-0001", "vencimento": "2026-10-22",
      "descricao": "Plano Profissional · 22 out a 21 nov", "periodo": { "inicio": "2026-10-22", "fim": "2026-11-21" },
      "valor_centavos": 44900, "status": "aberta", "forma": null, "pago_em": null,
      "situacao": { "codigo": "sem_forma", "rotulo": "Sem forma de pagamento", "tom": "alerta" },
      "acoes": { "pagar": false, "recibo": false } },
    { "tipo": "teste", "codigo": null, "vencimento": "2026-10-07",
      "descricao": "Teste grátis de 14 dias", "periodo": { "inicio": "2026-10-07", "fim": "2026-10-21" },
      "valor_centavos": 0, "status": null, "forma": null, "pago_em": null,
      "situacao": { "codigo": "teste_ativo", "rotulo": "Ativo", "tom": "info" },
      "acoes": { "pagar": false, "recibo": false } }
  ],
  "proximo": null, "anterior": null }
```

- A linha do teste não é uma `FaturaAssinatura`: a API a acrescenta no fim da lista (última página) com os dados do teste, `tipo: "teste"`. Depois do teste, `situacao` `teste_concluido` "Concluído", `neutro`. Empresa que não passou por teste não tem a linha.
- A 1ª fatura existe desde a criação da empresa (`criar_empresa`, `aberta`, vencimento `teste_fim + 1`, valor do plano), como já mostra `faturas_recentes` no painel da plataforma. Estender o teste (`plataforma.md`) move o vencimento e o período dela.
- `situacao`, na ordem:

  | `codigo` | Quando | `rotulo` | `tom` |
  | --- | --- | --- | --- |
  | `paga` | `paga` | "Paga em 22 out" | `sucesso` |
  | `cancelada` | `cancelada` | "Cancelada" | `neutro` |
  | `atrasada` | `atrasada` | "12 dias atrasada" | `perigo` |
  | `cartao_recusado` | aberta ou atrasada com a última tentativa no cartão recusada | "Cartão recusado · nova tentativa amanhã" | `perigo` |
  | `sem_forma` | aberta e a empresa sem forma | "Sem forma de pagamento" | `alerta` |
  | `aguardando` | aberta com forma | "Vence em 22 out" (ou "Vence hoje") | `info` |

- `descricao`: "Plano <nome> · <início> a <fim do período>" (mensal) ou "Plano <nome> anual · out 2026 a out 2027"; a fatura de diferença, "Mudança para o plano Completo · 01 a 21 nov" [D-2], [D-3]. A referência mostra "outubro a novembro"; o período exato depende de [D-2].
- `acoes.pagar`: `aberta` ou `atrasada`, a empresa tem forma, e o estado permite (tabela do início). `acoes.recibo`: `paga`.
- `forma`: a forma pela qual foi paga (`cartao`, `pix`, `boleto`); `null` em aberto.

## GET /api/assinatura/faturas/{codigo}/

Administrador. Uma linha do formato acima, mais:
- `cobranca`: `{ "forma": "boleto", "linha_digitavel": "...", "url_boleto": "https://...", "pix_copia_e_cola": null, "url_pagina": null, "vencimento": "2026-10-22" }` quando há cobrança emitida no parceiro; senão `null`.
- `recibo_url`: comprovante do parceiro quando `paga`; senão `null`. É link do parceiro com validade dele; o Giro não gera PDF de recibo no MVP.

`codigo` de outra empresa: 404.

## POST /api/assinatura/faturas/{codigo}/pagar/

Administrador. Para pagar agora uma fatura `aberta` ou `atrasada` (o botão aparece com `acoes.pagar`). Sem corpo: usa a forma cadastrada.

200: o `cobranca` do detalhe, já emitido. Para `cartao`, `url_pagina` é a página do parceiro onde o cartão é digitado (e fica guardado para as próximas, ADR 0023). Para `pix_automatico`, a cobrança avulsa por Pix da fatura (a autorização recorrente só cobra no vencimento). Se já existe cobrança válida no parceiro, devolve a mesma; não cria duas (como a T-029 faz nas contas a receber).

Erros: 409 `{ "codigo": "fatura_nao_pagavel", "mensagem": "Esta fatura já foi paga ou cancelada." }`; 422 `{ "codigo": "sem_forma_pagamento", "mensagem": "Escolha a forma de pagamento antes." }`; 503 `parceiro_indisponivel`; 422 `parceiro_recusou`.

A baixa **nunca** vem desta rota: vem do webhook (`financeiro.md`, "Webhooks", "O mesmo fluxo vale para a `FaturaAssinatura`"), que consulta a cobrança no parceiro antes de baixar. Fatura paga → `paga`, `pago_em`, `forma`; `inadimplente` ou `suspensa` sem outra fatura atrasada → `ativa` na hora (tabela de estados); auditoria `fatura_assinatura.pagar` (ator `sistema`, regra `PLT-02`).

---

## PATCH /api/assinatura/dados-fiscais/

Administrador. Corpo (parcial): `{ "razao_social": "Moto Rápida Locações Ltda", "email_cobranca": "financeiro@motorapida.com.br" }`.

200: `{ "dados_fiscais": { "razao_social", "cnpj", "email_cobranca" } }`.

- `email_cobranca` é campo novo da `Empresa`. Nasce igual ao e-mail do administrador da compra (`responsavel_email`). Recebe as faturas, o boleto, a régua da assinatura (`PLT-02`, `AUT-13`) e o comprovante. O WhatsApp da régua continua no `responsavel_telefone`.
- `razao_social`: até 150 caracteres. É a mesma `Empresa.razao_social` do painel da plataforma e do bloco "Dados da empresa" da `Admin-Marca` (fora do contrato de `empresas.md`): uma só origem, no `public`. Mudar a razão social atualiza o cadastro do pagador no parceiro (conta principal) antes da próxima cobrança.
- **CNPJ não muda por aqui**: o campo não é aceito (400 `validacao` "O CNPJ não muda por aqui. Fale com o suporte."). Trocar o CNPJ é trocar quem contrata, e fica com a equipe da plataforma [D-9].
- A emissão da nota fiscal da assinatura (NFS-e do Giro para a empresa) não está nas regras [D-9]: até a decisão, o bloco só guarda e mostra os dados.
- Auditoria `empresa.dados_fiscais` nos dois lugares, com antes e depois.

---

## Faturas, cobrança e régua (sem rota; para o backend)

O que precisa existir no `public` para a tela mostrar dados reais. Não há rota nova da plataforma aqui; `Plat-Cobranca` continua na fase 2.

- **Conta principal** do Giro no parceiro (ADR 0007): `ContaPagamentoRef` sem subconta, chave do ambiente (`GIRO_ASAAS_CHAVE_API`), como a T-029 já deixou preparado (CA-029-18). O webhook da conta principal tem token próprio, guardado só como hash em configuração (`GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH`), e a view do webhook procura primeiro a `ContaPagamento` e, se o token for o da conta principal, trata como fatura da assinatura no `public`.
- **Pagador**: cada empresa vira um cliente na conta principal (`cliente_externo_id` em `FormaPagamentoAssinatura`), com razão social, CNPJ e `email_cobranca`, criado na primeira cobrança, com as notificações do parceiro desligadas (as mensagens são do Giro).
- **Geração das faturas** (tarefa diária `plataforma.gerar_faturas`, 06:00): cria a fatura do período seguinte quando a atual vence, com o `preco_contratado_centavos` (ou o do `plano_proximo`, que é aplicado nessa hora). Única por `(empresa, competencia)` para `tipo = mensalidade`.
- **Emissão no parceiro** N dias antes do vencimento [D-7]: boleto (e e-mail), cobrança do Pix automático pela autorização (o parceiro pede de 2 a 10 dias úteis antes, ver T-029), cartão no dia do vencimento pelo token guardado.
- **Régua `AUT-13`** às 09:00, pela `PLT-02`: D-3 lembrete por e-mail; D0 e-mail + WhatsApp; D+3 e-mail + WhatsApp; D+7 aviso de suspensão (e-mail e tarefa de ligação para a equipe, fase 2 a tela); D+15 suspensão. Cartão recusado: uma nova tentativa no dia seguinte (`tentativas_cartao`).
- **Transições da empresa** pelo serviço de estados: fatura vencida sem pagamento → `inadimplente` (D+1); D+15 → `suspensa`; paga → `ativa`. Fim do teste sem forma cadastrada → `suspensa` no dia seguinte ao fim [D-1]. Cada transição grava auditoria no `public` e na empresa, e a `faixa_aviso` já existente passa a ter dados reais.

---

## Erros deste contrato

| HTTP | `codigo` | Quando |
| --- | --- | --- |
| 403 | `permissao` | perfil que não é administrador |
| 403 | `PLT-07` | escrita com token de suporte |
| 403 | `empresa_sem_operacao` | `pausada`, `cancelada` (a `suspensa` paga, ver o início) |
| 409 | `transicao_empresa` | mudar de plano fora de `em_teste` e `ativa` [D-5] |
| 409 | `valor_mudou` | diferença do upgrade mudou entre simular e confirmar |
| 409 | `fatura_nao_pagavel` | fatura paga ou cancelada |
| 422 | `PLT-04` | downgrade com uso que não cabe |
| 422 | `mudanca_ciclo`, `mesmo_plano` | ver mudança de plano |
| 422 | `sem_forma_pagamento` | pagar sem forma cadastrada |
| 422 | `parceiro_recusou` | o parceiro recusou (mensagem dele, sem o nome do parceiro) |
| 503 | `parceiro_indisponivel` | o parceiro não respondeu |

---

## Decisões pedidas ao produto

O contrato segue a recomendação de cada uma; a resposta pode mudar só o trecho marcado.

- **[D-1] Quando a empresa em teste vira `ativa`, e o que acontece no fim do teste.** A tabela de estados diz, em `em_teste`, "forma de pagamento cadastrada → `ativa`", e em `ativa`, "entra quando a 1ª fatura é paga". A 1ª fatura vence no dia seguinte ao fim do teste (`PLT-01`), e "14 dias sem pagamento → `suspensa`" cai antes dela. **Recomendo:** forma cadastrada → `ativa` (a 1ª fatura segue a régua como as outras); sem forma até o fim do teste → `suspensa` no dia seguinte (22 out), e volta a `ativa` ao cadastrar e pagar. Bate com "Escolha até 21 out para não perder o acesso" da tela e com "avisamos 3 dias antes do fim do teste" da `Compra-Checkout`.
- **[D-2] Dia de vencimento e período das faturas seguintes.** A regra só diz a 1ª. **Recomendo:** todo mês no mesmo dia da 1ª (Moto Rápida: dia 22), período de 22 a 21; em mês sem esse dia, o último dia do mês. Anual: uma fatura de 10 mensalidades por 12 meses. `competencia` = mês do início do período.
- **[D-3] Diferença proporcional do upgrade (`PLT-04`).** A regra diz "cobra a diferença proporcional" sem a conta nem o jeito de cobrar. **Recomendo:** (preço novo − preço contratado) × dias que faltam ÷ dias do período, contando o dia da mudança, numa fatura avulsa que vence em 3 dias (no cartão, cobra na hora); em teste, nada a cobrar, e a 1ª fatura passa ao valor novo (vale também para o downgrade em teste). Ex.: R$ 304,84 de Profissional para Completo em 01 nov.
- **[D-4] Mudar entre mensal e anual pela tela.** A regra não fala. **Recomendo:** fora do MVP (o suporte faz pela plataforma); a tela compara os planos no ciclo atual.
- **[D-5] Em que estados a empresa muda de plano, e se o downgrade agendado pode ser desfeito.** **Recomendo:** só em `em_teste` e `ativa` (inadimplente paga antes); o downgrade agendado pode ser desfeito até a virada.
- **[D-6] Cartão sem cobrar na hora.** A tela promete "cobrança automática todo mês", a `Compra-Checkout` diz "nada é cobrado agora", e o Giro não deve receber o número do cartão (ADR 0023). **Recomendo:** escolher "cartão" só grava a forma; o cartão é digitado na página do parceiro ao pagar a 1ª fatura (o link vai no e-mail do D-3 e no botão "Pagar"), e daí em diante a cobrança é automática. Para a regra D-1, a forma "cartão" já conta como cadastrada. A outra opção (guardar o cartão no teste com uma pré-autorização estornada) depende do parceiro e fica para o backend testar no sandbox, se o produto preferir.
- **[D-7] Antecedência da cobrança.** A tela diz "Boleto enviado por e-mail 5 dias antes"; a régua (`PLT-02`) começa no D-3; o Pix automático precisa ser emitido de 2 a 10 dias úteis antes (T-029). **Recomendo:** boleto e Pix automático emitidos 5 dias antes do vencimento (boleto vai por e-mail nesse dia), cartão cobrado no dia; a régua continua como está.
- **[D-8] O que o cartão de crédito recusado faz depois da nova tentativa.** `PLT-02` diz "tenta de novo no dia seguinte". **Recomendo:** uma nova tentativa só; depois, a régua segue (a empresa pode pagar por outro meio pelo botão "Pagar").
- **[D-9] Nota fiscal da assinatura e troca de CNPJ.** As regras não dizem se o Giro emite a NFS-e da assinatura (a `FIL-04` diz que o sistema não emite nota para as locadoras, que é outra coisa) nem quem troca o CNPJ. **Recomendo:** o Giro emite a NFS-e da assinatura pelo parceiro depois de cada pagamento (precisa do cadastro municipal do Giro; se não der para o MVP, o bloco só guarda os dados); razão social e e-mail de cobrança editáveis pelo administrador; CNPJ só pela equipe da plataforma.
- **[D-10] O cartão do plano Completo.** A referência cita "emissão de notas" (a `FIL-04` diz que o sistema não emite), "assinatura digital" (já do Profissional) e "portal do cliente" (não está nos recursos). **Recomendo:** o cartão aparece para quem não está no Completo e lista só os recursos reais do plano acima (`oferta`), sem NF-e nem portal até existirem; o título muda para algo como "Precisa de domínio próprio?" (texto do produto).
