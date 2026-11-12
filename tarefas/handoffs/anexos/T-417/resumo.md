# Capturas da T-417

Backend da branch (avulso, banco próprio, seed de 07 out 2026) e Next do worktree. Não há tela de referência para a seção "Despesas do veículo": ela usa o painel da ficha e as linhas da tela `Despesas`.

| Imagem | O que mostra |
| --- | --- |
| [Veiculo-despesas-gerente-1440.png](Veiculo-despesas-gerente-1440.png) · [390](Veiculo-despesas-gerente-390.png) | Rodrigo no QXA-4B21: seção com o ano, "Despesas no ano R$ 48,00", o óleo e "Lançar despesa"; custo de manutenção R$ 48 (CA-417-07) |
| [Veiculo-despesas-vendedor-1440.png](Veiculo-despesas-vendedor-1440.png) · [390](Veiculo-despesas-vendedor-390.png) | Bruna: só o botão, sem a lista e sem os indicadores (CA-417-09, CA-417-12) |
| [Veiculo-lancar-despesa-1440.png](Veiculo-lancar-despesa-1440.png) · [390](Veiculo-lancar-despesa-390.png) | Lançamento pela ficha, com o veículo travado (CA-417-10) |
| [Despesas-filtro-veiculo-1440.png](Despesas-filtro-veiculo-1440.png) · [390](Despesas-filtro-veiculo-390.png) | Filtro "Veículo" na tela `Despesas` (CA-417-06) |
| [Despesas-filtro-veiculo-escolhido-1440.png](Despesas-filtro-veiculo-escolhido-1440.png) · [390](Despesas-filtro-veiculo-escolhido-390.png) | Filtro com o PMZ-3E17 escolhido: só os pneus, indicadores iguais (CA-417-06) |
| [Veiculo-categorias-grupos-1440.png](Veiculo-categorias-grupos-1440.png) · [390](Veiculo-categorias-grupos-390.png) | Categorias em dois grupos (CA-417-01). A lista nativa aberta não sai em captura sem cabeça: o select ganhou `size` só para a captura, e mostra os grupos e as opções como a lista mostra |
| [Veiculo-categorias-grupos-escuro-1440.png](Veiculo-categorias-grupos-escuro-1440.png) · [390](Veiculo-categorias-grupos-escuro-390.png) | O mesmo com `prefers-color-scheme: dark`: o app não troca de tema pela preferência do sistema, então a captura sai igual à clara |

Ajuste do design-system (comentário no #492): o "Lançar despesa" da seção usa a variante `quieto` do `Button` (`wl-btn--quiet`, fundo sunken), a mesma do "Ver o histórico"; as capturas da ficha foram refeitas com ele.
