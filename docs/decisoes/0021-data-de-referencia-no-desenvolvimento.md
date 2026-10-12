# Data de referência do relógio no desenvolvimento

**Status:** aceita · 12 out 2026 · detalha o `comum.relogio` da 0009 (T-135)

## Contexto

Os números das regras ("Dados de referência para testes") estão presos a uma data: o caixa de 07 out, "vence hoje", os dias de atraso, a agenda, o sinal `devolve_hoje` da LOC-2836 em 14 out e o acerto de R$ 183,00, que só fecha se a devolução cair no dia do fim previsto (`DEV-07`, `LOC-10`).

Hoje o "agora" do domínio já tem um ponto só, `comum.relogio.agora()` e `hoje()`. Os testes o trocam pela fixture `relogio` (`conftest.py`), e o seed da T-127 o congela em 07 out só enquanto roda (`seed/relogio.py`). Depois do seed, o compose volta ao relógio real: em 12 out, a carteira de 07 out aparece com atrasos e vencimentos que não são os das regras, e o qa não consegue conferir as telas contra os números (item 1 das divergências da T-127).

O que não pode acontecer: data simulada em homologação ou produção, e data simulada sem a tela avisar.

## Decisão

### 1. Uma variável, lida só nas configurações de desenvolvimento

`GIRO_DATA_REFERENCIA`, no formato `AAAA-MM-DD` (ex.: `2026-10-07`).

- `config/settings/base.py`: `GIRO_DATA_REFERENCIA = None`. Produção, homologação e testes nunca leem a variável.
- `config/settings/dev.py`: lê a variável. Vazia ou ausente = desligada (a mesma regra da T-133 para variável vazia). Valor fora do formato faz o processo não subir (`ImproperlyConfigured`).
- `config/settings/prod.py`: variável presente **e não vazia** faz o processo não subir (`ImproperlyConfigured("GIRO_DATA_REFERENCIA só vale no desenvolvimento.")`). É a mesma barreira das chaves de exemplo: um `.env` de desenvolvimento copiado para o servidor não sobe.
- `config/settings/test.py`: `None` explícito. Os testes continuam com a fixture `relogio`; quem testa a data de referência usa `override_settings`.

### 2. A data é fixa; a hora é a real

Com a variável ligada:

```python
# comum/relogio.py
def agora() -> datetime:
    real = timezone.now()
    data = settings.GIRO_DATA_REFERENCIA
    if data is None:
        return real
    local = timezone.localtime(real)  # America/Sao_Paulo
    return local.replace(year=data.year, month=data.month, day=data.day)
```

`hoje()` não muda (continua `timezone.localdate(agora())`) e passa a devolver a data de referência.

- O dia fica parado e a hora anda. Assim, o que depende da hora continua funcionando como no real: bloqueio de 2 etapas (`contas/dois_fatores.py`), sessões, convites e tokens de assinatura expiram, e duas ações seguidas têm momentos diferentes.
- Não há modo de "instante congelado" no compose. Com o relógio parado, um bloqueio de login nunca termina e todos os registros têm o mesmo momento. Caso que depende de hora exata (a tolerância de 1 hora da `LOC-10`, as 53 h da `LOC-12`) se confere em teste, com a fixture `relogio`, e não na tela.
- Na virada da meia-noite real, o relógio simulado volta para 00:00 da mesma data. Quem trabalha nessa hora vê um "agora" menor que o anterior. Fica aceito: só existe no desenvolvimento.
- Datas sem hora gravadas pelos serviços (vencimento, dia do caixa) saem da data de referência, porque vêm de `relogio.hoje()`.

### 3. O que continua no relógio real

- `criado_em`, `atualizado_em` (`comum.models`) e `ocorrido_em` da auditoria: são `auto_now`/`auto_now_add` do Django e registram quando a linha foi gravada de verdade. Regra de negócio não compara esses campos com `relogio` (já era a convenção; o seed da T-127 vive com isso). Quem precisar de um momento do negócio grava um campo próprio a partir de `relogio.agora()`.
- Expiração do JWT (simplejwt), código TOTP (django-otp), throttles do DRF e o agendamento do Celery Beat: usam o relógio do sistema operacional, e cada um compara só consigo mesmo. As tarefas que o Beat dispara (`AUT-02` etc.) leem o dia pelo `relogio` e, portanto, trabalham na data de referência.
- O frontend não calcula data (ADR 0005). Onde a tela precisa de "hoje" (dia inicial da agenda, filtro "vence hoje", data padrão de um formulário), ela usa o `hoje` da API (item 4), e não o relógio do navegador.

