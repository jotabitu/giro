# T-387 · As 4 decisões do produto na ADR 0034 do WhatsApp · produto → orquestrador, arquiteto, dono, backend, qa

Branch `t-387-whatsapp-decisoes`, empilhada sobre a `t-385-whatsapp` (PR #404).

**As quatro decisões:**

1. **Textos com começo e fim fixos (decidido pelo produto).**
   - O texto ao cliente e à pessoa convidada abre com "Olá, {nome}.", e a marca vai no meio, sem artigo: "Moto Rápida informa: ...". Sem artigo não se erra o gênero, que foi o problema do "da {nome}" na T-299. A proposta da ADR ("Aqui é a {marca}") errava.
   - O texto termina com frase fixa:
     - cobranças: "Se você já pagou, desconsidere esta mensagem.", como já é na régua da assinatura;
     - recibo: "Este é o seu recibo.";
     - links: "O link vale por ...";
     - lembrete: "Para mudar o horário, ligue para a loja.".
   - O "fale com a gente por aqui" sai, e fica "Pague na loja.". Também sai o "Obrigado" da ADR.
   - Os 13 modelos, prontos para a Meta, estão em `docs/qa/criterios/whatsapp.md`, com variáveis, exemplos da Moto Rápida e o plano se a Meta recusar uma variável que é frase inteira.
2. **Aceite (decidido pelo produto).**
   - **Cliente:** `CLI-12` nova. A caixa "Aceita receber avisos pelo WhatsApp" fica no cadastro, desmarcada, com data e quem marcou. Na importação, vazio conta como "não". "SAIR", "PARAR" e "CANCELAR" desmarcam. Depois de 3 falhas seguidas, o celular fica marcado "sem WhatsApp".
   - **Pessoa convidada:** `USR-01`. O convite vai por WhatsApp só com "A pessoa aceita receber o convite pelo WhatsApp" marcado pelo administrador.
   - **Responsável pela assinatura:** `PLT-02`. A equipe Giro marca o aceite ao criar a empresa.
3. **Queda para o e-mail (decidido pelo produto).** Sem aceite, sem celular ou com o envio recusado, o aviso vai pelo e-mail com o mesmo texto. Isso vale também para:
   - o recibo do pagamento (`AUT-05`);
   - o lembrete (`AUT-01`);
   - o recibo da devolução (`DEV-02`), com o PDF anexo, porque o link de 15 minutos venceria no e-mail.
4. **Remetente "Giro Avisos": pede o dono.** Ele contraria a frase das Automações "nunca com o nome Giro". Está como `[decisão]` no backlog e em "Pontos em aberto":
   - **A (padrão do produto e do arquiteto):** exceção na fase 1, com a marca da locadora sempre no texto e o perfil "Avisos das empresas que usam o sistema Giro. Este número não recebe mensagens.";
   - **B:** um número por locadora já;
   - **C:** sem WhatsApp ao cliente final na fase 1.

   **O que o cliente deve ver**, para o produto: no remetente, o nome que a Meta aprovar. No texto, sempre a locadora, na segunda frase. Na resposta automática, o telefone da loja.

**Onde:**
- `docs/regras-de-negocio.md`:
  - bloco "Mensagens pelo WhatsApp" nas Automações;
  - `CLI-12`, `USR-01`, `PLT-02`, `AUT-01` e `AUT-05`;
  - notas de mudança e "Pontos em aberto".
- `docs/qa/criterios/whatsapp.md`: os 13 modelos e os critérios CA-WPP-01 a 07.
- `tarefas/backlog.md` e `tarefas/feito.md`.

**Próximo passo:**
- **Orquestrador:** levar a `[decisão]` do remetente ao dono, junto com a escolha da opção da ADR.
- **Arquiteto:** ao aceitar a ADR 0034, trocar os 13 modelos da ADR pelos de `whatsapp.md`. Em `docs/api/financeiro.md` ("Régua de cobrança: textos"):
  - trocar a abertura `{marca}: olá, {nome}.`;
  - trocar "Pague na loja ou fale com a gente por aqui";
  - pôr o recibo na queda para o e-mail.
  Em `clientes.md`, entra o campo do aceite; em `contas.md`, o aceite do convite.
- **Backend** (nas tarefas da ADR): o campo `aceita_whatsapp` com data e quem marcou, a marca "sem WhatsApp", o e-mail do recibo, do lembrete e da devolução com o PDF anexo, e os testes dos CA-WPP.
- **Frontend:** a caixa no cadastro do cliente e no convite.
- **Segurança:** a ADR já cita os dados que passam por servidores fora do Brasil. Ponha a Meta no aviso de privacidade.
