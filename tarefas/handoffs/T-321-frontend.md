# T-321 · Conferência das Movimentações e da ficha no navegador · frontend → orquestrador, backend, qa

**O que foi feito:** conferi no navegador, em 1440px e 390px, o quadro, a Nova movimentação, a chegada, a parada e a ficha do veículo com os blocos da T-275, contra a API da pilha `giro` (host `motorapida.localhost`, login do gerente Rodrigo) e um servidor próprio do frontend (`next dev -p 3321`, `API_URL_INTERNA=http://localhost:8000`). Branch `t-321-conferencia-movimentacoes`, a partir da T-289 com o merge da T-275 (backend).

**Corrigido:**
- `VistoriaRecente.tipo` agora é `"saida" | "devolucao"` (era `chegada`) e `vistoriador` pode ser `null`, como a API manda (o seed traz `vistoriador: null`). A ficha escrevia "chegada"; agora escreve "devolução" (palavra das telas) e omite o nome quando não há.
- Desktop: "Ver as 0 fotos da vistoria" aparecia sem foto nenhuma; o link só aparece com `total_fotos > 0`.
- Celular: a ficha não tinha "Fotos e avarias", a linha "Pagamento" nem "Movimentações", que a referência `Veiculo-Mobile` mostra. Entraram `FotosEAvariasCelular`, a linha Pagamento em "Agora" (pelo `pagamento.rotulo`, sem valor, como na referência) e `MovimentacoesCelular`.
- Testes: `FichaBlocos.test.tsx` (devolução sem vistoriador, sem fotos, três casos do celular). tsc e eslint limpos; 58 testes de `src/components/frota` passando.

**Conferido e igual à referência (sem mudança):**
- Quadro 1440px: quatro colunas, cartão "MOV-0001 · Centro → Filial Maraponga · João S. · saiu 14:41 · Registrar chegada"; 390px: abas "escolha a coluna" com contagem. Sem rolagem horizontal.
- Nova: busca por placa, a API recusa o veículo reservado (LOC-2866) com o motivo, destino/transferência, quem leva, "Sair agora" cria e volta ao quadro. Criei MOV-0001 (transferência) e MOV-0002 (com parada) no seed.
- Chegada 390px: "rodou 54 km · não pode ser menor que 4.246", combustível, 4 fotos obrigatórias na transferência ("Faltam 4 fotos."), recebido por; o botão fica acima da barra inferior.
- Parada 390px: "Cheguei ao …" e depois "Sair da parada" com valor, nota e a frase da despesa; confirmar volta ao quadro.
- Ficha: QXA-4B21 mostra "Pagamentos 3 contas atrasadas · R$ 918,87" e Cobrar (a pilha está em 16 out, não 07 out, por isso não é "Parcela 2 atrasada · R$ 306,09"); Movimentar desativado com o motivo; veículo 8 mostra Movimentar e Transferir com os links `?veiculo=`.

**Não consegui:** prints. O portal do Maestri responde "the portal is not rendering" (janela minimizada), então a conferência foi pelo DOM (texto, posições, `scrollWidth`) e não por imagem. Também não enviei foto de chegada (o seletor de arquivo não é operável pelo portal): a confirmação da chegada com 4 fotos e a saída da parada com nota ficaram só nos testes. A saída da parada sem nota, com valor 35,00, foi confirmada.

**Observações:**
- Na primeira carga logo depois do login, o quadro mostrou "Seu perfil não tem acesso a esta página." e o menu sem Movimentações; ao recarregar, normal (o `eu` ainda não tinha chegado). Não reproduzi de novo; vale o qa observar o `GuardaDeRota` na primeira carga.
- Rota exibida na chegada: "Centro → Filial Maraponga" mistura nome curto e nome completo; vem da API (`rota`).

**Para o backend (nada novo):** os itens do handoff da T-289 (VeiculoRef duplicado, `Quadro.itens`, `busca`/`levando` no quadro) seguem valendo.

**Próximo passo:** orquestrador abre o PR (ou junta à T-289, #331).