### 4. A tela mostra que a data é simulada

**Rota `GET /api/ambiente/`** (e `GET /api/plataforma/ambiente/` no urlconf do `public`), pública, sem login, `Cache-Control: no-store`, throttle padrão de anônimo:

```json
{ "hoje": "2026-10-07", "data_simulada": true }
```

Desligada (sempre, em produção): `{ "hoje": "2026-10-12", "data_simulada": false }`. A rota existe em todos os ambientes, para o frontend não tratar 404 como caso especial, e não diz nada além do que o relógio de quem a chama já sabe.

**Cabeçalho `X-Giro-Data-Simulada: 2026-10-07`** em toda resposta da API quando ligada (middleware em `comum`). Serve para `curl`, testes ponta a ponta e logs; o frontend não depende dele.

**Faixa no frontend:** com `data_simulada: true`, uma faixa fixa no topo, em todas as telas (login, sistema da locadora e painel da plataforma), com o texto: "Data simulada: 07/10/2026. Ambiente de desenvolvimento." Tom de aviso do design system, sem botão de fechar. A faixa não aparece quando `data_simulada` é `false`.

**Aviso no backend:** ao subir com a variável ligada, o backend, o worker e o beat registram um `WARNING` com a data, e o `manage.py check` mostra o aviso `giro.W001` ("Data de referência ligada: 2026-10-07").

### 5. Quem liga e desliga

- **Padrão do `.env.example`:** `GIRO_DATA_REFERENCIA=2026-10-07`, ligada. O seed é a Moto Rápida de 07 out, e o ambiente de desenvolvimento serve para conferir as telas contra as regras.
- **Quem muda:** quem usa o ambiente (pessoa ou agente qa) edita o próprio `.env` e recria os serviços que leem o relógio: `make relogio` (alvo novo) faz `docker compose up -d --force-recreate backend worker beat`. Backend, worker e beat leem o mesmo `.env` (âncora `x-backend` do compose) e ficam sempre na mesma data.
- **Desligar:** `GIRO_DATA_REFERENCIA=` (vazio) e `make relogio`.
- **Conferir a LOC-2836 em 14 out:** `GIRO_DATA_REFERENCIA=2026-10-14`, `make relogio` e a devolução antes das 19:00 do horário real (fim previsto 18:00 + 1 h de tolerância, `LOC-10`).
- **Seed:** `make seed` continua com o próprio relógio (`seed/relogio.py`), que troca `relogio.agora` só enquanto roda. Ele independe da variável e monta sempre a história de 07 out.
- **Homologação, produção e CI:** não podem ligar. Homologação com data simulada, se um dia for preciso, pede outra ADR.

## Consequências

- **Tarefa do backend (T-142):** itens 1 a 4 do lado do backend: `GIRO_DATA_REFERENCIA` nas configurações (base, dev, prod e test), `comum.relogio` como acima, a rota de ambiente nos dois urlconfs (contrato em `docs/api/README.md`, seção "Ambiente"), o cabeçalho, o aviso `giro.W001` e o `WARNING` ao subir, o `.env.example` e o alvo `make relogio`. Testes: `test_adr_0021_*` (data de referência em `hoje()` com a hora real; desligada com variável vazia; `prod.py` recusa subir; rota e cabeçalho ligados e desligados). Mudança em `Makefile` e `.env.example` com aval do devops no PR.
- **Tarefa do frontend (T-143):** a faixa do item 4 em todas as cascas, e o "hoje" das telas pela rota de ambiente.
- O relógio do domínio passa a depender de `settings`, sem custo em produção (um `None` lido por chamada).
- Um "agora" do domínio fica em uma data e o `criado_em` da mesma linha, em outra. Em tela, o que mostra "quando aconteceu" para o usuário é o momento do negócio, nunca o `criado_em`. Onde um contrato hoje expõe `criado_em` como momento do negócio (ex.: `pedido_em` das aprovações), a tela mostra a data real no desenvolvimento, sem efeito em regra. Não muda nada em produção, onde os dois relógios são o mesmo.
- O qa refaz a conferência das telas da T-127 com a data ligada, depois da T-133 (login) e da T-142.
