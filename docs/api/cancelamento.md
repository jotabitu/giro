# Cancelar e pausar a assinatura (Admin › Cancelar assinatura)

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-194, com os acréscimos da T-211 e da T-231) · **App:** `plataforma` (lê e grava no `public`, servido no host da empresa) · **Regras:** PLT-06, AUD-08, PLT-01, PLT-02, PLT-04, PLT-13, PLT-14, tabela de estados da empresa · **ADR:** 0010, 0012, 0016, 0025 · **Telas:** Admin-Cancelar e Admin-Assinatura (desktop e celular) · **Critérios:** `docs/qa/criterios/assinatura.md` (CA-ASS-30 a 39, 42 a 45, 54 a 58)

Decisão do dono em 14 out 2026 (T-190): cancelar e pausar entram no MVP. Os pontos em aberto da T-190 foram decididos na T-211 (a pausa começa no fim do período pago; o administrador desfaz o cancelamento pela tela até o último dia de acesso).

> **O que mudou na T-231 (decisões do dono de 15 out 2026, regras na T-229).** Os cinco casos que eram `[decisão]` ficaram com o padrão deste contrato (opção A em todos), e as marcas saíram: (1) cancelar em teste com a 1ª fatura paga segue a `ativa`, com acesso até o fim do período da 1ª fatura e sem estorno (CA-ASS-54); (2) o administrador desiste da pausa agendada até o último dia do período pago, com a ação nova `acoes.desistir_pausa`, e "Voltar da pausa" fica só para a `pausada` (CA-ASS-55); (3) mudar de plano e pausar com o cancelamento marcado são recusados, e o downgrade agendado continua (CA-ASS-56); (4) a fatura de diferença em aberto continua devida durante a pausa (CA-ASS-57); (5) o que fica no `public` depois do apagamento (CA-ASS-58). O prazo de guarda das faturas fica com o dono e o contador, e o MEI e o empresário individual, com a segurança (T-230).

Este contrato completa `assinatura.md`, que já tem a mudança de plano, as faturas, a régua e a reativação pela equipe; aqui ficam as rotas da `Admin-Cancelar`, a pausa, o desfazer, o que acontece com as faturas e a régua, e o apagamento no 90º dia.

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (itens 2 e 3). Datas no fuso `America/Sao_Paulo`; "hoje" é a data local (ADR 0021 no desenvolvimento).

---

## Quem usa

- Todas as rotas deste contrato são **só do administrador** (`PLT-06`). Outro perfil: 403 `{ "codigo": "permissao", "mensagem": "Só o administrador mexe na assinatura" }` (CA-ASS-45: o Rodrigo e a Lúcia).
- Suporte Giro dentro da empresa (`PLT-07`): 403 `{ "codigo": "PLT-07", "mensagem": "O suporte não mexe na assinatura da empresa" }` em toda escrita, como em `assinatura.md`. O `GET` responde com `acoes` todas `false`.
- 2 etapas recentes para cancelar: a T-199 (segurança) decide. Se entrar, a rota responde antes o 403 `2fa_recente` de `auditoria.md`, e este contrato ganha a linha na tabela de erros.

### Estado da empresa e o que cada rota aceita

`somente_leitura` (empresa `suspensa` ou `pausada`) faz toda escrita responder 403 `empresa_sem_operacao` (`plataforma.md`). Como a `suspensa` que paga (`assinatura.md`), estas rotas entram na **lista explícita de exceções** da permissão de `somente_leitura`, com teste: `POST cancelamento/` (a `suspensa` e a `pausada` cancelam, `PLT-06`) e `DELETE pausa/` (a `pausada` volta). A `cancelada` não entra no sistema (abaixo, "Empresa `cancelada`").

| Rota | `em_teste` | `ativa` | `inadimplente` | `suspensa` | `pausada` |
| --- | --- | --- | --- | --- | --- |
| ler (`GET cancelamento/`) | sim | sim | sim | sim | sim |
| cancelar | sim, acesso até o fim do teste | sim, acesso até o fim do período pago | sim, `cancelada` na hora | sim, na hora | sim, na hora |
| desfazer o cancelamento | com cancelamento marcado | com cancelamento marcado | — | — | — |
| pausar | não | sim | não | não | não |
| voltar da pausa | — | com pausa agendada: desiste, até a véspera de `pausa_inicio` | — | — | sim |

Fora da tabela: 409 `{ "codigo": "transicao_empresa", "mensagem": "<texto do caso>" }`, com os textos de cada rota abaixo.

**Cancelamento marcado** é a empresa que pediu o cancelamento e ainda tem acesso: `Empresa.acesso_ate` preenchido e `status` diferente de `cancelada`. O `status` não muda ao marcar (tabela de estados: `cancelada` entra no fim do acesso). **Pausa marcada** é `Empresa.pausa_inicio` preenchido: agendada enquanto `status` é `ativa`, em andamento quando é `pausada`.

---

## GET /api/assinatura/ (campos novos)

Os campos de `assinatura.md` não mudam. Entram dois blocos, `null` quando não há o que mostrar, e quatro `acoes`:

