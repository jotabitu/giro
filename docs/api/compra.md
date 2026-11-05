# Compra pública (self-service)

**Dono:** arquiteto · **Versão:** 05 nov 2026 (T-435; criado na T-430) · **Fase:** 2 · **App:** `plataforma` (schema `public`, sem login) · **Regras:** PLT-01, PLT-11, PLT-13, PLT-16, USR-01, IMP-01, IMP-06 · **ADRs:** 0023 (cartão só na página do parceiro), 0008 (`public`) · **Telas:** Compra-Planos, Compra-Checkout, Compra-Pronto (desktop e celular, linhas 15 a 17 de `docs/telas/README.md`) · **Rota no frontend:** `(publico)/compra`

Convenções gerais em `docs/api/README.md`. O serviço que cria a empresa é `plataforma.services.criar_empresa`, descrito em `plataforma.md` ("POST /api/plataforma/empresas/"), com a checagem do CNPJ (`plataforma.selectors.situacao_do_cnpj`, `PLT-16`).

**Por que um arquivo próprio, e não uma seção do `plataforma.md`.** O `plataforma.md` é o contrato da equipe Giro (login da plataforma, 2 etapas, função dono) e do lado da empresa já logada. Estas rotas são as únicas do Giro abertas a qualquer pessoa na internet, sem sessão, e criam schema. Elas têm autenticação, limites e revisão de segurança próprios (T-431) e um modelo próprio (`PedidoCompra`). Num arquivo só delas, a revisão de segurança lê tudo o que é anônimo num lugar, e o `plataforma.md` continua sendo o dono do serviço `criar_empresa`, que as duas portas (Django Admin e compra) chamam.

**Mudança de 05 nov 2026 (T-435):** o dono trocou a D-430-03. A compra consulta o CNPJ na BrasilAPI e preenche razão social, nome, cidade e UF, que a pessoa confere e edita (ADR 0039, campo `dados` da checagem do CNPJ). O resto das decisões D-430 continua igual.

As decisões D-430 foram respondidas pelo dono em 03 nov 2026 ("Aprovo os padrões"), menos a D-430-05 (Termos de uso e Acordo de tratamento de dados), que continua `[decisão]` aberta: ela não bloqueia a T-432 nem a T-433, mas **a compra não entra no ar sem esses textos**. Os ajustes das telas são da T-434 (design-system).

---

## Visão do fluxo

```
Compra-Planos ──► Compra-Checkout ──► código no e-mail ──► Compra-Pronto ──► convite (USR-01) ──► senha + 2 etapas ──► assistente (IMP)
 GET planos       POST cnpj, subdominio   POST confirmar        GET pedido (andamento)
                  POST pedidos (202)      (cria a empresa)
```

1. A pessoa escolhe plano e ciclo (`Compra-Planos`).
2. Preenche o checkout. A tela checa o CNPJ e o endereço de acesso enquanto ela digita.
3. "Criar minha conta" cria um **pedido**, não a empresa. O Giro manda um código de 6 dígitos para o e-mail informado.
4. Ela digita o código na própria tela. Só então o backend chama `criar_empresa`, numa tarefa do Celery (o schema leva segundos).
5. A `Compra-Pronto` acompanha a criação passo a passo e, no fim, leva ao convite do administrador.

**Confirmar o e-mail antes de criar** é a principal proteção: sem o código, nenhum schema nasce, e ninguém cria empresa com o e-mail de outra pessoa. D-430-01, decidido pelo dono em 03 nov 2026: confirmar antes de criar.

---

## Onde as rotas moram

- Servidas no domínio principal (`girolocadoras.com.br`), pelo `urls_public` do django-tenants, prefixo `/api/publico/compra/`. Nenhuma responde no subdomínio de uma empresa (404).
- Sem autenticação (`AllowAny`), sem cookie de sessão, sem CSRF (não há sessão para forjar). CORS só para a origem do próprio frontend.
- Todo corpo vem em JSON por `POST`. **CNPJ e e-mail nunca vão na URL** (nem em query string), para não cair em log de proxy.
- Toda resposta leva `Cache-Control: no-store`, menos o catálogo.

---

