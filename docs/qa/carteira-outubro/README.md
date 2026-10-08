# Carteira de outubro da Moto Rápida (T-056)

Dados de referência para os números de outubro da tela `Receber`, do contador do menu e do início `Financeiro`, calculados pela `FIN-15` em **07 out 2026** (quarta-feira), Filial Centro. Substituem os números das telas (R$ 74,2 mil em 318 parcelas etc.), que não fecham com as regras (ver "Dados de referência para testes").

| Arquivo | O que tem |
| --- | --- |
| `locacoes.csv` | as 42 locações abertas: código, cliente, categoria, plano |
| `parcelas.csv` | todas as parcelas que contam na `FIN-15`: código, vencimento, `valor_centavos`, situação (`paga`, `vence_hoje`, `atrasada`, `aberta`); sem caução |
| `gerar.py` | gera os dois CSV e calcula os números; determinístico, só biblioteca padrão |

O teste `backend/tests/aceitacao/test_t056_carteira_outubro.py` confere os CSV contra o gerador e os números abaixo. O seed da T-019 carrega estes CSV.

## Números de 07 out (`FIN-15`)

| Número | Valor |
| --- | --- |
| Previsto no mês | **R$ 52.002,10** em **128** parcelas (vencimento de 01 a 31 out, pagas ou não) |
| Recebido (opção A) | **R$ 13.401,70** em 30 parcelas = **25,77%** do previsto |
| Vence hoje | **R$ 2.625,80** em **6** parcelas (não pagas, vencimento em 07 out) |
| Em atraso | **R$ 1.646,40**, 2 clientes, 2 parcelas (qualquer mês) |
| Atraso por faixa | 1–7 dias R$ 299,40 (Carlos); 8–30 dias R$ 1.347,00 (Rafael); mais de 30 dias R$ 0 |
| A vencer (do mês) | R$ 35.974,60 em 92 parcelas |
| Abas da lista, período mês | Todas **130** · Em atraso **2** · Vencem hoje **6** · A vencer **92** · Pagas **30** |
| Contador do menu | **2** (parcelas atrasadas) |

Todas = 130 e não 128 porque "Em atraso" mostra atrasadas de qualquer mês (as duas são de setembro) e não entram no previsto de outubro. Recebido ≤ previsto por construção (opção A).

## Como a carteira foi montada

- **7 locações das telas**, com as parcelas à mão: LOC-2790 (Rafael, uma conta atrasada de R$ 1.347,00), LOC-2812 (Patrícia, mensal pago em 15 set, nada em outubro), LOC-2836 (Juliana, 30 set e 07 out pagas), LOC-2841 (Carlos, desde 23 set, 5 semanais de R$ 299,40 de 23 set a 21 out; a de 23 set está paga, a de 30 set atrasada, a de 07 out vence hoje), LOC-2848 (Diego, 3 diárias × R$ 109,00 = R$ 327,00 pagas em 06 out, mais a renovação de 1 diária de R$ 109,00 paga no cartão em 07 out, `LOC-08`), LOC-2850 (Marcos, mensal Urbana R$ 1.090,00 pago em 01 out), LOC-2856 (Lucas, R$ 329,00 pago hoje e R$ 329,00 em 14 out).
- **35 locações geradas** (clientes "Cliente 01" a "Cliente 35"; a T-019 dá os nomes), na proporção da frota (42/32/6/6 veículos): Urbana 20, Street 16, Scooter 3, Carro 3 no total das 42.

| Categoria | Plano | Geradas | Parcela |
| --- | --- | --- | --- |
| Urbana | semanal | 8 | R$ 299,40 |
| Urbana | Entregador (semanal) | 5 | R$ 279,00 |
| Urbana | mensal | 4 (vencem nos dias 1, 5, 7 e 18) | R$ 1.090,00 |
| Urbana | diária | 1 (retirada hoje) | R$ 44,90 |
| Street | semanal | 9 | R$ 329,00 |
| Street | mensal | 4 (dias 2, 6, 12 e 25) | R$ 1.190,00 |
| Scooter | semanal / mensal | 1 / 1 (dia 9) | R$ 449,00 / R$ 1.590,00 |
| Carro | semanal / mensal | 1 / 1 (dia 20) | R$ 649,00 / R$ 2.290,00 |

- Semanais em rodízio de segunda a sábado (4 de cada dia, nenhuma no domingo). Em outubro de 2026 quinta, sexta e sábado têm 5 vencimentos; os outros dias, 4. Os contratos seguem até 31 out ou depois (sem devolução prevista no mês).
- Tudo com vencimento até 06 out está `paga`, exceto a parcela de 30 set do Carlos (a de 23 set está paga) e a de 12 set do Rafael. Vencimento em 07 out: Juliana, Lucas, a diária Urbana e a renovação do Diego estão pagas (entram no caixa de 07 out); as outras seis (Carlos, 4 semanais de quarta e 1 mensal de dia 7) vencem hoje. Nada com vencimento futuro está pago (`LOC-05`: não existe pagamento antecipado).

## Registro nas regras

O Produto registrou estes números em "Dados de referência para testes", na linha "Contas a receber de outubro em 07 out" (T-059). Esta carteira segue essa linha: Previsto R$ 52.002,10 em 128 parcelas; Recebido R$ 13.401,70 em 30 (25,77%); Vence hoje R$ 2.625,80 em 6; Em atraso R$ 1.646,40 (2 clientes); abas 130 / 2 / 6 / 92 / 30.

## Para o design-system: trocar em `Receber` e `Financeiro`

`Receber` (desktop e celular): Previsto no mês **R$ 52,0 mil** · **128 parcelas**; Recebido **R$ 13,4 mil** · **26%** do previsto; Vence hoje **R$ 2.625,80** · **6 parcelas**; Em atraso e faixas sem mudança; abas Todas **130**, Em atraso **2**, Vencem hoje **6**, A vencer **92**, Pagas **30**. No `Financeiro`, "Entra hoje" usa o mesmo vence hoje (R$ 2.625,80, 6 parcelas). A lista de linhas das telas pode manter Rafael e Carlos; o rodapé "Mostrando ..." deve bater com a aba.

## Decisões do Produto (T-059) e pontos conhecidos

1. **Composição das 35 locações geradas e premissas** (Entregador só em Urbana; ninguém no mensal fidelidade; mensal à vista, `LOC-14`): confirmadas pelo Produto.
2. **LOC-2841** começa em 23 set (`LOC-05`: parcela 1 paga na retirada); a parcela de 30 set é a 2 de 5, como dizem a tela e os critérios. Sai a parcela de 28 out.
3. **Cartão de R$ 179,70 do caixa de 07 out:** decisão do dono do produto, a renovação de 1 diária do Kwid do Diego (R$ 109,00, `LOC-08`) entra na carteira como parcela paga em 07 out. O Pix de R$ 44,90 é a diária Urbana retirada hoje.
4. **LOC-2790:** R$ 1.347,00 fica como valor dado do seed (uma conta atrasada), porque os casos "Em aberto dos clientes" e `CLI-05` dependem dele.
5. **Tela `Locacoes`** (T-060): "71% da frota alugada" (42 de 86 é 49%) e "Devolvem hoje 4" (aqui só Juliana devolve hoje) não saem desta carteira.
