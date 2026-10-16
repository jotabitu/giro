# T-293 · Valor do dia na linha Pagamentos da ficha · arquiteto → backend

**O que foi feito:** pela decisão do produto na T-290, `locacao_atual.pagamento.valor_centavos` da ficha do veículo passa a ser o valor do dia, com multa e juros (`FIN-03`). É o mesmo `valor_hoje.total_centavos` do Receber e da mensagem do Cobrar.
**Onde:** `docs/api/veiculos.md`, "Blocos da ficha":
- o exemplo passa de 29940 para 30609;
- um item novo explica o `valor_centavos`;
- os textos do rótulo foram confirmados.

No backlog, o teste da seção da T-275 passa a esperar 30609.
**Caso:** QXA-4B21 em 07 out: 29940 + 599 de multa + 70 de juros = 30609, "Parcela 2 atrasada · R$ 306,09". Na conta que vence hoje, o valor é o principal. Com mais de uma conta atrasada, é a soma dos valores do dia.
**Regras cobertas:** FIN-03, CLI-07.
**O que ficou de fora:** o código, que vai junto com o da T-275 (`test_vei_ficha_pagamento_da_locacao` com 30609).
**Próximo passo para quem recebe:** o backend lê o valor do dia de `financeiro.selectors`, o mesmo cálculo do `valor_hoje`, sem refazer a conta na locação.