## Modelo novo: `PedidoCompra` (schema `public`, app `plataforma`)

| Campo | Tipo | Nota |
| --- | --- | --- |
| `id` | bigint | interno, nunca sai na API |
| `chave` | uuid4 | identifica o pedido na API; é o que a tela guarda (em memória ou `sessionStorage`, nunca na URL) |
| `status` | enum | `aguardando_confirmacao`, `confirmado`, `criando`, `pronto`, `falhou`, `expirado` |
| `plano` | FK `Plano` | só plano à venda |
| `ciclo` | enum | `mensal`, `anual` |
| `forma_pagamento` | enum, nulo | `cartao`, `pix_automatico`, `boleto` ou nulo (`PLT-13`, opcional) |
| `administrador_nome`, `administrador_email`, `administrador_celular` | texto | e-mail em minúsculas |
| `aceita_whatsapp` | bool | aceite do WhatsApp do responsável (`PLT-02`, ADR 0034) |
| `cnpj`, `razao_social`, `nome_exibicao`, `cidade`, `uf`, `subdominio` | texto | o que vai para `criar_empresa` |
| `situacao_cnpj` | enum | `nova` ou `ja_foi_cliente`, gravada na confirmação |
| `codigo_hash` | texto | hash Argon2 do código de 6 dígitos; o código nunca é gravado |
| `codigo_expira_em` | datetime | 15 min depois do envio |
| `tentativas_codigo` | int | até 5 |
| `reenvios` | int | até 3 |
| `aceite_termos_versao`, `aceite_termos_em` | texto, datetime | versão dos Termos e do Acordo de tratamento de dados aceita |
| `ip_hash` | texto | HMAC do IP com a chave dos segredos, para os limites e a auditoria; o IP em claro não é gravado |
| `empresa` | FK `Empresa`, nulo | preenchida no `pronto` |
| `andamento` | JSON | horários de cada passo da criação (abaixo) |
| `criado_em`, `expira_em` | datetime | `expira_em` = criado + 24 h |

- Mudança de status só por `plataforma.services` (`criar_pedido_compra`, `confirmar_pedido_compra`, `executar_pedido_compra`, `expirar_pedidos_compra`), sempre com evento de auditoria no `public` (`compra.pedido`, `compra.confirmar`, `compra.criar_empresa`, `compra.falhou`), sem dados pessoais no evento (só `chave`, plano, ciclo, situação e o `empresa_id`).
- Pedido `aguardando_confirmacao` ou `expirado` não é negócio: a tarefa diária `expirar_pedidos_compra` marca `expirado` os vencidos e, 7 dias depois, apaga os dados pessoais do pedido (nome, e-mail, celular, CNPJ, razão social), guardando só plano, ciclo, datas e status para o funil. Pedido `pronto` guarda os dados porque eles viraram a empresa.

---

## Rotas

### GET /api/publico/compra/planos/

Catálogo à venda (`PLT-11`), para a `Compra-Planos` e o resumo "Plano escolhido" do checkout. Sem limite de taxa próprio (é público e cacheável por 5 min).

- Só planos à venda. Na fase 2, até o Completo ter o que o diferencia, ele fica fora (`PLT-11`, "Catálogo da fase 1"; campo `a_venda` da T-378). Antes de a T-378 entrar, a T-432 filtra pelo `codigo` do Completo e anota a troca no código.
- Os textos de `inclui` são os da `PLT-11`, já no texto da fase 1 para o Profissional. A tela não escreve texto de plano.
- `teste` é calculado pela API para o dia de hoje (`America/Sao_Paulo`), para o quadro "Como funciona o teste" (`PLT-01`, `PLT-02`): início hoje, fim em hoje + 14, lembrete D-3 da 1ª fatura e 1ª fatura no dia seguinte ao fim.

