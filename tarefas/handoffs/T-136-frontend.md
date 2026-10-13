# T-136 · Permissões por perfil nas rotas (frontend) · frontend → seguranca, qa

**O que foi feito:**

- **Guarda de rota (D-26, `USR-09`):** `rotaPermitida(eu, rota)` em `frontend/src/lib/menu.ts` e `GuardaDeRota` na casca (`CascaDoApp.tsx`). Toda rota que o menu do perfil (menu do início e menu completo) não mostra responde "Seu perfil não tem acesso a esta página.", sem montar a tela nem chamar a API dela. `/inicio` e `/mais` abrem para todos. Telas que o menu não lista seguem a permissão:
  - `/locacoes/nova`: `locacoes_criar` e Locações no menu.
  - `/locacoes/[id]/vistoria` e `/devolucao`: `vistorias_fazer`.
  - `/locacoes/[id]` (ficha): Locações, Contas a receber, Clientes ou Avarias no menu (o financeiro chega pela ficha do cliente, o vistoriador pela lista de avarias; a API decide o que cada um lê).
  - `/clientes/novo`: `clientes_cadastrar`. `/veiculos/novo`: `veiculos === "editar"`.
- **Menu do início nas rotas dos itens (T-141, `USR-05`):** `gruposDaRota` usa o `menu_inicio` em `/inicio` e em toda rota que um item dele abre (só o caminho, com sub-rotas). João em `/vistorias` e em `/vistorias/avarias` vê o menu do início, com "Vistorias de hoje" ativo. Lúcia em `/financeiro/receber` mantém o menu do perfil e em `/clientes` vê o completo.
- **Veículos (D-25):** `preco_vigente`, `valor_venda_centavos`, `referencia_fipe_centavos`, `valor_compra_centavos`, `data_compra` e `indicadores_financeiros` são opcionais no tipo. A Frota esconde a coluna e o campo "Diária" quando nenhum veículo traz o preço; a ficha esconde Compra, Valor de venda, À venda por e Plano padrão. Rendimento e custo já sumiam por `indicadores_financeiros` ausente, e Manutenções some porque o menu do João não tem `manutencoes`. As categorias do cadastro continuam exigindo preço (quem cadastra tem o preço).
- **Clientes (D-28, D-29):** vistoriador recebe 403 e a rota mostra o aviso; a ficha da locação deixa o nome do cliente sem link quando a ficha dá 403. Nova `FichaDoFinanceiro` (`components/clientes/FichaDoFinanceiro.tsx`), usada quando `eu.perfil === "financeiro"` e a ficha vem sem `documentos`: cabeçalho com situação e WhatsApp, bloqueio com o motivo, Total pago e Em aberto, Parcelas atrasadas (`GET /api/financeiro/contas-receber/?cliente=&situacao=atrasadas`, com os dias e o valor do dia), Locações, Contato (celular e e-mail), Pagamentos (`situacao=pagas`) e **Cobrar** como única ação, só com `acao_principal.codigo === "cobrar"`. Sem documentos, endereço, CNH nem análise. Outros perfis com a resumida (suporte) continuam vendo o aviso de resumo.
- **Vistoria (`CLI-02`, `CLI-03`):** o bloco do cliente mostra Celular e "Retirada: Liberada / Não liberada" (some na devolução, onde `retirada_liberada` é `null`). O motivo continua nas pendências.
- **Falsos (mesmo comportamento do backend):** navegação (vistoriador com um menu só, rótulo do início por perfil, `locacoes` só com `locacoes_criar`, `veiculos` na barra com `consultar_veiculo`), clientes (403 do vistoriador; ficha do financeiro), frota (vistoriador sem valores e categorias sem preço), contas a receber com filtro `cliente`. Os ids de cliente do falso financeiro passaram a bater com os do falso de clientes (Rafael 1203, Carlos 1202, Lucas 1206).

**Onde:** `frontend/src/lib/menu.ts`, `components/casca/CascaDoApp.tsx`, `components/clientes/FichaDoFinanceiro.tsx` e `DetalheDoCliente.tsx`, `components/frota/ListaVeiculos.tsx` e `FichaVeiculo.tsx`, `components/vistorias/VistoriaDeSaida.tsx`, `components/locacoes/DetalheDaLocacao.tsx`, `lib/api/tipos-frota.ts`, `tipos-clientes.ts`, `veiculos.ts`, `lib/frota.ts` e os falsos em `src/testes/falsos/`.

**Contrato:** nenhum endpoint novo. O OpenAPI não mudou nesta tarefa (`api:gerar` e `typecheck` rodados mesmo assim).

**Regras cobertas:** `USR-05`, `USR-09`, `CLI-02`, `CLI-03`, `CLI-07` (Cobrar). Testes:

- `menu.test.ts`: `usr_05` (menu do início nas rotas dos itens, Lúcia, João, barra do João) e `usr_09` (`rotaPermitida` por perfil).
- `GuardaDeRota.test.tsx`: `usr_09` e `usr_05` (João, financeiro e administrador, rotas que abrem e rotas com o aviso).
- `DetalheDoCliente.test.tsx`: `usr_09` (403 do João; ficha do financeiro com Rafael, e Juliana sem Cobrar).
- `FichaVeiculo.test.tsx` e `ListaVeiculos.test.tsx`: `usr_09` (João sem Diária, sem valores, sem Manutenções).
- `VistoriaDeSaida.test.tsx`: `usr_09` (nome, celular, CNH e retirada liberada).
- `falso-navegacao.test.ts` ajustado ao menu do vistoriador.

**Verificação:** `npm run api:gerar`, `npm run lint`, `npm run typecheck` e a suíte do frontend (359 testes) passam. Não conferi no compose com a API real nem em 1440px e 390px no navegador: a conferência visual da `FichaDoFinanceiro` (não há tela de referência para ela) fica para o qa e o design-system.

**O que ficou de fora:**

- A `FichaDoFinanceiro` não tem tela HTML de referência (a conferência pediu o conteúdo, não o desenho); usei Panel, KpiTile e DataTable do design system. Se o design-system quiser uma tela, é só trocar a composição.
- Mapa rota → permissão está em `rotaPermitida`, à mão, para as telas fora do menu. Tela nova fora do menu precisa de linha lá (senão cai no menu e, não estando nele, mostra o aviso).
- "Marcar reembolso como feito" do financeiro (D-27) não existe como tela ainda (`/financeiro/reembolsos` só aparece como destino do painel); a ação de receber na ficha da locação já vem de `acoes`.
- A lista de manutenções da ficha do veículo (custo por serviço) ainda usa o falso; quando o contrato de manutenção existir, o vistoriador não deve ver o custo.

**Próximo passo para quem recebe:**

- **seguranca:** revisar o guarda de rota (`rotaPermitida`) e a exceção de `/locacoes/[id]` para o financeiro e o vistoriador; lembrar que o guarda é conforto, quem protege é o 403 da API.
- **qa:** no compose, com João e Paula (financeiro, a conta de teste se chama Paula Ribeiro no falso), conferir D-25 a D-29: João em `/clientes` e em `/financeiro/receber` vê o aviso; João na Frota sem Diária; Paula na ficha do Rafael com Cobrar, parcelas atrasadas e pagamentos; vistoria de saída com celular e retirada.
- **design-system:** olhar a `FichaDoFinanceiro` nos dois tamanhos.
- **orquestrador:** abrir o PR da branch `t-136-frontend-perfis`.
