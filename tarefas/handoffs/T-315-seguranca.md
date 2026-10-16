# T-315 · Revisão de segurança das Movimentações · segurança → orquestrador, backend, produto

**O que foi feito:** revisão da T-288 parte 1 (PR #324): suporte, `pessoas/` e `recebedores/`, fotos da vistoria rápida, nota da despesa da parada, baixa que cancela e isolamento. Relatório: `docs/seguranca/2026-10-16-t315-movimentacoes.md`.
**Onde:** `backend/tests/aceitacao/test_t315_seguranca_movimentacoes.py` (7 testes e 2 `xfail` estritos). Nenhum código de produção mudou.
**Regras cobertas:** MOV-02 a MOV-06, PLT-07, AUD-01, AUD-05, FIN-06 (testes `test_plt_07_*`, `test_aud_05_*`, `test_aud_01_*`, `test_mov_02_*`, `test_mov_03_*`).
**Testes rodados:** ruff, ruff format e mypy no arquivo novo; `test_t315_seguranca_movimentacoes`, `test_t288_movimentacoes` e `test_plt_07_lista_de_rotas_que_o_suporte_le`: 36 passed, 2 xfailed.

**Resposta à pergunta do backend:** confirmado. O suporte em "só ver" lê o quadro, a lista, `pessoas/`, `recebedores/` e os locais, sem URL assinada, e recebe 403 `PLT-07` no detalhe e no envio de foto (ADR 0013, item 2).

**Achados:** M-01 (média), B-01, B-02, B-03 (baixas). O resto está conforme: listas sem contato e só das filiais com acesso, fotos validadas pelo conteúdo, até 10 MB, sem EXIF, com nome aleatório e privadas, nota que nunca é trocada, baixa com o ator de quem baixou e isolamento por schema.

**Ordem de merge:** esta branch tem o merge da `t-288-movimentacoes-backend`, e o teste usa o código dela. Ela só entra depois do PR #324.

**Tarefa de backend para numerar:**

```
### T-??? · Suporte nas escritas das movimentações e o rastro das fotos da chegada
- **Agente:** backend · **Depende de:** T-288 parte 1 (PR #324), a escolha do produto (abaixo) · **Regras:** PLT-07, AUD-01, MOV-05 · **Severidade:** média · **Origem:** T-315 (segurança), M-01, B-01 e B-02 de `docs/seguranca/2026-10-16-t315-movimentacoes.md`
- **Pronto quando:**
  - o suporte em "ver e editar" não recebe 500 nas rotas de escrita das movimentações. Padrão proposto: `suporte_proibido = True` em criar, editar, iniciar, cancelar, chegada e saída da parada, fotos e chegada, com 403 `PLT-07` (o suporte não leva veículo). O detalhe segue legível em "ver e editar". Tirar o `xfail` de `test_plt_07_suporte_ver_e_editar_cria_sem_erro` (aceita 201 ou 403);
  - o envio da foto da chegada gera o evento `movimentacao.foto_chegada` (posição, id da foto, `substituiu`, sem URL), ou o `movimentacao.concluir` guarda os ids das 4 fotos. Tirar o `xfail` de `test_aud_01_foto_da_chegada_trocada_fica_na_auditoria` (ajustar o filtro ao evento escolhido);
  - `exigir_chegada` antes de `arquivos.validar` e `sem_metadados` em `enviar_foto` e `sair_parada`.
```

**Para o produto (`[decisão]` pequena, com padrão):** o suporte Giro em "ver e editar" pode criar e conduzir uma movimentação? **Padrão: não** (403 `PLT-07`). A movimentação tem quem leva e quem recebe, que são pessoas da empresa.

**Sugestões sem tarefa própria (para o orquestrador decidir):**
- **Varredura do suporte nas escritas (M-01, fora desta revisão):** o mesmo `*_por=usuario` num campo que exige `contas.Usuario` aparece no financeiro (`lancada_por`, `aberto_por`, `fechado_por`, `feito_por`). Um teste que percorra as rotas de escrita com token de suporte "ver e editar" e exija "nunca 500" pega todos de uma vez. Sugiro como tarefa de QA ou de backend.
- **B-03:** nota de despesa em imagem sem EXIF (`arquivos.sem_metadados`), em `comum`, para todas as notas.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar a tarefa de backend, levar a `[decisão]` ao produto e decidir sobre a varredura.
- **Backend:** ao corrigir, tirar os dois `xfail` deste arquivo.
