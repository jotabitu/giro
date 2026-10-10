# T-125 · Cancelar a troca de veículo na tela · frontend → orquestrador, qa, produto

**O que foi feito:** a tela da locação cancela a troca pendente (`LOC-09`) e respeita o cancelamento bloqueado (`LOC-12`). Os tipos vêm do OpenAPI da T-123 (`npm run api:gerar` não mudou nada: o `schema.d.ts` já estava atualizado).
- **Botão "Cancelar troca"** (desktop e celular) só quando `acoes.cancelar_troca` vem `true`. Abre uma janela com o motivo obrigatório; chama `POST /api/locacoes/{id}/trocar-veiculo/cancelar/` (`locacoes.cancelarTroca`). Ao concluir, recarrega a locação, a lista, a frota e a devolução, e avisa que a locação segue com o veículo atual. O erro 400 aparece no campo `motivo`; o 409 `transicao_troca` e o 409 `troca_saida_concluida` aparecem na janela com a mensagem da API, sem texto próprio.
- **Com troca pendente:** o botão de cancelar a locação some porque a API manda `acoes.cancelar = false`; a tela não decide isso. Se o 409 `troca_pendente` chegar (acesso antigo, outra aba), a janela de cancelar mostra a mensagem da API ("Conclua ou cancele a troca antes").
- **Bloco "Troca de veículo" no detalhe** (`troca` da API): veículo atual e novo (placa em mono), motivo, data do pedido, andamento da chegada do atual e da saída do novo (Em andamento, Concluída, Descartada), e, para quem vê valores, o preço do veículo novo e a diferença de caução com o status da conta. O vistoriador não recebe `preco` nem `caucao`, e a tela só omite o que não vem.
- **Acerto:** não mudou o componente: ele já mostra `itens` e `creditos` como a API devolve. O item `diferenca_troca` entra como cobrança em `itens` e como crédito (com "+") em `creditos`; o tipo já estava no enum gerado.

**Onde:** `frontend/src/components/locacoes/{AcoesDaLocacao,DetalheDaLocacao}.tsx`, `src/lib/api/{locacoes,tipos-locacoes}.ts`, `src/lib/locacoes.ts`, fixtures em `src/testes/falsos/{falso-locacoes,falso-vistorias}.ts`.

**Regras:** LOC-09, LOC-12, DEV-01, DEV-02.

**Testes:** `src/testes/falsos/falso-troca.test.ts` (8): sem troca, troca pendente (`cancelar_troca` true, `cancelar` false, bloco `troca`), 409 `troca_pendente` ao cancelar a locação, vistoriador sem preço, motivo obrigatório, 409 `troca_saida_concluida`, cancelamento que limpa a troca, vendedor, e o acerto com a diferença como cobrança (12000) e como crédito (4000, somando ao saldo). `DetalheDaLocacao.test.tsx` ganhou 2 (bloco, botões nos dois tamanhos, vistoriador). Suite: 274 testes, `lint` e `tsc` limpos.

**NÃO conferi:** no navegador nem no compose (sem seed da Moto Rápida, ver T-126); as janelas (`Dialogo`) não são renderizadas nos testes, que são de HTML estático e das fixtures. Os valores do bloco e do acerto das fixtures são de exemplo; os reais vêm da API.

**Pontos para o produto/qa:** a recusa `troca_saida_concluida` é provisória na T-122 (`[decisão]`); a tela só repete a mensagem. Quando a saída do novo está concluída, a API deve mandar `cancelar_troca = false` e o botão não aparece, então o caminho do 409 só ocorre em corrida entre duas pessoas.

**Próximo passo:** orquestrador abre o PR. QA: caso LOC-2836 (devolve 26300) e cancelar a troca com a conta de caução paga, quando houver seed.
