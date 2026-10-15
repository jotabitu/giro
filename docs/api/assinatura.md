# Assinatura da empresa (Admin › Assinatura)

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-217, T-213; T-193; T-183) · **App:** `plataforma` (lê e grava no `public`, servido no host da empresa) · **Regras:** PLT-01, PLT-02, PLT-03, PLT-04, PLT-05, PLT-06, PLT-11, PLT-13, PLT-14, PLT-15, AUT-13, tabela de estados da empresa · **ADR:** 0007, 0023 · **Telas:** Admin-Assinatura (desktop e celular) · **Critérios:** `docs/qa/criterios/assinatura.md` (CA-ASS-01 a 21, 26 a 29, 40, 41 e 46 a 49)

Decisão do dono em 14 out 2026: a tela `Admin-Assinatura` entra inteira no MVP, com a cobrança real. Este contrato completa o que `GET /api/assinatura/` (`plataforma.md`, "Do lado da empresa") ainda não entregava, levantado na T-170: mudar e comparar planos, forma de pagamento, faturas, dados da nota fiscal, o cartão do plano acima e a data da 1ª fatura. "Cancelar assinatura" e pausar (`PLT-06`, tela `Admin-Cancelar`) têm contrato próprio (T-194); aqui só aparecem onde mexem nas faturas.

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (itens 2 e 3 e apoio do `public`). Os módulos que cada plano liga (`PLT-12`) estão na ADR 0024 e em `plataforma.md`, "Módulos por plano".

> **O que mudou na T-193 (decisões do dono de 14 out 2026, regras na T-190).** Saíram as marcas [D-1] a [D-10]: as respostas estão nas regras e na tabela "Decisões de 14 out 2026". Mudou em relação ao que este contrato recomendava: (1) escolher a forma de pagamento **não** ativa a empresa; ela fica `em_teste` até o fim do teste, e só a 1ª fatura paga leva a `ativa` (U1); (2) a `oferta` vira o cartão "Precisa de mais veículos ou filiais?", com os itens prontos da `PLT-11`, sem domínio próprio nem API (U11). Entraram: uma tentativa só do cartão e "Pagar" por outro meio (U8), a NFS-e pelo parceiro depois de paga e o endereço nos dados fiscais (U9, `PLT-15`), os e-mails de cobrança, a mudança no teste com a 1ª fatura já paga (`PLT-04`), a mudança de ciclo e a reativação da cancelada pela equipe, e o vencimento depois da volta da pausa. Quem já começou a T-185, a T-186 ou a T-187 confere a seção "O que muda para as tarefas abertas", no fim.

> **O que mudou na T-213 (decisões do dono de 14 out 2026, regras na T-211).** (1) O endereço da nota (`PLT-15`, opção B) deixa de nascer nulo para sempre: é copiado uma vez do endereço da filial matriz, quando ela é criada no passo 6, e depois cada um muda por conta própria; o seed já nasce com o endereço da Filial Centro (CA-ASS-47 e 48). (2) O downgrade agendado é conferido na geração da fatura, 5 dias antes, e não acontece se deixou de caber; o plano muda no dia do vencimento (CA-ASS-40 e 41). (3) A reativação da `cancelada` com fatura em atraso deixa de ser `[decisão]`: a recusa 409 `fatura_em_atraso` fica (opção A, CA-ASS-46). Veja "O que muda para as tarefas abertas".

> **O que mudou na T-217 (decisão do produto de 14 out 2026, regra na T-216).** A reativação da `cancelada` pela equipe não cobra duas vezes o período já pago: com o último período pago ainda correndo, a fatura nova vence no dia seguinte ao fim dele e `dia_vencimento` não muda; senão, vence no dia da volta, como antes (CA-ASS-49). Veja "Mudança de ciclo e reativação pela equipe".

---

## Quem usa

- `GET /api/assinatura/` continua para **todos os perfis** (as telas de Filiais, Usuários e Veículos leem o `uso`). Os blocos novos do administrador (`forma_pagamento`, `dados_fiscais`, `oferta`, `acoes`) vêm **ausentes** para os outros perfis, como o bloco do vendedor em `veiculos.md`.
- Todas as outras rotas deste contrato são **só do administrador** (tabela de perfis: "Administração ... assinatura"; `PLT-04`, `PLT-13`). Outro perfil: 403 `{ "codigo": "permissao", "mensagem": "Só o administrador mexe na assinatura" }`.
- Suporte Giro dentro da empresa (`PLT-07`): só lê. Nenhuma escrita deste contrato aceita token de suporte, nem com "ver e editar" (dinheiro e dados fiscais da empresa são decisão do administrador): 403 `{ "codigo": "PLT-07", "mensagem": "O suporte não mexe na assinatura da empresa" }`. CA-ASS-19.

### Estado da empresa e o que cada rota aceita

`somente_leitura` (empresa `suspensa`, `pausada` ou `cancelada`) faz todo endpoint de escrita responder 403 `empresa_sem_operacao` (`plataforma.md`). **Exceção** (`PLT-13`, tabela de estados): a empresa `suspensa` precisa conseguir pagar para voltar a `ativa` na hora, então estas rotas continuam abertas para ela: `PUT forma-pagamento/`, `POST faturas/{codigo}/pagar/` e `PATCH dados-fiscais/`. A exceção fica numa lista explícita na permissão de `somente_leitura`, com teste (CA-ASS-27).

| Rota | `em_teste` | `ativa` | `inadimplente` | `suspensa` | `pausada`, `cancelada` |
| --- | --- | --- | --- | --- | --- |
| ler (`GET`) | sim | sim | sim | sim | sim (`cancelada` não entra no sistema, `AUD-08`) |
| mudar de plano e desfazer o downgrade | sim | sim | não (`PLT-04`) | não (`PLT-04`) | não |
| forma de pagamento | sim | sim | sim | sim | não |
| pagar fatura | sim | sim | sim | sim | não |
| dados fiscais | sim | sim | sim | sim | não |