```json
{
  "status": "ativa",
  "proxima_fatura": null,
  "cancelamento": {
    "pedido_em": "2026-11-05T13:20:00Z",
    "motivo": "preco_alto",
    "acesso_ate": "2026-11-21",
    "rotulo": "Assinatura cancelada. Você tem acesso até 21 nov."
  },
  "pausa": null,
  "acoes": { "...": "as de assinatura.md", "cancelar": false, "desfazer_cancelamento": true, "pausar": false, "voltar_pausa": false, "desistir_pausa": false }
}
```

- **`cancelamento`**: só com cancelamento marcado. `acesso_ate` é o último dia de acesso; `rotulo` é o texto pronto do estado da `Admin-Assinatura` (T-214). No anual, o ano entra na data ("até 21 out 2027"), como na descrição das faturas (`PLT-14`).
- **`pausa`**: só com pausa marcada.
  ```json
  { "situacao": "agendada", "meses": 2, "inicio": "2026-11-22", "ate": "2027-01-21", "volta_em": "2027-01-22",
    "rotulo": "Pausa marcada de 22 nov a 21 jan. Até lá, tudo continua." }
  ```
  Em andamento, `situacao: "em_andamento"` e `rotulo` "Assinatura pausada até 21 jan. Volta sozinha em 22 jan." Os dois textos são provisórios até a tela existir (T-214 ou T-200); o frontend mostra o que vier.
- **`proxima_fatura`** vem `null` com cancelamento marcado, com pausa marcada e em `pausada` (nada vai ser cobrado; a volta da pausa cria a fatura no dia). `plano_proximo` continua como está (ver "Mudanças enquanto há cancelamento ou pausa").
- **`faixa_aviso`** (`plataforma.md`) na `pausada`: "Assinatura pausada até 21 jan. Você só consulta os dados." (provisório, como acima). O cancelamento marcado não tem faixa no topo: o aviso fica na `Admin-Assinatura`.
- **`acoes`**, já cruzando perfil, estado e a tabela acima:
  - `cancelar`: administrador, sem cancelamento marcado, `status` em `em_teste`, `ativa`, `inadimplente`, `suspensa` ou `pausada`. Substitui o `cancelar: false` provisório de `assinatura.md`.
  - `desfazer_cancelamento`: administrador, cancelamento marcado e hoje ≤ `acesso_ate`.
  - `pausar`: administrador, `ativa`, sem cancelamento nem pausa marcados.
  - `voltar_pausa`: administrador, `pausada` (pausa em andamento). Botão "Voltar da pausa".
  - `desistir_pausa`: administrador, `ativa` com pausa agendada (hoje < `pausa_inicio`, isto é, até o último dia do período pago). Botão "Desistir da pausa". As duas ações nunca vêm `true` juntas e chamam a mesma rota (`DELETE pausa/`).
  - Com cancelamento marcado, `mudar_plano`, `desfazer_mudanca_plano` e `pausar` vêm `false`.

---

## GET /api/assinatura/cancelamento/

Administrador. Tudo o que a `Admin-Cancelar` mostra, montado pela API para o estado de hoje. Não grava nada.

```json
{
  "empresa": "Moto Rápida",
  "plano_resumo": "Plano Profissional · em teste até 21 out",
  "motivos": [
    { "codigo": "preco_alto", "rotulo": "Preço alto para o meu tamanho" },
    { "codigo": "faltou_funcao", "rotulo": "Faltou alguma função" },
    { "codigo": "outro_sistema", "rotulo": "Vou usar outro sistema" },
    { "codigo": "fechar_ou_pausar", "rotulo": "Vou fechar ou pausar a locadora" },
    { "codigo": "outro", "rotulo": "Outro motivo" }
  ],
  "alternativas": {
    "pausar": null,
    "mudar_para_essencial": {
      "plano": { "id": 1, "nome": "Essencial", "preco_mensal_centavos": 19900 },
      "resumo": "Até 30 veículos, 1 filial e 3 usuários.",
      "cabe": false,
      "excede": { "veiculos": { "usado": 86, "limite": 30 }, "usuarios": { "usado": 5, "limite": 3 } }
    }
  },
  "o_que_acontece": [
    { "codigo": "acesso", "rotulo": "Acesso", "valor": "continua até 21 out" },
    { "codigo": "cobrancas", "rotulo": "Cobranças futuras", "valor": "nenhuma" },
    { "codigo": "dados", "rotulo": "Seus dados", "valor": "guardados por 90 dias" },
    { "codigo": "apagamento", "rotulo": "Depois de 90 dias", "valor": "apagados de vez" },
    { "codigo": "contratos", "rotulo": "Contratos dos seus clientes", "valor": "continuam válidos" }
  ],
  "acesso_ate": "2026-10-21",
  "cancelada_em": "2026-10-22",
  "apagar_em": "2027-01-20",
  "confirmacao": { "nome": "Moto Rápida" },
  "exportar": { "texto": "Exportar baixa a auditoria em CSV. O resto dos seus dados você pede à equipe Giro." }
}
```

