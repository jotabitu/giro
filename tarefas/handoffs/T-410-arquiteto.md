# T-410 · Contrato da reserva na confirmação e do cancelamento automático · arquiteto → backend, frontend, qa

**O que foi feito:** o contrato da T-410 a partir das regras do PR #454 (produto) e da ADR 0035, nova. Este PR sai da branch do produto e depende do #454: mergear o #454 antes.

1. **ADR 0035** (`docs/decisoes/0035-reserva-e-contas-antes-da-retirada.md`): a conta guarda que espera a retirada (`ContaReceber.aguarda_retirada` e `liberada_em`), porque `financeiro` está abaixo de `locacoes` e o atraso é calculado pela data em muitos lugares; `q_atrasada` e `q_vence_hoje` viram as únicas expressões do atraso; a reserva é sempre na confirmação; a `AUT-17` em `locacoes`, pelo estado (execução perdida se recupera sozinha); o cancelamento automático reaproveita o núcleo do cancelamento antes da retirada; evento `locacoes.locacao_cancelada` para `vistorias` descartar a saída em rascunho; aviso no sino e por e-mail.
2. **`docs/api/locacoes.md`:** ciclo de vida; confirmação reserva com qualquer início e exige `disponivel`; 409 `inicio_vencido` (com `detalhes.inicio` e `detalhes.ultimo_dia_retirada`), conferido logo depois do `transicao_locacao`; o mesmo como impedimento na simulação; o `reservado` deixou de passar na Nova locação; `prazo_retirada` e `cancelamento.automatico` no detalhe; seção "Cancelamento automático da locação não retirada" (tabela do que muda, aviso com tipo, título, link, chave); interface interna.
3. **`docs/api/veiculos.md`:** `situacao.rotulo` "Reservado na LOC-2856" e bloco `reserva` (`locacao_id`, `codigo`, `motivo`: `locacao` ou `troca`); `locacao_atual.pagamento` da locação aguardando é sempre `em_dia`.
4. **`docs/api/financeiro.md`:** conta à espera da retirada fica `aberta`, na aba `a_vencer`, fora de atraso, indicadores, faixas, régua e contador; `valor_hoje` sem multa nem juros; `FIN-03` com `liberada_em`; `aguarda_retirada` na representação; interface interna.
5. **Modelo de dados:** os dois campos da conta e a nota da locação `aguardando_retirada`.

**Regras cobertas:** tabela de transições do veículo, `LOC-05`, `LOC-12`, `FIN-03`, `AUT-17`, `MOV-03`. Critérios: `docs/qa/criterios/T-410.md` (CA-410-01 a 23).

## Backend: o que mudar (uma branch)

1. **`financeiro`**
   - Migração: `ContaReceber.aguarda_retirada` (bool, padrão `false`) e `liberada_em` (data, nula).
   - `selectors.q_atrasada(hoje)` e `q_vence_hoje(hoje)`, com `aguarda_retirada=False`. Trocar todos os `Q(status=ABERTA, vencimento__lt=hoje)` e `vencimento=hoje` de conta a receber por elas: `financeiro/selectors.py` (linhas 192, 263, 276, 377, 378, 638 e as faixas em 351 a 354), `financeiro/leituras.py`, `financeiro/api/serializers.py` (status calculado, `faixa_atraso`, `dias_atraso`), `financeiro/services.py` (régua `AUT-03`, `parcela_atrasou`, bloqueio `CLI-05`), `locacoes/leituras.py`, `vistorias/services.py`, `plataforma/services.py`. Busque `vencimento__lt` e `vence_hoje` de novo no fim: em conta a receber, não pode sobrar nenhum à mão.
   - `devido_ate`: `aguarda_retirada` → multa e juros 0; senão, `inicio = max(vencimento, dia em que nasceu, liberada_em or vencimento)`.
   - `services.criar_contas(..., aguarda_retirada=False)` e `liberar_contas_da_retirada(origem, dia)`, idempotente.
   - `notificacoes.services.avisar(..., por_email=False)`: com `True`, e-mail depois do commit só para quem recebeu o aviso agora, com o remetente da locadora.
