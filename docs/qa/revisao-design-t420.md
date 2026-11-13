# Revisão de fidelidade visual: T-420 (PR #567)

Revisão do design-system das telas da T-420 contra as referências do #553. Feita pela leitura do código (`gh pr diff 567`) e do HTML das telas. **Sem captura da página rodando**: o que depende de dado da API está marcado "confirmar na captura".

Gravidade: **bloqueia** (impede o merge de `develop` em `main`), **ajuste** (corrigir na próxima tarefa de frontend), **detalhe** (pode esperar).

**Resultado geral: nenhum item bloqueia.** Estrutura, ordem, textos e tokens seguem as referências. Os itens abaixo são diferenças de componente, de conteúdo e de estado vazio.

## Preços: Planos de compra (`PlanosDeCompra.tsx`)

| # | Gravidade | Divergência | Correção sugerida |
| --- | --- | --- | --- |
| P1 | ajuste | A referência é uma tabela (`wl-table`: Plano, Periodicidade, Parcelas, Valor da parcela, Última parcela, Locações, Editar). O código monta linhas `flex` soltas, sem cabeçalho de coluna, e os campos não se alinham de uma linha para a outra. | Usar o `DataTable` do design system com as 7 colunas da referência, com `overflow-x-auto` no celular. |
| P2 | ajuste | A categoria aparece como `<small>` solto. A referência usa `CelulaDupla` (nome do plano e categoria embaixo). A "Última parcela" também usa célula dupla: valor em mono e "com a caução de R$ 300,00 abatida" embaixo. O código junta tudo numa frase só. | `CelulaDupla` nas colunas Plano e Última parcela. |
| P3 | detalhe | "Mensal · 24 parcelas" vira um texto só. A referência separa Periodicidade e Parcelas (mono). | Resolvido pela P1. |
| P4 | detalhe | "Desativado" (`StatusBadge`) e o link "Mostrar planos desativados" não existem na referência. Servem à regra, então ficam, mas o link está como `<button>` cru com `underline`. | Usar `Button` na variante `quieto` compacto, ou registrar o controle como padrão na tela de referência. |
| P5 | detalhe | A referência não tem estado de carregando nem vazio. O código tem os dois, com texto correto. | Nada a fazer. |

## Nova locação: tipo e plano de compra (`NovaLocacao.tsx`)

Ordem dos painéis (Tipo de locação, Cliente e veículo, Plano de compra, Cobrança, Resumo), textos de Cobrança, aviso dos 15 dias, Caução "Abatida na última parcela" e "Próximas parcelas" conferem com `Locacao-Compra-*`.

| # | Gravidade | Divergência | Correção sugerida |
| --- | --- | --- | --- |
| N1 | ajuste | O Resumo mostra as linhas que vêm de `sim.linhas` mais a linha fixa "Valor por mês". A referência tem `24 parcelas × R$ 1.190,00`, `Última parcela (caução abatida)`, `Caução (abatida na última parcela)` e só depois "Valor por mês". Se a API não mandar esses rótulos, o resumo fica diferente. | Confirmar na captura. Se faltar, o backend manda os rótulos de compra em `linhas`. A tela continua só exibindo. |
| N2 | ajuste | "Tipo de locação" reaproveita o componente `Plano` (cartão de escolha). Na referência são dois segmentos. Funciona, mas o rótulo longo "Com intenção de compra" pode quebrar linha no celular. | Usar `SegmentedControl`, ou conferir a quebra a 390 px. |
| N3 | detalhe | A descrição do plano mostra `p.periodicidade` cru ("mensal"). Hoje o valor da API já é minúsculo, então sai certo. | Usar `ROTULO_DA_PERIODICIDADE[...].toLowerCase()`, como no detalhe, para não depender do formato da API. |
| N4 | detalhe | "Retirada" e "Fim previsto" ficam dentro do painel "Plano de compra", como na referência. Fim previsto sai como `datetime-local` somente leitura. A referência mostra só a data. | Mostrar a data (mono) e manter a dica. |

## Detalhe da locação com compra (`CompraDaLocacao.tsx`, `DetalheDaLocacao.tsx`, `AcoesDaLocacao.tsx`)

