# Fundação comum dos models (`backend/comum/`)

**Status:** aceita · 07 out 2026 · complementa a 0003

## Contexto

Todo módulo precisa das mesmas peças: chave primária, datas de criação, código legível sequencial, dinheiro em centavos, status com transições fechadas, erro de negócio com código da regra e evento de auditoria. Se cada app fizer do seu jeito, os testes e a auditoria ficam desiguais. A ADR 0003 diz que o arredondamento é só na exibição, mas percentuais (desconto, multa, comissão, juros) geram frações de centavo e precisam de uma regra de arredondamento no cálculo.

## Decisão

`backend/comum/` é um pacote Django (app `comum`, instalado nos dois schemas) que nenhum outro app pode contornar. Ele não importa nenhum app de domínio.

| Módulo | O que oferece |
| --- | --- |
| `comum/models.py` | `ModeloBase` (abstrato): `id` `BigAutoField`, `criado_em`, `atualizado_em` (UTC). `ModeloAtivavel`: `ativo` (bool, padrão `True`) e manager `ativos`. `ModeloComCodigo`: `numero` (int) e `codigo` (texto, único no schema), preenchidos no primeiro `save()` a partir de `PREFIXO_CODIGO`. `Sequencia`: tabela de contadores (`chave` única, `ultimo_numero`). |
| `comum/codigos.py` | `proximo_numero(chave)`: `SELECT ... FOR UPDATE` na `Sequencia` dentro da transação; sem buracos (rollback devolve o número). Largura mínima por prefixo: `LOC` 4, `VEN` 4, `OS` 3, `FAT` 4 (`LOC-2856`, `VEN-0177`, `OS-118`, `FAT-2209`). O seed ajusta `ultimo_numero` para os números de referência. |
| `comum/campos.py` | `CentavosField` (`PositiveBigIntegerField`) para valores que nunca são negativos; `CentavosComSinalField` (`BigIntegerField`) só para saldos, diferenças e extrato. `PercentualField` (`DecimalField(5, 2)`). Nome do campo sempre termina em `_centavos` ou `_pct`. |
| `comum/dinheiro.py` | `aplicar_percentual(valor_centavos, pct) -> int`, `proporcional(valor_centavos, numerador, denominador) -> int` e `dividir_em_parcelas(total_centavos, n) -> list[int]` (diferença na última, ADR 0003). Contas intermediárias em `Decimal`; o resultado de cada valor calculado é arredondado para o centavo com `ROUND_HALF_UP`. Nenhum `float` em lugar nenhum. |
| `comum/estados.py` | `MaquinaDeEstados`: o model declara `TRANSICOES = {de: {para, ...}}` e `REGRA_TRANSICAO = "VEI-xx"`. `transicionar(objeto, novo_status, *, motivo=None)` valida, grava com `update_fields`, registra o evento de auditoria e levanta `TransicaoInvalida` (HTTP 409) fora da tabela. É a única forma de mudar `status`; o `save()` dos models com máquina recusa mudança de `status` que não venha dela. |
| `comum/erros.py` | `ErroDeRegra(codigo, mensagem, detalhes=None)` → HTTP 422; `TransicaoInvalida` e `Conflito` → HTTP 409; `LimiteDoPlano` (`PLT-03`) → HTTP 422; `EmpresaSemOperacao` (empresa `suspensa`, `pausada` ou `cancelada`) → HTTP 403. Exception handler do DRF devolve sempre `{"codigo", "mensagem", "detalhes"}`; erro de validação de campo devolve `{"codigo": "validacao", "mensagem", "campos": {campo: [mensagens]}}`. |
| `comum/auditoria.py` | `ator_atual()` (contextvar com usuário, IP, aparelho, suporte), `auditar(objeto, acao, categoria)` (context manager que tira o retrato antes e depois e grava o evento na mesma transação) e `registrar_evento(...)` para ações sem objeto (login, exportação). Detalhes na ADR 0010. |
| `comum/eventos.py` | despachante de eventos de domínio entre apps (ADR 0011). |
| `comum/tarefas.py` | `para_cada_empresa(...)` e `na_empresa(schema)` para o Celery (ADR 0012). |
| `comum/permissoes.py` | classes DRF por perfil, por filial (`USR-07`) e por permissão extra (`USR-03`); `EmpresaOperando` recusa escrita quando a empresa não está `em_teste`, `ativa` ou `inadimplente`. |
| `comum/arquivos.py` | storage privado S3 com prefixo `<schema>/<app>/<model>/<id>/` e URL assinada de 15 minutos (`AUD-05`). |

Models de domínio herdam de `ModeloBase` (sempre) e de `ModeloAtivavel`, `ModeloComCodigo` ou `MaquinaDeEstados` quando a entidade pede. Models com filial usam um campo `filial = ForeignKey("filiais.Filial", PROTECT)` declarado no próprio model, não em `comum` (que não conhece apps de domínio).

## Consequências

- O backend implementa tudo isso em T-001, com teste para cada peça: sequência sem buracos sob concorrência, divisão de parcelas (`16.068,00 / 12 = 1.339,00`), percentual (`3% de 21.068,00 = 632,04`), transição recusada com 409, formato do erro.
- `ROUND_HALF_UP` no centavo é o modo de arredondamento do sistema; se o produto definir outro para algum cálculo, a regra prevalece e vira parâmetro da função.
- Nenhum valor monetário é guardado com sinal sem o sufixo e o campo próprios, o que deixa o banco recusar valor negativo onde ele não faz sentido.
