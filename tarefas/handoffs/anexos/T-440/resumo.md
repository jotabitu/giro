# Capturas da T-440

Backend avulso da branch (banco próprio, seed de conferência de 07 out 2026) e Next do worktree, com a Mariana (administradora). Referência: `Onboarding-Importar-Desktop` e `-Mobile` (PR #495). A planilha da conferência é fictícia: 86 linhas nos 7 modelos do seed, sem as colunas filial e categoria, com placas novas (o seed já tem a frota) e os 3 erros do CA-027-03. O seed de conferência já tem 86 veículos, então aparece a nota do limite do plano ("O plano comporta mais 64 veículos"), que é da `IMP-03` e não muda.

| Imagem | O que mostra |
| --- | --- |
| [Importar-uma-filial-1440.png](Importar-uma-filial-1440.png) · [390](Importar-uma-filial-390.png) | Antes do envio, com só a Filial Centro: "Os veículos entram na Filial Centro.", sem pergunta. O apoio da caixa perdeu "e categoria" (CA-440-01, 03) |
| [Importar-categoria-de-cada-modelo-1440.png](Importar-categoria-de-cada-modelo-1440.png) · [390](Importar-categoria-de-cada-modelo-390.png) | Depois da conferência (83 prontos, 3 com erro): "Categoria de cada modelo" com os 7 modelos e quantos prontos cada um tem, 3 já escolhidos, "3 de 7 modelos com categoria", "Escolha a categoria de cada modelo." e "Importar os 83" travado (CA-440-05) |
| [Importar-corrigir-aqui-1440.png](Importar-corrigir-aqui-1440.png) · [390](Importar-corrigir-aqui-390.png) | "Corrigir aqui" com "Categoria desta linha": "Segue o modelo: Urbana 110–125" e a dica da exceção (CA-440-09) |
| [Importar-todos-com-categoria-1440.png](Importar-todos-com-categoria-1440.png) · [390](Importar-todos-com-categoria-390.png) | Os 7 modelos com categoria: "7 de 7 modelos com categoria" e "Importar os 83" liberado (CA-440-06) |
| [Importar-mais-de-uma-filial-1440.png](Importar-mais-de-uma-filial-1440.png) · [390](Importar-mais-de-uma-filial-390.png) | Com a Filial Messejana criada: "Filial dos veículos", sem nenhuma marcada, e a dica "Todos os veículos da planilha entram nela..." (CA-440-04) |
| [Importar-filial-sem-escolha-1440.png](Importar-filial-sem-escolha-1440.png) · [390](Importar-filial-sem-escolha-390.png) | Planilha enviada sem escolher a filial: a API recusa e o campo mostra "Escolha a filial dos veículos." (CA-440-04) |
| [Importar-sem-categoria-1440.png](Importar-sem-categoria-1440.png) · [390](Importar-sem-categoria-390.png) | Com todas as categorias inativas: "Cadastre os preços antes de importar veículos.", "Ir para a tabela de preços", sem a área de envio de veículos; a de clientes continua (CA-440-12) |

O estado de duas filiais e o de sem categoria foram montados só no banco da conferência (Filial Messejana criada e categorias inativadas, depois devolvidas).