| # | Gravidade | Divergência | Correção sugerida |
| --- | --- | --- | --- |
| D1 | ajuste | Na referência da locação **ativa**, a etiqueta "5 de 24 parcelas pagas" aparece só em Pagamentos. O código também a põe no cabeçalho de Andamento da compra, duplicada. Na **quitada** a referência repete nos dois, então ali está certo. | Mostrar a etiqueta em Andamento só quando `quitada_em`. |
| D2 | ajuste | A referência mostra a **última parcela** com "A vencer · caução abatida" e, na quitada, "Pago · Pix · caução abatida". `seloDaParcela` só trata a parcela de tipo caução. | A API manda a observação na última parcela e o `seloDaParcela` a anexa. Confirmar na captura. |
| D3 | ajuste | Na referência, Renovar e Trocar veículo continuam na barra, desligados, com a explicação embaixo ("A locação com intenção de compra não se renova." e "não troca de veículo. Encerre esta e abra outra."). O código esconde os botões sem explicar. | Mostrar o motivo da recusa que a API devolve em `acoes`, com texto de apoio sob os botões. Se a API não mandar o texto, registrar como ponto para o backend. |
| D4 | ajuste | Linha "Veículo" no Resumo da compra. Não está na referência (ativa nem quitada), e o veículo já aparece no topo. | Remover a linha. |
| D5 | ajuste | A mensagem "Parcela 6 atrasada há 16 dias. O cliente está bloqueado." sai de `l.situacao.rotulo`, que pode ter outro texto. | Confirmar na captura. O texto de bloqueio tem que vir pronto da API. |
| D6 | detalhe | Diálogo "Encerrar por atraso": a referência traz Motivo preenchido ("Parcela 6 com 16 dias de atraso"), Data editável e a nota com ícone de informação. O código deixa Motivo vazio, Data somente leitura e a nota como descrição do diálogo. O título leva o código: "Encerrar a LOC-2870 por atraso". | Preencher o Motivo sugerido pelo atraso (vindo da API). Data editável, se a regra permitir. A nota pode ficar na descrição. |
| D7 | detalhe | Quitada: o cabeçalho do veículo deve mostrar "RTA-2C55 · vendido". O código não mudou esse bloco. | Confirmar na captura. Se mostrar "Disponível" ou "Locada", é bug de dado. |

## Vendas (`ListaDeVendas.tsx`)

O código declara o recorte (só o que a API entrega; funil e propostas ficam na T-418). Dentro dele:

| # | Gravidade | Divergência | Correção sugerida |
| --- | --- | --- | --- |
| V1 | ajuste | A tabela "Transferências pendentes" confere (Cliente, Veículo, Origem, Situação, "Abrir locação"). Na lista de "Vendas" a coluna Situação mostra o estado da transferência. Na referência, a Situação das vendas é "Vendida 06 out", e a transferência fica no painel próprio. | Situação = "Vendida <data>", com o selo de transferência pendente só quando pendente. |
| V2 | detalhe | O cabeçalho tem subtítulo próprio ("Transferências no Detran e vendas da empresa."). A referência tem "Outubro · Filial Centro" e o botão "Nova venda". | Alinhar o subtítulo ao padrão (mês e filial). "Nova venda" entra com a T-418. |
| V3 | detalhe | No celular, `CartaoDaVenda` monta um cartão próprio com `bg-surface-sunken`, enquanto as outras listas de celular usam `LinhaDeLista`. | Usar `LinhaDeLista`, se couber. Conferir `Vendas-Mobile`. |
| V4 | detalhe | A coluna Valor sai sem `wl-mono`, ao contrário das outras tabelas de valor. | `wl-mono` na célula. |

## Painel do gerente: pendências (`InicioGerente.tsx`)

`Gerente-Desktop` e `Gerente-Mobile` **não têm** esse bloco: a T-420 o põe por decisão da tarefa. O padrão vem do `InicioGeral` do administrador.

| # | Gravidade | Divergência | Correção sugerida |
| --- | --- | --- | --- |
| G1 | ajuste | O `AlertCard` aparece sempre, até sem pendência ("Nenhuma pendência hoje", sem itens nem botão). Num painel que não tinha esse bloco, vira um cartão vazio ocupando a largura toda entre Aprovações e KPIs. | Só renderizar quando `pendencias.length > 0`. |
| G2 | detalhe | No administrador o `AlertCard` fica na coluna lateral de 360 px. No gerente ocupa a largura toda. | Aceitável. Registrar a posição na tela do gerente (carimbo de ajuste, `docs/agentes/telas-do-canvas.md`) para a referência não ficar defasada. |
| G3 | detalhe | O botão "Ver pendências" leva ao destino do primeiro item. Com itens de destinos diferentes, leva só ao primeiro. | Aceitável por ora. |

## Pendências do design system

- Atualizar `Gerente-Desktop` e `Gerente-Mobile` com o bloco de pendências (G2), pelo carimbo de ajuste. Faço num PR curto, se o orquestrador autorizar.
- Capturas pedidas ao QA para fechar os itens "confirmar": N1, D2, D5 e D7, a 1440 px e a 390 px.