- `empresa` e `confirmacao.nome` são o `Empresa.nome_exibicao`. `plano_resumo` segue o estado: "Plano Profissional · em teste até 21 out", "Plano Profissional · mensal", "Plano Profissional · anual até 21 out 2027".
- **`alternativas.pausar`** (`PLT-06`, CA-ASS-37): só quando `acoes.pausar` seria `true` (empresa `ativa`, sem pausa marcada); senão `null`. Quando vem: `{ "meses": [1, 2, 3], "inicio": "2026-11-22", "texto": "A pausa começa em 22 nov, no fim do período pago." }`. A tela chama `POST pausa/`.
- **`alternativas.mudar_para_essencial`**: só quando a empresa pode mudar de plano (`em_teste` ou `ativa`, `PLT-04`) e não está no Essencial; senão `null`. `cabe` e `excede` são os mesmos da linha do Essencial em `GET /api/assinatura/planos/` (inclusive `excede.abertos`, ADR 0024). "Ver plano" abre a lista de planos; a mudança segue `assinatura.md`.
- **`o_que_acontece`**: as cinco linhas, na ordem, com `valor` pronto para o estado (o frontend não monta texto):

  | Estado | `acesso` | `cobrancas` |
  | --- | --- | --- |
  | `em_teste` (1ª fatura em aberto) | "continua até 21 out" (fim do teste) | "nenhuma" |
  | `em_teste` (1ª fatura paga) | como a `ativa`: "continua até 21 nov" (fim do período da 1ª fatura); no anual, "continua até 21 out 2027", sem devolução | como a `ativa` |
  | `ativa` mensal | "continua até 21 nov" (fim do período pago) | "nenhuma" |
  | `ativa` anual | "continua até 21 out 2027", sem devolução | "nenhuma. Os meses que faltam não são devolvidos." |
  | `ativa` com fatura de diferença do upgrade em aberto | como a `ativa` | "nenhuma nova. A fatura FAT-0003, de R$ 304,84, continua devida." |
  | `inadimplente`, `suspensa` | "termina agora" | "nenhuma nova. A fatura em atraso continua devida." |
  | `pausada` | "termina agora" | "nenhuma" |

  `dados`, `apagamento` e `contratos` não mudam (`AUD-08`, `PLT-06`, CA-ASS-39).
- `acesso_ate`: o último dia de acesso se cancelar hoje (`null` quando termina agora). `cancelada_em`: o dia em que a empresa vira `cancelada` (dia seguinte a `acesso_ate`, ou hoje). `apagar_em`: `cancelada_em` + 90 dias (`AUD-08`). As três vêm da mesma função do `POST` (abaixo), então a tela mostra o que vai acontecer.
- `exportar.texto` (`PLT-06`, CA-ASS-38): "Exportar dados antes" leva à `Admin-Exportar` (auditoria em CSV). Nada promete "todos os seus dados".
- Com cancelamento marcado: 409 `{ "codigo": "transicao_empresa", "mensagem": "A assinatura já está cancelada. Você tem acesso até 21 nov." }` (a tela volta à `Admin-Assinatura`, que mostra o desfazer).

---

## POST /api/assinatura/cancelamento/

Administrador. Corpo:
```json
{ "motivo": "preco_alto", "nome_confirmacao": "Moto Rápida" }
```

- `motivo`: obrigatório, um dos `codigo` de `motivos` (400 `{ "codigo": "validacao", "campos": { "motivo": "Escolha o motivo." } }`). O motivo não muda nada no cancelamento (`PLT-06`); fica na `Empresa` e na auditoria.
- `nome_confirmacao` (`PLT-06`, CA-ASS-31): tem de ser igual a `confirmacao.nome` depois de tirar espaços das pontas, juntar espaços repetidos e ignorar maiúsculas e minúsculas; acentos contam ("Moto Rapida" não confere). Diferente: 422 `{ "codigo": "nome_nao_confere", "mensagem": "O nome digitado não confere com o nome da empresa." }`, e nada muda. O frontend só habilita o botão com o nome igual pela mesma regra, mas quem decide é a API.

200: o corpo de `GET /api/assinatura/` já atualizado (com `cancelamento` preenchido, ou `status: "cancelada"` quando foi na hora; nesse caso, a próxima requisição da empresa já é recusada, e a tela mostra a página de empresa cancelada).

Serviço `plataforma.services.cancelar_assinatura(empresa, motivo, por)`, numa transação, com a `Empresa` travada (`SELECT ... FOR UPDATE`). A conta das datas é uma função pura, `plataforma.calendario.datas_do_cancelamento(hoje, status, teste_fim, fim_do_periodo_pago)`, que devolve `acesso_ate`, `cancelada_em` e `apagar_em`, com teste dos casos dos dados de referência ("Cancelamento da Moto Rápida", (a) a (d)). `fim_do_periodo_pago` é o maior `periodo_fim` das faturas `mensalidade` `paga`, ou nulo; na `em_teste`, ele vence o `teste_fim` quando existe (caso (d)).

### O que acontece em cada estado

**Em teste com a 1ª fatura em aberto** (CA-ASS-30): cancelamento marcado, `acesso_ate` = `teste_fim`. A 1ª fatura vira `cancelada` (motivo `cancelamento_assinatura`), e a cobrança dela no parceiro, se já emitida, é cancelada. O `status` fica `em_teste` até o fim do teste; a empresa opera normalmente. Moto Rápida, cancelando em 10 out: acesso até 21 out, FAT-0001 `cancelada`, `cancelada` em 22 out, aviso em 13 jan 2027, apagamento em 20 jan 2027.

