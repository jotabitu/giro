# App `movimentacoes`

**Status:** aceita · 16 out 2026 · T-286 (regras `MOV-01` a `MOV-06`, decisão do dono de 16 out 2026, T-283) · detalha a 0011 e a 0015

## Contexto

As movimentações entraram no MVP (T-283). Uma movimentação leva um veículo da filial dele por locais de apoio até uma filial de destino. Ela mexe em quatro apps que já existem:

- `veiculos`: o status `em_movimentacao` (novo), o km da chegada e a transferência da `VEI-04` na chegada (`MOV-06`).
- `financeiro`: a despesa de cada parada com valor (`MOV-04`, `FIN-05`, `APR-03`).
- `locacoes`: iniciar é recusado se o veículo foi reservado ou alugado depois do agendamento (`MOV-03`), e a Nova locação não pode pegar o veículo que está saindo.
- `filiais` e `contas`: a filial de saída e a de destino, quem leva, quem recebe.

A ADR 0011 fixa a ordem de dependência dos apps; mudar a ordem pede ADR nova. O handoff da T-283 deixou em aberto se as movimentações ficam em `veiculos` ou num app novo.

## Decisão

### 1. App novo `movimentacoes`, no nível 11, ao lado de `vistorias`

```
 9. manutencao
10. locacoes
11. vistorias, movimentacoes
12. vendas
13. automacoes, relatorios
```

- **Por que não dentro de `veiculos`:** `veiculos` está no nível 6 e não pode importar de `financeiro` (8) nem de `locacoes` (10). A movimentação precisa dos dois: lança a despesa pelo serviço do financeiro e confere a locação aberta do veículo pelo selector de locações. Pôr isso em `veiculos` obrigaria a mandar tudo por evento, para cima, só para manter o app no lugar.
- **Por que no nível 11:** fica abaixo de `locacoes` (lê `locacoes.selectors.locacao_aberta(veiculo)`) e de `financeiro` (`financeiro.services.lancar_despesa`). Ninguém depende de `movimentacoes`: o que a Frota e a ficha mostram vem pelo registro de leituras da ADR 0015 (item 4). `vistorias` e `movimentacoes` ficam no mesmo nível e não se importam.
- Schema da empresa (`TENANT_APPS`). Estrutura de sempre (ADR 0011, item 4).

### 2. A vistoria rápida da chegada fica no próprio app

A chegada guarda o combustível e 4 fotos (`MOV-05`). Elas não viram uma `vistorias.Vistoria`: a vistoria de lá é da locação (pendências da `VIS-01`, painel obrigatório, avarias que vão para o acerto, agenda do vistoriador), e uma vistoria sem locação teria de desligar quase tudo isso. O app guarda `FotoChegadaMovimentacao` com as mesmas validações de arquivo de `comum.arquivos` (JPG ou PNG até 10 MB, imagem reprocessada e sem metadados de localização, armazenamento privado, URL de 15 minutos, `AUD-05`) e o combustível com o mesmo enum da vistoria (`reserva`, `um_quarto`, `meio`, `tres_quartos`, `cheio`). A agenda do vistoriador com as movimentações ficou fora do MVP (T-283).

### 3. Uma movimentação aberta por veículo, sem corrida com a locação

- Índice único parcial em `Movimentacao.veiculo` com `status IN ('agendada', 'em_transito', 'no_local')` (`MOV-03`). A segunda criação responde 409 pela restrição, mesmo em corrida.
- Criar, iniciar e "Sair agora" travam a linha do veículo (`veiculos.services.travar`, hoje `_travar`, que passa a ser público) antes de conferir o status e a locação aberta.
- `locacoes.services.confirmar` passa a travar a mesma linha do veículo antes de conferir a disponibilidade (`LOC-03`). Hoje ele trava só a locação: com o início no mesmo dia, o veículo segue `disponivel` até a ativação, e uma movimentação iniciada ao mesmo tempo passaria. Com as duas travas na mesma linha, uma espera a outra, e a segunda vê o status ou a locação já gravados.
- "Reservado ou alugado" da `MOV-03` inclui o veículo `disponivel` com locação `aguardando_retirada` (início hoje): para a movimentação, ele já tem dono. A recusa é 409 `MOV-03`.

### 4. O que os outros apps mostram vem por leitura registrada (ADR 0015)

`movimentacoes` registra, para `veiculos.Veiculo`:

- o bloco `movimentacao_aberta` (`{ id, codigo, status }` ou `null`) na lista e no detalhe, para a Frota mostrar "Em movimentação" nos veículos `indisponivel`, `em_manutencao` e `a_venda`, que mantêm o status (`MOV-03`);
- o bloco `movimentacoes` do detalhe (T-275);
- o filtro `?em_movimentacao=true` da Frota.

`veiculos` calcula `acoes.movimentar` com o perfil, o status e o bloco `movimentacao_aberta`. Sem o app instalado, o bloco vem `null`, e a ação, `false`.

### 5. A despesa nasce pela porta do financeiro, com origem

- Origem genérica nova: `movimentacao` entra no enum fechado de `origem_tipo` (ADR 0011, item 2). A despesa de uma parada sai com `origem_tipo = movimentacao`, o id e o código `MOV-0042` da movimentação.
- `financeiro.services.lancar_despesa` ganha o parâmetro `origem` (opcional) e continua aceitando `nota=None`. Quem exige a nota é a rota `POST /api/financeiro/despesas/` (`FIN-06`), que não muda.
- "Sem nota" não é campo: é a despesa sem `nota`. A representação da despesa ganha `sem_nota` (bool), e a nota pode ser anexada depois por uma rota nova do financeiro (`financeiro.md`).
- A despesa segue a `FIN-05` sem exceção: acima do limite da empresa, nasce `aguardando_aprovacao` com o pedido `APR-03`, que o financeiro já abre.

### 6. A transferência da chegada usa o serviço de `veiculos`

`veiculos.services.transferir` ganha a origem (`movimentacao`) e, com ela, não exige o veículo `disponivel`: o veículo pode chegar de uma movimentação estando `em_manutencao`, `indisponivel` ou `a_venda` (`MOV-03`, `MOV-06`). O resto da `VEI-04` vale igual: categoria no destino pedida na criação, `TransferenciaVeiculo` gravada, auditoria com a categoria de antes e a de depois.

A rota `POST /api/veiculos/{id}/transferir/` sai do contrato: "Transferir" na ficha abre a Nova movimentação (`MOV-06`), e a transferência só acontece na chegada. O backend remove a rota no mesmo PR em que o frontend troca o botão. A importação e o seed, que movem veículo entre filiais, usam o serviço.

## Consequências

- A ordem de dependência ganha `movimentacoes` no nível 11; o teste `test_limites_entre_apps.py` passa a conhecer o app.
- `veiculos` ganha o status `em_movimentacao` com as três transições das regras, o `travar` público, a origem na transferência e a leitura dos blocos acima. A tarefa diária de documentos (`AUT-06`, `VEI-03`) trata o `em_movimentacao` como o `alugado`: não muda o status e gera a tarefa urgente aos gerentes (`MOV-05`).
- `locacoes.services.confirmar` trava a linha do veículo. É uma linha a mais, sem mudança de regra.
- `financeiro` ganha a origem `movimentacao`, o `sem_nota` e a rota de anexar a nota.
- A ocupação (`VEI-06`) não muda: só `alugado` conta como alugado, e `em_movimentacao` conta como dia na frota (CA-246-12).
- Contrato em `docs/api/movimentacoes.md`; modelo nos itens 26 e 27 de `modelo-de-dados.md`.
