# T-248 · Regras das decisões de 15 out (clientes, aprovação, convite) · produto → arquiteto, backend, frontend, qa, seguranca

**O que foi feito:** escrevi as três decisões do dono de 15 out 2026 das notas dos testes na mão. Branch `t-248-regras-decisoes-15-out`, a partir da `origin/main` com o #239.

- `docs/regras-de-negocio.md`:
  - **`CLI-10` (nova), filtro de filial na lista de Clientes:**
    - o cliente continua da empresa, sem filial de cadastro;
    - a lista não segue o seletor do topo, e o filtro começa em "Todas as filiais", para todo perfil que abre a lista;
    - uma filial escolhida mostra os clientes com pelo menos uma locação nela, em qualquer estado; quem nunca alugou só aparece em "Todas";
    - o filtro oferece as filiais ativas da pessoa (administrador e financeiro, todas), e a API recusa filial sem acesso (403 `USR-07`);
    - os outros filtros, a busca e as contagens valem dentro da filial; os números do cliente continuam os dele na empresa.
  - **`USR-07`:** cita que a lista de Clientes não segue o seletor (`CLI-10`).
  - **`APR-09`, exceção do administrador:**
    - o administrador decide (aprova ou recusa) o próprio pedido;
    - os outros perfis continuam proibidos, também com a permissão extra (`USR-03`);
    - o pedido dele continua nascendo `pendente`, e outra pessoa que aprova também pode decidir (quem decide primeiro fecha);
    - o evento marca "aprovou o próprio pedido" (ou "recusou o próprio pedido").
  - **`APR-12`:** os pedidos do administrador entram nos números dele, porque ele pode decidi-los. **`FIN-05`** (detalhe da despesa) cita a exceção.
  - **`USR-01`, convite:**
    - o acesso só nasce por convite, e a senha só a pessoa cria;
    - "Copiar link do convite" no `convite_pendente` (vencido ou não), só para o administrador;
    - copiar gera um link novo de 7 dias, invalida o anterior, aparece uma vez, não sai por e-mail nem WhatsApp e grava evento `seguranca` sem o link;
    - o suporte Giro não copia (`PLT-07`), e o status e a contagem do plano não mudam.
  - Entidade Usuário (convite vencido), notas de mudança nas três seções e três linhas em "Decisões de 15 out 2026".
- `docs/qa/criterios/T-248.md`: CA-248-01 a 07 (Clientes), 08 a 11 (aprovação), 12 a 16 (convite).
- `tarefas/backlog.md`: as três decisões marcadas "Regra escrita na T-248" e o estado da T-248.

**Regras cobertas:** CLI-10, CLI-06, USR-01, USR-07, APR-09, APR-10, APR-12, FIN-05, PLT-07.

**Leituras do produto, para o dono conferir (dentro das decisões, sem número novo):**
- "Pelo menos uma locação" vale em qualquer estado, inclusive `cancelada`: é a leitura literal, e a mais simples de testar.
- O filtro mostra só filiais ativas; a desativada sai do filtro, e os clientes dela ficam em "Todas" (`USR-07`, `FIL-06`).
- O administrador também pode recusar o próprio pedido, com motivo: quem pode aprovar decide. Ele continua podendo cancelar em "Meus pedidos".

**O que ficou de fora:** o número do limite por hora do link copiado fica com o contrato (T-249); o CA-248-15 só pede o 429.

**Para quem recebe:**
- **Arquiteto (T-249):**
  - `clientes.md`: parâmetro `filial`, recusa 403 `USR-07`, contagens dentro da filial;
  - `aprovacoes.md`: `acoes.aprovar` e `acoes.recusar` verdadeiros para o administrador no próprio pedido, a marca no evento e os números da `APR-12` com os pedidos dele. Atenção: o contrato diz que há um `CHECK APR-09` no banco (decidido por ≠ pedido por), que precisa da exceção (ou sair do banco e ficar no serviço);
  - `contas.md`: rota do link (só administrador, só `convite_pendente`, link uma vez, evento, limite por hora, 409 `transicao_usuario`, 403 `PLT-07` no suporte) e o `acoes` do usuário.
- **Backend (T-250):** testes pelos nomes do backlog, com os casos CA-248-01 a 16.
- **Frontend (T-251):** botão Aprovar pelo `acoes`; filtro da lista de Clientes independente do seletor; aviso "O link anterior deixa de valer.".
- **QA:** CA-248-08 usa os números do caso "Números da tela Aprovações em 07 out" (Aprovadas 3, "1 h 10 min").
- **Segurança (T-252):** CA-248-15 e 16.
