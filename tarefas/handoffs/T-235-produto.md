# T-235 · Regras do apagamento pela T-230 · produto → orquestrador, arquiteto, design-system, backend, qa

**O que foi feito:** escrevi as decisões do dono de 15 out 2026 sobre a revisão da segurança (T-230) e o fornecedor no pedido de despesa (T-201). Branch `t-235-regras-apagamento`, a partir da `origin/main` com o #233.

- `docs/regras-de-negocio.md`:
  - **`AUD-08`, "O que fica depois do apagamento"** passou da A para a B, igual para toda empresa:
    - a linha fica só com o CNPJ (mais plano, datas, cidade e UF), com "Dados apagados";
    - o tomador fica na fatura e sai com ela no prazo de guarda;
    - a fatura `atrasada` guarda também o e-mail de cobrança, para a equipe cobrar à mão, até a baixa ou o fim do prazo;
    - a auditoria da plataforma guarda "alterado", sem o valor;
    - depois da última fatura, sai o CNPJ, e ficam reservados o subdomínio e o schema;
    - o pagador no parceiro perde e-mail e telefone.
  - **`PLT-14`:** a fatura guarda o tomador como foi na nota (ou na cobrança, sem nota), e mudar os dados fiscais não muda faturas já emitidas.
  - **`PLT-16` (nova), compra de quem já foi cliente:**
    - antes do apagamento, a compra é recusada, e a volta é pela reativação;
    - depois, cria uma empresa nova, `ativa`, sem teste, com a 1ª fatura vencendo na compra e subdomínio novo;
    - é recusada enquanto houver fatura atrasada da assinatura anterior;
    - sem o CNPJ na linha apagada, é uma compra comum.
  - Notas de mudança, dado de referência "Volta da Moto Rápida depois do apagamento", e quatro linhas em "Decisões de 15 out 2026". A linha do caso 5 da T-194 está marcada como substituída. O fornecedor saiu de "Pontos em aberto" como decidido (A).
- `docs/qa/criterios/assinatura.md`: CA-ASS-58 reescrito pela B (agora no caso da `ativa`, que tem nota); CA-ASS-59 a 62 novos.
- `docs/qa/criterios/aprovacoes.md`: CA-APR-11 (células do pedido de despesa).
- `tarefas/backlog.md`:
  - a `[decisão]` da T-230 e a do fornecedor (T-201) marcadas como resolvidas;
  - seção da T-235, com duas propostas sem número: arquiteto (contratos) e design-system (`Aprovacoes` e o aviso na `Compra-Checkout`).
- `tarefas/feito.md`: linha da T-235, PR a abrir.

**Regras cobertas:** AUD-08, PLT-14, PLT-16, PLT-06, PLT-01, APR-03.

**Para quem recebe:**
- **Arquiteto:**
  - `assinatura.md`: tomador na fatura (M-01).
  - `cancelamento.md`: limpeza da linha, e-mail na fatura atrasada, pagador no Asaas (B-01), CNPJ depois da última fatura.
  - `auditoria.md`: "alterado" no `public` (M-03).
  - `plataforma.md`: CNPJ único só entre empresas não apagadas (B-02) e a compra da `PLT-16`.
  - `aprovacoes.md`: a descrição no `resumo` da despesa. O contrato da T-201 tinha categoria, veículo, valor e vencimento; a decisão do dono inclui a descrição.
- **Design-system:** a tela `Aprovacoes` sem "Fornecedor" e sem "15 out · boleto"; o aviso da `PLT-16` na `Compra-Checkout`.
- **Backend (T-195):** os testes `test_aud_08_*` e `test_plt_16_*` dos CA-ASS-58 a 62, depois do contrato.
- **Qa:** CA-ASS-58 a 62 e CA-APR-11.

**Observações:**
- Na `PLT-16`, a aprovação do dono foi "sem teste, com a 1ª fatura vencendo na compra". Escrevi que a empresa nasce `ativa` (a régua normal segue, com D+1 `inadimplente`) e os textos das duas recusas e do aviso. Se o dono quiser outro estado até a 1ª fatura ser paga, é só ajustar.
- A recusa da compra antes do apagamento é o que o CNPJ único já fazia; ganhou só o texto.

**Próximo passo:** o orquestrador abre o PR e numera as propostas. Só documentos, sem teste para rodar.
