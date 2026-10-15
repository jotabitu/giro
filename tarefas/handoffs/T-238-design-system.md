# T-238 · Subir as telas de referência novas e alteradas · design-system → frontend (T-242, T-243), produto (T-246)

**O que foi feito:** as telas novas do dono entraram em `docs/telas/`, e o índice ganhou as linhas delas. A pasta do dono (`giro/docs/telas`) foi só lida; nada foi rodado nela além de `git status`, `git diff` e `git show`.

**Como foi conferido:** a pasta do dono está atrás da `main`. A base dela é o commit de 08 out (PR #54), e 125 dos arquivos têm data de 13 out às 14:57, uma cópia em bloco. Comparada com a `main`, essa cópia traz dados que as regras já corrigiram: CNPJ -10 no lugar de -95 (T-053), Messejana com CNPJ -02-90 (regra: 0003-57), "Terça, 07 out", contadores do menu 5/7/3/6, diárias 49,90 e 119,00, cartão do Diego de R$ 179,70 no caixa. Copiá-la por cima teria desfeito esses acertos. Por isso só entrou o que é novo ou foi alterado pelo dono em 14 out.

**Onde:**
- Novas (5): `Movimentacoes-Desktop/Mobile`, `Movimentacao-Nova-Desktop/Mobile`, `Movimentacao-Chegada-Mobile`.
- Alteradas com mesclagem de três vias, por palavra, descartando os trechos antigos: `Veiculo-Desktop` e `Veiculo-Mobile` (botão Movimentar, locação atual, fotos e avarias, movimentações, categoria e preço de hoje), `Frota-Desktop` e `Frota-Mobile` (botão Movimentações), `Clientes-Desktop` e `Clientes-Mobile` (nome e cartão do cliente abrem `Cliente-Detalhe-*`).
- Já na `main`, com a versão da `main` mantida por ser mais nova (decisões de 14 e 15 out, sem fornecedor, devolução em 14 out): `Aprovacoes-*`, `Cliente-Detalhe-*`, `Veiculo-Novo-*`, `Filial-*`.
- `docs/telas/README.md`: seção Frota com Movimentações, Nova movimentação e Registrar chegada (rota e app marcados como proposta da T-246).

**Checagens:** todos os links entre telas e do índice resolvem; os 138 arquivos estão no índice; sem emoji, sem exclamação, sem "check-in" nem "depósito" nas telas novas; cada tela com par desktop e celular, exceto `Movimentacao-Chegada` (só celular, como o dono desenhou), `Main`, `Menu` e `Dashboard`, que já eram assim.

**Regras cobertas:** VEI-01, VEI-02, VEI-04 (a movimentação ainda não tem regra).

**Divergências registradas em `tarefas/backlog.md`:**
1. Ficha do veículo (para T-242): LOC-2841 de 30 set a 04 nov e "desde 30 set" (regras: 23 set a 28 out), vistoria e km de 30 e 07 out (regras: 23 set), chassi ...4417 (regras: ...4401), última troca de óleo aos 17.900 km (regras: 18.900). A estrutura vale; os dados valem os das regras.
2. Movimentações (para T-246): código `MOV-` na tela e `MT-` na tarefa; "MT-03" é o modelo da moto; contadores antigos no menu; placas fora do seed; lavagem com três valores.
3. Cópia de 13 out da pasta do dono (acima).

**O que ficou de fora:** as edições que o dono possa ter feito nos arquivos de 13 out. Não dá para separá-las do que é cópia antiga sem a lista dele. Se houver, pedir uma cópia feita a partir da `main` atual. O `CLAUDE.md` ainda diz "123 telas"; são 138 arquivos em `html/` (a contagem é do orquestrador).

**Próximo passo para quem recebe:** o frontend (T-242) usa `Veiculo-Desktop` e `Veiculo-Mobile` como estrutura e puxa os dados da API; o que a tela mostra e a API não manda vira pedido ao arquiteto. O produto (T-246) parte das três telas de movimentação e decide código, estados e fase.
