# CampoDeDinheiro

Campo de valor em reais: o ponto de milhar e a vírgula aparecem enquanto a pessoa digita. É o único campo de dinheiro do sistema. Visual e estados são os do TextField (48px, rótulo acima, borda `line`, erro em `critical`, `wl-mono` quando a tela já usava).

Os dígitos entram pela direita como centavos: "5", "0", "0", "0", "0", "0" mostram `0,05`, `0,50`, `5,00`, `50,00`, `500,00` e `5.000,00`. Apagar volta um dígito; vazio fica vazio. Colar "5.000,00" ou "5000" dá `5.000,00`. Teto de R$ 999.999.999,99.

`prefixo` põe "R$ " na frente, só onde a tela de referência já mostra (placeholder "R$ 0,00" ou valor "R$ 90,00"); sem ele, só `5.000,00`. Linhas de tabela e planos que montam o próprio rótulo usam `InputDeDinheiro` (o mesmo comportamento num `<input class="wl-input">`).

O campo só formata; o valor enviado à API segue em centavos (`valor_centavos`) e a validação é da API. Código em `frontend/src/design-system/components/CampoDeDinheiro/` (T-509), preview em `/design-system/campo-de-dinheiro`.
