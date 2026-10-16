# T-242 · Ficha do veículo igual à referência · frontend → arquiteto, design-system, qa

**O que foi feito** (`frontend/src/components/frota/FichaVeiculo.tsx`, sobre a T-267):
- **Desktop:** cabeçalho com Editar, **Movimentar** (novo, desativado), Mandar para oficina e Colocar à venda; KPIs; bloco **Agora** (selo "<situação> desde 23 set", cliente com iniciais, contrato, período, alerta da locação e "Ver locação", mais a **Próxima manutenção** com serviço e km); Locações; Manutenções; coluna Dados (agora com **Categoria** e **Preço de hoje**, antes "Plano padrão") e Documentos. Saiu o painel de foto em espaço reservado, que a referência não tem.
- **Celular:** mesma ordem da referência: cabeçalho, indicadores, Agora, **Próxima manutenção** (novo), Documentos, Manutenções e os botões; saiu a foto de espaço reservado.
- Tudo o que aparece vem da API; nada é calculado na tela. Os cartões financeiros seguem só a chave `indicadores_financeiros` (T-156).
- O falso da API (`falso-frota.ts`) passou para o estado do QXA-4B21 das regras: LOC-2841 de 23 set a 28 out, chassi ...4401, óleo aos 18.900 km, km atualizado em 23 set, LOC-2702 até 22 set; e o QXA não está mais "atrasado". Testes da ficha atualizados e dois novos trechos (ausência de "faltam", "Cobrar", Movimentações, foto). `tsc`, `eslint` e os 500 testes passam.
- Conferido no navegador (Next do worktree na porta 3100, API real, `rodrigo`, veículo ADJ-4T71): desktop 1440px e celular 390px.

**Pedidos ao Arquiteto (a referência mostra, a API não manda; a tela não inventa):**
1. **Locação atual** (`locacao_atual`): plano e preço ("Semanal R$ 299,40") e a situação dos pagamentos ("Parcela 2 atrasada · R$ 299,40"; hoje só há `alerta` livre da locação). Sem isso não há o botão "Cobrar" nem a linha Pagamentos.
2. **Próxima manutenção:** `faltam_km` (ou o intervalo e o km da última), uso médio ("cerca de 6 dias"), o serviço seguinte ("revisão 20 mil, a 1.050 km") e o gatilho da OS agendada (MAN-03, 500 km). A barra de progresso e o "faltam 950 km" dependem disso.
3. **Fotos e avarias** (vistoria de saída da locação atual): as seis fotos, "ver as 12 fotos", as avarias (descrição, lado, data, "já existia, não cobrar") e o vistoriador. O bloco inteiro está fora da ficha por falta de contrato.
4. **Movimentações** do veículo (MOV-01 a MOV-06, T-246): lista, "ver todas" e o motivo de o botão Movimentar estar desativado ("Veículo alugado não se movimenta."). Hoje o botão fica desativado com "Ainda não está disponível" e o bloco não aparece. Falta também uma flag em `acoes` (ex.: `movimentar`).
5. **Manutenções antigas** e **locações:** o total "14 no total" e a lista seguem a API; os valores da referência (pastilha, revisão 15 mil) são exemplo.
6. **Rendeu no ano, Ocupação, Custo de manutenção** e **Documentos** (CRLV, IPVA, seguro, rastreador), **Renavam**, **Compra** e **FIPE**: a ficha mostra o que a API devolve; o seed não os traz para todos os veículos (ex.: o ADJ-4T71 mostra R$ 0 e "Nenhum documento cadastrado").

**Divergência de texto:** o selo vem da `situacao.rotulo` da API ("Alugado"); a referência diz "Alugada" (moto, feminino). Fica "Alugado desde 23 set" até o produto decidir se o rótulo concorda com o gênero.

**O que ficou de fora:** os blocos dos pedidos 1 a 4 (sem contrato na API) e a revisão visual lado a lado do design-system.

**Próximo passo:** Arquiteto responde os pedidos; design-system revisa lado a lado. A T-243 (editar veículo) depende desta ficha.