**Em teste com a 1ª fatura já paga** (decisão do dono de 15 out 2026, T-229, opção A; CA-ASS-54): segue a `ativa`, como a mudança de plano no teste com a 1ª paga (`PLT-04`). Cancelamento marcado, `acesso_ate` = fim do período da 1ª fatura (o `periodo_fim` dela), sem estorno. O `status` segue como sem o cancelamento: `em_teste` até `teste_fim` e `ativa` no dia seguinte, pela transição de `assinatura.md` (1ª fatura paga); a empresa opera normalmente até `acesso_ate`. A fatura do período seguinte não é gerada (`gerar_faturas`, abaixo) e, se já tiver sido, vira `cancelada` como na `ativa`. O desfazer vale até `acesso_ate`. Moto Rápida, FAT-0001 (22 out a 21 nov) paga em 12 out, cancelando em 15 out: `em_teste` até 21 out, `ativa` de 22 out a 21 nov, nenhuma fatura em 22 nov, `cancelada` em 22 nov, apagamento em 20 fev 2027; desfazendo em 10 nov, nada nasce, e a fatura de 22 nov é gerada em 17 nov. Teste `test_plt_06_cancelar_no_teste_com_a_1a_paga`.

**Ativa** (CA-ASS-32, CA-ASS-33): cancelamento marcado, `acesso_ate` = **fim do período pago** = o maior `periodo_fim` entre as faturas `mensalidade` `paga` (a véspera do próximo vencimento). Nada mais é gerado (`gerar_faturas`, abaixo). A fatura `mensalidade` do período seguinte, se já foi gerada e não foi paga, vira `cancelada` (motivo `cancelamento_assinatura`) e a cobrança dela no parceiro é cancelada; se já foi paga (boleto pago antes do vencimento), ela conta como período pago e o acesso vai até o fim dela. Faturas `diferenca_plano` em aberto **continuam devidas** (`PLT-06`), com a régua delas, até a empresa virar `cancelada`. Anual: o acesso vai até o fim do ano pago, sem devolução. Exemplos: cancela em 05 nov → acesso até 21 nov, nenhuma fatura em 22 nov, `cancelada` em 22 nov, apagamento em 20 fev 2027; cancela em 19 nov, depois de gerada a fatura de 22 nov em 17 nov → essa fatura vira `cancelada`. Anual de 22 out 2026 a 21 out 2027, cancela em 05 nov 2026 → acesso até 21 out 2027.

**Inadimplente, suspensa ou pausada** (CA-ASS-34): `status` → `cancelada` na hora (`cancelada_em` = agora, `acesso_ate` nulo, `apagar_em` = hoje + 90). As faturas `atrasada` (do período ou da diferença) continuam `atrasada` e devidas; as `mensalidade` ainda `aberta` viram `cancelada` (nada novo é cobrado); a régua (`PLT-02`, `AUT-13`) para para todas. Na `pausada`, a pausa acaba (`pausa_inicio` e `pausada_ate` limpos). Moto Rápida `inadimplente` em 25 out: `cancelada` na hora, FAT-0001 `atrasada`, e nada sai em 29 out (D+7) nem em 06 nov (D+15).

**Com pausa agendada** (`ativa`, antes de `pausa_inicio`): o cancelamento desmarca a pausa e segue a `ativa`. O acesso vai até o mesmo dia (a véspera de `pausa_inicio`).

Em todos os casos: grava `cancelamento_pedido_em` e `motivo_cancelamento`; a forma de pagamento fica como está até a empresa virar `cancelada` (para o desfazer cobrar pela mesma forma); os contratos com clientes finais não mudam (CA-ASS-39: nenhum serviço de `contratos` é chamado). Auditoria `empresa.cancelar` no `public` (categoria cobrança) e na empresa (categoria configurações), com o motivo, `acesso_ate`, `apagar_em` e as faturas canceladas. Testes `test_plt_06_cancelar_no_teste`, `test_plt_06_cancelar_ativa`, `test_plt_06_cancelar_anual_sem_devolucao`, `test_plt_06_cancelar_inadimplente_para_a_regua`, `test_plt_06_nome_nao_confere`.

Erros:
- 409 `transicao_empresa` "A assinatura já está cancelada. Você tem acesso até 21 nov." com cancelamento marcado.
- 422 `nome_nao_confere`, 400 `validacao` (motivo).

## DELETE /api/assinatura/cancelamento/

Administrador. **Desfaz o cancelamento** (`PLT-06`, decisão do dono de 14 out 2026, T-211, opção A; CA-ASS-43 a 45). Sem corpo. Só com cancelamento marcado e hoje ≤ `acesso_ate`.

200: o corpo de `GET /api/assinatura/` (sem `cancelamento`, com `proxima_fatura` de volta).

Serviço `plataforma.services.desfazer_cancelamento(empresa, por)`, numa transação, com a `Empresa` travada:

