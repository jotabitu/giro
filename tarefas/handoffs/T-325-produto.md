# T-325 · Suporte Giro nas escritas do financeiro · produto → orquestrador, backend (T-324), segurança, qa

Decisão do dono em 19 out 2026: **opção A** da `[decisão]` da T-324 (achado da T-317), a mesma das movimentações (T-319).

**O que foi feito:**

- **Regra:** o suporte Giro, mesmo em "ver e editar", lê o caixa, as despesas e os reembolsos, mas recebe 403 `PLT-07` ao:
  - abrir caixa e fechar caixa (`FIN-07`);
  - lançar despesa, pela tela `Despesas` ou paga no caixa (`FIN-05`);
  - marcar reembolso como feito (`DEV-02`).
  O 403 vem antes de ler a nota ou o comprovante e de conferir o corpo, e nada é gravado.
- **Onde ficou:** `PLT-07`, `FIN-05`, `FIN-07` e `DEV-02`, com notas de mudança nas seções Plataforma e Financeiro. A seção nova "Decisões de 19 out 2026" tem a linha da decisão. O reembolso mora na `DEV-02` (acerto da caução), e não numa regra `FIN`; a nota da seção Financeiro cita as três.
- **Backlog:** a `[decisão]` da T-324 está riscada. A T-324 depende agora da T-325 e cita a `DEV-02`.
- **Critério:** CA-017-24 em `docs/qa/criterios/T-017.md`, com o suporte Diego Santos na Moto Rápida em "ver e editar" (Chamado #1042):
  - em 07 out, o caixa da Filial Centro, aberto, com a gaveta de 28100;
  - o óleo de R$ 48,00 da QXA4B21;
  - em 14 out, o reembolso de 18300 da Juliana (LOC-2836).
  Ele lê tudo. As quatro escritas dão 403 (nunca 500) e nada muda: o caixa continua aberto com 28100, as despesas de outubro da Centro somam 706670 e o reembolso fica `a_fazer`. Com "só ver", também 403.

**Regras cobertas:** PLT-07, FIN-05, FIN-07, DEV-02.

**Próximo passo:**
- **Backend (T-324):** pela opção A. Use `suporte_proibido` nas quatro views, como na T-316. Elas saem de `QUEBRADAS` em `test_t317_varredura_suporte.py`. Escreva o teste `test_plt_07_suporte_nao_escreve_no_financeiro` pelo CA-017-24.
- **QA:** CA-017-24.
- **Segurança e orquestrador:** a decisão vale só para essas quatro ações. Outras escritas do financeiro passam pelo `_usuario_do_ator`, que devolve `None` para o suporte, e não deram 500 na varredura. São elas: sangria, estorno de movimento, receber, cobrar, pagar despesa e anexar nota. O handoff da T-317 aponta que podem gravar "sistema" como autor (`AUD-05`). Se o dono quiser a mesma linha nelas, é decisão nova. Não decidi, porque fica fora do pedido.
- **Orquestrador:** abrir o PR desta branch.