200:
```json
{
  "planos": [
    { "codigo": "essencial", "nome": "Essencial", "descricao": "Para quem está começando a frota.",
      "mensal_centavos": 19900, "anual_centavos": 199000,
      "limites": { "veiculos": 30, "filiais": 1, "usuarios": 3 },
      "inclui": ["Locação, vistoria e contas a receber", "Contrato digital, assinado pelo cliente no celular", "Sua marca e seu endereço de acesso"],
      "destaque": false },
    { "codigo": "profissional", "nome": "Profissional", "descricao": "Para locadoras com equipe e mais de uma loja.",
      "mensal_centavos": 44900, "anual_centavos": 449000,
      "limites": { "veiculos": 150, "filiais": 3, "usuarios": 10 },
      "inclui": ["Tudo do Essencial, mais despesas", "Pix e boleto automáticos e cobrança pelo WhatsApp"],
      "destaque": true }
  ],
  "teste": { "dias": 14, "inicio": "2026-10-07", "fim": "2026-10-21", "lembrete": "2026-10-19", "primeira_fatura": "2026-10-22" }
}
```
O exemplo usa hoje = 07 out 2026, a Moto Rápida dos dados de referência. `limites` com `null` quer dizer "sem limite". O selo "Mais escolhido" sai de `destaque`.

### POST /api/publico/compra/cnpj/

Checagem do CNPJ antes de comprar (`PLT-16`). A tela chama quando o CNPJ fica completo.

Corpo: `{ "cnpj": "12.345.678/0001-90" }` (aceita com ou sem pontuação; o backend guarda só os dígitos).

- 400 `{ "codigo": "validacao", "campos": { "cnpj": ["Confira o CNPJ. Os números não batem."] } }` quando os dígitos verificadores não conferem.
- 200 com a situação de `situacao_do_cnpj`, traduzida para a tela:

| `situacao_do_cnpj` | 200 | Na tela |
| --- | --- | --- |
| `nova` | `{ "pode_comprar": true, "teste_gratis": true, "aviso": null, "dados": {...} }` | preenche os campos com `dados` |
| `ja_foi_cliente` | `{ "pode_comprar": true, "teste_gratis": false, "aviso": "Este CNPJ já usou o teste grátis. A 1ª fatura vence hoje.", "primeira_fatura": "2027-03-01" }` | o aviso, e o quadro do teste troca para "1ª fatura hoje" com o valor do plano |
| `em_uso` | `{ "pode_comprar": false, "codigo": "cnpj_em_uso", "mensagem": "Este CNPJ já tem uma assinatura no Giro. Para voltar, fale com a equipe Giro." }` | a mensagem no campo e "Criar minha conta" desligado |
| `fatura_em_atraso` | `{ "pode_comprar": false, "codigo": "fatura_anterior_em_atraso", "mensagem": "Há uma fatura em aberto da assinatura anterior. Fale com a equipe Giro para pagar antes de assinar de novo." }` | idem |

- Quando pode comprar, `dados` traz o que a BrasilAPI devolveu (ADR 0039): `{ "razao_social": "Moto Rápida Locações Ltda", "nome_fantasia": "Moto Rápida", "cidade": "Fortaleza", "uf": "CE", "ativo": true }`, ou `null` se o provedor caiu ou não achou o CNPJ. A tela preenche razão social, nome, cidade e UF, e a pessoa edita. A frase "Moto Rápida Locações Ltda · Fortaleza, CE · CNPJ ativo" sai desses dados. `ativo` só informa e não recusa. Nada da empresa já cliente do Giro sai na resposta. *Antes (D-430-03, 03 nov 2026): sem consulta. Trocada pelo dono em 05 nov 2026.*
- **Enumeração:** essa rota diz a qualquer pessoa se um CNPJ é ou foi cliente do Giro. O que um CNPJ é (razão social, endereço) já é público, mas ser cliente do Giro é dado comercial do cliente. A proteção é o limite por IP (abaixo) e a auditoria das recusas. D-430-04, decidido pelo dono em 03 nov 2026: a checagem responde como na tabela, com o limite.
- A mesma checagem roda de novo na confirmação, que é o que vale (o CNPJ pode mudar de situação entre as duas).

### POST /api/publico/compra/subdominio/

Checagem do endereço de acesso. Corpo: `{ "subdominio": "motorapida" }`, ou `{ "nome": "Moto Rápida" }` para pedir uma sugestão.

