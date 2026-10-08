# T-060 · Telas do Receber e do Financeiro com a carteira de outubro · design-system → orquestrador, qa

**O que foi feito (telas de `docs/telas/html/`, números das regras da T-059, `FIN-15`):**
- **`Receber` (desktop e celular):** Previsto no mês R$ 52,0 mil em 128 parcelas; Recebido R$ 13,4 mil (26% do previsto); Vence hoje R$ 2.625,80 em 6 parcelas; abas Todas 130, Em atraso 2, Vencem hoje 6 (celular: Hoje 6), A vencer 92, Pagas 30. Em atraso (R$ 1.646,40, 2 clientes) já batia.
- **`Financeiro` (desktop e celular):** "Entra hoje" R$ 2.625,80 em 6 parcelas. Mesmo valor em "A receber hoje" da `Main` e do `Dashboard-Mobile`, que mostravam R$ 1.890 (é o mesmo "vence hoje"; fora da lista, mas ficaria em desacordo).
- **`Caixa` (desktop e celular):** "Entrou hoje" R$ 1.111,90; cartão R$ 109,00; a linha do Diego vira "LOC-2848 · renovação de 1 diária"; o Pix de R$ 44,90 vira "LOC-2826 · diária Urbana", sem nome de cliente (o nome vem da T-019).
- **`Locacoes`:** LOC-2841 "23 set → 28 out" e LOC-2848 "06 out → 10 out" (desktop; o celular só tem a LOC-2841).
- **`Comissoes` (desktop):** LOC-2848 vale R$ 436,00; a comissão de R$ 16,00 não muda. O celular não mostra o valor.
- **CNPJ da Filial Messejana:** 12.345.678/0003-57 em `Filial` e `Filial-Mobile`.
- **FleetBar a 390 px conferido no navegador** (Playwright no scratchpad, `next dev` da main): sem rolagem horizontal; os 5 segmentos quebram em 3 + 2 dentro do painel (largura de 294 px); a 1440 px ficam numa linha só; botão `wl-btn--sm` mede 44 px a 390 px.

**Onde:** `docs/telas/html/{Receber,Financeiro,Caixa,Locacoes,Comissoes,Filial}-{Desktop,Mobile}.dc.html`, `Main.dc.html`, `Dashboard-Mobile.dc.html`; `tarefas/{backlog,em-andamento}.md` (T-060 saiu do backlog e entrou em andamento).
**Verificação:** conferi por busca que não restam os valores antigos (74,2 mil, 318, 1.182,60, 179,70 do caixa, 0002-76 nas telas `Filial`). Não há teste para HTML de referência.
**O que ficou de fora:** `Financeiro` mostra outros números (saldo R$ 48.320, caixa por semana, "+18,4 mil") que nenhuma regra da T-059 cobre; não mexi.
**Próximo passo para quem recebe:** orquestrador abre o PR e move a T-060 para `feito.md`; arquiteto troca o CNPJ da Messejana em `docs/api/filiais.md`, se houver; qa pode usar os números das telas contra o seed.
