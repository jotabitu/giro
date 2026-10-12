# T-132 · Contrato e textos da T-129 · produto → orquestrador, frontend, qa, backend

**Parte do arquiteto (139992a):** `docs/api/empresas.md` traz a fórmula das cores da marca como implementada em `backend/apps/empresas/marca.py` (`cor_sobre` pelo contraste WCAG; `cor_suave` e `cor_suave_escuro` em OKLCH; valores fixos do `wl-theme.css` para a cor padrão), no lugar da mistura sRGB das telas, e registra `cor_marca` vazio em vez de nulo (decisão 1 do handoff da T-129).

**Parte do produto:**
- **Receita do painel (decisão 2 da T-129):** `receita_locacao` e `receita_semana` **não** incluem multa e juros por atraso. A `FIN-15` passou a dizer isso: mesma base do `Receber`, valor das contas de locação pagas no período (parcelas e cobranças do acerto, como avaria e multa de encerramento), sem caução. Multa e juros pagos ficam só na DRE, na linha de multas (`FIN-13`). Motivo: o painel acompanha o aluguel recebido e precisa bater com o `Receber`. Registrado em "Mudanças em 12 out 2026 (T-132)" no fim da seção Financeiro.
- **Textos sem exemplo (decisão 4 da T-129):** todos aprovados como o backend escreveu e fixados em `docs/api/painel.md`:
  - `atencao.texto` com zero: "Nenhum contrato pede atenção"; `pendencias.titulo` com zero: "Nenhum contrato precisa de ação hoje".
  - `convidar_equipe.detalhe` sem convite: "Chame quem vai usar o sistema com você".
  - `equipe_hoje.resumo` de quem não fez nada hoje: "último acesso hoje", "último acesso ontem", "último acesso em 03 out", "ainda não acessou".
  - Tendências que caem: "3 a menos esta semana" (`alugados_agora`) e "6% a menos que a anterior" (`receita_semana`), com `tendencia: "desce"`; sem variação ou sem base de comparação, `contexto` e `tendencia` `null`.
  - `para_hoje`: "Devolver R$ X a Fulano por Pix", "no cartão" e "em dinheiro" (`DEV-02`); o de dinheiro só aparece até a T-017, porque com o caixa o reembolso em dinheiro nasce `feito`.

**Mudança de código:** nenhuma. O código da T-129 já faz o que ficou fixado; nenhuma tarefa de backend nova.

**Regras:** `FIN-15` (ampliada), `FIN-13`, `FIN-03`, `DEV-02`, `IMP-01`.

**Próximo passo:**
- **Orquestrador:** abrir o PR da branch `t-132-contrato-textos-t129` (arquiteto e produto).
- **Frontend:** os textos vêm prontos da API; com `contexto` `null`, o cartão mostra o número sem a linha de contexto.
- **QA:** nos testes do painel, a receita do seed não soma `multa_centavos` nem `juros_centavos` das contas pagas.