- Limpa `cancelamento_pedido_em`, `motivo_cancelamento`, `acesso_ate` e o `apagar_em` previsto. `status`, `dia_vencimento`, plano e forma de pagamento não mudam.
- **A fatura nasce de novo.** Cada fatura que este cancelamento cancelou (`motivo_cancelamento = cancelamento_assinatura`, cancelada depois de `cancelamento_pedido_em`, sem `substituida_por`) ganha uma fatura nova: mesmo `tipo`, `plano`, `valor_centavos`, `vencimento`, `periodo_inicio`, `periodo_fim`, `competencia` e descrição, `aberta`, com o próximo código `FAT-`. A cancelada continua `cancelada` e aponta para a nova (`substituida_por`). A restrição de `(empresa, competencia)` vale só para as não canceladas, então as duas convivem.
- **Cobrança pela forma cadastrada, como na emissão** (`PLT-02`): com vencimento em até 5 dias, a cobrança é emitida na hora (boleto com Pix e o e-mail no mesmo dia; cobrança do Pix automático pela autorização; cartão guardado cobrado no dia do vencimento pela tarefa); mais longe, a `gerar_faturas` emite 5 dias antes, como sempre.
- Se o cancelamento não cancelou nada (a fatura do período seguinte ainda não tinha sido gerada), nada nasce: a `gerar_faturas` gera no dia certo (CA-ASS-44, primeiro caso).
- Auditoria `empresa.desfazer_cancelamento` nos dois lugares, com as faturas novas. Testes `test_plt_06_desfazer_cancelamento_no_teste` (CA-ASS-43), `test_plt_06_desfazer_cancelamento_na_ativa` (CA-ASS-44), `test_plt_06_quem_nao_desfaz` (CA-ASS-45).

Exemplos (dados de referência "Desfazer o cancelamento da Moto Rápida"):
- Em teste, cancela em 10 out e desfaz em 15 out: FAT-0001 continua `cancelada`; nasce a FAT-0002 `aberta`, R$ 449,00, vencendo em 22 out, "Plano Profissional · 22 out a 21 nov" (emitida em 17 out pela `gerar_faturas`); `em_teste` até 21 out; nenhum apagamento marcado.
- Ativa, cancela em 05 nov e desfaz em 10 nov: nada nasce; a fatura de 22 nov é gerada em 17 nov.
- Ativa, cancela em 19 nov (FAT-0002 de 22 nov `cancelada`) e desfaz em 20 nov: nasce a FAT-0003 `aberta`, R$ 449,00, vencendo em 22 nov, "Plano Profissional · 22 nov a 21 dez", com o boleto por e-mail em 20 nov.

Erros:
- 409 `{ "codigo": "transicao_empresa", "mensagem": "Não há cancelamento para desfazer." }` sem cancelamento marcado (inclusive na empresa que virou `cancelada` na hora, CA-ASS-45).
- A partir do dia seguinte a `acesso_ate`, a empresa já é `cancelada` e não entra no sistema (abaixo): a rota nem chega a responder. Só a equipe Giro reativa (`reativar_empresa`, `assinatura.md`).

---

## POST /api/assinatura/pausa/

Administrador (`PLT-06`, CA-ASS-35, 37, 42). Corpo: `{ "meses": 2 }`.

- `meses`: 1, 2 ou 3. Outro valor: 400 `{ "codigo": "validacao", "campos": { "meses": "Escolha de 1 a 3 meses." } }` (CA-ASS-35: 4 meses é recusado).
- Só a `ativa`, sem cancelamento nem pausa marcados. Erros 409 `transicao_empresa`:
  - `em_teste`: "A pausa só vale para a assinatura ativa. No teste, você pode cancelar ou mudar de plano."
  - `inadimplente` ou `suspensa`: "Pague a fatura em atraso antes de pausar."
  - Pausa marcada: "Já existe uma pausa marcada até 21 jan."
  - Cancelamento marcado: "Desfaça o cancelamento antes de pausar."

200: o corpo de `GET /api/assinatura/` com `pausa.situacao: "agendada"`.

Serviço `plataforma.services.pausar_assinatura(empresa, meses, por)`, com a `Empresa` travada:

- **A pausa começa no fim do período pago** (decisão do dono de 14 out 2026, T-211, opção A): `pausa_inicio` = fim do período pago + 1 (o próximo vencimento); `pausada_ate` = `pausa_inicio` + `meses` meses − 1 dia, com a regra do mês sem o dia da `PLT-01`. Função pura `plataforma.calendario.periodo_da_pausa(inicio, meses)`, com teste. Moto Rápida, pausando por 2 meses em 05 nov: `ativa` até 21 nov, `pausada` de 22 nov a 21 jan 2027, volta em 22 jan.
- A fatura `mensalidade` do período seguinte, se já foi gerada e não foi paga, vira `cancelada` (motivo `pausa`), com a cobrança cancelada no parceiro (CA-ASS-42: pausando em 19 nov, a FAT-0002 de 22 nov vira `cancelada`). Se já foi paga, a pausa começa no fim do período dela.
- Até `pausa_inicio`, a empresa segue `ativa`, com tudo funcionando. A `gerar_faturas` não gera fatura para período que começa dentro da pausa.
- Auditoria `empresa.pausar` nos dois lugares, com `meses`, `pausa_inicio`, `pausada_ate` e a fatura cancelada. Testes `test_plt_06_pausar_por_ate_3_meses`, `test_plt_06_pausa_comeca_no_fim_do_periodo_pago` (CA-ASS-42), `test_plt_06_quem_nao_pausa` (CA-ASS-37).

## DELETE /api/assinatura/pausa/

Administrador. **Voltar da pausa** (`PLT-06`, CA-ASS-36). Sem corpo. Entra na lista de exceções do `somente_leitura`, para a `pausada`.

