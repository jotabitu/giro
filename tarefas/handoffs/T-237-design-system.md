# T-237 · Telas sem fornecedor e aviso da PLT-16 · design-system → orquestrador, frontend

**O que foi feito:** branch `t-237-telas-apagamento`, empilhada na `origin/t-235-regras-apagamento` (PR #235, ainda não mesclado). Só HTML de referência em `docs/telas/html/`.

- `Aprovacoes-Desktop` e `Aprovacoes-Mobile`: no pedido de despesa saem "Fornecedor" (Moto Peças CE) e "15 out · boleto". Ficam categoria (Manutenção), descrição (Pneus (2)), veículo (Honda Pop 110i · PMZ-3E17), valor (R$ 1.200,00) e vencimento (07 out). O título passa de "2 pneus" para "Pneus (2)", como a descrição do seed. Sem forma de pagamento (`APR-03`, `FIN-05`, CA-APR-11).
- `Compra-Checkout-Desktop` e `Compra-Checkout-Mobile`: depois do cartão "CNPJ ativo", faixa informativa (`info-soft`/`info-ink`, tokens existentes) com "Este CNPJ já usou o teste grátis. A 1ª fatura vence hoje." (`PLT-16`).
- `docs/telas/README.md`: linha da compra cita a `PLT-16`.

**Regras cobertas:** APR-03, FIN-05, PLT-16, PLT-01.

**Para o frontend:**
- O aviso só aparece quando a API reconhece um CNPJ que já foi cliente e foi apagado; a tela exibe o texto que a API devolver, sem decidir por conta própria. A recusa por CNPJ ainda não apagado ou fatura atrasada (`PLT-16`) não tem tela de referência nova: usa o erro de campo padrão do CNPJ. Se quiser tela dessa recusa, peça.
- O pedido de despesa mostra o que o `resumo` devolver (categoria, descrição, veículo, valor, vencimento).

**Limites:** não abri as telas num navegador; conferi a marcação e os tokens por leitura.
