# T-118 · Regra do encerramento aprovado com devolução no fim previsto · produto → orquestrador, backend, qa

Em 10 out 2026, o dono do produto decidiu a `[decisão]` que o backend levantou na T-117. Ficou a **opção A**, que é o que o código da T-117 já faz.

A situação: o encerramento antecipado foi aprovado, mas a devolução acontece no dia do fim previsto ou depois. Nesse caso a devolução **não é antecipada**:

- não há multa nem crédito da `LOC-12`;
- passando do prazo, cobra o atraso da `LOC-10`.

**O que foi feito:**

- **`docs/regras-de-negocio.md`:**
  - `DEV-07`: frase nova depois de "antes da hora, não é antecipada.". O exemplo agora cita também o caso novo.
  - Notas de mudança da T-118, datadas de 10 out, no fim de Vistoria e devolução e de Dados de referência.
  - Caso de referência novo: "Encerramento aprovado e devolução no fim previsto", com o caso 1 e a variante de 30 out.
  - Linha nova na tabela de decisões.
- **`tarefas/backlog.md`:**
  - a `[decisão]` da T-117 saiu e virou uma linha de registro;
  - entrou uma `[decisão]` nova da T-118, sobre o status final da locação (ver abaixo);
  - foi criada a T-119 (backend, teste).

**Caso de referência:** Carlos, LOC-2841, com a aprovação para 07 out (estimativa: multa 5988), devolve em 28 out às 09:00. Nada foi pago depois de 07 out.

| Item | Valor |
| --- | --- |
| Parcela 2 (30 set, 28 dias) | 30818 |
| Parcela 3 (07 out, 21 dias) | 30749 |
| Parcela 4 (14 out, 14 dias) | 30679 |
| Parcela 5 (21 out, 7 dias) | 30609 |
| Multa de encerramento | nenhuma (0 dias restantes) |
| Cobranças | 122855 |
| Caução | 30000 |
| **Cobrar** | **92855** |

Ao encerrar:

- nenhuma parcela é cancelada;
- as parcelas 2 a 5 vão para `renegociada`;
- nasce uma conta `acerto` de 92855 com vencimento em 31 out.

Variante (opcional): devolução em 30 out às 09:00. As parcelas dão 122935 e o atraso de 2 diárias dá 10980, então cobra **103915**.

**Casos existentes:** nenhum muda. O CA-016-24 continua com 36537, o CA-016-25 com 67377 e a Patrícia (LOC-2812) com 8480 de multa e 28620 a devolver.

## Status final da locação: ficou em `[decisão]`

O esperado era o encerramento normal: `encerrada` (`DEV-06`), com o pedido aprovado sem efeito. O código da T-117 faz outra coisa:

- `locacoes.services.encerrar` manda a locação para `cancelada` sempre que há `encerramento_antecipado_aprovado_em`, sem olhar o dia da devolução;
- ele também grava `cancelada_em` e registra o evento com o motivo "Encerramento antecipado: ..." e a regra `LOC-12`;
- `vistorias.services.iniciar_devolucao` copia a `cancelamento_forma` para a devolução.

Por isso a regra e o caso de referência **não dizem** o status final. A pergunta está no backlog, de forma fechada:

- **Opção A (padrão sugerido):** `encerrada`;
- **Opção B:** `cancelada`, como o código faz hoje.

## Próximo passo para quem recebe

- **Orquestrador:** abrir o PR e levar a `[decisão]` do status final ao dono do produto.
- **Backend (T-119):** escrever `test_dev_07_encerramento_aprovado_devolucao_no_fim_previsto_sem_multa` com os números acima. Não há mudança de produção. O teste não confere o status da locação até a `[decisão]` ser respondida. Como no CA-016-24, a caução de 30000 vai na fixture.
- **QA:** conferir o caso novo quando a T-119 entrar.
