# T-194 · Contrato de cancelar e pausar (com o acréscimo da T-211) · arquiteto → orquestrador, backend (T-195, T-185, T-186), frontend (T-198), segurança (T-199), produto, qa

**O que foi feito:** contrato de cancelar, pausar, desfazer o cancelamento e apagar a empresa no 90º dia, pelas regras `PLT-06` e `AUD-08` (T-190) e pelas decisões da T-211 (pausa no fim do período pago, que cancela a fatura já gerada; desfazer pela tela até o último dia de acesso). Branch `t-194-contrato-cancelar-pausar`, **empilhada sobre a `t-217-contrato-reativacao`** (que já está sobre a `t-213-contrato-endereco-downgrade`), porque mexe nos mesmos trechos de `assinatura.md`. Mesclar a T-213 (#219) e a T-217 (#221) antes; depois disso, o PR da T-194 mostra só o commit dela. Só documentos.

- **`docs/api/cancelamento.md`** (novo):
  - `GET /api/assinatura/cancelamento/`: tudo da `Admin-Cancelar` pronto pela API (motivos, `alternativas.pausar` só na `ativa`, `mudar_para_essencial` com `cabe` e `excede`, as cinco linhas de "O que acontece" por estado, `acesso_ate`, `cancelada_em`, `apagar_em`, o nome a digitar e o texto do exportar).
  - `POST cancelamento/` com `motivo` e `nome_confirmacao` (422 `nome_nao_confere`). Em teste: acesso até o fim do teste, 1ª fatura `cancelada`. Ativa: acesso até o fim do período pago, a fatura do período seguinte já gerada vira `cancelada`, a diferença do upgrade continua devida; anual sem devolução. Inadimplente, suspensa ou pausada: `cancelada` na hora, atrasada continua devida, régua parada.
  - `DELETE cancelamento/` (desfazer): só com cancelamento marcado e até `acesso_ate`; a fatura que o cancelamento cancelou nasce de novo, `aberta`, código novo, mesmo valor, vencimento e período, cobrada pela forma cadastrada (na hora com vencimento em até 5 dias). CA-ASS-43 a 45.
  - `POST pausa/` (1 a 3 meses, só a `ativa`; começa no fim do período pago; cancela a fatura já gerada, CA-ASS-42) e `DELETE pausa/` (volta manual: `ativa`, fatura vencendo hoje, `dia_vencimento` muda; antes de começar, desiste da pausa).
  - `GET /api/assinatura/`: blocos `cancelamento` e `pausa`, `acoes.cancelar`, `desfazer_cancelamento`, `pausar`, `voltar_pausa`; `proxima_fatura` `null` com cancelamento ou pausa marcados.
  - Tarefas: as transições novas em `virar_estados` (cancelada no dia seguinte ao acesso, início e fim da pausa), os filtros da `gerar_faturas`, a régua parada na `cancelada`, a forma de pagamento desfeita no parceiro na virada, 403 `empresa_cancelada` em todo pedido da `cancelada`, o aviso de 7 dias (`aud_08_avisar_apagamento`) e o apagamento (`aud_08_apagar_empresas`).
- **ADR 0025** (apagamento da empresa cancelada): `DROP SCHEMA` inteiro pela conexão de migração (ADR 0016), numa função única que recebe o `empresa_id` e confere a empresa de novo; storage pelo prefixo `<schema>/`; passos retomáveis; o que fica no `public`.
- **`docs/api/assinatura.md`**: aponta para o contrato novo, tira o `cancelar: false` provisório, 409 da mudança de plano com cancelamento marcado, `gerar_faturas` com os filtros, reativação com a fatura sem forma; bloco "Da T-194" em "O que muda para as tarefas abertas".
- **`docs/api/plataforma.md`**: `situacao` `cancelando` e `cancelada` pelo modelo novo (o `status` só vira `cancelada` no fim do acesso); exceções do `somente_leitura`.
- **`docs/decisoes/modelo-de-dados.md`**: `Empresa.pausa_inicio`, `cancelamento_pedido_em`, `motivo_cancelamento` (enum), `aviso_apagamento_enviado_em`, `apagada_em`; `FaturaAssinatura.motivo_cancelamento`, `cancelada_em`, `substituida_por`.
- **`tarefas/backlog.md`**: `[decisão]` com 5 casos que a `PLT-06` não cobre, cada um com o padrão que o contrato segue: cancelar em teste com a 1ª já paga, desistir da pausa antes de começar, mudar de plano com cancelamento marcado, diferença em aberto durante a pausa, o que fica no `public` depois do apagamento. Estado da T-194 e do item 1 da T-211 atualizados.

**Regras cobertas:** PLT-06, AUD-08 (e PLT-01, PLT-02, PLT-04, PLT-13, PLT-14 onde mexem).

**Para quem recebe:**
- **Produto:** a `[decisão]` dos 5 casos (padrão no contrato; a T-195 pode começar por ele). Se quiser, uma linha na tabela de automações para as duas tarefas do `AUD-08`, como a `AUT-16`. O cabeçalho de `docs/qa/criterios/assinatura.md` ainda diz "cancelar e pausar ainda sem contrato".
- **T-195 (backend):** o contrato inteiro e a ADR 0025; testes `test_plt_06_*` e `test_aud_08_*` listados no contrato; o apagamento tem de existir antes do 90º dia do primeiro cancelamento real.
- **T-185 e T-186 (backend):** o bloco "Da T-194" de `assinatura.md`.
- **T-198 (frontend):** a seção "O que muda para as tarefas abertas" do contrato novo.
- **T-199 (segurança):** 2 etapas recentes para cancelar (o contrato deixa o lugar do 403 `2fa_recente`), a ADR 0025 e o prazo dos backups depois do 90º dia.
- **Devops:** o worker que roda `aud_08_apagar_empresas` precisa da `DATABASE_URL_MIGRACAO`.
- **Qa (T-204, T-215):** CA-ASS-30 a 39 e 42 a 45 com o relógio de referência.

**Próximo passo:** o orquestrador abre o PR depois da T-213 e da T-217.