200: `{ "subdominio": "motorapida", "disponivel": true, "endereco": "motorapida.girolocadoras.com.br" }`, ou `{ "subdominio": "motorapida", "disponivel": false, "sugestao": "motorapida2", "mensagem": "Este endereço já está em uso. Escolha outro." }`.

- Regras do `plataforma.md`: só `a-z`, `0-9` e `-`, de 3 a 30 caracteres, nem reservado (`admin`, `www`, `api`, `app`, `suporte`, `status`). Fora disso, 400 `validacao` com "Use de 3 a 30 letras sem acento, números ou hífen.", e para os reservados "Este endereço não pode ser usado. Escolha outro.".
- "Em uso" inclui o subdomínio de empresa apagada, que continua reservado (`PLT-16`, `AUD-08`). A resposta não diz por que está em uso.
- A sugestão tira acentos, espaços e pontuação do nome e acrescenta número até achar um livre.
- O checkout não tem o campo do endereço; a `Compra-Pronto` mostra um. D-430-02, decidido pelo dono em 03 nov 2026: o checkout ganha o campo "Endereço de acesso", pré-preenchido com a sugestão a partir do nome da empresa e editável; o design-system ajusta a tela na T-434.

### POST /api/publico/compra/pedidos/

"Criar minha conta". Cria o `PedidoCompra` e manda o código. **Não cria empresa.**

Corpo:
```json
{
  "plano": "profissional", "ciclo": "mensal", "forma_pagamento": null,
  "administrador": { "nome": "Mariana Costa", "email": "mariana@motorapida.com.br", "celular": "85998124410", "aceita_whatsapp": true },
  "empresa": { "cnpj": "12345678000190", "razao_social": "Moto Rápida Locações Ltda", "nome_exibicao": "Moto Rápida",
               "cidade": "Fortaleza", "uf": "CE", "subdominio": "motorapida" },
  "aceite_termos": true
}
```

202:
```json
{ "chave": "6f1c0c2e-...", "status": "aguardando_confirmacao", "email": "m•••••@motorapida.com.br",
  "codigo_expira_em": "2026-10-07T12:27:04Z", "mensagem": "Enviamos um código de 6 dígitos para m•••••@motorapida.com.br. Digite o código para criar o seu sistema." }
```

- `forma_pagamento` é opcional ("Opcional durante o teste"). Só grava a forma, como na `Admin-Assinatura` (`PLT-13`): escolher não ativa a empresa nem cobra. **Nenhum campo de cartão** é aceito (ADR 0023): corpo com `numero_cartao`, `validade`, `cvv` ou parecido é 400 `{ "codigo": "cartao_nao_aceito" }`, e o campo é descartado antes de qualquer log.
- `plano` fora do catálogo à venda: 400 `{ "codigo": "plano_fora_da_venda", "mensagem": "O plano Completo ainda não está à venda." }` para o Completo (`PLT-11`), "Escolha um dos planos da lista." para os outros.
- `aceite_termos` diferente de `true`: 400 `validacao`, "Para continuar, aceite os Termos de uso e o Acordo de tratamento de dados.". A versão aceita é gravada no pedido e passa para a empresa. Os textos ainda não existem: `[decisão]` D-430-05, aberta. Não bloqueia a T-432 nem a T-433, mas a compra não entra no ar sem eles.
- E-mail inválido: "Confira o e-mail."; celular: "Confira o celular com DDD."; nome vazio: "Informe seu nome completo.".
- O CNPJ e o subdomínio são checados de novo aqui (as mesmas respostas das rotas acima, como 409 `cnpj_em_uso`, `fatura_anterior_em_atraso`, `subdominio_em_uso`). Essa checagem não reserva nada: o subdomínio só fica reservado quando a empresa nasce.
- Pedido novo com o mesmo e-mail e CNPJ de um pedido ainda `aguardando_confirmacao` substitui o anterior (que vira `expirado`), sem contar como pedido novo no limite por CNPJ.
- Envio do código por e-mail, depois do commit, com o remetente da plataforma. Assunto "Seu código para criar o sistema no Giro"; corpo "Seu código é 482913. Ele vale por 15 minutos. Se você não pediu, ignore este e-mail.". A marca é a do Giro (tela de compra).

### POST /api/publico/compra/pedidos/{chave}/confirmar/

