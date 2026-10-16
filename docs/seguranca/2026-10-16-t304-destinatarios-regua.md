# T-304 · Destinatários do e-mail da régua da assinatura

**Data:** 16 out 2026 · **Agente:** segurança · **Regras:** AUT-13, PLT-02, PLT-09, PLT-15, LGPD (art. 6º, III, necessidade)
**Base:** branch `t-186c-regua-mensagens` (PR #304): `apps/plataforma/services.py` (`destinatarios_da_cobranca`, `_como_pagar`, `mensagem_da_regua`, `_pedir_ligacao`, `avisar_pela_regua`, `regua_da_assinatura`), `apps/plataforma/tasks.py` (`plataforma_enviar_boleto`, `plataforma_avisar_downgrade_recusado`, `aut_13_regua_assinatura`), `tests/aceitacao/test_t186c_regua_assinatura.py`; handoff `tarefas/handoffs/T-186c-backend.md`.
**Método:** leitura do código e dos testes do PR #304. O código ainda não está na `main`, então os testes pedidos vão como tarefa de backend (handoff `tarefas/handoffs/T-304-seguranca.md`), não como `xfail` nesta branch.

## Resumo

Os três pontos do handoff da T-186c estão certos: a ligação vai só para a equipe da plataforma, o telefone do responsável fica fora do evento de auditoria, e nenhum CPF nem token sai na régua. Há um achado médio (M-01, os destinatários juntos no "Para") e um médio de disponibilidade (M-02, uma falha de envio cala a régua do dia para todas as empresas). Um baixo (B-01) sobre os avisos internos que já vão juntos.

| Ponto | Situação | Onde está |
| --- | --- | --- |
| Destinatários juntos | **um `send_mail` só**, com o `email_cobranca` e os administradores no "Para" | M-01 |
| Cada um recebe o seu | **sim**, para os e-mails que levam o `email_cobranca` | M-01 |
| Ligação só para a equipe | `_pedir_ligacao` roda dentro do `schema_context(public)` de `avisar_pela_regua` e filtra `funcao_plataforma__in=("dono", "financeiro")`, `status="ativo"`. No `public` só há usuários da plataforma (a restrição de `contas.Usuario` exige `perfil=""` com `funcao_plataforma` preenchida), então nenhum usuário de empresa recebe | conforme |
| Telefone do responsável | vai no corpo do e-mail interno, que é a finalidade (a equipe liga, `PLT-02`, `PLT-09`). O evento `fatura_assinatura.pedir_ligacao` guarda só `{"empresa": pk}` | conforme |
| CPF na régua | nenhum: os textos usam código, nome de exibição, valor, datas, forma de pagar e, na ligação, nome e telefone do responsável | conforme |
| Token na régua | nenhum token de acesso, sessão, convite ou API. Saem o link do boleto, a linha digitável, o Pix copia e cola e a página do parceiro para o cartão: são o meio de pagar, para quem paga, e já saíam assim no e-mail do boleto (T-186b) | conforme, com nota abaixo |
| Cartão | só bandeira e final ("Visa final 4242"), o que o PCI DSS permite exibir | conforme |
| Auditoria | `fatura_assinatura.regua` com `marco` e `whatsapp: bool`, sem telefone nem e-mail | conforme |

**Nota sobre a página do cartão (`cobranca_url_pagina`):** é um link de pagamento do parceiro que vale para quem o tiver. Vai para o `email_cobranca`, que a própria empresa escolheu como destino da cobrança (`PLT-15`), e para os administradores. Não é um acesso ao Giro: quem abre só paga a fatura e cadastra o cartão no parceiro. Não peço mudança. Com M-01 corrigido, ele deixa de ir para mais de uma caixa na mesma mensagem, o que reduz o encaminhamento por "responder a todos".

## Achados

### M-01 · O e-mail de cobrança e os administradores recebem a mesma mensagem, todos no "Para" · média

**Onde:** `avisar_pela_regua` (`send_mail(..., recipient_list=destinatarios)`), e o mesmo padrão já na `main` em `plataforma_enviar_boleto` e `plataforma_avisar_downgrade_recusado` (`tasks.py`). Os três usam `destinatarios_da_cobranca`.
**Problema:** o `email_cobranca` muitas vezes é de fora da empresa (o contador, um escritório de cobrança, o financeiro de outra empresa do grupo). Com todos no "Para", esse terceiro recebe o e-mail de cada administrador ativo da locadora, e cada administrador recebe o do terceiro. O e-mail do administrador é dado pessoal (em geral nominal, `mariana@motorapida.com.br`), e entregá-lo a um terceiro não é necessário para a cobrança: viola a necessidade (LGPD, art. 6º, III) sem base que a justifique. O teste do PR confirma o formato: `lembrete.to == [COBRANCA, MARIANA]`. Dois efeitos a mais:
- "responder a todos" do contador espalha o assunto da cobrança (e o link de pagar) entre pessoas que a empresa não escolheu juntar;
- um endereço recusado pelo servidor de destino pode fazer a mensagem inteira voltar como erro, conforme o provedor de envio, e os outros deixam de receber.

**Cada destinatário deve receber o seu?** Sim. Uma mensagem por destinatário, com só ele no "Para", mesmo texto. Cópia oculta (Bcc) não serve como saída: o "Para" fica vazio ou "undisclosed-recipients", o que piora a entrega (filtros de spam), e a lista continua passando junta pelo provedor numa transação só.
**Sugestão (tarefa no handoff):** uma função `enviar_a_cada_um(destinatarios, assunto, texto)` em `apps/plataforma`, que monte um `EmailMessage` por endereço e envie todos numa conexão (`get_connection().send_messages(...)`), usada pela régua, pelo boleto e pelo downgrade recusado. Devolve quantos saíram. O teste vira `len(mailoutbox) == 2` e `to == [COBRANCA]`, `to == [MARIANA]`.
**Reprodução:** `test_aut_13_ca_ass_10_lembrete_d3_por_email` no PR #304: a mensagem única tem `to == [COBRANCA, MARIANA]`.

### M-02 · Uma falha de envio para a régua do dia para todas as empresas · média (disponibilidade)

**Onde:** `regua_da_assinatura` chama `avisar_pela_regua` em sequência, sem proteção; `avisar_pela_regua` envia o e-mail e o WhatsApp dentro do `transaction.atomic()` com a fatura travada.
**Problema:** qualquer exceção numa fatura (servidor SMTP fora do ar, endereço inválido recusado na hora, o provedor de WhatsApp) desfaz o evento dessa fatura e interrompe o laço: as faturas seguintes do mesmo dia não recebem nada. Como a régua só manda no dia exato do marco, o aviso de todas se perde, inclusive o D+7 e a ligação. Um exemplo concreto: o `nome_exibicao` aceita quebra de linha no meio (o `CharField` do DRF só apara as pontas), e o Django recusa assunto com quebra de linha (`BadHeaderError`). Não há injeção de cabeçalho, o Django barra; mas uma empresa com esse nome derruba a régua de todas as outras naquele dia. Outra: o e-mail sai, o WhatsApp falha, a transação desfaz o evento e a fatura fica como "não avisada"; uma nova execução no mesmo dia manda o e-mail de novo.
**Sugestão (tarefa no handoff):**
- no laço, cada fatura isolada, como o `_cada_uma` da geração: a falha vai para o log (sem o corpo da mensagem) e as outras seguem;
- gravar o evento e enviar depois do commit (`transaction.on_commit`, ou uma tarefa por fatura na fila, como o e-mail do boleto), para não segurar a trava da fatura durante o SMTP e não reenviar o que já saiu;
- `nome_exibicao` sem quebra de linha nem caractere de controle na validação (cadastro, compra e edição), com o teste de um nome com `\n` recusado.
Se a decisão do marco perdido (`[decisão]` da T-299, opção B) entrar na T-303, o D+7 que falhar sai na execução seguinte; mesmo assim, o laço não deve parar no primeiro erro.

### B-01 · Avisos só para administradores também vão juntos · baixa

**Onde:** `plataforma_avisar_limite_90`, `plataforma_avisar_entrada_do_suporte` (`apps/plataforma/tasks.py`) e `contas_avisar_bloqueio` (`apps/contas/tasks.py`).
**Problema:** todos os administradores no "Para" da mesma mensagem. São pessoas da mesma empresa, que já se veem na tela de Usuários, então não há terceiro recebendo dado que não teria. Fica como baixa só pela consistência e pela entrega (um endereço recusado não derruba os outros).
**Sugestão:** usar a mesma `enviar_a_cada_um` de M-01 quando alguém mexer nessas tarefas. Não precisa de tarefa própria.

## O que não muda

- O WhatsApp vai só para o `responsavel_telefone` (`PLT-02`), sem o caminho de pagar nem link: certo.
- A régua roda no `public` e lê os administradores no schema de cada empresa (`destinatarios_da_cobranca`), sem cruzar empresas: o PR tem `test_aut_13_regua_isolada_por_empresa`.
- A tarefa de ligação por e-mail é provisória (a tela `Plat-Cobranca` é da fase 2). Quando virar fila, o telefone sai da caixa de e-mail e passa a ficar só na tela, atrás da permissão `PLT-09`, o que é melhor. Até lá, o e-mail para Dono e Financeiro é aceitável.