Fora da tabela: 409 `{ "codigo": "transicao_empresa", "mensagem": "<texto do caso>" }`, com os textos de cada rota abaixo. Em `pausada` e `cancelada` a 403 `empresa_sem_operacao` vem antes.

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
    "endereco": { "cep": "60325000", "logradouro": "Av. Bezerra de Menezes", "numero": "1200", "complemento": null, "bairro": "São Gerardo", "cidade": "Fortaleza", "uf": "CE" },
    "email_cobranca": "mariana@motorapida.com.br"
  },
  "oferta": {
    "titulo": "Precisa de mais veículos ou filiais?",
    "plano": { "id": 3, "nome": "Completo", "preco_mensal_centavos": 89900 },
    "itens": ["Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário"]
  },
  "acoes": { "mudar_plano": true, "desfazer_mudanca_plano": false, "escolher_forma_pagamento": true, "editar_dados_fiscais": true, "cancelar": false }
}
```

- `teste.inicio` é novo (a tabela de faturas mostra a linha do teste com essa data). `teste` é `null` fora de `em_teste`.
- **`status`** segue a tabela de estados: a empresa fica `em_teste` até `teste.fim`, **mesmo com a forma escolhida ou a 1ª fatura paga** (`PLT-01`, U1). Com isso continuam a faixa "Teste grátis até 21 out", os avisos da `IMP-06` e a troca livre de plano (CA-ASS-02, CA-ASS-03).
- **`proxima_fatura`** é o que a tela mostra em "R$ 449,00 por mês, a partir de …": a próxima fatura do período (`tipo = mensalidade`) ainda não paga, ou a que ainda vai nascer. A 1ª fatura vence **no dia seguinte ao fim do teste** (`PLT-01`): Moto Rápida, teste de 07 a 21 out, vence em **22 out** (a referência diz 21 out e erra; correção na T-188). Com a FAT-0001 já paga no teste, a próxima é a de 22 nov ("Plano Profissional · 22 nov a 21 dez"). Com um downgrade ou mudança de ciclo agendados, `valor_centavos` e `descricao` já são os do que vale na virada. `null` em `pausada` e `cancelada` (o que a T-194 mostra no lugar fica no contrato dela).
- **`plano_proximo`**: `{ "id", "nome", "ciclo", "vale_em": "2026-11-22" }` quando há downgrade (`PLT-04`) ou mudança de ciclo pela equipe agendados; senão `null`. A tela mostra "Muda para Essencial em 22 nov" com `vale_em`.
- **`forma_pagamento`** (`PLT-13`):
  - `forma`: `cartao`, `pix_automatico`, `boleto` ou `null`.
  - `cartao`: `{ "bandeira": "visa", "final": "4242" }` quando já há cartão guardado no parceiro; senão `null`. O Giro nunca tem o número do cartão (ADR 0023).
  - `situacao.codigo`, na ordem (a primeira que valer):

    | `codigo` | Quando | `rotulo` | `tom` |
    | --- | --- | --- | --- |
    | `sem_forma` | `forma` nula | em teste: "Nenhuma cadastrada. Escolha até 21 out para não perder o acesso."; fora dele: "Nenhuma cadastrada." | `alerta` |
    | `aguardando_autorizacao` | Pix automático pedido e ainda não autorizado no banco | "Autorize o Pix automático no app do seu banco." | `alerta` |
    | `cartao_recusado` | a última cobrança no cartão foi recusada (`PLT-02`) | 1ª recusa: "O cartão foi recusado. Tentamos de novo amanhã."; 2ª: "O cartão foi recusado de novo. Pague a fatura por Pix ou boleto." | `perigo` |
    | `cartao_na_primeira_fatura` | `cartao` escolhido e ainda sem cartão guardado | "Você cadastra o cartão ao pagar a primeira fatura." | `info` |
    | `ativa` | resto | "Cartão Visa final 4242 · cobrança automática todo mês", "Pix automático autorizado", "Boleto enviado por e-mail 5 dias antes" | `sucesso` |
  - `prazo`: último dia para escolher a forma sem a empresa ir a `suspensa` no dia seguinte = `teste.fim`, só em `em_teste` com `forma` nula; senão `null`. Escolher a forma **não** muda o `status` (U1): ela só evita a suspensão no fim do teste e deixa a 1ª fatura seguir a régua.
- **`dados_fiscais`** (`PLT-15`): ver `PATCH /api/assinatura/dados-fiscais/`. CNPJ só com dígitos. `endereco` é `null` até a matriz ser criada no passo 6 (a compra não pede endereço; ver `PATCH /api/assinatura/dados-fiscais/`, "De onde vem o endereço").
- **`oferta`** é o cartão do plano acima (`PLT-11`): o primeiro plano ativo acima do atual pela `ordem`. `titulo` é sempre "Precisa de mais veículos ou filiais?"; `itens` são os textos prontos do que o plano acima inclui e o atual não, na ordem da tabela da `PLT-11`, montados pela API a partir do catálogo (a mesma fonte da `Compra-Planos` e da `Plat-Planos`). Nunca citam NF-e, domínio próprio, portal do cliente, API e integrações nem contrato digital como extra (CA-ASS-20, CA-ASS-21). `null` quando a empresa já está no Completo ou não há plano ativo acima. O frontend não monta texto de recurso: mostra `titulo`, `plano.nome`, o preço e os `itens`, e "Ver planos" abre a lista de `GET /api/assinatura/planos/`.

  | Plano atual | `oferta.plano` | `itens` |
  | --- | --- | --- |
  | Essencial | Profissional | "Vendas, manutenção e despesas", "Pix e boleto automáticos, cobrança pelo WhatsApp", "Comissão de vendedores e relatórios", "Até 150 veículos, 3 filiais e 10 usuários" |
  | Profissional | Completo | "Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário" |
  | Completo | — | `oferta: null` |

  Os textos de cada plano ficam num só lugar no backend (o catálogo da `PLT-11`, `plataforma/catalogo.py`, função pura), com teste que confere a tabela da regra. Quando o produto mudar a `PLT-11`, muda só esse arquivo.
- **`acoes`** já cruza perfil, estado da empresa e a tabela acima; o frontend mostra só o que vier `true`. `desfazer_mudanca_plano` vem `true` com downgrade agendado pelo administrador. `cancelar` (e `pausar`) ficam no contrato da T-194; até ele, `cancelar: false` e o link "Cancelar assinatura" fica como a T-170 deixou.

Caso do seed: Moto Rápida em 07 out → `status` `em_teste`, `proxima_fatura` 22 out, 44900, `forma` nula com `sem_forma` e prazo 21 out, `endereco` igual ao da Filial Centro (Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000), `email_cobranca` igual ao e-mail da Mariana, `oferta` Completo com os 3 itens, `acoes` todas `true` menos `desfazer_mudanca_plano` e `cancelar`.

---

## GET /api/assinatura/planos/

Administrador. "Mudar de plano" e "Comparar planos" abrem a mesma lista. Sem paginação.

```json
{ "ciclo_atual": "mensal",
  "resultados": [
    { "id": 1, "nome": "Essencial", "ordem": 1, "atual": false,
      "preco_mensal_centavos": 19900, "preco_anual_centavos": 199000,
      "limite_veiculos": 30, "limite_filiais": 1, "limite_usuarios": 3,
      "itens": ["Locação, vistoria e contas a receber", "Contrato digital, assinado pelo cliente no celular", "Sua marca e seu endereço de acesso"],
      "mudanca": "downgrade",
      "cabe": false,
      "excede": { "veiculos": { "usado": 86, "limite": 30 }, "usuarios": { "usado": 5, "limite": 3 } } },
    { "id": 2, "nome": "Profissional", "ordem": 2, "atual": true, "...": "...", "mudanca": null, "cabe": true, "excede": {} },
    { "id": 3, "nome": "Completo", "ordem": 3, "atual": false,
      "preco_mensal_centavos": 89900, "preco_anual_centavos": 899000,
      "limite_veiculos": null, "limite_filiais": null, "limite_usuarios": null,
      "itens": ["Tudo do Profissional", "Veículos, filiais e usuários sem limite", "Implantação acompanhada por chamada", "Suporte prioritário"],
      "mudanca": "upgrade", "cabe": true, "excede": {} }
  ] }