Corpo: `{ "codigo": "482913" }`.

- Código certo e no prazo: o pedido vira `confirmado`, roda `situacao_do_cnpj` de novo (grava `situacao_cnpj`), vira `criando` e agenda `executar_pedido_compra` no Celery. 202 com o corpo de `GET /pedidos/{chave}/`.
- Erros do código vêm com `codigo` e `mensagem` no primeiro nível (e `tentativas_restantes` no `codigo_invalido`), sem `detalhes`.
- Código errado: 400 `{ "codigo": "codigo_invalido", "mensagem": "Código incorreto. Você tem mais 4 tentativas.", "tentativas_restantes": 4 }`. Na 5ª errada, o código morre: 400 `{ "codigo": "codigo_bloqueado", "mensagem": "Muitas tentativas. Peça um código novo." }`.
- Código vencido: 400 `{ "codigo": "codigo_expirado", "mensagem": "O código venceu. Peça um código novo." }`.
- Pedido `expirado` ou chave desconhecida: 404 `{ "codigo": "pedido_nao_encontrado", "mensagem": "Este pedido não vale mais. Comece de novo pela escolha do plano." }`. A mesma resposta para os dois casos.
- Pedido já confirmado: 200 com o andamento (idempotente; o duplo clique não cria duas empresas).
- Comparação do código em tempo constante (`check_password` do Argon2).

### POST /api/publico/compra/pedidos/{chave}/reenviar-codigo/

Sem corpo. Gera código novo (o anterior deixa de valer), zera `tentativas_codigo`, até 3 reenvios por pedido e no mínimo 60 s entre eles. 202 `{ "codigo_expira_em": "...", "mensagem": "Enviamos um código novo." }`. Fora do limite: 429 `{ "codigo": "limite_reenvio", "mensagem": "Aguarde um minuto para pedir outro código." }` ou, depois do 3º, "Você já pediu 3 códigos. Comece de novo pela escolha do plano.".

### GET /api/publico/compra/pedidos/{chave}/

Andamento para a `Compra-Pronto` (a tela consulta a cada 2 s enquanto `status` = `criando`).

200:
```json
{
  "status": "pronto",
  "administrador": { "nome": "Mariana", "email": "mariana@motorapida.com.br" },
  "empresa": { "nome_exibicao": "Moto Rápida", "endereco": "motorapida.girolocadoras.com.br" },
  "passos": [
    { "passo": "administrador", "texto": "Conta de administrador criada", "feito_em": "2026-10-07T12:12:04Z" },
    { "passo": "banco",         "texto": "Banco de dados exclusivo da empresa", "feito_em": "2026-10-07T12:12:09Z" },
    { "passo": "endereco",      "texto": "Endereço de acesso reservado", "feito_em": "2026-10-07T12:12:10Z" },
    { "passo": "assinatura",    "texto": "Teste de 14 dias ativo, até 21 out", "feito_em": "2026-10-07T12:12:10Z" }
  ],
  "acessar": { "url": "https://motorapida.girolocadoras.com.br/convite/....", "uma_vez": true }
}
```
- `administrador` e `empresa` só saem depois de `confirmado` (antes, quem tem a chave não vê dados). `administrador.nome` é o primeiro nome, para "Tudo pronto, Mariana".
- O passo `assinatura` diz "Teste de 14 dias ativo, até 21 out" na compra com teste, e "1ª fatura de R$ 449,00 vence hoje" na `ja_foi_cliente` (`PLT-16`, sem teste, empresa nasce `ativa`). O texto vem pronto da API.
- `status` `falhou`: `{ "status": "falhou", "mensagem": "Não conseguimos criar o seu sistema agora. A equipe Giro já foi avisada e fala com você por e-mail." }`. A tarefa desfaz a transação de `criar_empresa` (nada fica pela metade: schema que nasceu é removido no mesmo rollback do django-tenants), avisa o Sentry e manda e-mail à equipe. Não há nova tentativa automática para não criar duas vezes.
- Pedido `expirado`, ou mais de 24 h depois do `pronto`: 404 `pedido_nao_encontrado`.

