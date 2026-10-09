# Formato dos momentos na API: UTC com `Z`, por um ponto só

**Status:** aceita · 09 out 2026 · detalha o `docs/api/README.md` (Formatos) e a 0006 (T-088)

## Contexto

O `docs/api/README.md` pede momento em ISO 8601, UTC, com `Z` (`"2026-10-07T12:12:00Z"`). O backend tem `TIME_ZONE = "America/Sao_Paulo"` e `USE_TZ = True`, e hoje sai de três jeitos, conforme o caminho:

| Caminho | Exemplo (12:12:00,123456 UTC) | Onde |
| --- | --- | --- |
| `serializers.DateTimeField()` puro | `"2026-10-07T09:12:00.123456-03:00"` | aprovações (`pedido_em`, `decidido_em`), veículos (`km_atualizado_em`, `historico_status[].em`, `alterado_em`, `url_expira_em`), filiais (`criado_em`), plataforma |
| `datetime` solto num `dict` da resposta (encoder do DRF) | `"2026-10-07T12:12:00.123456Z"` | contas (`eu`, sessões, usuários, suporte), que montam o corpo à mão e usam o serializer só no OpenAPI |
| `DateTimeField(default_timezone=UTC)` ou `strftime` à mão | `"2026-10-07T12:12:00.123456Z"` ou `"2026-10-07T12:12:00Z"` | clientes (`_momento`), `contas/dois_fatores.py` (`tentar_de_novo_em`) |

Conferido no container do backend com DRF 3.18.3. Os testes de aceitação não pegaram a diferença porque o relógio congelado não tem fração de segundo e os casos que olham o momento passam pelo encoder. Em produção, quase todo momento vem de `timezone.now()` e tem microssegundos.

`TIME_ZONE` não pode virar `UTC`, nem a requisição pode ativar `UTC` com `timezone.activate`: `comum.relogio.hoje()` usa `timezone.localdate()`, e "hoje" (vencimento, atraso, caixa do dia) é o dia de São Paulo.

## Decisão

### 1. Formato único

- **Saída:** todo momento sai como `AAAA-MM-DDTHH:MM:SSZ`, em UTC, **sem fração de segundo**. É o exemplo do README, é o que o frontend e os testes já esperam, e o mesmo momento sai igual em qualquer rota. Data sem hora continua `"2026-10-21"`.
- **Entrada:** ISO 8601 com fuso (`Z` ou `-03:00`). O frontend sempre manda com fuso. Sem fuso, o DRF lê no horário de São Paulo (comportamento atual, sem mudança).
- Momento sem fuso (`datetime` *naive*) numa resposta é defeito: o renderizador levanta `TypeError` e o teste quebra, em vez de sair um horário ambíguo.

### 2. Um ponto de configuração, em `comum` e no DRF

O formato fica no **renderizador JSON**, e não em cada campo:

```python
# comum/renderizacao.py
class EncoderDoGiro(rest_framework.utils.encoders.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            if timezone.is_naive(obj):
                raise TypeError("Momento sem fuso na resposta da API (ADR 0020)")
            return obj.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        return super().default(obj)

class JSONRenderer(rest_framework.renderers.JSONRenderer):
    encoder_class = EncoderDoGiro
```

```python
# config/settings/base.py, dentro de REST_FRAMEWORK
"DATETIME_FORMAT": None,  # o DateTimeField devolve o datetime cru; quem formata é o renderizador
"DEFAULT_RENDERER_CLASSES": [
    "comum.renderizacao.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
],
```

Com `DATETIME_FORMAT = None`, o `DateTimeField.to_representation` do DRF devolve o `datetime` sem converter para o fuso do servidor. Assim, os dois caminhos de hoje (campo de serializer e valor solto no `dict`, inclusive em `detalhes` de erro) passam pelo mesmo encoder. Nenhum app precisa lembrar de nada.

Foi preferido a um `MomentoField` em `comum` porque o campo não cobre o valor solto no `dict` (contas inteiro, `detalhes.tentar_de_novo_em`), e cada serializer novo teria que lembrar de usá-lo.

### 3. O que fica proibido fora de `comum/renderizacao.py`

- `DateTimeField(format=...)` e `DateTimeField(default_timezone=...)`;
- montar momento em texto com `strftime("%Y-%m-%dT...")` para a resposta: passe o `datetime` com fuso;
- `renderer_classes` em view ou `APIView`: toda resposta JSON passa pelo renderizador de `comum`.

Texto para pessoas (e-mail, WhatsApp, PDF, `mensagem`) continua formatado no horário de São Paulo, como hoje (`plataforma/tasks.py`). Esta ADR trata só do JSON da API.

### 4. Teste de arquitetura

`backend/tests/test_formato_das_datas.py`:

- `test_adr_0020_campo_de_serializer_sai_em_utc_com_z`: `DATETIME_FORMAT` é `None` e um `DateTimeField` com 09:12:00,123456 em São Paulo sai `"2026-10-07T12:12:00Z"` pelo renderizador configurado;
- `test_adr_0020_valor_solto_na_resposta_sai_em_utc_com_z`: o mesmo para um `datetime` dentro de `detalhes` e de uma lista;
- `test_adr_0020_momento_sem_fuso_e_erro`;
- `test_adr_0020_ninguem_formata_momento_por_conta_propria`: varre `apps/` e `comum/` (fora de `tests/` e `migrations/`) e recusa os itens do item 3.

Os três primeiros entram como `xfail(strict=True)` até a T-093 ligar o renderizador: quando ela ligar, eles passam e o `strict` obriga a tirar a marca. O quarto já vale agora, com a lista `PENDENTES_T093` (os dois arquivos de hoje): arquivo novo que formata momento por conta própria quebra o teste já, e a T-093 esvazia a lista.

## Consequências

- **Tarefa do backend (T-093, "Momentos em UTC na API"):** criar `comum/renderizacao.py`, ligar as duas chaves no `REST_FRAMEWORK`, tirar o `_momento` de `clientes/api/serializers.py` (vira `DateTimeField` puro) e o `strftime` de `contas/dois_fatores.py` (passa o `bloqueado_ate`), tirar o `xfail` e esvaziar `PENDENTES_T093`. Com isso, contas, aprovações, plataforma, veículos, filiais e clientes ficam iguais sem tocar nos serializers deles.
- **Prova de conceito** (feita na T-088, fora do repositório): com essas mudanças, os quatro testes passam e o OpenAPI gerado sai idêntico (o tipo continua `string`, `format: date-time`). Ou seja, **o OpenAPI não muda** e o cliente tipado do frontend também não.
- **O que muda para quem consome:** as rotas de aprovações, veículos, filiais e plataforma deixam de sair com `-03:00`, e todas perdem a fração de segundo. O frontend já converte para `America/Sao_Paulo` ao exibir, então nada muda na tela. Comparação de momentos no frontend deve ser por `Date`, nunca por texto.
- `serializer.data` passa a ter `datetime`, e não texto, nos campos de momento. Quem usar `.data` fora de uma `Response` (gravar em JSON, mandar para tarefa Celery) passa o resultado por `comum.renderizacao.EncoderDoGiro`. Hoje ninguém faz isso.
- Ordenação e cursores não dependem do texto do momento, então perder a fração não muda a ordem das listas.
