# T-417 · Despesas do veículo na ficha, com categorias próprias · produto → backend, frontend, qa

**O que foi feito:** a decisão do dono de 29 out 2026 virou regra, com notas de mudança, e os critérios de aceite.

1. **`FIN-06`:** categorias em dois grupos. Do veículo: IPVA e licenciamento, seguro, multa de trânsito, peças, combustível (novas), manutenção, rastreamento. Da empresa: fixas, impostos, pessoal, outros. Nenhuma exige veículo; as despesas já lançadas não mudam de categoria (o "IPVA ROE2A88" do seed fica em impostos). Multa de trânsito não cria cobrança ao cliente. O vistoriador lança manutenção e peças (tabela de perfis).
2. **`FIN-16`:** filtro "Veículo" na tela `Despesas` (a API já tem `?veiculo=`); não muda abas nem indicadores.
3. **`FIN-17` (nova):** lista na ficha, só para administrador, gerente e financeiro (ausente na API para os outros); despesas do veículo no ano, de qualquer filial, com as recusadas, 20 por página; total "Despesas no ano" sem as recusadas; "Lançar despesa" para quem lança, com o veículo travado e a filial do veículo.
4. **`VEI-05`:** o cartão "Custo de manutenção" soma só manutenção e peças; o "Rendeu no ano" desconta todas as despesas do veículo. Hoje o código (`financeiro/selectors.py`, `custo_do_veiculo_no_ano`) soma todas: muda.
5. **Seed:** linha "Despesas do veículo em 07 out"; nenhum número muda.

**Onde:** `docs/regras-de-negocio.md` (perfis, Veículos, Financeiro, Dados de referência, "Decisões de 29 e 30 out 2026"); `docs/qa/criterios/T-417.md` (CA-417-01 a 13).

**Leituras do produto (não vieram do dono):** os dois grupos e a ordem; "IPVA e licenciamento" no lugar de só IPVA; nenhuma categoria exige veículo; vistoriador com peças; quem vê a lista; o cartão de manutenção só com manutenção e peças. Sem ponto em aberto novo.

**Próximo passo:**
- **Arquiteto (curto):** chaves das categorias novas no contrato (sugestão: `ipva_licenciamento`, `seguro`, `multa_transito`, `pecas`, `combustivel`), bloco da lista no veículo (ou rota `GET /api/veiculos/{id}/despesas/?ano=`), mensagem do 403 do vistoriador.
- **Backend:** enum, migração, lista e total, `custo_do_veiculo_no_ano` só com manutenção e peças, filial do veículo no lançamento pela ficha, testes `test_fin_17_...`.
- **Frontend:** seção e botão na ficha, grupos no select, filtro por veículo em `Despesas`.
- **QA:** CA-417-01 a 13.
