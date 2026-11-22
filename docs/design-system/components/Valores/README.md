# Valores

Lista de rótulo à esquerda e valor à direita, com linha fina entre as linhas: o "Resumo" da venda (preço de tabela, desconto, preço final, entrada, saldo, comissão) e os dados curtos de um contrato ou de uma conta. Substitui o `.kv` copiado em cada tela.

- `div.wl-kv` por linha, com dois `span`: rótulo (`ink-muted`) e valor (500, alinhado à direita). Sem linha depois da última. 15 px.
- Todo valor vem pronto da API ("− R$ 1.832,00", "12 × R$ 1.339,00"). A tela não soma nem arredonda.
- Para o total, repita o padrão e deixe o rótulo dizer o que é ("Preço final"); não crie linha em destaque, o texto basta.
- Para quatro ou cinco fatos em colunas dentro de um bloco, use o `wl-facts` da ficha, não esta lista.
