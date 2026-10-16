# T-186 (parte 3) · Régua da assinatura · backend → orquestrador, qa (T-204, T-215), arquiteto, produto, segurança

Última das 3 partes da T-186 (branch `t-186c-regua-mensagens`, sobre a `t-186b-faturas-cobranca`, com a main do PR #302 mesclada).

**O que foi feito:**

- **Tarefa `aut_13_regua_assinatura`** (Beat, 09:00, `services.regua_da_assinatura`), pela `PLT-02`, só no dia exato de cada marco (como a `AUT-03`) e idempotente no mesmo dia:
  - **D-3:** lembrete por e-mail com o caminho de pagar da fatura: boleto (link e linha digitável), página do parceiro para o cartão ainda não digitado (CA-ASS-11), "a cobrança é automática no cartão Visa final 4242" (cartão guardado) ou "pelo Pix automático"; sem forma, "Escolha a forma de pagamento em Assinatura".
  - **D0 e D+3:** e-mail e WhatsApp para o `responsavel_telefone`. O D+3 diz o dia da suspensão (D+15).
  - **D+7:** aviso de suspensão por e-mail, sem WhatsApp, e a **tarefa de ligação** para a equipe Giro.
  - Cartão recusado: o texto segue o da tela ("O cartão foi recusado. Tentamos de novo amanhã." e, depois da 2ª, pagar por Pix ou boleto pelo "Pagar"); a régua continua (CA-ASS-12).
- E-mails para o `email_cobranca` e os administradores ativos, sem repetir (`destinatarios_da_cobranca`), com a marca Giro, sem exclamação. Todos terminam com "Se você já pagou, desconsidere esta mensagem.".
- Para na fatura paga ou cancelada e na empresa `cancelada` (`PLT-06`, CA-ASS-03). A pausada segue para a fatura de diferença (T-231), porque não tem mensalidade.
- Auditoria no public: `fatura_assinatura.regua` (ator `sistema`, regra `AUT-13`, `depois.marco`), que também é a marca de que o marco já saiu; `fatura_assinatura.pedir_ligacao` (regra `PLT-02`).

**Onde:** `backend/apps/plataforma/{services,tasks}.py`, `README.md` do app, `backend/config/settings/base.py` (Beat). Testes: `backend/tests/aceitacao/test_t186c_regua_assinatura.py` (7).
**Contrato:** nenhuma rota nova; OpenAPI sem mudança.
**Regras cobertas:** AUT-13 e PLT-02 (`test_aut_13_ca_ass_10_lembrete_d3_por_email`, `test_aut_13_ca_ass_11_d3_com_o_link_da_pagina_do_cartao`, `test_aut_13_d0_d3_d7_com_whatsapp_e_ligacao`, `test_aut_13_ca_ass_03_paga_nao_recebe_mais_nada`, `test_aut_13_ca_ass_12_cartao_recusado_a_regua_segue`, `test_aut_13_cancelada_a_regua_para`). Isolamento: `test_aut_13_regua_isolada_por_empresa`.
**Testes rodados:** ruff, ruff format e mypy em `apps/plataforma`, `tests/aceitacao` e `config`; `test_t186c_regua_assinatura`, `test_t186b_faturas_cobranca`, `test_t186_estados` e `test_t185b_forma_faturas` depois do merge da main: 55 passaram. Suíte toda não rodada (pouca memória).

**Pontos em aberto:**

- **Tarefa de ligação (arquiteto):** o contrato pede "tarefa de ligação para a equipe" e deixa a tela para a fase 2, sem modelo. Hoje é um e-mail ao Dono e ao Financeiro da plataforma (`PLT-09`), com o nome e o telefone do responsável, mais o evento `fatura_assinatura.pedir_ligacao`. Se a fase 2 pedir uma fila (tabela), o ponto de troca é `_pedir_ligacao`.
- **Textos (produto):** as mensagens não têm modelo nas regras nem nas telas; escrevi seguindo o `CLAUDE.md`. Vale uma leitura do produto, principalmente o D+7 ("A equipe Giro vai ligar para ajudar.").
- **Marco perdido:** se a tarefa não rodar no dia do marco, ele não sai depois (como na `AUT-03`).
- **T-296** (decidida pelo dono, opção B: Pix automático sem autorização faz sair o boleto com Pix): fora desta parte, como pediu o orquestrador; quando entrar, o D-3 já mostra o boleto, porque o texto segue a cobrança viva.
- **WhatsApp:** sai pelo provedor falso até a integração de WhatsApp existir.

**Próximo passo para quem recebe:**

- **QA (T-204, T-215):** CA-ASS-03, 10, 11 e 12 (datas da régua) com o relógio de referência.
- **Segurança:** o e-mail da ligação vai só para a equipe da plataforma e leva o telefone do responsável; nenhum CPF nem token sai na régua.
- **Orquestrador:** com esta parte, a T-186 fica completa.