```

- Só planos `ativo=true`, mais o plano atual mesmo se desativado (`PLT-05`: quem já assina continua).
- Preço mostrado é o de **tabela**; o atual mostra também `preco_contratado_centavos` (pode ser diferente, `PLT-05`). A comparação é no ciclo atual (`PLT-04`, CA-ASS-18); `preco_anual_centavos` vem para a tela mostrar o anual como informação.
- `itens`: os textos da `PLT-11` ("O que inclui"), do mesmo catálogo da `oferta`, separados em itens. Substituem a lista de códigos de `recursos` nesta rota; o código do módulo que o plano liga fica no backend (`Plano.recursos`, ADR 0024).
- `mudanca`: `upgrade` se o plano tem `ordem` maior, `downgrade` se menor, `null` no atual. `cabe` e `excede` usam a mesma contagem do `uso` (`PLT-03`, `PLT-04`): Moto Rápida não cabe no Essencial (86 de 30 veículos, 5 de 3 usuários; 1 filial cabe). O que fica aberto nos módulos que saem (`PLT-12`) entra em `excede.abertos`, no mesmo formato de `detalhes.abertos` da 422 abaixo (ADR 0024, CA-ASS-24); um plano com `abertos` tem `cabe: false`. No seed, a Moto Rápida tem despesas de outubro em aberto (os pneus de R$ 1.200,00 aguardando aprovação e as que nasceram `a_pagar`, dados de referência `FIN-05`), então o Essencial dela traz também `abertos`, contados na hora; a QA fixa os números no teste a partir do seed (T-204).

## POST /api/assinatura/mudanca-plano/simular/

Administrador. Não grava nada (ADR 0005). Corpo: `{ "plano_id": 3, "ciclo": "mensal" }`.

200:
```json
{ "tipo": "upgrade", "vale_em": "2026-10-10",
  "preco_novo_centavos": 89900,
  "diferenca_centavos": 0,
  "fatura_diferenca": null,
  "proxima_fatura": { "vencimento": "2026-10-22", "valor_centavos": 89900, "descricao": "Plano Completo · 22 out a 21 nov" },
  "mensagem": "O plano Completo vale agora. A primeira fatura, em 22 out, fica em R$ 899,00." }
```

O plano novo entra pelo preço de tabela dele no ciclo da empresa, que vira o `preco_contratado_centavos` (`PLT-04`, `PLT-05`).

- **No teste com a 1ª fatura em aberto** (`em_teste`, FAT-0001 não paga): troca livre e sem cobrança. Upgrade e downgrade valem na hora (o downgrade também só se couber); a 1ª fatura passa ao valor do plano novo (a cobrança dela, se já emitida no parceiro, é refeita com o valor novo); o teste não reinicia nem muda de data. CA-ASS-13: Moto Rápida para o Completo em 10 out → `tipo: "upgrade"`, `vale_em` 10 out, `diferenca_centavos: 0`, FAT-0001 a 89900.
- **Upgrade com período pago** (`ativa`, ou `em_teste` com a 1ª fatura já paga): vale na hora e cobra a diferença proporcional (`PLT-04`): `(preço novo − preço contratado) × dias que faltam no período ÷ dias do período`, contando o dia da mudança, com o preço do ciclo da empresa, em `Decimal`, `ROUND_HALF_UP` uma vez no centavo (ADR 0009). O período é o da fatura paga que está correndo (no teste com a 1ª já paga, o da 1ª fatura; antes de ele começar, "dias que faltam" é o período inteiro). A diferença vai numa **fatura avulsa** (`tipo = diferenca_plano`) que vence em 3 dias, cobrada pela forma cadastrada (no cartão guardado, cobrada na hora). `fatura_diferenca`: `{ "valor_centavos": 30484, "vencimento": "2026-11-04", "descricao": "Mudança para o plano Completo · 01 a 21 nov" }`.
  - CA-ASS-14: período de 22 out a 21 nov (31 dias), Profissional para Completo em 01 nov → 45000 × 21 ÷ 31 = 30483,87 → **30484** (R$ 304,84), vence 04 nov; a fatura de 22 nov já vem com 89900.
  - No teste com a FAT-0001 paga em 18 out e o upgrade em 19 out: 45000 × 31 ÷ 31 = **45000**, "Mudança para o plano Completo · 22 out a 21 nov", vence em 22 out; a empresa continua `em_teste` até 21 out.
- **Downgrade com período pago**: só se o uso couber (limites e módulos, `PLT-03`, `PLT-12`); não cabe → 422 (abaixo). Cabe → `tipo: "downgrade"`, `vale_em` = vencimento da próxima fatura, `diferenca_centavos: 0`, `mensagem` "O plano Essencial vale a partir de 22 nov. Até lá, você continua no Profissional." Nada é cobrado nem devolvido (CA-ASS-16).
- **Ciclo** diferente do atual (mensal ↔ anual): 422 `{ "codigo": "mudanca_ciclo", "mensagem": "Para mudar entre mensal e anual, fale com o suporte." }` (`PLT-04`, CA-ASS-18). A equipe muda pela plataforma (ver "Mudança de ciclo e reativação pela equipe").
- Mesmo plano e ciclo: 422 `{ "codigo": "mesmo_plano", "mensagem": "Este já é o seu plano." }`.
- Plano inativo (que não é o atual): 404.

## POST /api/assinatura/mudanca-plano/

Administrador. Mesmo corpo do simular, mais `"confirmar_valor_centavos"` = `diferenca_centavos` do simular (se o valor mudou entre simular e confirmar, 409 `{ "codigo": "valor_mudou", "detalhes": { "diferenca_centavos": ... } }` e nada é gravado).

200: o corpo de `GET /api/assinatura/` já atualizado.

Erros:
- 422 `{ "codigo": "PLT-04", "mensagem": "Seu uso não cabe no plano Essencial. Desative veículos ou usuários antes de mudar.", "detalhes": { "veiculos": { "usado": 86, "limite": 30 }, "usuarios": { "usado": 5, "limite": 3 } } }` (CA-ASS-15; o exemplo mostra só os limites: a Moto Rápida do seed tem também despesas abertas, então a recusa dela traz `abertos`, como abaixo, e o produto ajusta o texto do CA-ASS-15).
- 422 `PLT-04` também quando um módulo que sai tem algo aberto (`PLT-12`, ADR 0024), com todos os impedimentos de uma vez, como a `FIL-06`:
  ```json
  { "codigo": "PLT-04",
    "mensagem": "Seu uso não cabe no plano Essencial. Resolva o que está aberto antes de mudar: 1 despesa a pagar e 1 OS aberta.",
    "detalhes": {
      "abertos": [
        { "grupo": "despesas_a_pagar", "quantidade": 1, "texto": "1 despesa a pagar" },
        { "grupo": "ordens_servico", "quantidade": 1, "texto": "1 OS aberta" }
      ],
      "abertos_texto": "1 despesa a pagar e 1 OS aberta" } }
  ```
  (CA-ASS-24). Grupos, na ordem: `despesas_aguardando_aprovacao` ("1 despesa aguardando aprovação", "{n} despesas aguardando aprovação"), `despesas_a_pagar` ("1 despesa a pagar", "{n} despesas a pagar"), `ordens_servico` ("1 OS aberta", "{n} OS abertas": OS fora de `concluida` e `cancelada`), `vendas` ("1 venda aberta", "{n} vendas abertas", `VEN-10`), `comissoes` ("1 comissão a pagar", "{n} comissões a pagar": ainda não `paga` nem `estornada`, `FIN-09`). Só vêm os grupos com quantidade maior que zero e dos módulos que saem (de Profissional ou Completo para Essencial: `manutencao_despesas` e `vendas_comissoes`; entre Profissional e Completo nenhum módulo sai). `abertos_texto` junta os `texto` com ", " e " e " antes do último. Com limite e módulo ao mesmo tempo, `detalhes` traz os dois (`veiculos`, `usuarios`, `filiais` e `abertos`) e a mensagem é "Seu uso não cabe no plano Essencial. Desative veículos ou usuários e resolva o que está aberto antes de mudar: {abertos_texto}." Quem conta é `plataforma.services.pendencias_dos_modulos` (ADR 0024, item 7).
- 409 `{ "codigo": "transicao_empresa", "mensagem": "Pague a fatura em atraso antes de mudar de plano." }` em `inadimplente` e `suspensa` (`PLT-04`, CA-ASS-17).
- 409 `{ "codigo": "transicao_empresa", "mensagem": "Já existe uma mudança agendada para 22 nov. Desfaça antes de escolher outra." }` com `plano_proximo` preenchido e outro downgrade pedido. Um upgrade com downgrade agendado desfaz o agendamento e segue como upgrade.
- 422 `mudanca_ciclo`, `mesmo_plano` como no simular.

Serviço único `plataforma.services.mudar_plano(empresa, plano, ciclo, por, motivo=None)`, o mesmo da ação `mudar-plano` do painel da plataforma (`plataforma.md`, "Ações sobre a empresa"). Trava a `Empresa` e o `UsoEmpresa` (`SELECT ... FOR UPDATE`) para a conta do uso e a mudança serem da mesma foto. Downgrade grava `plano_proximo`; a tarefa `gerar_faturas` confere se ainda cabe e gera a fatura, e o plano muda no dia do vencimento (ver "Downgrade agendado: conferência e virada"). Auditoria `empresa.mudar_plano` no `public` (categoria cobrança) e na auditoria da empresa (categoria configurações), com plano antigo, novo, ciclo e a diferença. Teste com o código: `test_plt_04_upgrade_em_teste`, `test_plt_04_upgrade_proporcional`, `test_plt_04_upgrade_no_teste_com_primeira_paga`, `test_plt_04_downgrade_nao_cabe`, `test_plt_04_downgrade_agendado_e_desfeito`, `test_plt_04_downgrade_agendado_deixa_de_caber` (CA-ASS-40), `test_plt_04_downgrade_cabia_na_geracao` (CA-ASS-41).

## DELETE /api/assinatura/mudanca-plano/

Administrador. Desfaz o downgrade agendado (`plano_proximo` → nulo) até a véspera de `vale_em` (`PLT-04`). 200 com o corpo de `GET /api/assinatura/`; a próxima fatura volta ao valor de antes (CA-ASS-16: desfeito em 10 nov, a de 22 nov volta a 89900). Desfeito depois de a fatura do período seguinte ter sido gerada pelo plano menor (entre 17 e 21 nov no exemplo), a fatura `aberta` volta ao valor do plano atual e a cobrança dela no parceiro é refeita, como na troca no teste. Sem downgrade agendado, ou com a mudança de ciclo feita pela equipe (só a equipe desfaz): 404. Auditoria `empresa.desfazer_mudanca_plano` nos dois lugares.

### Downgrade agendado: conferência e virada (`PLT-04`, CA-ASS-40 e 41)

Decisão do dono em 14 out 2026 (T-211, opção A).

- **Conferência na geração da fatura.** Quando `gerar_faturas` vai criar a fatura do período seguinte (5 dias antes do vencimento, `PLT-02`) e há downgrade agendado em `plano_proximo`, ela confere o uso de novo, com a mesma conta da 422 `PLT-04` (limites do `UsoEmpresa` e `pendencias_dos_modulos` no schema da empresa, ADR 0024), com a `Empresa` e o `UsoEmpresa` travados.
- **Não cabe** (CA-ASS-40): o downgrade não acontece. Limpa `plano_proximo` (a tela deixa de dizer "O plano Profissional vale a partir de 22 nov", e `acoes.desfazer_mudanca_plano` volta a `false`), gera a fatura pelo plano atual e pelo `preco_contratado_centavos` (R$ 899,00 no exemplo), e manda e-mail ao administrador e ao `email_cobranca` com o motivo, o mesmo `detalhes` da 422 (`excede`, `abertos`, `abertos_texto`: "11 de 10 usuários"). Auditoria `empresa.mudar_plano_recusado` no `public` e na empresa (ator `sistema`, regra `PLT-04`), com o plano agendado e o `detalhes`.
- **Cabe** (CA-ASS-41): a fatura sai pelo plano menor (R$ 449,00), com a descrição dele ("Plano Profissional · 22 nov a 21 dez"), e `plano_proximo` continua até o vencimento. Até lá, `Empresa.plano` ainda é o atual, então `exigir_limite` e os módulos seguem o plano atual (os 6 convites de 19 nov entram). O que entrar nesses 5 dias não desfaz a mudança.
- **Virada no dia do vencimento**: `plataforma.virar_estados` (00:05) chama `plataforma.services.aplicar_mudanca_agendada(empresa)` nas empresas com `plano_proximo` cujo `vale_em` é hoje e cuja fatura do período já foi gerada: grava `plano`, `ciclo` (com `ciclo_proximo`) e `preco_contratado_centavos` com o preço de tabela do plano novo, limpa `plano_proximo` e `ciclo_proximo`, e recalcula o `uso`. Não confere de novo: com 11 de 10 usuários, ninguém sai e novos convites ficam bloqueados até sobrar vaga (`PLT-03`); o que ficou aberto num módulo que sai fica guardado (`PLT-12`). Auditoria `empresa.mudar_plano` (ator `sistema`) nos dois lugares. A mudança de ciclo pela equipe vira pelo mesmo serviço.
- Não passam pela conferência: a troca no teste com a 1ª fatura aberta (vale na hora) e a mudança só de ciclo pela equipe, que não tem limite a conferir.

---

## PUT /api/assinatura/forma-pagamento/

Administrador (`PLT-13`). Corpo: `{ "forma": "cartao" | "pix_automatico" | "boleto" }`. Os dados do cartão **nunca** passam pelo Giro (ADR 0023); não há campo de cartão neste corpo.

200:
```json
{ "forma_pagamento": { "forma": "pix_automatico", "situacao": { "codigo": "aguardando_autorizacao", "...": "..." }, "cartao": null, "prazo": null },
  "proximo_passo": { "tipo": "autorizar_pix", "pix_copia_e_cola": "000201...", "expira_em": "2026-10-08T15:00:00Z" } }
