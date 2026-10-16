# T-299 · Leitura dos textos da régua da assinatura · produto → orquestrador, backend, qa (T-204, T-215), segurança

Leitura dos textos que o backend escreveu na T-186 parte 3 (PR #304, `apps/plataforma/services.py`: `mensagem_da_regua`, `_como_pagar`, `_pedir_ligacao`). A seção da T-299 está no backlog da branch `t-186c-regua-mensagens`; esta branch parte da `main` e não a tem.

**O que foi feito:**

- Textos fixados em `docs/qa/criterios/assinatura.md`, seção "Textos da régua da assinatura (T-299)", com CA-ASS-64 a 67. A `AUT-13` aponta para lá, e a nota de mudança está no fim da seção Plataforma das regras.
- A base do backend fica. Seis ajustes:
  1. **"da empresa {nome}"** no lugar de "da {nome}" (o nome pode ser masculino), também no assunto do D+7 e no e-mail da ligação.
  2. **Suspensão com as palavras da tabela de estados:** "a empresa fica suspensa: só ver e exportar os dados, sem criar locação, venda nem cobrança" (antes: "o acesso fica só para leitura"). O D+7 ganha "Pagando, o acesso volta na hora." Assunto do D+7: "Giro: a empresa Moto Rápida fica suspensa em 06 nov".
  3. **D+7, a ligação:** "A equipe Giro vai ligar para o responsável pela assinatura.", e só quando há o telefone do responsável (antes: "A equipe Giro vai ligar para ajudar.", sempre). A tarefa de ligação sai sempre.
  4. **WhatsApp:** começa com "Giro: " e leva o caminho de pagar (no boleto, só o link) e o rodapé. Antes, não dizia de quem era nem como pagar.
  5. **Cobrança automática** (cartão guardado sem recusa, Pix automático autorizado) no D-3 e no D0: rodapé "Não é preciso fazer nada."; Pix automático: "O pagamento sai pelo Pix automático no dia do vencimento.".
  6. **Endereço da página** `Admin-Assinatura` (no subdomínio da empresa) em todo e-mail, na linha "Assinatura: {endereço}".
- E-mail da ligação: assunto "Ligação de cobrança: Moto Rápida, FAT-0001 com 7 dias de atraso", com o e-mail de cobrança e "nome não cadastrado" / "celular não cadastrado".
- Nota da fase 2 (fila de ligações na `Plat-Cobranca`, ponto de troca `_pedir_ligacao`) na mesma seção dos critérios.
- **[decisão] marco perdido** (backlog e "Pontos em aberto"): A) nenhum marco é recuperado (como a `AUT-03`, o código de hoje); B) só o D+7 sai na próxima execução, até o D+14, uma vez. Padrão: B.

**Onde:** `docs/qa/criterios/assinatura.md`, `docs/regras-de-negocio.md` (`AUT-13`, nota T-299, Pontos em aberto), `tarefas/backlog.md`, `tarefas/feito.md`.
**Regras cobertas:** PLT-02, AUT-13.

**Tarefa de backend proposta (para o orquestrador numerar):**

### T-NNN · Textos da régua da assinatura
- **Agente:** backend · **Depende de:** T-186 parte 3 (PR #304), T-299 · **Regras:** AUT-13, PLT-02 · **Critérios:** CA-ASS-64 a 67 · **Pronto quando:** `mensagem_da_regua`, `_como_pagar` e `_pedir_ligacao` com os textos da seção "Textos da régua da assinatura (T-299)" de `docs/qa/criterios/assinatura.md`: "da empresa {nome}"; suspensão pela tabela de estados; D+7 com "Pagando, o acesso volta na hora." e a frase da ligação só com `responsavel_telefone`; WhatsApp com "Giro: ", o caminho de pagar (boleto só com o link) e o rodapé; "Não é preciso fazer nada." na cobrança automática sem recusa (D-3 e D0); a linha "Assinatura: {endereço}" em todo e-mail; o e-mail da ligação com o novo assunto, o e-mail de cobrança e "não cadastrado". Com o padrão B da `[decisão]` do marco perdido: o D+7 que não saiu no dia sai na próxima execução até o D+14, uma vez (e a ligação junto). Testes `test_aut_13_textos_da_regua_no_boleto`, `test_aut_13_automatica_nao_pede_nada`, `test_aut_13_whatsapp_com_marca_e_caminho`, `test_aut_13_d7_e_a_ligacao`, `test_aut_13_d7_perdido_sai_ate_d14`.

**Para a segurança:** hoje o e-mail da régua vai num `send_mail` só, com o e-mail de cobrança e os administradores juntos no "Para". Quando o e-mail de cobrança é de fora (contador), ele vê o e-mail dos administradores. Vale ver se cada destinatário recebe o seu.

**Próximo passo:**
- **Orquestrador:** numerar a tarefa de backend, abrir o PR desta branch e levar a `[decisão]` do marco perdido ao dono.
- **QA (T-204, T-215):** CA-ASS-64 a 67 com o relógio de referência, depois da tarefa de backend.
