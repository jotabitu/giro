# T-380 · API de reembolsos e pendências do pagamento · backend → frontend (T-371), qa

**O que foi feito:** as duas listas da T-358 (`docs/api/financeiro.md`, telas `Reembolsos` e `Pendências do pagamento` da T-360), com a M-02 da revisão da T-384.
- `GET /api/financeiro/reembolsos/`:
  - `?status=a_fazer|feito|todos` (padrão `a_fazer`), `?periodo=hoje|semana|mes` (padrão `mes`, vale para os feitos), `?busca=` (cliente ou código da origem);
  - `indicadores` (`a_fazer` sem período, `feitos` no período, textos prontos), `contagens` das abas e paginação por cursor;
  - item com `criado_em`, `origem` (`tipo` `devolucao`, `cancelamento` ou `credito`; `id` da locação para o "Ver acerto"; `veiculo` "QXA-4B21 · Honda CG 160 Fan"), `origem_rotulo`, `motivo`, `forma_rotulo`, `status_rotulo`, `feito_por` e `acoes.marcar_feito`;
  - com o token de suporte, `comprovante: null` (AUD-09, M-02) e `marcar_feito: false` (PLT-07).
- `POST .../reembolsos/{id}/feito/` devolve o item no mesmo formato.
- `GET /api/financeiro/pendencias-pagamento/`:
  - `?status=aberta|resolvida|todas` (padrão `aberta`), `?periodo=mes`, `?busca=` (id da cobrança no parceiro, cliente ou código da origem);
  - `indicadores` ("R$ 628,40 em análise", "3 resolvidas no mês", pela hora do evento da resolução), `contagens` e cursor;
  - item com `cobranca` (`id_no_parceiro`, `forma`, `forma_rotulo`), `origem` (`codigo`, `conta_id`, `parcela`), `motivo_rotulo`, `detalhe` pronto (FIN-03, o devido no dia da cobrança, o mesmo da baixa), `status_rotulo`, `resolucao` (`{texto: "Baixada: …" | "Ignorada: …", em}`) e `acoes`;
  - `baixar` só com a conta aberta e fora do estorno; o suporte vê as duas ações `false`.
- Pendências: 403 `PLT-12` sem `recebimento_parceiro` na lista e no resolver. Escopo da empresa inteira, sem o `X-Filial` (contrato).

**Onde:** `backend/apps/financeiro/selectors.py` (fim do arquivo), `api/views.py`, `api/serializers.py` e `backend/apps/locacoes/leituras.py` (bloco `locacao` do `financeiro.Reembolso`, ADR 0015, pelo código da origem).
**Contrato:** `docs/api/financeiro.md`; OpenAPI regenerado em `docs/api/openapi.yaml`. Serializers novos com nomes próprios (`ListaDeReembolsosSerializer`, `ListaDePendenciasPagamentoSerializer` e os blocos), sem colisão no `spectacular --validate`.
**Regras cobertas:** DEV-02, AUT-05, PLT-07, PLT-12, AUD-09. Testes em `backend/tests/aceitacao/test_t380_reembolsos_pendencias.py`: `test_dev_02_lista_de_reembolsos_indicadores_e_filtros`, `test_dev_02_marcar_feito_devolve_o_item_da_lista`, `test_plt_07_reembolso_suporte_sem_marcar_feito`, `test_aut_05_lista_de_pendencias_indicadores_e_filtros`, `test_aut_05_acoes_da_pendencia_pela_conta`, `test_plt_12_pendencias_essencial_403` e `test_dev_02_aut_05_isolamento_entre_empresas`.

**O que ficou de fora e pontos para conferir:**
- O formato das duas listas mudou (antes, só `resultados` com menos campos). Nenhuma tela usava; a T-371 é a primeira.
- Os textos do `detalhe` do estorno ("O parceiro estornou o pagamento de R$ 1.347,00.") e da conta que não está aberta ("Pagou R$ 1.347,00, mas a conta já estava cancelada.") não estão no contrato: o **produto** confere.
- O `POST .../resolver/` segue aberto para o suporte em "ver e editar": o contrato só desliga as `acoes`. A **segurança** decide se a rota também dá 403 `PLT-07`, como o `feito/` dos reembolsos.
- `indicadores.a_fazer.texto` conta clientes ("1 cliente com devolução"); `quantidade` conta reembolsos.
- O crédito de semanas (`LOC-13`) tem rótulo, mas hoje nenhum serviço cria reembolso com essa origem.

**Próximo passo para quem recebe:** frontend, a T-371 liga as duas telas pelo cliente gerado (`npm run api:gerar`); qa, os testes acima com os números do seed.
