# T-399 · Ambiente do filho do CRLV-e com o Sentry ligado · backend → orquestrador, seguranca, arquiteto

**O que foi feito:**
- O filho da leitura de PDF passa a nascer pelo `/usr/bin/env -i PATH=... LANG=... <python> -I trabalhador.py <tipo>` (`comando(tipo)` em `backend/integracoes/leitura_documentos/__init__.py`). O `env=AMBIENTE` do `Popen` continua lá, mas não é mais o que garante o M-01.
- Causa: o sentry-sdk 2.73 (`StdlibIntegration`) troca o `subprocess.Popen.__init__` e acrescenta `SUBPROCESS_SENTRY_TRACE` e `SUBPROCESS_BAGGAGE` a uma cópia do `env`. O `env -i` descarta tudo o que chega e dá `exec` no intérprete, com o mesmo PID, o mesmo grupo (o `killpg` do tempo continua valendo) e o mesmo código de saída (o SIGXCPU e o SIGKILL chegam iguais).
- Quando o SDK propaga: com as opções do Giro (`traces_sample_rate=0.0`), o 2.73 não acrescenta nada. Ele acrescenta quando a opção não existe, como no `sentry_sdk.init()` sem argumentos que o fixture da T-270 deixa no fim (por isso o teste da ADR 0026 falhava depois do `test_t270_sentry`), ou quando o rastreio estiver ligado algum dia. A correção vale para os dois casos.

**Regras cobertas:** ADR 0026, item 4 (M-01). Testes em `backend/tests/aceitacao/test_t265_leitura_crlv.py`:
- `test_t399_adr_0026_filho_so_com_path_e_lang_com_o_sentry_ligado`: liga o Sentry (opções do Giro sem `traces_sample_rate`, transporte de mentira). Primeiro confirma que um processo criado só pelo `env=` recebe o `SUBPROCESS_SENTRY_TRACE`, e depois confere que o filho da leitura tem só `LANG` e `PATH`. Sem o `env -i`, ele falha com o `SUBPROCESS_BAGGAGE` a mais (conferido).
- `test_adr_0026_pai_chama_isolado_sem_preexec_fn`: passa a conferir a linha de comando com o `env -i`, e os dois caminhos absolutos.
- `test_t270_sentry.py` e `test_t265_leitura_crlv.py` na mesma rodada, nessa ordem: 33 passaram, com o sentry-sdk 2.73.0. Ruff, format e mypy limpos nos arquivos mexidos.

**O que ficou de fora:**
- O texto do item 4 da ADR 0026 ainda descreve a chamada como `subprocess.run(..., env={...})`. A ADR é do arquiteto e ficou como estava.
- O `/usr/bin/env` existe nas imagens `giro-backend:latest` e `giro-backend:producao` (conferido). Fora do Docker, no Windows, a leitura não roda; ela já não rodava antes (o `PATH` do filho é de Linux).

**Próximo passo para quem recebe:**
- Segurança: rever o M-01 com o `env -i` (o pai ainda passa o `env` do Sentry ao `env`, que o descarta antes do `exec`).
- Arquiteto: atualizar a chamada citada no item 4 da ADR 0026, se quiser.
