# T-275 · Dados da ficha do veículo que a API não manda · arquiteto → backend, frontend, produto, design-system

**O que foi feito:** contrato dos pedidos 1 a 4 do handoff do frontend da T-242, em `docs/api/veiculos.md`, "Blocos da ficha". Tudo vem só no detalhe do veículo; a lista da Frota não muda.
**Onde:** `docs/api/veiculos.md` (tabela de blocos e a seção nova), `tarefas/backlog.md` (seção da T-275).
**Contrato:**
- **Pedido 1, pagamentos da locação:** `locacao_atual.plano` (periodicidade, plano especial e o preço do período congelado). `locacao_atual.pagamento` traz a situação (`atrasado`, `vence_hoje` ou `em_dia`), o `rotulo` pronto, a conta mais antiga, o valor, quantas estão atrasadas e `cobrar`. O botão "Cobrar" chama o `cobrar` de contas a receber. O vistoriador não recebe pagamento nem valor.
- **Pedido 2, próxima manutenção:** `manutencao.proxima` ganha `faltam_km`, `intervalo_km`, `progresso_pct` (a barra), `depois` (o serviço seguinte), `nota` (o gatilho de 500 km da `MAN-03`) e `dias_estimados`. Este último fica `null` até o produto decidir, e a tela não mostra o trecho.
- **Pedido 3, fotos e avarias:** `vistoria_recente` é a última vistoria concluída: as cinco fotos fixas com URL de 15 minutos, `total_fotos`, as avarias abertas com `preexistente` e a locação, e o vistoriador. O financeiro não recebe o bloco.
- **Pedido 4, movimentações:** entram no MVP (dono, 16 out). O detalhe ganha o bloco `movimentacoes` (total, as 3 últimas e a em andamento) e `acoes.movimentar` com `motivo_movimentar`, para a tela mostrar o botão desativado com o motivo. O fornecedor é o app da T-286; até ele existir, o bloco vem `null` e a ação vem `false`.
**Regras cobertas:** MAN-03, VIS-01, FIN-01, CLI-07, LOC-01, LOC-15, MOV-02, MOV-03, USR-09, AUD-05. Caso de teste: QXA-4B21 em 07 out (Parcela 2 atrasada, R$ 299,40; troca de óleo aos 19.900 km, faltam 950).
**O que ficou de fora:**
- O app `manutencao` (fase 2): até ele existir, `manutencao` vem `null`.
- A lista de vistorias por veículo ("e as vistorias anteriores").
- O contrato das movimentações, que é a T-286.
- Duas [decisão] para o produto: o uso médio em dias, e o texto e o alvo do Cobrar com mais de uma conta atrasada.
- Uma [divergência] para o design-system: a foto "Pneu" e o lado da avaria; o selo fica "Alugado", pela regra.
**Próximo passo para quem recebe:** o backend implementa pelo "Pronto quando" da T-275 no backlog; depois, o frontend liga os blocos.
