# T-385 · ADR e contrato da integração real do WhatsApp · arquiteto → orquestrador, dono, produto, backend

**O que foi feito:** ADR 0034, `docs/decisoes/0034-whatsapp-real.md`, **proposta**.
- **Inventário:** o código manda WhatsApp em 8 pontos da fase 1. São eles o convite, o contrato para assinar, o contrato assinado, a régua de cobrança, o recibo do pagamento, o recibo da devolução e a régua da assinatura (D0 e D+3). O lembrete de devolução (`AUT-01`, T-367) será o 9º. Todos usam hoje o provedor falso.

| Opção | Piloto (R$/mês) | 20 empresas (R$/mês) | White label |
| --- | --- | --- | --- |
| A · Meta direta, um número do Giro | cerca de 75 | cerca de 500 | remetente "Giro Avisos", marca da locadora no texto; a resposta chega ao Giro |
| B · Meta direta, um número por locadora (Tech Provider) | mesmo preço por mensagem, na WABA de cada locadora | idem | completo; cadastro e aprovação de modelos por empresa |
| C · Parceiro oficial (360dialog, Twilio, Zenvia, Blip) | cerca de 375 a 400 | cerca de 800 a 850 | como na A ou na B, conforme o número |

Os custos são estimativas de outubro de 2026: utilidade a cerca de US$ 0,007 por mensagem entregue no Brasil, e cerca de 600 mensagens por empresa por mês. Conferir na tabela da Meta.

**Recomendação:** A agora, com a interface pronta para a B na fase 2. A C só se o dono não quiser operar o cadastro na Meta.

**A ADR também traz:**
- os 13 modelos de utilidade da fase 1;
- o opt-in (campo `aceita_whatsapp`, saída por "SAIR");
- a queda para o e-mail;
- o webhook `GET`/`POST /api/webhooks/whatsapp/`, com `X-Hub-Signature-256` e roteamento pelo `wamid` numa tabela do `public` sem conteúdo;
- a lista do que o dono contrata;
- o esboço do provedor (`Aviso`, `avisar`, `MetaCloud` com `urllib`, sem dependência nova; `prod.py` recusa o falso);
- 5 tarefas de backend.

**`[decisão]` para o produto, antes de aceitar:**
1. **Textos dos modelos.** A Meta recusa modelo que começa ou termina com variável, e hoje os textos começam com "{marca}:" e às vezes terminam com o código Pix. A proposta é "Olá, {nome}. Aqui é a {marca}. ... Obrigado." e tirar "fale com a gente por aqui", que levaria a resposta ao Giro na A.
2. **Opt-in.** Uma caixa no Novo cliente e no detalhe ("Aceita receber avisos da {marca} pelo WhatsApp"), com o padrão desmarcado na importação. O convite por WhatsApp só sai com o aceite marcado pelo administrador. Muda `CLI` e `USR-01`.
3. **Queda para o e-mail** dos recibos e do lembrete de devolução, hoje só WhatsApp. O padrão proposto é cair para o e-mail.
4. **Remetente** "Giro Avisos" na A, como meio-termo do white label.

**O dono escolhe a opção** e contrata: Meta Business verificado, número dedicado, nome de exibição e cartão na WABA; na C, o contrato com o parceiro.

**Onde:** `docs/decisoes/0034-whatsapp-real.md`, `docs/decisoes/README.md` e `tarefas/feito.md`. Nenhum contrato de `docs/api` mudou: a ADR é proposta, e o webhook entra em `financeiro.md` ou `plataforma.md` quando ela for aceita.
**Regras cobertas:** `USR-01`, `AUT-01`, `AUT-03`, `AUT-05`, `AUT-13`, `PLT-02`, `DEV-02` (nenhuma muda aqui).
**O que ficou de fora:** não criei conta na Meta nem em parceiro. Os preços não foram cotados no site.
**Próximo passo para quem recebe:**
- o dono escolhe a opção, e o produto responde às 4 decisões;
- o arquiteto passa a ADR para aceita e escreve o webhook no contrato;
- saem as 5 tarefas de backend da ADR.

Branch `t-385-whatsapp`, sem PR.