```

`proximo_passo` por forma:

| Forma | O que o backend faz | `proximo_passo` |
| --- | --- | --- |
| `boleto` | grava a forma. O boleto (com Pix) de cada fatura é criado no parceiro 5 dias antes do vencimento e vai por e-mail nesse dia (`PLT-02`). | `null` |
| `pix_automatico` | cria a autorização recorrente na conta principal (`criar_autorizacao_recorrente`, frequência do ciclo, valor = `preco_contratado_centavos`). A forma fica `aguardando_autorizacao` até o webhook confirmar. | `{ "tipo": "autorizar_pix", "pix_copia_e_cola", "expira_em" }`; o frontend desenha o QR a partir do copia e cola (como na T-029). |
| `cartao` | grava a forma. O cartão é digitado **na página do parceiro** ao pagar a 1ª fatura (o link vai no lembrete do D-3 e no "Pagar"); o parceiro guarda o cartão, e as faturas seguintes são cobradas nele no dia do vencimento, sem passar pela tela (`PLT-13`). Se há fatura `aberta` com cobrança já emitida ou `atrasada` agora, devolve a página dela. | `{ "tipo": "pagina_parceiro", "url": "https://...", "fatura": "FAT-0001" }` ou `null` (a 1ª fatura ainda sem cobrança emitida) |

- **A forma não muda o estado da empresa** (`PLT-13`, tabela de estados): `em_teste` continua `em_teste`, `suspensa` continua `suspensa` até pagar. CA-ASS-02.
- **A troca vale para a próxima cobrança e para a fatura em aberto** (`PLT-13`, CA-ASS-26). Trocar de forma cancela a anterior no parceiro: autorização do Pix automático cancelada (`cancelar_autorizacao`) e token do cartão esquecido. Fatura `aberta` ou `atrasada` com cobrança já emitida em outra forma: a cobrança antiga é cancelada no parceiro e a nova sai pela forma nova (na emissão, ou no "Pagar"). Se o parceiro disser que a antiga já foi paga, nada é cancelado e a baixa segue pelo webhook.
- Parceiro fora do ar: 503 `{ "codigo": "parceiro_indisponivel", "mensagem": "Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos." }` (o mesmo da T-029), nada gravado. Parceiro recusou: 422 `parceiro_recusou` com o motivo.
- Auditoria `assinatura.forma_pagamento` (forma antiga e nova; nunca token nem dado do cartão), nos dois lugares.

---

## GET /api/assinatura/faturas/

Administrador. Lista da tabela "Faturas" (`PLT-14`), da mais nova para a mais antiga, 25 por página. `?status=aberta|paga|atrasada|cancelada`.

```json
{ "resultados": [
    { "tipo": "fatura", "codigo": "FAT-0001", "vencimento": "2026-10-22",
      "descricao": "Plano Profissional · 22 out a 21 nov", "periodo": { "inicio": "2026-10-22", "fim": "2026-11-21" },
      "valor_centavos": 44900, "status": "aberta", "forma": null, "pago_em": null,
      "situacao": { "codigo": "sem_forma", "rotulo": "Sem forma de pagamento", "tom": "alerta" },
      "acoes": { "pagar": false, "recibo": false, "nota_fiscal": false } },
    { "tipo": "teste", "codigo": null, "vencimento": "2026-10-07",
      "descricao": "Teste grátis de 14 dias", "periodo": { "inicio": "2026-10-07", "fim": "2026-10-21" },
      "valor_centavos": 0, "status": null, "forma": null, "pago_em": null,
      "situacao": { "codigo": "teste_ativo", "rotulo": "Ativo", "tom": "info" },
      "acoes": { "pagar": false, "recibo": false, "nota_fiscal": false } }
  ],
  "proximo": null, "anterior": null }
