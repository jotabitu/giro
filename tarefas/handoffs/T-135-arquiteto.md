# T-135 · Data de referência do relógio no desenvolvimento · arquiteto → orquestrador, backend, devops, frontend, qa

**O que foi feito:** ADR 0021, que resolve o item 1 das divergências da T-127.
- **Variável `GIRO_DATA_REFERENCIA`** (`AAAA-MM-DD`), lida só em `config/settings/dev.py`. Vazia ou ausente, fica desligada. `base.py` e `test.py` têm `None`, e `prod.py` recusa subir com ela não vazia (homologação e produção usam `prod.py`, e o CI usa `test.py`).
- **Data fixa, hora real:** `comum.relogio.agora()` devolve a data de referência com a hora real de São Paulo, e `hoje()` a segue. Sem modo de instante congelado no compose: com o relógio parado, o bloqueio de 2 etapas nunca terminaria. Caso que depende de hora exata (tolerância da `LOC-10`, 53 h da `LOC-12`) se confere em teste, com a fixture `relogio`.
- **Continuam no relógio real:** `criado_em`, `atualizado_em`, `ocorrido_em` (auto_now), JWT, TOTP, throttles e o agendamento do Beat. As tarefas do Beat leem o dia pelo `relogio`.
- **A tela avisa:** rota pública `GET /api/ambiente/` (e `/api/plataforma/ambiente/`) com `{ "hoje", "data_simulada" }`, contrato em `docs/api/README.md`, seção "Ambiente". Cabeçalho `X-Giro-Data-Simulada` em toda resposta com a data ligada. Faixa fixa "Data simulada: 07/10/2026. Ambiente de desenvolvimento." em todas as telas. O "hoje" das telas vem dessa rota, e não do navegador.
- **Quem liga e desliga:** o `.env.example` já vem com `2026-10-07`, ligado. Quem usa o ambiente edita o próprio `.env` e roda `make relogio` (alvo novo, recria backend, worker e beat). Para desligar, deixe a variável vazia. O `make seed` continua com o próprio relógio de 07 out (`seed/relogio.py`), sem depender da variável.
- **Quadro:** T-142 (backend, com aval do devops no `Makefile` e no `.env.example`) e T-143 (frontend) no backlog; T-135 em `feito.md` com "PR a abrir".

**Onde:** `docs/decisoes/0021-data-de-referencia-no-desenvolvimento.md`, `docs/decisoes/README.md`, `docs/api/README.md` (seção "Ambiente"), `tarefas/backlog.md`, `tarefas/feito.md`.

**Regras:** nenhuma regra nova nem mudada. A ADR serve para conferir na tela `LOC-10`, `DEV-07`, `DEV-03` (LOC-2836 em 14 out) e os números de 07 out dos dados de referência.

**Decisões que tomei (técnicas):**
1. Variável de ambiente, e não um ajuste no banco ou na tela: não há como ligar a data pela API, e um servidor de produção não sobe com ela.
2. Uma data para todo o compose, e não por empresa ou por requisição: um cabeçalho que mudasse a data por requisição seria uma porta para fraudar prazos se escapasse para produção.
3. A rota de ambiente existe também em produção (sempre `false`), para o frontend não tratar 404 como caso especial.
4. Virada da meia-noite real: o relógio simulado volta para 00:00 da mesma data. Fica aceito no desenvolvimento.

**O que ficou de fora:** data simulada em homologação (pediria outra ADR). Onde um contrato mostra `criado_em` como momento do negócio (ex.: `pedido_em` das aprovações), a tela do desenvolvimento mostra a data real. Isso não afeta regra nem produção.

**Próximo passo para quem recebe:**
- **Orquestrador:** abrir o PR. A T-142 pode andar junto com a T-133 (as duas mexem em `config/settings` e no `.env.example`; uma depois da outra evita conflito).
- **Backend:** T-142.
- **Devops:** dar aval no PR da T-142 para o `make relogio` e o `.env.example`.
- **Frontend:** T-143, depois da T-142.
- **QA:** depois da T-133 e da T-142, refazer a conferência das telas da T-127 com a data em 07 out, e a devolução da LOC-2836 com `GIRO_DATA_REFERENCIA=2026-10-14`, antes das 19:00 no horário real.
