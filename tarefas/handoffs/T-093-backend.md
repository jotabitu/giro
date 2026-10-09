# T-093 · Momentos em UTC na API · backend → orquestrador, frontend, qa

**O que foi feito (ADR 0020):**
- `backend/comum/renderizacao.py` traz o `EncoderDoGiro` e o `JSONRenderer`, como na ADR. O momento sai `AAAA-MM-DDTHH:MM:SSZ`, em UTC e sem fração de segundo. Um momento sem fuso levanta `TypeError`.
- O `REST_FRAMEWORK` ganhou duas chaves, dentro do dict: `DATETIME_FORMAT: None` e `DEFAULT_RENDERER_CLASSES`. A primeira classe é o renderizador de `comum`, e o `BrowsableAPIRenderer` vem depois.
- `clientes/api/serializers.py`: o `_momento` saiu e os campos viraram `DateTimeField` puro.
- `contas/dois_fatores.py`: o `tentar_de_novo_em` passa o `bloqueado_ate` sem `strftime`.
- Locações não precisou de mudança: o `_momento` de `locacoes/api/serializers.py` já é `DateTimeField` puro desde o ajuste da T-015.
- `backend/tests/test_formato_das_datas.py`: os 3 testes de comportamento passam sem `xfail`. `PENDENTES_T093` ficou vazia, então qualquer arquivo novo que formate momento por conta própria quebra o teste.

**O que muda para quem consome:**
- Contas, aprovações, plataforma, veículos, filiais, clientes e locações saem todos com `Z` e sem fração. Antes, aprovações, veículos, filiais, plataforma e locações saíam com `-03:00`.
- Nenhum serializer desses apps foi tocado. O formato vem do renderizador.
- **Frontend:** o tipo não muda. Compare momentos por `Date`, nunca por texto.
- **QA:** nos testes, compare o momento com `Z` e sem fração, ou compare como `datetime`.
- `serializer.data` agora tem `datetime` nos campos de momento. Quem usar `.data` fora de uma `Response` passa o resultado por `comum.renderizacao.EncoderDoGiro`. Hoje ninguém faz isso.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `490 passed, 13 xfailed`. Antes eram 487 passed e 16 xfailed: os 3 `xfail` da ADR 0020 viraram passed, e os 13 que sobram são da T-015 (T-090 a T-092).
- Os 427 avisos do pytest são `InsecureKeyLengthWarning` da chave JWT de teste (`config/settings/test.py`). Não vêm desta tarefa.
- O OpenAPI foi regerado com `--validate` e saiu idêntico.
- Rodei no Postgres descartável, com `rodar.sh` (`--rm`, `POSTGRES_HOST`), na imagem `giro-backend:latest`.

**Próximo passo:**
- **Orquestrador:** abrir o PR.
- **QA:** conferir as rotas de aprovações e veículos, que eram as que saíam com `-03:00`.
