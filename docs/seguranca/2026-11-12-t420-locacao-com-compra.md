# Locação com intenção de compra · 12 nov 2026

**Tarefa:** T-420 · **Autor:** seguranca · **Base:** PR #559 (Backend, `origin/t-420-locacao-com-compra-backend`, `6567f000`) e PR #560 (Backend 2, `origin/t-420-venda-da-quitacao`), sobre a `develop` de 12 nov; `LOC-16`, `VEN-11`, ADR 0037, `docs/api/locacoes.md` e `docs/api/vendas.md`.
**Escopo:** permissão por perfil e filial nas rotas novas, isolamento entre empresas, dinheiro (centavos, parcelas e caução), idempotência e corrida na quitação e na venda, mudança de status por serviço com auditoria, nada apagado, dado pessoal no aviso e na API de vendas.

## Resumo

Não achei nada alto. As permissões e o escopo de filial estão certos em todas as rotas novas. A quitação e a venda aguentam dois webhooks e dois cliques: a linha da locação fica travada, o `quitada_em` é conferido e a venda tem `locacao` única. O status só muda por serviço, sempre com auditoria. Nada se apaga, e a API de vendas só expõe o nome do cliente.

**Dois achados médios, os dois na condição da quitação do PR #559, com a mesma correção:**

- **M-01:** a quitação não confere se a caução foi paga. Com a caução cancelada (ou renegociada), a última parcela sai abatida mesmo assim, a locação quita e, se a caução for maior que a parcela, nasce um reembolso da "sobra" de um dinheiro que nunca entrou. **Provado com teste.**
- **M-02:** a quitação conta as parcelas pagas pelo `numero_parcela`. Uma parcela renegociada some da conta, e as contas novas nascem com os números 1, 2… O cliente paga tudo e a locação nunca quita. **Provado com teste.**

Há também quatro achados baixos, que não bloqueiam.