```

- A linha do teste não é uma `FaturaAssinatura`: a API a acrescenta no fim da lista (última página) com os dados do teste, `tipo: "teste"`. Depois do teste, `situacao` `teste_concluido` "Concluído", `neutro`. Empresa que não passou por teste não tem a linha.
- A 1ª fatura existe desde a criação da empresa (`criar_empresa`, `aberta`, vencimento `teste_fim + 1`, valor do plano, `PLT-01`, `PLT-14`), e `faturas_recentes` do painel da plataforma lê as mesmas faturas. Estender o teste (`plataforma.md`) move o vencimento e o período dela, e o dia de vencimento das seguintes.
- `situacao`, na ordem:

  | `codigo` | Quando | `rotulo` | `tom` |
  | --- | --- | --- | --- |
  | `paga` | `paga` | "Paga em 22 out" | `sucesso` |
  | `cancelada` | `cancelada` | "Cancelada" | `neutro` |
  | `cartao_recusado` | aberta ou atrasada com a última tentativa no cartão recusada | 1ª recusa: "Cartão recusado · nova tentativa amanhã"; 2ª: "Cartão recusado · pague por Pix ou boleto" | `perigo` |
  | `atrasada` | `atrasada` | "12 dias atrasada" | `perigo` |
  | `sem_forma` | aberta e a empresa sem forma | "Sem forma de pagamento" | `alerta` |
  | `aguardando` | aberta com forma | "Vence em 22 out" (ou "Vence hoje") | `info` |

- `descricao` (`PLT-14`): "Plano Profissional · 22 out a 21 nov" (mensal), "Plano Profissional anual · out 2026 a out 2027" (anual), "Mudança para o plano Completo · 01 a 21 nov" (diferença do upgrade). Mês com o mesmo dia, como "22 out a 21 nov"; meses diferentes dentro do texto não levam o ano, salvo no anual.
- `acoes.pagar`: `aberta` ou `atrasada` e o estado permite (tabela do início). Sem forma cadastrada, `pagar` vem `false` na `aberta` que ainda não venceu e `true` na `atrasada` e em qualquer fatura da `suspensa` (o corpo de `pagar/` escolhe o meio). `acoes.recibo`: `paga`. `acoes.nota_fiscal`: `paga` com a nota `emitida` (`PLT-15`).
- `forma`: o meio pelo qual foi paga (`cartao`, `pix`, `boleto`); `null` em aberto.

## GET /api/assinatura/faturas/{codigo}/

Administrador. Uma linha do formato acima, mais:
- `cobranca`: `{ "forma": "boleto", "linha_digitavel": "...", "url_boleto": "https://...", "pix_copia_e_cola": "...", "url_pagina": null, "vencimento": "2026-10-22" }` quando há cobrança emitida no parceiro; senão `null`.
- `recibo_url`: comprovante do parceiro quando `paga`; senão `null`. É link do parceiro com validade dele; o Giro não gera PDF de recibo no MVP.
- `nota_fiscal` (`PLT-15`): `{ "situacao": "emitida" | "processando" | "erro", "numero": "2026/118", "url": "https://..." }` quando a emissão foi pedida ao parceiro; `null` antes disso e enquanto a emissão estiver desligada (ver "Nota fiscal da assinatura"). `erro` não mostra o motivo do parceiro ao administrador ("A nota está com a equipe Giro."); a equipe vê pelo Django Admin.

`codigo` de outra empresa: 404.

## POST /api/assinatura/faturas/{codigo}/pagar/

Administrador. Para pagar agora uma fatura `aberta` ou `atrasada` (o botão aparece com `acoes.pagar`). Corpo opcional: `{ "meio": "cartao" | "pix" | "boleto" }`.

- Sem `meio`, usa a forma cadastrada: `cartao` → página do parceiro; `pix_automatico` → Pix avulso da fatura (a autorização recorrente só cobra no vencimento); `boleto` → boleto com Pix.
- Com `meio`, paga por outro meio **sem trocar a forma cadastrada**: é o caminho da `PLT-02` depois da 2ª recusa do cartão (CA-ASS-12) e o da `suspensa` sem forma (CA-ASS-27). Para mudar a forma das próximas, `PUT forma-pagamento/`.

200: o `cobranca` do detalhe, já emitido. Para `cartao`, `url_pagina` é a página do parceiro onde o cartão é digitado (e fica guardado para as próximas, ADR 0023). Se já existe cobrança válida no parceiro no mesmo meio, devolve a mesma; não cria duas (como a T-029 faz nas contas a receber). Em outro meio, cancela a antiga no parceiro antes de criar a nova (uma cobrança viva por fatura).

Erros: 409 `{ "codigo": "fatura_nao_pagavel", "mensagem": "Esta fatura já foi paga ou cancelada." }`; 422 `{ "codigo": "sem_forma_pagamento", "mensagem": "Escolha a forma de pagamento antes." }` (sem forma e sem `meio`); 503 `parceiro_indisponivel`; 422 `parceiro_recusou`.

A baixa **nunca** vem desta rota: vem do webhook (`financeiro.md`, "Webhooks", "O mesmo fluxo vale para a `FaturaAssinatura`"), que consulta a cobrança no parceiro antes de baixar. Fatura paga → `paga`, `pago_em`, `forma`, e daí não se edita (`PLT-14`). Efeito no estado da empresa (tabela de estados):
- `em_teste`, 1ª fatura paga antes do fim do teste: continua `em_teste`; vira `ativa` no dia seguinte ao fim do teste (tarefa `virar_estados`, abaixo). Nenhuma mensagem da régua sai depois do pagamento (CA-ASS-03).
- `em_teste` no dia do vencimento, `inadimplente` ou `suspensa`, sem outra fatura atrasada: `ativa` na hora (CA-ASS-04 a 06, CA-ASS-27).
- Auditoria `fatura_assinatura.pagar` (ator `sistema`, regra `PLT-14`), e o pedido da NFS-e (abaixo).

---

## PATCH /api/assinatura/dados-fiscais/

Administrador (`PLT-15`). Corpo (parcial):
```json
{ "razao_social": "Moto Rápida Locações Ltda",
  "endereco": { "cep": "60115170", "logradouro": "Av. Dom Luís", "numero": "500", "complemento": "Sala 3", "bairro": "Meireles", "cidade": "Fortaleza", "uf": "CE" },
  "email_cobranca": "financeiro@motorapida.com.br" }