**Em andamento** (`pausada`): serviço `plataforma.services.voltar_da_pausa(empresa, por)`:
- `status` → `ativa` na hora; limpa `pausa_inicio` e `pausada_ate`.
- Fatura nova `mensalidade`, `aberta`, com o `preco_contratado_centavos`, vencendo **hoje**, período de hoje até a véspera do mesmo dia no mês (ou ano) seguinte; `dia_vencimento` passa ao dia de hoje (`PLT-01`, `PLT-06`). A cobrança é emitida na hora pela forma cadastrada (boleto com Pix e e-mail; cobrança do Pix automático; cartão guardado cobrado na hora). A régua conta o D0 hoje.
- Com downgrade agendado (`plano_proximo`), a fatura da volta é a "próxima fatura" do downgrade: passa pela conferência de `assinatura.md` ("Downgrade agendado: conferência e virada") e, cabendo, sai pelo plano menor, que vale já na volta.
- Moto Rápida, de volta em 10 dez: `ativa`, fatura de R$ 449,00 vencendo em 10 dez ("Plano Profissional · 10 dez a 09 jan"), e as seguintes todo dia 10.
- Auditoria `empresa.voltar_pausa` nos dois lugares. Teste `test_plt_06_volta_manual_da_pausa`.

**Agendada** (`ativa`, hoje < `pausa_inicio`): **desiste da pausa** (`PLT-06`, decisão do dono de 15 out 2026, T-229, opção A; CA-ASS-55), pelo botão "Desistir da pausa" (`acoes.desistir_pausa`), até o último dia do período pago (a véspera de `pausa_inicio`). Serviço `plataforma.services.desistir_da_pausa(empresa, por)`, com a `Empresa` travada: limpa `pausa_inicio` e `pausada_ate`, e a fatura que a pausa cancelou (motivo `pausa`, sem `substituida_por`) nasce de novo como no desfazer do cancelamento: mesmo valor, vencimento e período, `aberta`, próximo código `FAT-`, a cancelada aponta para ela (`substituida_por`), e a cobrança sai pela forma cadastrada como na emissão (`PLT-02`). Se a pausa não cancelou nada (a fatura ainda não tinha sido gerada), nada nasce, e a `gerar_faturas` gera no dia certo. `status`, plano, `plano_proximo` e `dia_vencimento` não mudam. Moto Rápida, pausa pedida em 19 nov (FAT-0002 de 22 nov `cancelada`) e desistida em 20 nov: nasce a FAT-0003 `aberta`, R$ 449,00, vencendo em 22 nov, "Plano Profissional · 22 nov a 21 dez", com o boleto por e-mail em 20 nov; a empresa segue `ativa`. A partir de `pausa_inicio` a empresa já é `pausada`, e a mesma rota é a volta (acima). Auditoria `empresa.desistir_pausa` nos dois lugares, com a fatura nova. Teste `test_plt_06_desistir_da_pausa_agendada` (inclui o 403 do Rodrigo e do suporte).

Sem pausa marcada: 409 `{ "codigo": "transicao_empresa", "mensagem": "Não há pausa para encerrar." }`.

---

## Mudanças enquanto há cancelamento ou pausa

Decisões do dono de 15 out 2026 (T-229, opção A; `PLT-06`, `PLT-04`):

- **Cancelamento marcado** (CA-ASS-56): mudar de plano (e desfazer o downgrade) é recusado com 409 `{ "codigo": "transicao_empresa", "mensagem": "Desfaça o cancelamento antes de mudar de plano." }`, e pausar, como acima. Forma de pagamento, pagar fatura e dados fiscais continuam (a diferença do upgrade em aberto continua devida e pode ser paga). `plano_proximo` fica como estava: enquanto o cancelamento está marcado, a fatura do período seguinte não é gerada, então o downgrade não vira; se o cancelamento for desfeito, ele segue a conferência e a virada de `assinatura.md` na fatura seguinte. Empresa do CA-ASS-16, no Completo com o Profissional agendado para 22 nov, cancela em 05 nov e desfaz em 10 nov: a fatura de 22 nov é gerada em 17 nov e, cabendo, sai pelo Profissional. Teste `test_plt_06_mudar_de_plano_com_cancelamento_marcado`.
- **Pausa agendada:** mudar de plano segue `assinatura.md` (é a `ativa`); o downgrade vale na fatura da volta.
- **Pausa em andamento:** a `pausada` é `somente_leitura`; fora as exceções, nada se escreve.
- **Fatura de diferença em aberto ao começar a pausa** (CA-ASS-57): continua devida, com a régua dela (`AUT-13` roda para a `pausada`); a empresa fica `pausada` e não vira `inadimplente` nem `suspensa` durante a pausa (as transições de `assinatura.md` pulam a `pausada`). Se ela ainda estiver `atrasada` na volta (manual ou automática), `voltar_da_pausa` põe a empresa em `inadimplente` em vez de `ativa` (D+1 já passou), e a contagem do D+15 segue o vencimento dela: a `virar_estados` a leva a `suspensa` quando hoje ≥ vencimento + 15, como em `assinatura.md`. A fatura da volta nasce do mesmo jeito. Moto Rápida, pausa a partir de 22 nov e diferença vencendo em 23 nov: régua em 23 nov (D0) e 26 nov (D+3), `pausada` em 24 nov; volta em 01 dez sem pagar → `inadimplente`, e `suspensa` em 08 dez se não pagar. Teste `test_plt_06_diferenca_em_aberto_na_pausa`.

---

## Tarefas e estados (sem rota; para o backend)

### `plataforma.virar_estados` (00:05)

Antes das transições de `assinatura.md` (o cancelamento vem primeiro, para a `em_teste` cancelada não ir a `suspensa`):