| Ponto | Como está | Onde conferi |
| --- | --- | --- |
| Quem cria plano de compra | `POST`, `PATCH` e `desativar`: só administrador; leitura: administrador, gerente e vendedor; vistoriador e financeiro: 403 | `PlanosCompraView`, `PlanoCompraView`, `DesativarPlanoCompraView` (#559) |
| Quem cria e confirma a locação da compra | os mesmos perfis da comum (`CRIAM`), com a filial do cabeçalho; plano ativo e da categoria do veículo; desconto, extras, plano especial, fim escolhido e parcelamento recusados no serviço, e o `CHECK locacao_tipo_campos` segura o desconto no banco | `_montar_compra`, `_recusar_fora_do_plano`, migração `locacoes/0008` |
| Quem encerra por atraso | administrador e gerente (`ENCERRAM_POR_ATRASO`); a locação vem de `filtrar_por_filial` (404 fora do escopo); motivo obrigatório; só `ativa`, só compra e só com parcela atrasada; linha travada, e o segundo clique dá 409 (`_sem_cancelamento_em_curso`) | `EncerrarPorAtrasoView`, `services.encerrar_por_atraso` (#559) |
| Quem registra a transferência | administrador e gerente, com conferência na view e de novo no serviço (perfil e `filiais_permitidas`); a locação vem de `filtrar_por_filial`; a venda fica travada (`select_for_update`), e a segunda vez dá 409 `VEN-11`; a data não pode ser depois de hoje nem antes da quitação | `TransferenciaView`, `registrar_transferencia` (#560) |
| Quem lê vendas | administrador e financeiro veem todas as filiais deles; gerente, as filiais dele; vendedor, só as vendas dele; vistoriador: 403; rota fechada sem o recurso `vendas_comissoes` (`PLT-12`) | `vendas/selectors.visiveis`, `ViewDeVendas` (#560); ver B-03 |
| Suporte Giro | as rotas novas usam `com_padrao`, que traz as permissões padrão (empresa operando, escopo e suporte); a ação `registrar_transferencia` do detalhe já sai falsa para o suporte | `comum/permissoes.com_padrao`; `locacoes/selectors._venda` |
| Vistoriador no detalhe | o bloco `compra` passa por `sem_valores`: os campos `_centavos` saem, inclusive o `valor_centavos` de `falta_para_quitar`; sobram o plano, as contagens e o `andamento` em texto, sem valor | `locacoes/api/views._detalhe`, `selectors.sem_valores` |
| Isolamento | `PlanoCompra` e `Venda` vivem no schema da empresa; o teste de isolamento do plano e o da lista de vendas passam nos dois PRs | `test_loc_16_isolamento_do_plano_entre_empresas`, `test_ven_11_*isolamento*` |
| Dinheiro em centavos | tudo inteiro: `ultima_parcela_da_compra = max(0, P − C)` e `sobra_da_caucao = max(0, C − P)`, sem `float`. Conferi a soma: com C ≤ P, o cliente paga (n − 1)·P + (P − C) + C = n·P; com C > P, paga (n − 1)·P + C e recebe C − P de volta, ou seja, n·P. A soma fecha **quando a caução foi paga** (M-01) | `locacoes/calculo.py` |
| Última parcela de R$ 0,00 | não vira conta (`financeiro` não cria conta zerada) e conta como paga só quando as outras n − 1 estão pagas | `parcelas_pagas`; `test_loc_16_ca_420_14_*`; ver M-02 |
| Corrida na quitação (dois webhooks) | o pagamento e o `financeiro.parcela_paga` rodam na mesma transação, e `quitar_se_pago` trava a linha da locação antes de ler as contas. Com dois pagamentos ao mesmo tempo, o segundo espera a trava e lê as contas depois do commit do primeiro (READ COMMITTED). Não há quitação perdida nem quitação dobrada (`quitada_em` conferido depois da trava) | `quitar_se_pago` (#559) |
| Idempotência da venda | `criar_venda_da_quitacao` só roda dentro da quitação, com a locação travada; devolve a venda que já existe; `Venda.locacao` é `OneToOne`. O aviso usa a `chave` `quitacao-transferencia-{id}` e sai depois do commit | `vendas/services.py` (#560) |
| Veículo `alugado` → `vendido` | só pela `vendas`, por `veiculos.services.transicionar` (trava, histórico e auditoria). Nenhuma ação manual do veículo leva a `vendido` (bloquear, desbloquear, à venda, voltar à frota e baixar têm destino fixo). Na compra, o veículo só sai de `alugado` na devolução, então ele está `alugado` na quitação | `veiculos/services.py`, `TRANSICOES_VEICULO` |
| Status por serviço e auditoria | `locacao.quitar` e `locacao.encerrar_por_atraso` (com motivo) por `estados.transicionar` e `auditar`; `venda.criar_da_quitacao` e `venda.registrar_transferencia` auditados; `plano_compra.criar/editar/desativar`; quitação e venda com o ator Sistema | diffs dos dois PRs |
| Nada apagado | plano desativa (`ativo=False`), venda não se cancela (409 `VEN-11`), FKs `PROTECT` | `desativar_plano_compra`, `vendas/services.cancelar` |
| Devolução da compra sem encerramento | a tela esconde "Registrar devolução", e a API também segura: a `DEV-07` (`antecipada_sem_aprovacao`) recusa a devolução antes do fim previsto sem o encerramento aprovado | `vistorias/services.py` |
| Dado pessoal | a API de vendas, a ficha do veículo e o aviso trazem só o nome do cliente, a placa e o código (sem CPF, CNH ou contato). O aviso vai aos gerentes da própria filial. O contrato da compra usa os mesmos marcadores pessoais do contrato comum | `vendas/selectors.representacao`, `_titulo_do_aviso`, `prontos.TEXTO_COMPRA` |

## Achados

### M-01 · média · A quitação abate e devolve uma caução que não foi paga

**PR:** #559 (Backend). **Onde:** `backend/apps/locacoes/services.py:2453` (`quitar_se_pago`), linhas 2472 e 2494; `parcelas_pagas` (linha 2430).

**O caso:** a quitação pede que nenhuma conta da locação esteja `aberta` e que as parcelas estejam pagas. Ela não confere se a **caução foi paga**. Uma caução `cancelada` ou `renegociada` não está `aberta` e passa. Nesse caso:

1. a última parcela continua com o valor abatido (P − C), ou nem existe, quando C ≥ P. O cliente leva o veículo pagando C a menos;
2. com C > P, `devolver_ao_cliente` gera um `Reembolso` Pix de C − P calculado sobre `locacao.caucao_centavos`, o valor previsto, e não sobre a caução que entrou.

Isso acontece sem ninguém fazer nada de errado no momento: basta uma retirada à mão (`LOC-17`, antes do 1º pagamento) e o gerente ou o financeiro cancelar a caução em aberto ("cliente sem caução"), que o `FIN-01` permite. O reembolso nasce `a_fazer`, e alguém precisa fazer o Pix. Mas ele aparece como devido, com o motivo "Sobra da caução na quitação", e nada mostra que essa caução nunca entrou.

**Reprodução (teste rodado, passa: o defeito existe):** plano semanal de 104 × R$ 199,00 e caução de R$ 300,00. A locação é confirmada, vistoriada e assinada, só com a 1ª parcela paga. Depois: `services.registrar_retirada`, `financeiro.cancelar(caucao)` e as parcelas 2 a 103 pagas. A locação fica `encerrada` com `quitada_em`, a caução continua `cancelada` e nasce um `Reembolso` de R$ 101,00. O teste está no fim deste relatório.

**Correção sugerida:** usar a caução paga, como o acerto já faz (`vistorias.services.caucao_paga`, `DEV-02`):

- quitar só se a caução paga (conta `caucao` `paga`, não estornada) for igual à `caucao_centavos` da locação. Sem ela, o andamento mostra a caução em "falta para quitar";
- calcular a sobra sobre a caução paga: `max(0, caucao_paga − P)`;
- teste `test_loc_16_quitacao_sem_caucao_paga_nao_quita`.

### M-02 · média · Parcela renegociada impede a quitação para sempre

**PR:** #559 (Backend). **Onde:** `backend/apps/locacoes/services.py:2430` (`parcelas_pagas`, o conjunto de `numero_parcela` na linha 2436).

**O caso:** `parcelas_pagas` conta os números distintos das contas `parcela` pagas e não estornadas. O `financeiro.renegociar` (`FIN-01`: administrador, gerente e financeiro) faz assim:

- a parcela original vai para `renegociada` e sai da contagem;
- as contas novas nascem na mesma origem e com o mesmo tipo `parcela`, mas numeradas **1, 2, …** (ou sem número, quando é uma só). Esses números já existem no conjunto;
- quando a renegociação junta contas de origens diferentes, as novas vão para a origem `cliente` e saem da locação.

Resultado: o cliente paga o acordo inteiro, nenhuma conta fica `aberta`, e a contagem nunca chega ao total. A locação fica `ativa` para sempre, sem quitação, sem venda e sem transferência. É o contrário do que o contrato promete ("Pagas todas as parcelas…, a locação fica quitada"). O mesmo cálculo de números deixa o caminho aberto a erro no outro sentido se um dia a renegociação passar a numerar acima do total.

**Reprodução (teste rodado, passa: o defeito existe):** plano de 24 × R$ 1.190,00. As parcelas 1 a 23 são pagas, e a 24ª é renegociada em duas contas de R$ 445,00, que nascem com os números 1 e 2. As duas são pagas. Fica zero conta `aberta`, `parcelas_pagas` dá 23, e a locação continua `ativa`, sem `quitada_em`.

**Correção sugerida (a mesma base da M-01):** decidir a quitação pelo dinheiro e pela origem das contas, não pelos números:

- cada parcela do plano conta como quitada se estiver `paga` (não estornada) ou se estiver `renegociada` e todas as contas que nasceram dela (`nasceu_de` da `Renegociacao`) estiverem pagas;
- e nenhuma conta da locação, nem conta nascida de uma renegociação dela (inclusive na origem `cliente`), pode estar em aberto.

Se o produto preferir proibir a renegociação de parcela da compra, a recusa tem que estar no `financeiro.renegociar`, com uma regra escrita. A dúvida vai para o Produto: hoje a `LOC-16` não fala de renegociação. Teste sugerido: `test_loc_16_parcela_renegociada_e_paga_quita`.

### B-01 · baixa · A quitação deixa aberto o pedido de cancelamento (`APR-02`)

**PR:** #559. **Onde:** `quitar_se_pago`.

**O caso:** um vendedor pede o cancelamento, o pedido fica `pendente`, e o cliente paga a última parcela. A locação quita, mas o pedido continua na fila de aprovações. Quando alguém tenta aprovar, `_pode_cancelar` recusa (a locação está `encerrada`), e o pedido não se resolve pela fila.

**Sugestão:** na quitação, fechar o pedido aberto, como a `AUT-17` já faz na não retirada (`LOC-12`: "o pedido de desconto ou de cancelamento ainda aberto é fechado"), com o evento do Sistema.

### B-02 · baixa · "Encerrar por atraso" aceita qualquer data no futuro

**PR:** #559. **Onde:** `EncerrarPorAtrasoSerializer` (`locacoes/api/serializers.py:89`) e `_dia_do_cancelamento` (só recusa data passada).

**O caso:** um encerramento por atraso com data daqui a dois anos marca `encerramento_antecipado_aprovado_em`. A partir daí, a quitação fica bloqueada para sempre, mesmo que o cliente pague tudo. O atraso da `LOC-10` só corre depois dessa data, e as parcelas até lá continuam devidas. Pode ser engano de digitação ou de quem quer segurar a locação. Hoje o cancelamento comum aceita a mesma coisa.

**Sugestão:** limitar a data, por exemplo a hoje mais 30 dias ou ao vencimento da próxima parcela, a definir com o Produto. Ou aceitar só hoje no encerramento por atraso, que é uma ação da locadora e não um pedido do cliente.

### B-03 · baixa · `GET /api/vendas/` ignora a filial escolhida no cabeçalho

**PR:** #560. **Onde:** `backend/apps/vendas/selectors.py:32` (`visiveis` usa `filiais_permitidas(usuario)`).

**O caso:** as outras listas filtram pelo escopo da requisição (`X-Filial`) com `filtrar_por_filial`, que o `filiais.selectors` chama de "o único jeito" (`USR-07`). A lista de vendas devolve as vendas de todas as filiais da pessoa, mesmo com uma filial escolhida. Não vaza nada de fora das filiais dela, mas é diferente do resto e confunde a contagem da tela.

**Sugestão:** `filtrar_por_filial(selectors.visiveis(usuario), request)` na view, mantendo o filtro do vendedor. No detalhe, o mesmo.

### B-04 · baixa · A tarefa da transferência pode não chegar a ninguém

**PR:** #560. **Onde:** `vendas/services._avisar_gerentes` (linha 54).

**O caso:** o aviso vai só aos gerentes ativos da filial. Numa filial sem gerente (empresa pequena, só com o administrador, ou gerente desligado), ninguém recebe a tarefa. As `pendencias` do painel ainda não leem `transferencias_pendentes` (fica para depois, como diz o PR). A transferência no Detran tem prazo legal, e enquanto ela não sai, a locadora continua respondendo pelo veículo.

**Sugestão:** sem gerente ativo na filial, avisar os administradores (a confirmar com o Produto, porque a `LOC-16` fala só dos gerentes da `FIL-02`). Ligar as pendências do painel na mesma leva, numa tarefa à parte se precisar.

## Teste usado na prova

O teste rodou num contêiner avulso na rede `giro-backend-teste`, com o banco próprio `giro_seg_t420` (`--create-db`), sobre um worktree temporário do PR #559, e passou (2 testes, 42 s). Ele **não** está neste PR e não vai para o repositório: ele confirma o defeito, e o teste da correção é outro (o que pede "quita" ou "não quita"). Os trechos que importam:

```python
def test_sonda_caucao_cancelada_quita_e_devolve_sobra(compra):
    plano_ = _criar_plano(compra, nome="Compra Street 104 semanas", periodicidade="semanal",
                          parcelas=104, valor_parcela_centavos=19900)
    locacao = _confirmada(compra, plano_["id"])
    _vistoriar(locacao.pk); _assinar(locacao.pk)
    _pagar(locacao, 1)                                   # a caução fica aberta
    services.registrar_retirada(locacao, "Cliente sem a caução hoje")
    caucao = ContaReceber.objects.get(origem_tipo="locacao", origem_id=locacao.pk, tipo="caucao")
    financeiro.cancelar(caucao, motivo="Dispensada")
    _pagar(locacao, *range(2, 104))
    locacao.refresh_from_db()
    assert locacao.status == "encerrada" and locacao.quitada_em is not None
    assert Reembolso.objects.get().valor_centavos == 10100

def test_sonda_parcela_renegociada_nunca_quita(compra, plano):
    locacao = _retirada(_confirmada(compra, plano["id"]))
    _pagar(locacao, *range(2, 24))
    ultima = [c for c in _contas(locacao) if c.numero_parcela == 24][0]
    novas = financeiro.renegociar([ultima], [financeiro.ContaNova(date(2028, 10, 10), 44500),
                                             financeiro.ContaNova(date(2028, 11, 10), 44500)],
                                  motivo="Acordo", usuario=None)
    assert sorted(c.numero_parcela for c in novas) == [1, 2]
    for conta in novas:
        financeiro.marcar_paga(conta, forma="pix")
    assert services.parcelas_pagas(locacao) == 23
    assert Locacao.objects.get(pk=locacao.pk).status == "ativa"
```

## Recomendação

- **#559:** corrigir M-01 e M-02 antes do merge, no mesmo PR ou numa tarefa logo atrás, antes de ligar a compra para alguma empresa. As duas mexem na mesma função (`quitar_se_pago` e `parcelas_pagas`). B-01 e B-02 podem ir junto.
- **#560:** pode entrar como está. B-03 e B-04 viram tarefa baixa.
- **Produto:** dizer na `LOC-16` o que acontece com parcela renegociada e com caução não paga (M-01 e M-02) e se a data do encerramento por atraso tem limite (B-02).
