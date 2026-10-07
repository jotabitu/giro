# T-038 · Contratos da API de locações, vistorias e devolução · arquiteto → backend, frontend, orquestrador

**O que foi feito:**
- `docs/api/locacoes.md`: lista com indicadores, abas e `situacao`/`pagamento`/`acao_principal` decididos pela API; detalhe com parcelas, contrato e histórico; nova locação em `simular` → `POST` (rascunho) → `confirmar` (preços congelados, contas a receber, reserva do veículo, pedido de desconto `APR-01`); ativação automática pelas 3 condições; renovação (`LOC-08`), troca de veículo (`LOC-09`), cancelamento e encerramento antecipado com simulação (`LOC-12`, `LOC-13`, `APR-02`); planos especiais.
- `docs/api/vistorias.md`: agenda do vistoriador (`VIS-05`), vistoria de saída e de chegada com fotos, itens e avarias (`VIS-01` a `VIS-04`), recusa da retirada por `CLI-02`, `CLI-03` e `CLI-05`, devolução com comparação saída × agora, acerto com itens informados e calculados (`DEV-01`, `DEV-02`) e encerramento (`DEV-06`), recibo.
- `docs/api/contratos.md` (app `contratos`, ADR 0011): modelos versionados, lista fechada de marcadores e HTML sanitizado (S-09), PDF em task Celery com `url_fetcher` que só aceita o logo da empresa (S-09), link de assinatura de 7 dias, uso único, token no fragmento e rate limit (S-15), assinatura com IP, aparelho e hash, aditivo de renovação, cláusula de juros (`FIN-03`).
- Modelo de dados: `Devolucao` (no lugar de `AcertoDevolucao`) com créditos e `modo` dos itens, `TrocaVeiculo`, avaria resolvida pela OS, campos de encerramento antecipado na `Locacao`, prazo do link e HTML final no `Contrato`.

**Casos do seed nos contratos:**
- Acerto LOC-2836: caução 30000 − (3200 + 8500) = **18300**, devolver R$ 183,00 por Pix (`DEV-03`).
- Total pago LOC-2836: 32900 + 32900 + 30000 = **95800** (`LOC-05`, `LOC-06`).
- Retirada LOC-2856: 32900 + 30000 = **62900**.
- Encerramento LOC-2812: restante 42400, multa **8480**, crédito 37100, devolve **28620** (`LOC-12`, `LOC-13`).

**Onde:** `docs/api/locacoes.md`, `docs/api/vistorias.md`, `docs/api/contratos.md`, `docs/decisoes/modelo-de-dados.md`, `tarefas/backlog.md`.

**Regras cobertas:** LOC-01 a LOC-15, VIS-01 a VIS-05, DEV-01 a DEV-06, IMP-04, APR-01, APR-02, CLI-02, CLI-03, CLI-05, FIL-03, FIL-05, FIN-03 (cláusula), AUD-05; segurança S-09 e S-15.

**O que ficou de fora:**
- Os lançamentos de dinheiro (receber parcela, pagar com caução, devolver caução, saída do caixa) estão citados, mas o formato fica em `financeiro.md` (T-017).
- Abertura de OS por avaria (`DEV-04`) aparece como chamada a `manutencao.services.abrir_os_de_avaria`; o contrato de manutenção ainda não existe.
- Dúvidas para o produto no backlog (seção T-038), todas com proposta e sem bloquear: fórmula do combustível, extras por dia ou por período, vigência da renovação, caução e cobranças na troca de veículo, gerente cancelando e dando desconto direto, estados da comissão de locação. Divergências de telas para T-028 na mesma seção.

**Próximo passo para quem recebe:**
- Backend: T-015 por `locacoes.md` e `contratos.md` (criar o app `contratos` e listá-lo em `backend/README.md`); T-016 por `vistorias.md`. O combustível entra como valor informado até a decisão.
- Frontend: T-022 pode montar Nova locação, lista, detalhe, vistoria e devolução com dados falsos destes contratos.
- Orquestrador: falta `financeiro.md` (T-017) para fechar o fluxo de ponta a ponta da fase 1, e `empresas.md` (marca e regras de cobrança).