| De | Quando | Para | Serviço |
| --- | --- | --- | --- |
| `em_teste`, `ativa`, `inadimplente`, `suspensa` com cancelamento marcado | hoje > `acesso_ate` | `cancelada` | `virar_cancelada` |
| `ativa` (ou `inadimplente` pela diferença) com pausa agendada | hoje = `pausa_inicio` | `pausada` | `iniciar_pausa` |
| `pausada` | hoje > `pausada_ate` | `ativa`, com a fatura nova vencendo hoje | `voltar_da_pausa(empresa, por=sistema)` |

`virar_cancelada(empresa)`: `status` → `cancelada`, `cancelada_em` = agora, `apagar_em` = hoje + 90 dias (`AUD-08`: Moto Rápida em teste, `cancelada` em 22 out → apagamento em 20 jan 2027; ativa, em 22 nov → 20 fev 2027). Na mesma rotina, depois do commit: a autorização do Pix automático é cancelada no parceiro (`cancelar_autorizacao`), o token do cartão é esquecido e `forma` fica nula (ADR 0023: o Giro não guarda meio de pagamento de quem saiu); as cobranças `aberta` que ainda existirem são canceladas no parceiro. A régua para. Auditoria `empresa.virar_cancelada` (ator `sistema`, regra `PLT-06`) nos dois lugares. Testes com o relógio de referência (ADR 0021): `test_plt_06_cancelada_no_dia_seguinte_ao_acesso`, `test_plt_06_pausa_e_volta_automatica` (CA-ASS-35).

As três transições são idempotentes (ADR 0012): rodando duas vezes no mesmo dia, nada muda na segunda.

### `plataforma.gerar_faturas` (06:00)

Não gera fatura para: empresa `pausada` ou `cancelada`; empresa com cancelamento marcado quando o período da fatura começa depois de `acesso_ate`; empresa com pausa agendada quando o período começa em `pausa_inicio` ou depois. A emissão no parceiro emite também as faturas `aberta` sem cobrança com vencimento em até 5 dias, como as que nasceram do desfazer.

### Régua (`AUT-13`)

Para por inteiro na empresa `cancelada` (`PLT-06`), inclusive para as faturas `atrasada`, que continuam devidas. Com cancelamento marcado, segue para as faturas que continuam devidas (diferença do upgrade) até a virada. Fatura `cancelada` não tem régua.

### Empresa `cancelada`

- Não entra no sistema (`AUD-08`). O middleware de empresa, que já resolve o tenant pelo host, responde a **todo** pedido de uma `cancelada` (inclusive `entrar` e `renovar`) com 403 `{ "codigo": "empresa_cancelada", "mensagem": "Esta assinatura foi cancelada. Para pedir seus dados ou voltar, fale com a equipe Giro." }`, e os tokens ainda válidos param na hora. O frontend mostra uma página só com essa mensagem e o contato da equipe (sem marca da locadora; a marca vem da API que já recusou). Teste `test_aud_08_cancelada_nao_entra`.
- `para_cada_empresa` (ADR 0012) já não inclui a `cancelada`: nenhuma automação da empresa roda.
- Nos 90 dias, os dados são pedidos à equipe Giro (`AUD-08`), que exporta pelo Django Admin ou à mão, como no pedido do titular. A reativação segue `assinatura.md` ("Mudança de ciclo e reativação pela equipe"): como `forma` ficou nula, a fatura nova da reativação nasce sem forma, e o administrador escolhe a forma ao entrar (`PLT-13`).

### Aviso e apagamento (`AUD-08`, ADR 0025)

- **Aviso, 7 dias antes:** tarefa diária `plataforma.aud_08_avisar_apagamento` (09:00, no `public`): empresas `cancelada`, `apagada_em` nulo, `aviso_apagamento_enviado_em` nulo e `apagar_em` − 7 ≤ hoje. Manda e-mail aos administradores ativos da empresa (lidos no schema dela) com a data: "Os dados da Moto Rápida serão apagados em 20 jan 2027. Para pedir uma cópia ou reativar a assinatura, fale com a equipe Giro." Grava `aviso_apagamento_enviado_em` (uma vez só). Moto Rápida em teste: aviso em 13 jan 2027. Auditoria `empresa.avisar_apagamento` no `public`. Teste `test_aud_08_aviso_7_dias_antes`.
- **Apagamento no 90º dia:** tarefa diária `plataforma.aud_08_apagar_empresas` (03:30, no `public`): empresas `cancelada` com `apagar_em` ≤ hoje e `apagada_em` nulo, uma por vez, cada uma pelo serviço `plataforma.services.apagar_empresa(empresa_id)` (ADR 0025): trava a `Empresa`, confere de novo `status = cancelada` e `apagar_em` ≤ hoje, apaga os arquivos do prefixo `<schema>/` no storage, apaga o schema da empresa pela conexão de migração (ADR 0016), e limpa o `public` (abaixo). Cada passo pode rodar de novo; `apagada_em` só é gravado no fim. Falhou no meio: tenta de novo no dia seguinte e avisa o Sentry. Auditoria `empresa.apagar` no `public` (categoria segurança, ator `sistema`, regra `AUD-08`), com o schema, a quantidade de arquivos e a data. Testes `test_aud_08_apaga_no_90_dia`, `test_aud_08_nao_apaga_outra_empresa`, `test_aud_08_nao_apaga_reativada`.
- **O que fica no `public`** (`AUD-08`, decisão do dono de 15 out 2026, T-229, opção A; CA-ASS-58, teste `test_aud_08_o_que_fica_no_public`): a linha da `Empresa`, com `status` `cancelada` e `apagada_em`, sem os dados de contato (`responsavel_nome`, `responsavel_email`, `responsavel_telefone`, `email_cobranca` limpos), mas com razão social, CNPJ e endereço, que estão nas faturas e nas notas do Giro; as `FaturaAssinatura` (registro de cobrança e nota fiscal do próprio Giro); a auditoria da plataforma (`AUD-02`, 5 anos). Saem: `Dominio`, `UsoEmpresa`, `ContaPagamento` (a chave cifrada da subconta; a subconta no parceiro é da locadora e não é fechada pelo Giro) e `FormaPagamentoAssinatura`. O `subdominio` e o `schema_name` ficam reservados (o endereço antigo não passa a outra locadora). As faturas ficam sem data para sair até o dono e o contador decidirem o prazo de guarda ("Pontos em aberto" das regras); nenhuma tarefa apaga faturas. Se a T-230 (segurança) mudar o que fica para o MEI e o empresário individual, a limpeza da linha muda aqui.
- A tarefa que apaga tem de existir antes do 90º dia do primeiro cancelamento real (`AUD-08`): a T-195 entrega as duas tarefas junto com o cancelamento.

