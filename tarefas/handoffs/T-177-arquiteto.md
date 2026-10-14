# T-177 · Contrato das despesas: busca, exportar e despesa por veículo · arquiteto → orquestrador, backend, frontend, qa

**O que foi feito:** ajustei os contratos de Despesas e da Exportação às decisões do dono de 13 out 2026 (T-176: `FIN-05`, `FIN-06`, `FIN-16`, nota na `AUD-07`) e aos critérios `docs/qa/criterios/despesas.md` (CA-DES-01 a 19).

**Onde:**
- `docs/api/financeiro.md`, "Despesas":
  - **Quem pode:** linhas novas "Lançar despesa como paga no caixa" (quem abre e fecha caixa) e "Exportar as despesas em CSV" (só administrador).
  - **`GET /despesas/`:** `?busca=` acha pela descrição (sem diferenciar maiúsculas e acentos) ou pela placa (sem hífen). Muda a lista e as `contagens`, nunca os `indicadores`. `despesa_por_veiculo_centavos` = gasto ÷ frota ativa no fim do mês (hoje, no mês corrente), arredondado uma vez com `ROUND_HALF_UP` (8217 no seed; 6902 no CA-DES-02), `null` sem veículo. Exemplo de resposta com `busca=pneu`.
  - **`POST /despesas/`:** `nota` obrigatória; sem `forma` no lançamento; erros em ordem fixa: 403 `FIN-06` (vistoriador fora de manutenção), 403 `FIN-05` (`pago_no_caixa` de quem não opera caixa), 400 `validacao` (`nota`: "Envie a foto da nota."), 422 `APR-03` (pago no caixa acima de R$ 500), 422 `FIN-07` "Abra o caixa do dia para pagar por ele". Nada é gravado em nenhum erro.
  - Interface interna: o item de exportação `despesas` registrado por `financeiro/exportacao.py`.
- `docs/api/auditoria.md`, "Exportação": a exceção do MVP para as despesas e a seção nova "Despesas em CSV". Corpo `{ itens: ["despesas"], formato: "csv", mes, filial_id | null }`. Colunas e formato de cada uma, todas as situações (as recusadas também), `conteudo` "Despesas · Filial Centro · 01/10/2026 a 31/10/2026" ("Todas as filiais" com `null`). Mensagem nova do 422 `exportacao_indisponivel`. A `Admin-Exportar` continua só com a auditoria.
- `docs/decisoes/modelo-de-dados.md`: `Despesa.descricao_busca` e `Exportacao.parametros` (e o item `despesas`).
- `tarefas/backlog.md`: seção da T-177 retirada.

**Regras cobertas:** FIN-05, FIN-06, FIN-07, FIN-16, AUD-07, APR-03.

## Decisões do dono no PR #187 (13 out 2026)

- **O financeiro também exporta as despesas** (não só o administrador): perfis por item em `POST /api/exportacoes/` (`auditoria` só administrador; `despesas` administrador e financeiro), no download e em "Exportações recentes" (o financeiro vê só as das despesas). Chave nova `pode.despesas_exportar` em `contas.md`, para o frontend não deduzir o botão pelo perfil.
- **Placa com hífen no CSV:** `PMZ-3E17`, hífen depois do 3º caractere nas placas de 7.

## Decisões do arquiteto

| # | Ponto | Decisão |
| --- | --- | --- |
| 1 | Busca sem acento | Campo `descricao_busca` gravado pelo serviço (NFKD), com migração de dados; placa por `normalizar_placa`. Sem a extensão `unaccent`, que pediria ADR de infraestrutura. |
| 2 | Frota no fim de um mês passado | `veiculos.selectors.frota_ativa_em(dia, filiais)` pelo histórico de status; filial = a atual do veículo (a troca de filial não tem histórico). |
| 3 | Quem monta o CSV das despesas | `financeiro`, por um registro de itens em `auditoria/exportacao.py` (o app de baixo registra, o de cima chama, como na ADR 0015). `auditoria` não pode importar `financeiro` (ADR 0011). Sem ADR nova. |
| 4 | Item e corpo | Item novo `despesas`, separado de `financeiro` (fase 2). `mes` e `filial_id` no corpo, e não o `X-Filial`: a task roda depois, então a filial fica gravada em `parametros`, com o nome copiado. |
| 5 | Despesas junto de outro item | 422 `exportacao_indisponivel`: período e filial não combinam com a auditoria. |
| 6 | Formato das células | Datas `DD/MM/AAAA`, valor `1200,00`, rótulos em vez de códigos, placa com hífen (decisão do dono); mesmo CSV da auditoria (BOM, `;`, proteção contra fórmula). |

**O que ficou de fora:**
- Seed: o PR #180 (T-019, qa) já lança as 6 despesas de outubro; a T-178 só acrescenta a nota nelas (orquestrador, 13 out 2026).

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR depois do #186 (esta branch saiu da `origin/t-176-decisoes-t167`).
- **Backend (T-178):** contrato pronto; `test_*` como na T-178. A mensagem do 422 `FIN-07` muda em `lancar_despesa`, e a do `exportacao_indisponivel` em `auditoria/services.py`.
- **Frontend (T-179):** "Exportar" só com `pode.despesas_exportar` (administrador e financeiro), com o mês e a filial da tela; o indicador da despesa por veículo some com `null`; "Foto da nota" obrigatória; a mensagem do 422 aparece como vier.
- **QA:** a coluna `veiculo` sem hífen e o texto de `conteudo` fecham o "texto final no contrato" do CA-DES-06.
