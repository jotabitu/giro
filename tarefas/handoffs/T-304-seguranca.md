# T-304 · Destinatários do e-mail da régua da assinatura · segurança → orquestrador, backend

**O que foi feito:** revisão do PR #304 (T-186 parte 3) quanto aos destinatários dos e-mails da régua, ao e-mail da ligação e a CPF e tokens nas mensagens. Relatório: `docs/seguranca/2026-10-16-t304-destinatarios-regua.md`.
**Onde:** só documentação; nenhum código mudou (o código revisado está no PR #304, ainda fora da `main`).
**Regras cobertas:** AUT-13, PLT-02, PLT-09, PLT-15, LGPD (necessidade).

**Resposta à pergunta da tarefa:** sim, cada destinatário deve receber o seu e-mail. Hoje o `email_cobranca` (às vezes de fora, como o contador) e os administradores vão juntos no "Para", e um vê o endereço do outro (M-01, média). O resto está conforme: a ligação vai só para Dono e Financeiro da plataforma, o telefone do responsável fica fora da auditoria, e nenhum CPF nem token sai na régua.

**Achados:** M-01 (média), M-02 (média, disponibilidade), B-01 (baixa, sem tarefa própria).

**Tarefa de backend para numerar** (pode ir junto da T-303, que mexe nas mesmas funções):

```
### T-??? · Um e-mail por destinatário e a régua que não para no primeiro erro
- **Agente:** backend · **Depende de:** T-186 parte 3 (PR #304) · **Regras:** AUT-13, PLT-02, PLT-15, LGPD · **Severidade:** média · **Origem:** T-304 (segurança), M-01 e M-02 de `docs/seguranca/2026-10-16-t304-destinatarios-regua.md`
- **Pronto quando:**
  - `enviar_a_cada_um(destinatarios, assunto, texto)` em `apps/plataforma` monta um `EmailMessage` por endereço, só ele no "Para" (sem Bcc), e envia numa conexão (`get_connection().send_messages`); usada em `avisar_pela_regua`, `plataforma_enviar_boleto` e `plataforma_avisar_downgrade_recusado`. Teste `test_aut_13_cada_destinatario_recebe_o_seu`: no D-3 da Moto Rápida saem 2 mensagens, `to == [COBRANCA]` e `to == [MARIANA]`, mesmo assunto e texto; o mesmo para o boleto (`test_plt_02_boleto_um_por_destinatario`). Ajustar `test_aut_13_ca_ass_10_lembrete_d3_por_email`, que hoje confere `to == [COBRANCA, MARIANA]`.
  - `regua_da_assinatura` isola cada fatura, como o `_cada_uma` da geração: uma falha vai para o log, sem o corpo da mensagem, e as outras faturas do dia seguem. Teste `test_aut_13_falha_numa_fatura_nao_para_as_outras` (o envio da 1ª levanta exceção; a 2ª recebe o aviso e ganha o evento).
  - E-mail e WhatsApp saem depois do commit do evento (`transaction.on_commit` ou uma tarefa por fatura), não dentro da transação com a fatura travada; o e-mail que já saiu não sai de novo se o WhatsApp falhar.
  - `nome_exibicao` recusa quebra de linha e caractere de controle no cadastro, na compra e na edição (400 com "Use um nome sem quebra de linha."); teste com `"Moto\nRápida"`.
```

**O que ficou de fora:** testes com `xfail` nesta branch, porque o código revisado não está na `main`. Os avisos só para administradores (B-01: limite de 90%, entrada do suporte, bloqueio) podem usar a mesma função quando forem tocados.
**Próximo passo para quem recebe:**
- **Orquestrador:** numerar a tarefa acima e decidir se vai junto da T-303.
- **Backend:** ao fazer a T-303, já escrever os textos chamando `enviar_a_cada_um`.
