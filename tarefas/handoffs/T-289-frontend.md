# T-289 · Movimentações: telas ligadas na API · frontend → orquestrador, backend, qa, design-system

**O que foi feito:** as telas das Movimentações (quadro, Nova movimentação, Registrar chegada) saíram dos dados de exemplo e chamam a API real (T-288 parte 1, PR #324; contrato T-314, PR #325). Entraram a tela da parada, o Movimentar e o Transferir da ficha, a marca "Sem nota" com o "Anexar nota" em Despesas e o "rodou N km" na chegada.
- **Cliente:** `lib/api/movimentacoes.ts` agora é `http` nas rotas do contrato (quadro, obter, criar, iniciar, cancelar, `chegarNaParada`, `sairDaParada`, `enviarFotoDaChegada`, `registrarChegada`, locais, `pessoas`, `recebedores`). `lib/api/tipos-movimentacoes.ts` deriva do OpenAPI gerado (`components["schemas"]`). A camada de exemplo saiu de `lib/api` e virou o falso dos testes (`testes/falsos/falso-movimentacoes.ts`, como os outros módulos).
- **Quem leva e quem recebe (T-300):** a Nova movimentação usa `GET /api/movimentacoes/pessoas/?filial=` e a chegada usa `GET /api/movimentacoes/{id}/recebedores/`; `eu: true` mostra "(você)".
- **`pode.movimentacoes`** entrou no tipo `Pode` e nos falsos (`gerir`, `levar`, `nao`); o falso de navegação ganhou o item Movimentações no fim da Operação do administrador e do gerente. **`movimentacoes` em `GIRO_MODULOS_ATIVOS`:** uma linha em `backend/config/settings/base.py` (padrão do `contas.md` da T-314).
- **Tela da parada** (`Movimentacao-Parada-*`): rota `/veiculos/movimentacoes/{id}/parada`, uma tela para os dois passos pelo estado da API. `acoes.chegar_parada` mostra "Cheguei ao {local}" (previsto e aviso); `acoes.sair_parada` mostra "Sair da parada" com o valor pago, a nota (foto ou PDF até 10 MB) e as explicações da `MOV-04`; confirma e volta ao quadro. O cartão do quadro ganhou "Cheguei na parada" e "Registrar saída" só quando `acoes` manda.
- **Ficha do veículo:** "Movimentar" por `acoes.movimentar` (link para a Nova movimentação com `?veiculo=`; desativado com o `motivo_movimentar` quando a API manda o motivo; escondido sem as duas chaves) e "Transferir" por `acoes.transferir` (`?veiculo=&transferir=1`: a Nova movimentação já escolhe a primeira outra filial da pessoa, que pode trocar).
- **Despesas:** a lista marca "Sem nota" (`sem_nota`) no lugar do clipe; o detalhe mostra a origem (`MOV-0001`, link para o quadro com a busca) e, para quem lança despesa (`despesas_lancar = todas`) numa despesa sem nota, o "Anexar nota" (`POST /api/financeiro/despesas/{id}/nota/`; 409 `nota_existente` pelo erro da API).
- **Quadro:** o OpenAPI não tem `busca` no quadro, então o filtro de texto (código, placa, modelo) separa o que já veio, e o número da coluna acompanha; a consulta vai só com a filial do seletor.
- **Chegada:** o "rodou 26 km · não pode ser menor que 3.120" é só conta de exibição (T-302); quem confere o km é a API (`VEI-01`).

**Onde:** `frontend/src/lib/api/{movimentacoes,tipos-movimentacoes,financeiro,tipos}.ts`; `components/movimentacoes/{ParadaDaMovimentacao,CartaoDaMovimentacao,QuadroDeMovimentacoes,NovaMovimentacao,RegistrarChegada}.tsx`; `components/frota/FichaVeiculo.tsx`; `components/financeiro/{ListaDespesas,DetalheDaDespesa,Comuns}.tsx`; `app/(empresa)/veiculos/movimentacoes/[id]/parada/page.tsx`; falsos em `testes/falsos/`.
**Contrato:** `docs/api/movimentacoes.md`, `docs/api/contas.md` (T-314), `docs/api/financeiro.md` (nota e `sem_nota`), `docs/api/veiculos.md` (`acoes.movimentar`, `acoes.transferir`).
**Regras cobertas:** MOV-01 a MOV-06, USR-05. Testes: `Movimentacoes.test.tsx` (25: quadro, Nova, chegada, parada, cartão, "rodou N km"), `Despesas.test.tsx` (34, 5 novos de nota), `FichaVeiculo.test.tsx` (18, 3 novos de Movimentar e Transferir), `falso-navegacao.test.ts`, `menu-movimentacoes.test.ts`. Rodados: `src/components/movimentacoes`, `src/components/financeiro`, `src/components/frota`, `src/testes`, `src/lib`; `tsc --noEmit` e `eslint` limpos.

**Para o backend (o OpenAPI gerado não bate com o contrato):**
1. `VeiculoRef` aparece duas vezes e o gerador fica com a de `id` e `placa`; a movimentação devolve também `modelo` e `status` (o serializer tem). A tela usa um tipo próprio (`VeiculoDaMovimentacao`).
2. `Quadro.colunas[].itens` aponta para `Linha`, que é a linha da importação; as linhas do quadro têm `paradas_total` e `resumo` (contrato). `LinhaDaMovimentacao` é derivada da representação.
3. O OpenAPI não tem `busca` nem `levando` em `GET /api/movimentacoes/quadro/` (o contrato só tem `?filial=`); a busca da tela é local.

**Não consegui verificar no navegador:** a pilha giro em `localhost:3000` está com o código da T-288, mas o banco ainda não tem a tabela `movimentacoes_movimentacao` (falta rodar as migrações): o login responde 500 (`relation "movimentacoes_movimentacao" does not exist`). Não rodei `migrate` na pilha. Com as migrações aplicadas, falta conferir as telas em 1440px e 390px (quadro, Nova, parada, chegada, ficha e Despesas).
**Também não rodei os testes do backend** para a linha de `GIRO_MODULOS_ATIVOS`; os testes de menu que não fixam a lista dependem do padrão.

**O que ficou de fora:**
- A parada no desktop é a mesma tela do celular, não a janela de `Movimentacao-Parada-Desktop` sobre o quadro.
- A coluna e o filtro "em movimentação" da Frota (`?em_movimentacao=true`, `movimentacao_aberta`) e a lista de movimentações com período; sem referência de tela.
- Dúvida de texto herdada: `Movimentacao-Nova-*` ainda fala em OS na parada de oficina (já no backlog para o design-system); a Nova segue o contrato (serviço e valor previsto).
- Testes de clique (marcação estática, como nas outras telas): as transições estão testadas no falso.

**Próximo passo para quem recebe:** orquestrador roda as migrações na pilha e abre o PR; backend corrige os três pontos do OpenAPI; QA confere os CA-246 com o gerente e o vistoriador que leva.