---

## Erros deste contrato

| HTTP | `codigo` | Quando |
| --- | --- | --- |
| 400 | `validacao` | motivo ausente ou fora da lista; `meses` fora de 1 a 3 |
| 403 | `permissao` | perfil que não é administrador |
| 403 | `PLT-07` | escrita com token de suporte |
| 403 | `empresa_sem_operacao` | escrita fora das exceções na `suspensa` e na `pausada` |
| 403 | `empresa_cancelada` | qualquer pedido de uma empresa `cancelada` |
| 409 | `transicao_empresa` | cancelar já cancelada; desfazer sem cancelamento; pausar fora da `ativa` ou com pausa ou cancelamento marcados; voltar ou desistir sem pausa; mudar de plano com cancelamento marcado |
| 422 | `nome_nao_confere` | nome digitado diferente do nome da empresa |
| 503 | `parceiro_indisponivel` | o parceiro não respondeu ao cancelar ou emitir uma cobrança (nada é gravado) |

---

## O que muda para as tarefas abertas

- **T-195 (backend, cancelar, pausar e apagamento):** tudo deste contrato. Modelo: `Empresa.cancelamento_pedido_em`, `motivo_cancelamento` enum, `pausa_inicio`, `aviso_apagamento_enviado_em`, `apagada_em`; `FaturaAssinatura.motivo_cancelamento`, `cancelada_em`, `substituida_por` (`modelo-de-dados.md`). Exceções do `somente_leitura`, `empresa_cancelada` no middleware, as transições em `virar_estados`, os filtros da `gerar_faturas`, as duas tarefas do `AUD-08` e o `apagar_empresa` da ADR 0025. Testes `test_plt_06_*` e `test_aud_08_*` acima, CA-ASS-30 a 39, 42 a 45 e 54 a 58. Da T-231: `desistir_da_pausa`, o caso (d) em `datas_do_cancelamento`, a volta da pausa em `inadimplente` com a diferença atrasada, e o que fica no `public`.
- **T-184, T-185 e T-186 (faturas, rotas, régua):** `acoes.cancelar` deixa de ser `false` fixo; `proxima_fatura` `null` com cancelamento ou pausa marcados; a `gerar_faturas` pula os períodos de depois do acesso e da pausa e emite as faturas `aberta` sem cobrança; a régua para na `cancelada`. Se a T-195 vier depois, os campos novos entram na migração dela.
- **T-198 (frontend):** `Admin-Cancelar` lê `GET cancelamento/` (motivos, alternativas, `o_que_acontece`, nome) e manda `POST`; a `Admin-Assinatura` mostra `cancelamento.rotulo` com "Desfazer cancelamento" (`acoes.desfazer_cancelamento`), a `pausa` com "Voltar da pausa" (`acoes.voltar_pausa`, só na `pausada`) ou "Desistir da pausa" (`acoes.desistir_pausa`, pausa agendada), as duas pela mesma rota, e a página da `empresa_cancelada`. CA-ASS-30, 31, 35 a 38, 43 a 45, 54 a 56.
- **T-199 (segurança):** 2 etapas recentes para cancelar; ADR 0025 (conexão de migração na tarefa, conferência do schema antes de apagar, nada de outra empresa); o prazo dos backups do banco e do storage depois do 90º dia (com o devops).
- **T-214 e T-200 (design-system):** os textos provisórios de `pausa.rotulo` e da faixa da `pausada`; a página da empresa cancelada.
- **Qa (T-204, T-215):** CA-ASS-30 a 39, 42 a 45 e 54 a 58 com o relógio de referência e os dados de referência "Cancelamento" (com o caso (d)), "Pausa" (com a desistência) e "Desfazer o cancelamento da Moto Rápida".
- **Devops:** o worker do Celery que roda `aud_08_apagar_empresas` precisa da `DATABASE_URL_MIGRACAO` (ADR 0016, 0025).
