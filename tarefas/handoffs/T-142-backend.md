# T-142 · Data de referência do relógio no desenvolvimento · backend → frontend, qa, devops

**O que foi feito:** a parte do backend da ADR 0021.
- `GIRO_DATA_REFERENCIA` (`AAAA-MM-DD`): `None` em `base.py` e `test.py`; lida só em `dev.py` (vazia, só espaços ou ausente = desligada; fora do formato, `ImproperlyConfigured` e o processo não sobe); `prod.py` recusa subir com ela não vazia ("GIRO_DATA_REFERENCIA só vale no desenvolvimento.").
- `comum.relogio.agora()` devolve o dia de referência com a hora real de São Paulo; `hoje()` o segue. Desligada, é o `timezone.now()` de antes.
- `GET /api/ambiente/` (empresa) e `GET /api/plataforma/ambiente/` (public): públicas, sem autenticação (token qualquer é ignorado), `Cache-Control: no-store`, limite de 120/min por IP (`ambiente_ip`). Corpo `{ "hoje", "data_simulada" }`.
- Cabeçalho `X-Giro-Data-Simulada: AAAA-MM-DD` em toda resposta com a data ligada (`comum.ambiente.DataSimuladaMiddleware`).
- Aviso `giro.W001` no `manage.py check` e `WARNING` no logger `giro.relogio` ao subir (no `ready()` do `comum`, por onde passam backend, worker e beat).
- `make relogio`: `docker compose up -d --force-recreate backend worker beat`.
- `docs/agentes/retomada.md`: como ligar, mudar (ex.: 14 out para a LOC-2836) e desligar.

**Onde:** `backend/comum/relogio.py`, `backend/comum/ambiente.py` (novo), `backend/comum/apps.py`, `backend/comum/limites.py`, `backend/config/settings/{base,dev,prod,test}.py`, `backend/config/urls.py`, `backend/config/urls_publico.py`, `Makefile`, `docs/agentes/retomada.md`, `docs/api/openapi.yaml`.

**Contrato:** `docs/api/README.md`, seção "Ambiente" (sem mudança no contrato). No OpenAPI, `ambiente_retrieve` e `plataforma_ambiente_retrieve` com `AmbienteSerializer`.

**Regras/ADR cobertas:** ADR 0021, testes em `backend/tests/test_data_de_referencia.py` (`test_adr_0021_*`: ligada com a hora real, desligada, dev lê a variável e recusa formato errado, produção recusa, testes não leem, aviso no check e ao subir, rota e cabeçalho nos dois urlconfs) e `test_adr_0021_painel_do_seed_com_a_data_de_referencia` em `test_t127_seed.py`.

**O que ficou de fora:**
- **`.env.example`** (`GIRO_DATA_REFERENCIA=2026-10-07` com comentário): o arquivo está bloqueado por regra de permissão para o agente backend; não contornei. **devops**, por favor inclua a linha no mesmo PR (ou o orquestrador), e dê o aval no alvo `make relogio`.
- **Números do painel com o seed:** com a data em 07 out e o relógio real, "em atraso" dá **164640** em 2 clientes, como nas regras. "Entra hoje" dá **29940** (1 parcela), e não 262580, porque a T-138 (qa, D-21) pagou no seed as parcelas que venceriam até 07 out, para não aparecerem atrasadas no relógio real. Com o relógio congelado da fixture o número é o mesmo: não é da T-142. Agora que a data pode ficar em 07 out, o **qa** pode tirar esse contorno do seed para "entra hoje" voltar aos 262580 (o teste novo do seed precisa acompanhar).

**Verificação:** ruff, format e mypy limpos; suíte completa do backend 747 de 747; OpenAPI regerado sem avisos; no frontend, `api:gerar`, `typecheck` e os testes da faixa e do ambiente (9) passando; `manage.py check` com dev e a data ligada mostra o `giro.W001`.

**Próximo passo para quem recebe:**
- **frontend (T-143):** a rota já responde de verdade; a faixa e o "hoje" das telas podem sair do falso.
- **qa:** refazer a conferência das telas da T-127 com a data ligada e decidir o contorno D-21 do seed.
- **devops:** `.env.example` e aval do `Makefile`.