2. **`locacoes`**
   - `confirmar`: 409 `inicio_vencido` logo depois do `transicao_locacao`; trava o veículo, exige `disponivel` (senão `LOC-03`) e reserva sempre (sai o `if data_local(...) > relogio.hoje()` da linha 540); contas com `aguarda_retirada=True` (também as refeitas pela aprovação do desconto); aviso da `AUT-17` na hora se confirmada no último dia depois das 08:00.
   - `impedimentos`: o `reservado` deixa de passar (linha 213); impedimento `inicio_vencido`.
   - `verificar_ativacao`: `financeiro.liberar_contas_da_retirada(origem, dia local)` na mesma transação da `ativa`.
   - `selectors.ultimo_dia_retirada(locacao)`: data local do `inicio` + 3. Uma função só.
   - `services.cancelar_nao_retirada(locacao_id)` (núcleo do `_aplicar_cancelamento`, motivo "Não retirada em 3 dias da data de início", auditoria `locacao.cancelar_nao_retirada`, ator Sistema, reembolso `estorno_cartao` se o 1º pagamento foi no cartão, senão `pix`, sempre `a_fazer`) e `avisar_nao_retirada(locacao)` (gerentes da filial, texto, link e chave do contrato).
   - Evento `locacoes.locacao_cancelada` depois do commit de todo cancelamento antes da retirada, pedido ou automático; `vistorias` assina e descarta a saída em rascunho.
   - Tarefas `aut_17_cancelar_nao_retiradas` (00:10) e `aut_17_avisar_nao_retiradas` (08:00), com as `_de_todas` no Beat (`config/settings/base.py`) e o módulo `locacoes_vistoria`.
   - Detalhe: `prazo_retirada` e `cancelamento.automatico`.
3. **`veiculos` / leituras:** bloco `reserva` fornecido por `locacoes` (ADR 0015), anotado na lista; `situacao.rotulo` "Reservado na LOC-x".
4. **Acerto do ambiente** (CA-410-23): migração de dados ou comando `acertar_reservas_t410`, idempotente: contas abertas de locação `aguardando_retirada` com `aguarda_retirada=True`; veículo `disponivel` dessas locações para `reservado`, motivo "Reserva da LOC-x". As que passaram do prazo caem na próxima `AUT-17`.
5. **Seed:** em 07 out, o SAK-1D39 (LOC-2856) fica `reservado`; conferir o comentário de `seed/frota.py` ("SAK1D39 fica alugado"). Nenhum valor muda (LOC-2836 R$ 958,00, caixa de 07 out R$ 1.111,90).
6. **Testes** com o código no nome: `test_loc_05_nada_vence_antes_da_retirada` (Receber, painel, régua, bloqueio, análise do cliente, lista de locações, ficha do veículo), `test_fin_03_retirada_sem_multa`, `test_loc_12_inicio_vencido`, `test_loc_12_cancelamento_automatico`, `test_aut_17_execucao_perdida`, `test_aut_17_aviso_uma_vez`, `test_vei_reserva_na_confirmacao`. Rodar o OpenAPI e o `api:gerar` (campos novos: `prazo_retirada`, `cancelamento.automatico`, `reserva`, `aguarda_retirada`).

## Frontend: o que mudar (depois do backend)

- Frota e ficha do veículo: mostrar `situacao.rotulo` como vem ("Reservado na LOC-2856"); se quiser o link, `reserva.locacao_id`. Nada de montar o texto.
- Nova locação: o impedimento `inicio_vencido` aparece como os outros (`impedimentos`), e o 409 de mesmo código no confirmar mostra a `mensagem`. Nenhuma conta de data na tela.
- Locação: o detalhe da cancelada automática mostra o motivo que vem; `prazo_retirada` só se a tela de referência pedir (hoje não pede).
- Receber, sinais e ficha: nada muda na tela; os status já vêm certos da API.

## Pontos para o orquestrador

- **Push:** a regra pede sino, push e e-mail no aviso. O push não existe no código nem tem contrato; a `AUT-17` sai com sino e e-mail. Anotado no backlog da T-410.
- **Vistoria de saída em rascunho:** o cancelamento pedido antes da retirada também não a descartava; o evento novo corrige os dois casos.
- **Janela de 00:00 a 00:10:** retirada concluída nesses minutos do dia seguinte ao prazo leva a `ativa`, e a locação não cai (ADR 0035, item 3). Se o produto quiser recusar a ativação pela hora, é regra nova.
- Os três pontos em aberto do produto continuam com o padrão A; a opção B do período pediria outra ADR.