**O que a `Compra-Pronto` mostra e para onde leva.** "Tudo pronto, {nome}", o endereço, os 4 passos com o horário (em `America/Sao_Paulo`), "Acessar meu sistema" e "ou use o link do e-mail em qualquer aparelho".

- "Acessar meu sistema" abre `acessar.url`: o link do convite do administrador (`USR-01`), que leva a criar a senha e ativar as 2 etapas e, depois, ao assistente de implantação (`Pos-Dashboard` até a `IMP-01`, `USR-08`). A pessoa já provou que lê o e-mail (o código), então o mesmo navegador recebe o link, como no "Copiar link do convite": `acessar` sai **uma vez só**, na primeira leitura depois do `pronto`, e nas seguintes vem `null` (a tela troca o botão por "Abra o link que enviamos para {email}."). D-430-06, decidido pelo dono em 03 nov 2026: assim.
- O e-mail de boas-vindas da tela é o convite da `USR-01`. O link vale **7 dias** (`USR-01`), e não 48 horas como diz a tela: `[divergência]` D-430-07, vale a regra: o design-system corrige na T-434 o texto para "O link vale por 7 dias.".
- Nada na `Compra-Pronto` mostra a marca da locadora: a compra é tela do Giro (white label, `CLAUDE.md`).

---

## O que a criação faz (`executar_pedido_compra`)

Chama `criar_empresa` com os dados do pedido, sem duplicar a regra:

- `situacao_cnpj` = `nova`: empresa `em_teste`, `teste_inicio` = hoje, `teste_fim` = hoje + 14, 1ª fatura `aberta` com o valor do plano e do ciclo vencendo no dia seguinte ao fim do teste (`PLT-01`; Moto Rápida, compra em 07 out: teste até 21 out, FAT-0001 de R$ 449,00 vencendo em 22 out, ou R$ 4.490,00 no anual).
- `ja_foi_cliente`: empresa `ativa`, sem teste, 1ª fatura vencendo hoje (`PLT-16`, CA-ASS-61), e os avisos da `IMP-06` não saem.
- `em_uso` ou `fatura_em_atraso` na hora da confirmação: o pedido vira `falhou` com a mensagem da `PLT-16` correspondente no lugar da mensagem genérica.
- O administrador nasce `convite_pendente` com o convite da `USR-01` (e-mail sempre; WhatsApp só com `aceita_whatsapp`, ADR 0034). O e-mail do administrador já está confirmado pelo código, mas o acesso continua nascendo pelo convite (senha e 2 etapas, `USR-06`).
- `forma_pagamento`, quando veio, é gravada como na `Admin-Assinatura` (`PLT-13`); sem ela, a régua da `PLT-02` avisa antes do fim do teste.
- O responsável pela assinatura é o administrador da compra, com o aceite do WhatsApp de `aceita_whatsapp` (`PLT-02`).
- `Empresa.origem` = `compra` (o Django Admin grava `admin`), para o funil da `Plat-Implantacoes` (`IMP-05`) e a auditoria.
- Grava os horários de cada passo em `andamento`.

Mudanças na `criar_empresa` (T-435): recebe `origem`, a versão aceita dos Termos e um `andamento` opcional (dicionário que ela preenche com o horário de cada passo). A situação do CNPJ é conferida lá dentro para as duas portas: com `ja_foi_cliente`, a empresa nasce `ativa`, sem teste, com `empresa_anterior` e a 1ª fatura hoje. O Django Admin continua chamando sem os parâmetros novos.

- `aceita_whatsapp` fica só no pedido: a empresa ainda não tem campo para o aceite do responsável (ADR 0034 proposta). Entra quando o WhatsApp real entrar.
- O link de "Acessar meu sistema" é um convite a mais do administrador, criado na primeira leitura depois do `pronto`, com o mesmo vencimento do convite do e-mail e sem invalidá-lo. O token em claro nunca é gravado.

---

## Proteção da rota pública

Tudo com o que já existe: throttles do DRF no cache do Redis (como o `AcessoPorIP` de `contas/api/acesso.py`), Argon2 e Celery. **Nenhuma dependência nova.**

