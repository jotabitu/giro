# T-021 · Telas de veículos e clientes · frontend → orquestrador, qa, backend (T-013, T-014)

**O que foi feito (com dados falsos de `docs/api/veiculos.md` e `clientes.md`):**
- Frota (`/veiculos`): busca (placa, modelo, chassi), tipo (todos, motos, carros), chips de situação com a contagem da API, tabela no desktop e cartões no celular, paginação por cursor. Filtros, busca e cursor ficam na URL.
- Ficha do veículo (`/veiculos/[id]`): situação, indicadores (o bloco financeiro some quando a API devolve `indicadores_financeiros: null`), "Agora" com a locação atual, locações, manutenções, dados (campos nulos não aparecem) e documentos com a situação da API.
- Clientes (`/clientes`): KPIs de `indicadores` e `contagens` (`null` aparece como "—"), chips de situação, ordenação (desktop), tabela e cartões, ação principal por linha levando a `rotaDaAcao` (CLI-07), aviso do bloqueio automático (CLI-05).
- Novo cliente (`/clientes/novo`): PF e PJ, só nome, documento e celular obrigatórios (CLI-03), máscaras na digitação (a API recebe só dígitos), análise do cadastro ao lado via `analisar` (CLI-04), consentimento, "Salvar e iniciar locação" (CLI-08) abre `/locacoes/nova?cliente=<id>`. Erro 400 cai no campo; 409 `CLI-01` oferece abrir o cadastro existente.
- Cadastro do cliente (`/clientes/[id]`): pendências em texto, envio dos 4 documentos (câmera no celular), análise. Quem só recebe a resumida vê o resumo. É o destino de "Completar cadastro" e de depois de salvar.
**Onde:** `frontend/src/components/{frota,clientes,lista}/`, `frontend/src/app/(empresa)/{veiculos,clientes}/`, `frontend/src/lib/{frota,clientes,filtros-url,formatos}.ts`, falsos em `lib/api/falso-frota.ts` e `falso-clientes.ts` (tipos em `tipos-frota.ts`, `tipos-clientes.ts`).
**Troca pela API real:** reescrever `veiculos` e `clientes` em `lib/api/index.ts` com o cliente gerado e apagar os `falso-*.ts`. Contas de teste: as da T-020; o falso decide por perfil (vendedor não vê financeiro do veículo, vistoriador vê só o resumo do cliente).
**Contrato:** `docs/api/veiculos.md`, `docs/api/clientes.md`. Regras: VEI-01, CLI-01, CLI-03, CLI-04, CLI-05, CLI-06, CLI-07, CLI-08 (testes: `lib/clientes.test.ts`, com o código da regra no nome).
**Verificação:** lint, typecheck, 62 testes e `next build` verdes. Conferi no portal do Maestri a 390 px (viewport emulado + UA iOS) e 1440 px: sem rolagem horizontal, listas, ficha, formulário, erro de CPF, 409 e criação até a ficha. Captura de tela indisponível (janela do Maestri minimizada), então a fidelidade visual foi conferida por estrutura e medidas, não por imagem: o design-system deve olhar os dois tamanhos.
**Dependências novas:** nenhuma.
**O que ficou de fora:**
- "Cadastrar veículo", "Exportar", "Editar", "Colocar à venda" e demais ações de `acoes` da ficha: não há tela de cadastro nem endpoints nos falsos, e as transições pedem diálogo com motivo (componente `Dialogo` da T-046, ainda fora da main). Entram quando a T-046 chegar.
- Edição dos dados do cliente (PATCH): `/clientes/[id]` só envia documentos e mostra a análise.
- Locações e manutenções da ficha usam tipos mínimos locais (contratos de locações e manutenção ainda não escritos).
- Seleção da categoria da CNH e a caixa de consentimento são `<select>` e `<input type="checkbox">` nativos com as classes do tema: falta `Select` e `Checkbox` no design system (pedido ao design-system). O chip de filtro está em `components/lista/FiltroChips.tsx` até existir no design system.
- Rotas ainda inexistentes: `/locacoes/nova`, `/locacoes/[id]`, `/vendas/[id]`, `/financeiro/receber` (telas das T-022 e T-023).
- Texto "N novos no mês passado" em vez do nome do mês: a API manda só o número.
**Próximo passo para quem recebe:** backend (T-013, T-014) confere se `contagens`, `indicadores` e `acao_principal` batem com o uso; design-system revisa a fidelidade e decide `Select`, `Checkbox` e `FiltroChips`; qa pode usar as contas falsas até a API sair.
