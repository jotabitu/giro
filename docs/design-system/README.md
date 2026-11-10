Base visual do sistema de gestão de venda e locação de motos e automóveis, vendido em modelo white label: a estrutura é fixa e neutra, e cada empresa cliente aplica apenas a própria cor, logotipo e nome.

## White label

- Cada cliente troca somente `brand`, `brand-soft` e `on-brand`, além do logotipo no slot da sidebar e do nome fantasia. Todos os outros tokens são iguais para todos os clientes.
- `brand` é sempre preenchimento, nunca texto ou borda sobre `surface`: aparece no botão de destaque, no chip de atalho da busca, no segmento destacado da barra de frota, no contador do item de menu ativo e nos marcadores do card de alertas.
- Ao cadastrar a cor do cliente, calcule `on-brand` pelo contraste: `ink` se a cor for clara, `#ffffff` se for escura (mínimo 4,5:1). `brand-soft` é a mesma cor clareada para cerca de 85% de branco no tema claro e escurecida no tema escuro.
- Como `brand` pode ser qualquer cor, nenhum significado depende dela. Status usam os tokens semânticos (`success`, `info`, `warning`, `critical`) e sempre trazem texto.
- A cor padrão, para demonstração e clientes sem identidade, é o verde-limão `#c8f04a`.

## Tom e escrita

- Português do Brasil, frases curtas e diretas, tratamento por "você".
- Primeira letra maiúscula e o resto minúsculo em botões, títulos e menus: "Nova locação", "Contas a receber".
- Números sempre formatados: `R$ 1.250,00`, `12.430 km`, `71%`, datas `06/10/2026` em formulários e `06 out` em listas.
- Placas, códigos de contrato (`LOC-2841`), chassi e atalhos em `data` (Geist Mono).
- Títulos de alerta dizem o número e a ação: "7 contratos precisam de ação hoje", nunca "Atenção!".
- Sem emoji e sem pontos de exclamação.

## Cor

- Página em `canvas`; todo conteúdo fica em painéis `surface`; blocos internos em `surface-sunken`. Essa escada de três tons substitui sombras e bordas.
- Texto em `ink`; metadados, rótulos e cabeçalhos de tabela em `ink-muted`.
- `solid` (preto no tema claro, quase branco no escuro) marca o que está ativo ou é principal: botão primário, item de menu atual, segmento escolhido, primeiro KPI, card de alertas. Texto sobre ele em `on-solid` e `on-solid-muted`.
- Status do veículo: Disponível `success`, Reservado `info`, Alugado `solid`, Em manutenção `warning`, Em preparação e Vendido neutros, Atrasado `critical`. Prioridade Alta é a pílula sólida `critical`.

## Tipografia

- Uma família, Geist (Google Fonts), para tudo; Geist Mono só para o estilo `data`.
- `display` uma vez por tela (saudação ou título da página), `title` nos painéis, `heading` em blocos internos, `metric` nos números de KPI, `body` no resto, `caption` em `ink-muted` para metadados, `overline` nos grupos do menu.
- Pesos: 400 para texto, 500 para ênfase e botões, 600 para títulos e números.

## Forma, espaço e camadas

- Tudo é arredondado: painéis `radius-xl` (32px), blocos internos `radius-lg` (24px), campos e barras `radius-md` (14px), e botões, menus, status e busca em `radius-pill`.
- Painéis têm padding `space-6` e ficam a `space-6` uns dos outros; blocos dentro de um painel ficam a `space-3`.
- **Escala de espaços (T-445).** A grade é de 4px, com meios-passos de 2px. O número do passo é o tamanho em px dividido por 4: `0.5` = 2px, `1` = 4px, `1.5` = 6px, `2` = 8px, `2.5` = 10px, `3` = 12px, `3.5` = 14px, `4` = 16px, `5` = 20px, `6` = 24px, `7` = 28px, `8` = 32px, `9` = 36px, `10` = 40px, `11` = 44px, `12` = 48px. Os meios-passos (`0.5`, `1.5`, `2.5`, `3.5`) são para respiros pequenos que as telas de referência usam (6px entre rótulo e campo, 10px entre ícone e texto); prefira o passo inteiro quando a referência não pedir o meio. `7`, `9`, `11` e `12` são para lado de controle e alvo de toque (`size-11` = 44px). `40`, `60` e `64` (160, 240 e 256px) valem só para largura e altura de bloco, nunca para espaço entre elementos. Em CSS, o ponto vira hífen: `--space-1-5`.
- O Tailwind do app usa esta escala **no lugar** da dele (`tailwind.config.ts`): classe fora da escala (`gap-13`, `mt-15`) não gera CSS e o espaço fica zero, sem erro. O teste `src/design-system/escala.test.ts` recusa essas classes; medida pontual fora da escala se escreve com valor arbitrário (`mt-[18px]`) e precisa de motivo no PR. A fonte da escala é `tokens.json`; depois de mudar, rode `node scripts/gerar-tokens.mjs` em `frontend/` e copie os valores para `wl-theme.css`.
- Sem sombras em painéis. `shadow-pop` só em menus, popovers e modais.
- Layout de tela: sidebar de 280px à esquerda; à direita, cabeçalho com `display`, busca, notificações e ação principal; abaixo, grade de painéis com o mais importante à esquerda e o card de alertas à direita.

## Interação e acessibilidade

- Foco de teclado: anel de 2px em `focus` com 2px de afastamento em todo elemento interativo.
- Alvos de toque de no mínimo 40px; botões principais têm 48px (56px no cabeçalho).
- Todo texto atinge 4,5:1 sobre o fundo indicado na nota do token, nos dois temas.
- Status e alertas nunca dependem só da cor: sempre há palavra, número ou ícone.
- A vistoria (check-out e check-in) é pensada primeiro para celular, em uma coluna, com botões de largura total.

## Iconografia

- Ícones de traço de 20px, linha de 1,75px, pontas arredondadas, cor herdada do texto (`currentColor`).
- Biblioteca recomendada para o produto: Lucide (licença ISC), que segue esse mesmo desenho. Os ícones das prévias são desenhos simples feitos para este sistema, só para referência; troque pelos equivalentes do Lucide na implementação.
- Ícone sempre acompanha texto, exceto em botões de ícone com `aria-label`.

## Componentes

Em React: `frontend/src/design-system/` (preview em `/design-system`). As classes ficam em `components/bundle.css` com prefixo `wl-` e não dependem de JavaScript: Button, StatusBadge, Sidebar, SegmentedControl, KpiTile, DataTable, FleetBar, SearchField, TextField, AlertCard e VehicleCard. Cada um tem uma prévia e um guia de uso.