```

200: `{ "dados_fiscais": { "razao_social", "cnpj", "endereco", "email_cobranca" } }`.

- `email_cobranca` (`Empresa.email_cobranca`) nasce igual ao e-mail do administrador da compra (`responsavel_email`). Recebe as faturas, o boleto, a régua da assinatura (`PLT-02`, `AUT-13`), o comprovante e a NFS-e. A troca vale a partir da próxima mensagem (CA-ASS-29).
- `razao_social`: até 150 caracteres. É a mesma `Empresa.razao_social` do painel da plataforma e do bloco "Dados da empresa" da `Admin-Marca`: uma só origem, no `public`.
- `endereco`: o endereço da nota (`Empresa.endereco_*`), no formato do endereço da filial (`filiais.md`): CEP com 8 dígitos, UF da lista; `complemento` opcional, o resto obrigatório quando o bloco vem. Quando o bloco vem, vem inteiro; `endereco: null` é recusado (400 `validacao`), para a nota não voltar a esperar. Editar aqui não muda nenhuma filial (CA-ASS-48).
- Mudar a razão social ou o endereço atualiza o pagador na conta principal (`criar_ou_atualizar_pagador`) antes da próxima cobrança e vale para as próximas notas; nota já emitida não muda.
- **CNPJ não muda por aqui**: o campo não é aceito (400 `{ "codigo": "validacao", "campos": { "cnpj": "O CNPJ não muda por aqui. Fale com o suporte." } }`). Trocar o CNPJ é trocar quem contrata, e fica com a equipe Giro (`PLT-15`).
- Auditoria `empresa.dados_fiscais` nos dois lugares, com antes e depois.

**De onde vem o endereço** (`PLT-15`, decisão do dono em 14 out 2026, T-211, opção B; CA-ASS-47 e 48):

- A compra (`Compra-Checkout`) não pede endereço, e a empresa nasce com `endereco_*` nulos. Antes do passo 6, os dados fiscais mostram o endereço vazio.
- **Cópia única da matriz.** `filiais.services.criar_filial`, quando a filial nasce matriz, chama na mesma transação `plataforma.services.copiar_endereco_da_matriz(endereco)` (interface de `plataforma` para `filiais`, como `registrar_passo_implantacao`). O serviço trava a `Empresa` no `public` e só grava se ela ainda não tem endereço (`endereco_cep` nulo); senão, não faz nada. Na prática, copia uma vez, da primeira filial, seja ela criada pelo assistente (`Onboarding-Filial`), pela tela de Filiais ou pela importação. Auditoria `empresa.dados_fiscais` no `public` (ator `sistema`, regra `PLT-15`, com a filial de origem).
- **Sem ligação depois.** `editar_filial`, `tornar_matriz` e a criação de outra matriz não mudam o endereço da nota; o `PATCH` acima não muda filial nenhuma. `filiais` não lê o endereço da empresa.
- **Nota que esperava.** Quando a empresa passa a ter endereço (pela cópia ou pelo `PATCH`), `transaction.on_commit` agenda `plataforma.pedir_notas_pendentes(empresa_id)`, que pede as notas das faturas pagas marcadas "nota pendente" (só com `GIRO_NFSE_ASSINATURA_ATIVA=true`; desligada, nada é pedido, e o critério só confere o endereço).
- **Seed Moto Rápida.** A `Empresa` nasce com o endereço da Filial Centro (Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000), pelo mesmo serviço quando o seed cria a matriz. Testes `test_plt_15_endereco_nasce_da_matriz` (CA-ASS-47) e `test_plt_15_endereco_da_nota_e_da_filial_separados` (CA-ASS-48).

---

## Faturas, cobrança e régua (sem rota; para o backend)

O que precisa existir no `public` para a tela mostrar dados reais. As faturas de todas as empresas, do lado da equipe Giro, ficam no Django Admin até a `Plat-Cobranca` (fase 2; `plataforma.md`, "Faturas de todas as empresas", `PLT-14`).

- **Conta principal** do Giro no parceiro (ADR 0007): `ContaPagamentoRef` sem subconta, chave do ambiente (`GIRO_ASAAS_CHAVE_API`), como a T-029 já deixou preparado (CA-029-18). O webhook da conta principal tem token próprio, guardado só como hash em configuração (`GIRO_WEBHOOK_PRINCIPAL_TOKEN_HASH`), e a view do webhook procura primeiro a `ContaPagamento` e, se o token for o da conta principal, trata como fatura da assinatura no `public`.
- **Pagador**: cada empresa vira um cliente na conta principal (`cliente_externo_id` em `FormaPagamentoAssinatura`), com razão social, CNPJ, endereço e `email_cobranca`, criado na primeira cobrança, com as notificações do parceiro desligadas (as mensagens são do Giro).
- **Dia de vencimento** (`PLT-01`): `Empresa.dia_vencimento` (1 a 31) nasce com o dia de `teste_fim + 1` e muda só quando a empresa volta da pausa ou é reativada pela equipe depois de acabar o período pago (o dia da volta, `PLT-06`) ou quando a equipe estende o teste. Em mês sem esse dia, vence no último dia do mês, e no mês seguinte volta ao `dia_vencimento` (CA-ASS-08: 31 jan, 28 fev, 31 mar). Cada fatura paga do vencimento até a véspera do vencimento seguinte; anual, do vencimento até a véspera do mesmo dia no ano seguinte, com 10 mensalidades (CA-ASS-09). `competencia` = mês do início do período. Função pura `plataforma.calendario.proximo_periodo(dia_vencimento, ciclo, inicio)`, com teste dos casos da `PLT-01`.
- **Geração das faturas** (tarefa diária `plataforma.gerar_faturas`, 06:00): 5 dias antes do vencimento seguinte, cria a fatura do período seguinte com o `preco_contratado_centavos`, pelo plano e pelo preço do que estiver agendado em `plano_proximo` (downgrade, ou ciclo pela equipe), depois da conferência do downgrade ("Downgrade agendado: conferência e virada"); a troca do plano em si é no dia do vencimento. Única por `(empresa, competencia)` para `tipo = mensalidade`. Não gera para `pausada` nem `cancelada`, nem para a empresa com cancelamento marcado cujo acesso acaba antes do período (T-194).
- **Emissão no parceiro** (`PLT-02`), na mesma tarefa: 5 dias antes do vencimento, o boleto com Pix (e o e-mail nesse dia) ou a cobrança do Pix automático pela autorização (o parceiro pede de 2 a 10 dias úteis antes, ver T-029); com `cartao` e sem cartão guardado, a cobrança com a página do parceiro, cujo link vai no D-3 e no "Pagar". Cartão guardado: cobrado no dia do vencimento pelo token (`cobrar_cartao_salvo`), às 06:00.
- **Cartão recusado** (`PLT-02`, U8): a tarefa grava `cartao_recusado_em` e soma `tentativas_cartao`; com 1 tentativa, cobra de novo uma vez no dia seguinte; com 2, não há outra tentativa automática, e a régua segue (CA-ASS-12). A empresa paga por outro meio com `pagar/` e `meio`. O teto de 2 fica numa constante com o código da regra, com teste `test_plt_02_cartao_uma_tentativa_a_mais`.
- **Régua `AUT-13`** às 09:00, pela `PLT-02`: D-3 lembrete por e-mail; D0 e-mail + WhatsApp; D+3 e-mail + WhatsApp; D+7 aviso de suspensão (e-mail e tarefa de ligação para a equipe, a tela é fase 2); D+15 suspensão. Os e-mails vão para o `email_cobranca` e para os administradores ativos da empresa; o WhatsApp, para o `responsavel_telefone`. Fatura paga, cancelada, ou empresa `cancelada`: a régua para (`PLT-06`).
- **Transições da empresa** (tarefa `plataforma.virar_estados`, 00:05, e o webhook), pelo serviço de estados, com auditoria no `public` e na empresa, e a `faixa_aviso` já existente passando a ter dados reais:

  | De | Quando | Para |
  | --- | --- | --- |
  | `em_teste` | dia seguinte ao fim do teste, com a 1ª fatura paga | `ativa` |
  | `em_teste` | 1ª fatura paga a partir do dia seguinte ao fim do teste | `ativa` na hora |
  | `em_teste` | dia seguinte ao fim do teste, sem forma de pagamento | `suspensa` (CA-ASS-06) |
  | `em_teste` | dia seguinte ao vencimento da 1ª fatura (D+1), com forma e sem pagamento | `inadimplente` (CA-ASS-05, CA-ASS-11) |
  | `ativa` | D+1 de uma fatura sem pagamento | `inadimplente` |
  | `inadimplente` | D+15 | `suspensa` |
  | `inadimplente`, `suspensa` | fatura paga, sem outra atrasada | `ativa` na hora |

  Com a FAT-0001 vencendo em 22 out: com forma e sem pagamento, `inadimplente` em 23 out e `suspensa` em 06 nov; sem forma, `suspensa` já em 22 out (CA-ASS-05, CA-ASS-06). A `suspensa` sem forma que paga depois volta a `ativa`, e a próxima fatura continua no `dia_vencimento` (22 nov).
- **Faturas e cancelamento ou pausa**: o que acontece com a 1ª fatura, a fatura do período seguinte já emitida e a régua quando a empresa cancela ou pausa está no contrato da T-194 (`PLT-06`). Volta da pausa: `ativa` com uma fatura nova vencendo no dia da volta, e `dia_vencimento` passa a esse dia (CA-ASS-35, CA-ASS-36).

### Nota fiscal da assinatura (`PLT-15`)

- Depois da baixa de cada fatura, a tarefa `plataforma.emitir_nota_fatura` (Celery, depois do commit) pede a NFS-e ao parceiro pela conta principal (Asaas), com o tomador da `Empresa` (razão social, CNPJ, endereço, `email_cobranca`) e o serviço do Giro (código do serviço, alíquota e cadastro municipal na configuração, `GIRO_NFSE_*`, nunca no código). O retorno vem por webhook da conta principal (ou consulta, se o parceiro não avisar), e a nota vai por e-mail para o `email_cobranca` com o link do PDF. Situações: `processando`, `emitida` (número e link), `erro` (fica para a equipe no Django Admin, que pede de novo).
- **Ligada só com `GIRO_NFSE_ASSINATURA_ATIVA=true`.** Enquanto o cadastro municipal do Giro não estiver pronto (a validar com o contador), a configuração fica desligada: nada é pedido, `nota_fiscal` vem `null` e o bloco só guarda e mostra os dados (CA-ASS-29 em `xfail`). A tarefa de código é a T-197, `[bloqueada]`.
- Sem endereço na empresa (antes do passo 6), a nota não é pedida e a fatura fica marcada para a equipe (Django Admin, filtro "nota pendente"); quando o endereço passa a existir (cópia da matriz ou dados fiscais), `pedir_notas_pendentes` pede as notas das faturas pagas (ver "De onde vem o endereço").
- A interface de pagamentos (ADR 0007) ganha `emitir_nota_servico(conta, pedido)` e `situacao_nota(conta, id_externo)`; o fake de pagamentos devolve `emitida` com número fixo, para os testes.
- Fatura paga que for estornada no parceiro: o cancelamento da nota fica com a equipe (fase 2, `Plat-Cobranca`).

### Mudança de ciclo e reativação pela equipe

Do lado da equipe Giro; não há rota da empresa. No MVP, a equipe usa o Django Admin, que chama o mesmo serviço das ações da plataforma (fase 2, `plataforma.md`, "Ações sobre a empresa").

- **Mensal ↔ anual** (`PLT-04`, U4): `plataforma.services.mudar_plano(empresa, plano, ciclo, por, motivo)` com o ciclo novo grava `plano_proximo` e `ciclo_proximo` e vale na próxima fatura, com o preço de tabela do plano no ciclo novo, que vira o preço contratado. A tela da empresa mostra a mudança em `plano_proximo` (sem `desfazer_mudanca_plano`). Auditoria `empresa.mudar_ciclo` nos dois lugares, com o motivo.
- **Reativar a `cancelada`** (`PLT-06`, `AUD-08`): só dentro dos 90 dias (`apagar_em` no futuro), por `plataforma.services.reativar_empresa(empresa, por, motivo)`: volta a `ativa` na hora e limpa `cancelada_em`, `acesso_ate` e `apagar_em`. A fatura nova (`tipo = mensalidade`, `preco_contratado_centavos`, plano e ciclo atuais) depende do último período pago (`PLT-06`, decisão de 14 out 2026, T-216):
  - **Período pago ainda correndo** (a fatura `mensalidade` `paga` de fim mais tarde tem `periodo_fim >= hoje`): a fatura nova vence em `periodo_fim + 1` e cobre o período seguinte, pelo `dia_vencimento`, que **não muda**. Nada vence no dia da volta. CA-ASS-49: Moto Rápida no Completo, FAT-0001 (22 out a 21 nov) paga, cancelada na hora em 10 nov, diferença do upgrade paga e reativada em 15 nov → `ativa` em 15 nov, fatura de R$ 899,00 vencendo em 22 nov, "Plano Completo · 22 nov a 21 dez", e as seguintes todo dia 22. Só a empresa que virou `cancelada` na hora (inadimplente ou suspensa) chega aqui; a fatura de diferença do upgrade não conta como período pago.
  - **Período pago já acabou** (ou nenhuma fatura do período paga): a fatura nova vence no dia da volta e `dia_vencimento` passa a esse dia, como na volta da pausa. CA-ASS-46: reativada em 01 dez → FAT-0002 de R$ 449,00 vencendo em 01 dez, "Plano Profissional · 01 dez a 31 dez", e as seguintes todo dia 1.
  - Se já existe fatura `mensalidade` não cancelada para esse período (gerada antes do cancelamento), ela é a fatura nova: não nasce outra (a restrição de `(empresa, competencia)` também impede). A emissão no parceiro segue a `PLT-02`: com vencimento até 5 dias à frente, na hora (boleto por e-mail no dia); mais longe, pela `gerar_faturas`, 5 dias antes, como a 1ª fatura (no CA-ASS-49, em 17 nov). A régua volta a valer para ela.
  - A conta do vencimento fica numa função pura, `plataforma.calendario.vencimento_da_reativacao(hoje, ultimo_periodo_pago_fim, dia_vencimento)`, que devolve o vencimento e o `dia_vencimento`, com teste dos dois casos. Teste com o código: `test_plt_06_reativar_no_periodo_pago` (CA-ASS-49). Depois dos 90 dias (dados apagados): 409 `transicao_empresa`. Com fatura `atrasada` de antes do cancelamento, a reativação é recusada com 409 `{ "codigo": "fatura_em_atraso", "mensagem": "Receba a fatura em atraso antes de reativar." }` e nada muda; a equipe recebe a fatura (2ª via, baixa pelo webhook) e reativa depois (decisão do dono em 14 out 2026, T-211, opção A; CA-ASS-46, `test_plt_06_reativar_so_com_atrasada_paga`). Auditoria `empresa.reativar` nos dois lugares, com o motivo.

---

## Erros deste contrato

| HTTP | `codigo` | Quando |
| --- | --- | --- |
| 400 | `validacao` | campo inválido; CNPJ enviado em `dados-fiscais/` |
| 403 | `permissao` | perfil que não é administrador |
| 403 | `PLT-07` | escrita com token de suporte |
| 403 | `empresa_sem_operacao` | `pausada`, `cancelada` (a `suspensa` paga, ver o início) |
| 409 | `transicao_empresa` | mudar de plano fora de `em_teste` e `ativa`; outra mudança já agendada |
| 409 | `valor_mudou` | diferença do upgrade mudou entre simular e confirmar |
| 409 | `fatura_nao_pagavel` | fatura paga ou cancelada |
| 409 | `fatura_em_atraso` | reativar a `cancelada` com fatura atrasada (equipe, `PLT-06`) |
| 422 | `PLT-04` | downgrade com uso que não cabe |
| 422 | `mudanca_ciclo`, `mesmo_plano` | ver mudança de plano |
| 422 | `sem_forma_pagamento` | pagar sem forma cadastrada e sem `meio` |
| 422 | `parceiro_recusou` | o parceiro recusou (mensagem dele, sem o nome do parceiro) |
| 503 | `parceiro_indisponivel` | o parceiro não respondeu |

---

## O que muda para as tarefas abertas

- **T-184 (faturas e conta principal):** `Empresa.dia_vencimento`, `ciclo_proximo` e `endereco_*`; na `FaturaAssinatura`, os campos da nota (`nota_situacao`, `nota_numero`, `nota_externa_id`, `nota_url`, `nota_pedida_em`); a 1ª fatura e o seed não mudam (FAT-0001, 22 out, 44900); o pagador leva o endereço. Modelo em `modelo-de-dados.md`.
- **T-185 (rotas):** `oferta` com `titulo` e `itens` (sai `recursos_a_mais` e `sem_limite`); `itens` no lugar de `recursos` em `planos/`; `acoes.desfazer_mudanca_plano`; upgrade no teste com a 1ª fatura paga; 409 da segunda mudança agendada; `meio` no `pagar/`; `endereco` nos dados fiscais; `acoes.nota_fiscal` e `nota_fiscal` no detalhe; `prazo` só com `forma` nula. Os testes de `PLT-04` seguem a conta da regra (R$ 304,84). `excede.abertos` e a 422 com `detalhes.abertos` usam `pendencias_dos_modulos`, que a T-196 entrega; se a T-185 fechar antes, os grupos valem 0 (`test_plt_12_downgrade_recusado_com_modulo_aberto` fica com a T-196).
- **T-186 (régua e estados):** a forma **não** ativa a empresa; a tabela de transições acima (vira `ativa` no dia seguinte ao teste com a 1ª paga); `inadimplente` em D+1; emissão 5 dias antes; teto de 2 tentativas do cartão; e-mails para o `email_cobranca` e os administradores; downgrade que deixou de caber (limites e, pela ADR 0024, `pendencias_dos_modulos` no schema da empresa; o e-mail leva o `abertos_texto`); `dia_vencimento` com o mês sem o dia. Testes `test_plt_01_*`, `test_plt_02_*` com o relógio de referência e os casos CA-ASS-01 a 12.
- **T-187 (tela):** cartão da `oferta` só com o que vier (título e itens da API); comparação com `itens`; "Pagar" depois da 2ª recusa oferece Pix ou boleto (`meio`); endereço no bloco de dados fiscais; botão da nota na fatura paga com `acoes.nota_fiscal`; "Desfazer" do downgrade com `acoes.desfazer_mudanca_plano`.
- **T-188 (telas de referência):** sem mudança além do que a T-200 já pede (título "Precisa de mais veículos ou filiais?").
- **T-189 (segurança):** o `meio` do `pagar/` não troca a forma (sem novo token); dados da nota sem dado pessoal além dos da empresa.
- **T-197 (NFS-e, bloqueada):** a seção "Nota fiscal da assinatura".

**Da T-213 (endereço e downgrade, regras da T-211):**

- **T-184 (faturas e seed):** `plataforma.services.copiar_endereco_da_matriz` e a chamada em `filiais.services.criar_filial` (só quando a filial nasce matriz; o serviço não grava se já houver endereço); o seed passa a ter o endereço da Filial Centro nos dados fiscais (o "Caso do seed" deixou de dizer `endereco` nulo); `pedir_notas_pendentes` depois do commit quando o endereço passa a existir. Testes `test_plt_15_endereco_nasce_da_matriz` e `test_plt_15_endereco_da_nota_e_da_filial_separados`.
- **T-185 (rotas):** `PATCH dados-fiscais/` recusa `endereco: null`; `DELETE mudanca-plano/` depois da fatura gerada pelo plano menor devolve a fatura `aberta` ao valor do plano atual; `GET` do seed com o endereço preenchido.
- **T-186 (régua e estados):** conferência do downgrade na geração da fatura e `aplicar_mudanca_agendada` no dia do vencimento, em `virar_estados`. Testes `test_plt_04_downgrade_agendado_deixa_de_caber` e `test_plt_04_downgrade_cabia_na_geracao` (CA-ASS-40 e 41).
- **T-187 (tela):** o bloco de dados fiscais já vem com o endereço no seed; o endereço não se apaga pela tela (o formulário troca o bloco inteiro).
- **Reativação pela equipe** (quem fizer `reativar_empresa`): o 409 `fatura_em_atraso` deixou de ser provisório. O vencimento da fatura nova muda na T-217 (`PLT-06`, T-216).

**Da T-217 (reativação no período pago, regra da T-216):**

- **T-184 (faturas):** `FaturaAssinatura.periodo_fim` é o que decide; a fatura nova da reativação usa `proximo_periodo` a partir de `periodo_fim + 1` sem mexer em `dia_vencimento`.
- **T-186 (estados e régua):** a fatura da reativação com vencimento a mais de 5 dias é emitida pela `gerar_faturas` como a 1ª; a régua volta a valer para ela.
- **Quem fizer `reativar_empresa`** (backend, ainda sem número; Django Admin no MVP): os dois casos acima, `vencimento_da_reativacao` e os testes `test_plt_06_reativar_no_periodo_pago` (CA-ASS-49) e `test_plt_06_reativar_so_com_atrasada_paga` (CA-ASS-46).