| Rota | Por IP | Por e-mail | Por CNPJ | Resposta |
| --- | --- | --- | --- | --- |
| `cnpj/` | 20 por hora | | | 429 |
| `subdominio/` | 60 por hora | | | 429 |
| `pedidos/` | 5 por hora, 20 por dia | 3 por dia | 3 e-mails diferentes por dia | 429 |
| `confirmar/` | 30 por hora | 5 tentativas por código | | 400 / 429 |
| `reenviar-codigo/` | 10 por hora | 3 por pedido, 60 s entre eles | | 429 |

- 429 sempre com `{ "codigo": "limite", "mensagem": "Muitas tentativas. Tente de novo mais tarde." }` e `Retry-After`. A mensagem não diz qual limite estourou.
- O IP vem do cabeçalho que o proxy de produção garante (ADR 0033); o backend não confia em `X-Forwarded-For` de fora.
- **Teto diário de empresas criadas pela compra** (padrão 50 por dia, em `settings`). Acima dele, a confirmação deixa o pedido `confirmado` sem criar, e a equipe Giro recebe e-mail para liberar pelo Django Admin; a tela mostra "Recebemos o seu pedido. A equipe Giro libera o seu sistema e avisa você por e-mail.". Protege contra criação em massa de schemas mesmo com e-mails válidos. D-430-08, decidido pelo dono em 03 nov 2026: teto de 50 por dia.
- **Captcha** não entra agora: pede serviço externo (ADR nova). Com o código no e-mail, o teto diário e os limites, o risco que fica é o gasto de e-mails de código. D-430-09, decidido pelo dono em 03 nov 2026: sem captcha; rever com os números da produção.
- O código e a chave do pedido nunca vão para log nem para o Sentry (`before_send` já filtra campos com `codigo`; a T-432 confere).
- Respostas de 404 do pedido são iguais para chave inexistente e expirada.

---

## Ajustes das telas (T-434, design-system)

- `Compra-Planos`: mostra o Completo e o texto antigo do Profissional ("vendas, manutenção... comissão de vendedores e relatórios"). Vale a `PLT-11` da fase 1: o card do Completo sai, e o texto vem da API. O link "Entrar" do topo não tem para onde levar no domínio principal (o login é no endereço de cada locadora): D-430-10, decidido pelo dono em 03 nov 2026: sai da tela.
- `Compra-Checkout`: falta o campo do endereço de acesso (D-430-02); razão social, nome, cidade e UF viram campos editáveis, preenchidos pela consulta do CNPJ (ADR 0039), e a frase "CNPJ ativo" sai de `dados`; entra o passo do código de 6 dígitos ("Digite o código que enviamos para m•••••@motorapida.com.br", com "Reenviar código"). O campo "Tamanho da frota hoje" não tem regra nem vai para nenhum lugar: D-430-11, decidido pelo dono em 03 nov 2026: sai da tela. O quadro "Como funciona o teste" usa `teste` da API.
- `Compra-Pronto`: "48 horas" vira "7 dias" (D-430-07).

---

## Testes que a T-432 escreve (nomes)

- `test_plt_11_catalogo_publico_sem_completo`, `test_plt_11_pedido_com_completo_recusado`
- `test_plt_01_compra_publica_teste_e_primeira_fatura` (Moto Rápida: 07 out → teste até 21 out, fatura 22 out, R$ 449,00; anual R$ 4.490,00)
- `test_plt_16_checagem_cnpj_quatro_situacoes`, `test_plt_16_compra_publica_sem_teste`, `test_plt_16_situacao_muda_ate_a_confirmacao`
- `test_plt_13_compra_sem_cartao` (forma opcional; campos de cartão recusados, ADR 0023)
- `test_usr_01_convite_do_administrador_da_compra`, `test_compra_link_do_convite_sai_uma_vez`
- `test_compra_nao_cria_empresa_sem_codigo`, `test_compra_codigo_cinco_tentativas`, `test_compra_codigo_expira`, `test_compra_confirmar_idempotente`
- `test_compra_limites_por_ip_email_cnpj`, `test_compra_teto_diario`, `test_compra_falha_desfaz_schema`
- `test_compra_rotas_so_no_dominio_principal`, `test_compra_pedido_expirado_apaga_dados_pessoais`
