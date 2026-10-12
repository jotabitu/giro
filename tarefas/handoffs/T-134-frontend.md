# T-134 · Painel, marca e ficha do cliente na API nova · frontend → orquestrador, design-system, qa, produto

**O que foi feito:**
- **Marca** (`GET /api/marca/`): nova `src/lib/api/marca.ts` (pública, sem token; 404 do host sem empresa vira `null`), `useMarcaDaEmpresa` (`src/lib/marca-empresa.ts`) com consulta `["marca"]` de 5 min. As três variáveis (`--brand`, `--on-brand`, `--brand-soft`, e `cor_suave_escuro` no tema escuro) são as que a API mandou, validadas como `#RRGGBB` (`src/lib/marca.ts`); nenhuma conta de contraste, mistura ou iniciais no frontend. Usada no login, convite, esqueci/redefinir a senha (`CabecalhoMarca`) e na casca (sidebar, cabeçalho do celular, Mais). Logo sempre em `<img>`; sem logo, as `iniciais` da API. Sem marca ou com falha: "Sua locadora", sem logo, cores padrão.
- **Painel**: início e contadores já usavam a API real; `tipos-painel.ts` agora vem do `schema.d.ts` (com os valores fechados em cima, como em `tipos-locacoes.ts`). Dois achados do tipo gerado: `gravidade` da pendência é `critica | alerta | info` (o tipo à mão dizia `atencao`, então o "alerta" nunca ganhava a marcação no AlertCard; agora mapeia para `atencao`) e `caixas_do_dia` pode vir `null` (o bloco some). `tomDoStatus` do painel passou a ser o de `lib/tom`.
- **Ficha do cliente**: `locacoes()` faz só `GET /api/locacoes/?cliente=`; `pago_centavos` é o `pagamento.pago_centavos` da linha e o ícone vem de `veiculo.tipo`. Saiu `pago_detalhe` (a coluna Pago mostra só o valor), saiu a soma da caução de todas as locações e saiu a seção Histórico (e `clientes.historico`). O total pago e o em aberto continuam de `financeiro` do cliente.
- **Ficha do veículo**: a seção Manutenções (desktop e celular) só aparece com `manutencoes` no `eu.navegacao.menu_completo` (`temNoMenu`); sem ela, nem a consulta é feita.

**Onde:** `frontend/src/lib/{marca,marca-empresa,painel,menu}.ts`, `src/lib/api/{marca,clientes,tipos,tipos-clientes,tipos-painel,index,relatorios}.ts`, `src/components/{acesso/CabecalhoMarca,casca/CascaDoApp,clientes/DetalheDoCliente,frota/FichaVeiculo,inicio/InicioGeral,inicio/InicioFinanceiro}.tsx`, fixtures em `src/testes/` (`falso.ts`, `falso-clientes.ts`, `falso-painel.ts`, `api-falsa.ts`).

**Regras:** USR-05, USR-07, USR-08, FIN-13, VEI-06 (só exibição); S-12 (logo em `<img>`).

**Testes:** `src/lib/marca.test.ts` (5: cores da API sem recalcular, tema escuro, cor inválida não injeta CSS, marca neutra), `InicioFinanceiro.test.tsx` (2: `caixas_do_dia` null e KPI `valor: null` somem), ficha do veículo sem Manutenções fora do menu, ficha do cliente sem Histórico e com o pago da linha (LOC-2836 = R$ 658,00). `api:gerar` (sem mudança no `schema.d.ts`), `tsc`, `eslint` e 282 testes passando.

**Acréscimo (início com bloco `null`, tira o D-02 da T-137):** o início do financeiro quebrava com `Cannot read properties of null (reading 'length')` quando `para_hoje` ou `caixas_do_dia` vinham `null`. Agora os dois caem no estado vazio ("Nada para pagar ou devolver hoje.", "Nenhum caixa aberto hoje."), com "Entra hoje" e "Em atraso" intactos (USR-08). Revisei as outras cinco variantes (geral, gerente, vendedor, vistoriador, implantacao): listas e blocos que podiam vir `null` ganharam padrão vazio, e KPI `null` ou lista de KPIs `null` não renderiza. Testes: `InicioFinanceiro.test.tsx` (fixture com `null`) e `InicioNulos.test.tsx` (as cinco variantes com todos os blocos `null`). 288 testes, tsc e eslint limpos.

**Pontos para conferir:**
1. **Locação atual na ficha do cliente:** preço do período, parcelas pagas/total e caução em garantia não vêm da linha da lista; leio o detalhe de **uma** locação (a em andamento), sem somar nada. Se a API passar a mandar isso no cliente (`locacao_atual`), tiro a chamada. O KPI "Caução em garantia" usa só a locação atual. `com_atraso` ainda conta os `sinais` da lista no cliente; se virar número da API, trocar.
2. **design-system:** mudei `objectFit` do logo da `Sidebar` de `cover` para `contain` (o logo da API pode ser largo, 120x36, e o slot é 40x40). O mesmo nos outros dois slots da casca. Avisar o design-system para refletir no componente de referência. `aplicarMarca`/`cssDaMarca` (com a conta de cores) seguem no design system só para a página de catálogo; a app não os usa mais.
3. **Entrada do suporte:** não existe tela dessa rota no frontend ainda; quando existir, usa o mesmo `CabecalhoMarca`.
4. **Marca no servidor:** a consulta é no cliente, então há um instante com "Sua locadora" e a cor padrão antes da resposta. Ler no servidor do Next (layout) elimina isso; fica como melhoria se incomodar.

**NÃO conferi:** no navegador nem no compose (login do compose segue bloqueado, T-127); a marca foi testada nas funções puras e nos tipos, não renderizada com a cor da Moto Rápida real.

**Próximo passo:** orquestrador abre o PR. Design-system: item 2. QA: com o seed, conferir a ficha da Juliana (LOC-2836 pago R$ 658,00) e o menu sem Manutenções.
