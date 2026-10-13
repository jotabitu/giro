# Backlog

Ordem = prioridade. A fase 1 entrega o MVP (rodar uma locação de ponta a ponta numa filial piloto). O orquestrador revisa esta lista a cada fim de tarefa.

## Decisões

As pendências de regra foram decididas em 07 out 2026 (seção "Decisões de 07 out 2026" de `docs/regras-de-negocio.md`). Continuam com o dono do produto, fora do código:

- [bloqueada] Registrar girolocadoras.com.br e girolocacao.com.br.
- [bloqueada] Busca no INPI da marca "Giro" (classes 42 e 9).
- [bloqueada] Abrir a conta do Asaas (a integração começa no sandbox, não depende disso).
- (T-013) A transferência de veículo com categoria só da filial (`VEI-04`) foi decidida em 08 out 2026 pelo dono do produto: opção B, recomendada pelo produto (na transferência, pedir a categoria do destino só quando a atual não vale lá). Virou regra na T-082 (PR #71) e vira código na T-083.
- (T-081) Aprovar uma correção de km (`APR-06`) depois que outra leitura mudou o km foi decidido em 08 out 2026 pelo dono do produto: fica como está. A aprovação responde 409 `km_mudou`, o pedido continua pendente, e o gerente recusa e pede de novo com o km atual. Assim a leitura mais nova não é apagada. O produto registra a regra na próxima tarefa de regras de veículos.
- (T-079) Documento (CRLV ou seguro) que vence com o veículo `reservado` ou em `manutencao` foi decidido em 08 out 2026 pelo dono do produto: as duas coisas juntas. A `AUT-06` gera tarefa urgente aos gerentes, como no `alugado`, e a retirada é recusada até renovar. Virou regra na T-084 (PR #76); a tarefa urgente vai na T-085 e a recusa da retirada na T-016.
- (T-014) As duas leituras do backend foram confirmadas em 09 out 2026 pelo dono do produto: CNH C, D ou E aluga carro (`CLI-02`, CTB art. 143), e cliente `bloqueado` não pode ser inativado sem antes desbloquear (`CLI-09`). Viraram regra na T-087 (PR #83); os testes ganham os casos novos na T-089.
- (T-088) A ocupação da `VEI-06` com mudança de status no meio do dia foi decidida em 09 out 2026 pelo dono do produto: opção A, vale a fração de dia, como o código da T-013 já faz. Virou regra na T-094 (PR #89); o teste entra na T-096.

A dúvida da segurança S-02 (T-032: o suporte Giro vê CPF e CNH completos?) foi decidida em 07 out 2026 e virou a regra `AUD-09` (mascarado, nunca completo).

As dúvidas levantadas pelo arquiteto em T-006 foram aprovadas em 07 out 2026 e viraram regra (T-031; ver "Decisões de 07 out 2026" em `docs/regras-de-negocio.md`).

As dúvidas de filiais da T-030 e de contas da T-036 (itens 6 a 10) foram decididas em 07 out 2026 e viraram regra (T-037: seção Filiais, `LOC-11`, `VEI-04`, `USR-01`, `USR-06`). O item 12 (desbloqueio manual) foi decidido em 07 out 2026 e virou regra (`CLI-05`, `APR-05`, T-041). Os itens 11 e 13 de clientes foram decididos em 07 out 2026 e viraram regra (`CLI-07`, `CLI-09`, T-041). As dúvidas da T-038 (locações e vistorias) e a do pro rata dos juros foram decididas em 07 out 2026 e viraram regra (T-041: `FIN-03`, `DEV-01`, `DEV-03`, `LOC-08`, `LOC-09`, `FIN-09` e a tabela de perfis); no merge da branch do arquiteto, as linhas `[decisão]` da T-038 saem.

A dúvida do backend na T-069 (reativar quem teve o convite cancelado) foi analisada na T-075 e decidida em 08 out 2026: opção B. Vira regra na T-076 e código na T-077.

Levantadas pelo arquiteto em T-030 (07 out 2026):

- [divergência] Dados de exemplo nas telas da plataforma (para T-028): `Plat-Empresa-Detalhe` mostra CNPJ 41.208.733/0001-52 (seed: 12.345.678/0001-10), FAT-0001 vencendo em 21 out (PLT-01: dia seguinte ao fim do teste, 22 out) e "13 dias" de teste em 07 out (contrato: 14); `Plat-Empresas` mostra Moto Rápida com 4 usuários (seed: 5).

Levantadas pelo arquiteto em T-036 (07 out 2026):

- [divergência] `Frota` mostra a reserva do Kwid como `RES-0412`, mas a reserva é uma locação `aguardando_retirada` com código `LOC-` (regras, Veículos e Locação). `docs/api/veiculos.md` mostra o código `LOC-`. Para T-028, junto com as diárias da Frota que não batem com a tabela (CG 160 R$ 49,90, Pop R$ 39,90, NMax R$ 69,90, Mobi R$ 119,00).

Levantadas pelo arquiteto em T-038 (07 out 2026); as dúvidas foram decididas pelo dono do produto (T-041) e já estão nos contratos:

- [divergência] Telas de locação (para T-028): `Devolucao` mostra "faltou 1/2 tanque" para LOC-2836, mas o seed fecha R$ 32,00 com chegada em 3/4 (16 L × 1/4 × R$ 5,50 + R$ 10); `Locacao` diz "Com 3 dias de atraso numa parcela, o contrato entra na lista de bloqueio" (`CLI-05`: 15 dias) e tem o campo "Filial de devolução" (`FIL-05`: a devolução é na filial da locação); `Vistoria` mostra LOC-2856 com diária R$ 44,90, 30 dias, franquia de 3.000 km, caução R$ 500 e total R$ 1.347 (é semanal Street: R$ 329,00 + caução R$ 300,00, km livre); `Locacoes` mostra ROE-2A88 como Pop 110i e RHT-9F02 como Biz 125 (na `Frota` são Mobi e Kwid) e LOC-2848 com Kwid QYC-4D72 (no `Vistoriador`, QYC-4D72 é uma CG 160); `Contratos-Modelos` tem "Termo de devolução" como modelo, mas modelo de contrato só tem finalidade locação ou venda e o recibo da devolução é documento do sistema.

Levantadas pelo arquiteto em T-043 (07 out 2026):

- Decidido em 07 out 2026 (DEV-02, item 21): devolução de caução e reembolsos por Pix: no MVP o sistema registra o valor a devolver (`Reembolso`, `a_fazer`) e a pessoa faz o Pix pela conta da locadora e marca como feito com o comprovante; transferência automática pelo parceiro só depois das proteções de saque da subconta (S-05). Confirmar se atende o botão "Encerrar e devolver R$ 183,00 por Pix" da `Devolucao`.
- [divergência] Telas do financeiro e da auditoria (para T-028): `Receber` usa faixas 1–7, 8–15, 16–30 e 30+ (`FIN-02`: 1–7, 8–30, mais de 30) e mostra Rafael com parcela de R$ 350,00 de 05 set; `Caixa` gera Pix de R$ 299,40 para a parcela atrasada de Carlos (com multa e juros, `FIN-03`, são R$ 306,09); `Admin-Auditoria` diz "3 senhas erradas" (`USR-06`: 5); `Admin-Exportar` mostra Lúcia (financeiro) exportando, mas exportar é da Administração (só administrador).

Levantadas pelo produto em T-037, T-041 e T-047 (07 out 2026); estavam no commit 0a81a9b e saíram no merge 1050b77, restauradas pela T-049. Em todas vale o seed:

- [divergência] `Filial` (para T-028): mostra "3 de 3 filiais" e as filiais Caucaia e Messejana, mas o seed tem 1 filial (`Filiais` mostra "1 de 3"); "após o check-in" deve ser "após a devolução".
- [divergência] Telas de acesso e filial (T-036, para T-028): `Login` e `Convite` dizem que o gerente usa 2 etapas (`USR-02`: só administrador e financeiro); `Admin-Usuarios` convida só por celular (o e-mail é obrigatório, `USR-01`); tirar "Manter conectado" do `Login` (`USR-06`); o campo "Gerente responsável" da `Filial` vira só leitura (`FIL-02`); tirar da `Filial` vagas, tabela de preço padrão, conta de recebimento, centro de custo, nota fiscal, "aceita devolução de outras filiais", "compartilha a frota" e "Rascunho"; trocar "Domingo e feriados" por domingo e uma lista de feriados (`FIL-03`).
- [divergência] `Frota` (T-037, para T-028): diz "52 motos e 34 carros", mas o seed tem 80 motos e 6 carros; as diárias certas são as da tabela (Street R$ 54,90 para a CG 160, Urbana R$ 44,90 para a Pop 110i, Carro compacto R$ 109,00 para o Mobi).
- [divergência] Financeiro e auditoria (T-041, para T-028): `Caixa` e `Financeiro` dizem "Terça, 07 out", mas 07 out 2026 é quarta; no `Caixa`, "Diego Martins · LOC-2848 · 3 diárias R$ 179,70" não bate com a diária do Kwid (R$ 109,00): o valor fica (o total de R$ 1.182,60 depende dele) e a descrição muda; o `Caixa` diz que a parcela 2 de 5 do Carlos "venceu 07 out", mas ela venceu em 30 set; em `Receber`, o Rafael aparece com R$ 350,00 e 32 dias, mas o seed tem R$ 1.347,00 e 25 dias; `Despesas` mostra o IPVA de R$ 186,40 "Aguardando gerente", mas pela `FIN-05` ele nasce `a_pagar`, e o valor aguardando é R$ 1.200,00; `Admin-Auditoria` mostra "Street semanal R$ 319 → R$ 329" em 06 out, e pelo seed é R$ 299,40 → R$ 329,00, valendo desde 01 out.
- [divergência] `Gerente` (T-047, `USR-08`, para T-028): mostra 3 devoluções atrasadas (seed: 1, Rafael), 5 em manutenção (seed: 7), frota de 83 veículos (seed: 86), "4 pneus" (em `Despesas` são 2) e uma "Carla Andrade · Atendente" que não existe no seed, num perfil que não existe (os perfis são administrador, gerente, vendedor, vistoriador e financeiro); e QXA-4B21 aparece "Atrasado" pela LOC-2841, que tem parcela atrasada e não devolução atrasada (a situação "Atrasado" é só de `devolucao_atrasada`).

Levantadas pelo produto em T-053 (08 out 2026):

- [divergência] CNPJ do seed (T-010, resolvido pelo produto): 12.345.678/0001-10 não passa no dígito verificador; o CNPJ da Moto Rápida e da Filial Centro passa a ser **12.345.678/0001-95** (regras e critérios T-010, T-012 e T-014 já trocados). Falta trocar nas telas (`Admin-Assinatura`, `Admin-Marca`, `Compra-Checkout`, `Contratos-Modelos`, `Filiais`, `Filial`, `Onboarding-Contrato`, `Onboarding-Marca`, `Onboarding-Recebimentos` (chave Pix), `Plat-Empresa-Detalhe`), para o design-system, e em `docs/api/filiais.md` e `docs/api/plataforma.md` (`12345678000195`), para o arquiteto. O exemplo da Filial Caucaia em `filiais.md` (`12345678000200`) também tem dígito errado: o certo é `12345678000276`.
- Decidido em 08 out 2026 pelo dono do produto (`FIN-15`): a base do "Recebido" da tela `Receber` é a opção A, só as contas que vencem no mês e já foram pagas.
- [divergência] Contadores do menu (`FIN-15`, `docs/api/painel.md`): a barra lateral das 32 telas desktop e o `Menu-Mobile` mostram "Contas a receber 7", "Despesas 3" e "Conciliação 6"; pelo seed em 07 out (Mariana) são 2 (parcelas atrasadas de Carlos e Rafael), 1 (os pneus aguardando aprovação) e sem número (conciliação é fase 2, contador `null`). Em 30 das 32 telas desktop (todas menos `Main` e `Pos-Dashboard`), a barra lateral ainda mostra "Manutenções 5" (o seed tem 7, como no `Menu-Mobile`; o contador real é `null` até o app de manutenção existir). Para o design-system.
- [divergência] Números de outubro do `Receber` (e "Entra hoje" do `Financeiro`): "Previsto no mês" R$ 74,2 mil em 318 parcelas, "Recebido" R$ 21,6 mil, "Vence hoje" R$ 1.890 em 9 parcelas, "A vencer" 226 e "Pagas" 72 não saem do seed e não fecham com as regras (9 parcelas custam pelo menos R$ 2.511,00; 42 locações dão no máximo 210 vencimentos no mês; as abas somam 309, não 318). Proposta: o qa monta a carteira de outubro no seed (parcelas das 42 locações pela tabela de preços), o produto registra os números em "Dados de referência para testes" e o design-system troca as telas. Até lá, o teste da `FIN-15` usa um caso pequeno próprio. Para o arquiteto: em `docs/api/financeiro.md`, `recebido_pct` de 21,6 sobre 74,2 é "29.11", e as `contagens` seguem as abas da `FIN-15` ("todas" = soma das quatro); os mesmos 189000 e "9 parcelas" estão em `docs/api/painel.md`.

Levantadas pelo produto em T-059 (08 out 2026):

- Decidido em 08 out 2026 pelo dono do produto: o cartão de R$ 179,70 do Diego (LOC-2848) no caixa de 07 out vira a renovação de 1 diária do Kwid, R$ 109,00 (`LOC-08`). O caixa passa a R$ 1.111,90. A carteira de outubro está registrada em "Dados de referência para testes" (`FIN-15`).
- [divergência] Carteira de outubro (T-056, para o qa): `gerar.py` e os CSV precisam de duas mudanças. (1) A LOC-2841 começa em 23 set: parcela 1 paga em 23 set, a 2 atrasada em 30 set, a 3 vencendo em 07 out, e a 4 e a 5 em 14 e 21 out; sai a de 28 out. (2) A LOC-2848 ganha uma parcela de R$ 109,00 com vencimento em 07 out, paga no cartão. Números esperados: Previsto R$ 52.002,10 em 128; Recebido R$ 13.401,70 em 30 (25,77%); Vence hoje R$ 2.625,80 em 6; A vencer R$ 35.974,60 em 92; abas 130 / 2 / 6 / 92 / 30. O README da carteira e os testes `test_fin_15_*` também mudam.
- [divergência] Telas do caixa e das locações (T-059, para o design-system, junto com a T-060):
  - `Caixa` (desktop e celular): "Entrou hoje" R$ 1.111,90; cartão R$ 109,00; a linha do Diego vira "LOC-2848 · renovação de 1 diária"; o Pix de R$ 44,90 não é do Marcos (que é mensal, pago em 01 out) e sim da diária Urbana retirada hoje (LOC-2826; o nome do cliente vem da T-019).
  - `Locacoes`: LOC-2841 de "23 set → 28 out" e LOC-2848 de "06 out → 10 out".
  - `Comissoes`: a locação LOC-2848 vale R$ 436,00 (3 diárias + a renovação), não R$ 179,70; a comissão de R$ 16,00 não muda, porque renovação não gera comissão (`FIN-09`).
  - Nos números do `Receber` e do `Financeiro` da T-060 valem os da linha nova das regras: R$ 52,0 mil em 128 parcelas, R$ 13,4 mil (26%), abas 130 / 2 / 6 / 92 / 30. O README da T-056 diz 25% e 93 / 29.
- [divergência] Contratos (T-059, para o arquiteto): em `docs/api/financeiro.md`, o caixa de exemplo passa a 111190 (cartão 10900); em `docs/api/painel.md`, `caixa_hoje` fica com `recebido_centavos` 111190 e `saldo_dia_centavos` 106390; em `docs/api/veiculos.md`, a LOC-2841 é "assinada em 23 set".


Levantadas pelo produto em T-112 (09 out 2026), estado do QXA-4B21 em 07 out (caso "Estado do QXA-4B21 em 07 out" nos dados de referência):

- [divergência] Telas, para o design-system (T-028): `Frota-Desktop` e `Frota-Mobile` trocam "Atrasado" por "Alugado" (tom `solido`), 2024 prata por 2023 vermelha, 14.212 km por 18.950 km e próxima manutenção 15.000 km por 19.900 km. `Veiculo-Desktop` e `Veiculo-Mobile`: Km atual "atualizado 23 set" (não 07 out); LOC-2841 de 23 set a 28 out (não 30 set a 04 nov); a LOC-2702 termina até 12 set (hoje vai a 29 set e cruza com a LOC-2841); troca de óleo de 12 set aos 18.900 km (não 17.900; `MAN-03`, a cada 1.000 km); chassi 9C2KC2210PR004401 do seed (não 9C2KC2210PR004417), e o Renavam 01289934410 é o da SAK1D39 no seed, não pode se repetir. `Main`: a LOC-2841 sai de "Devoluções da semana" (devolve em 28 out, não em 10 out). `Vistoriador-Desktop` e `Vistoriador-Mobile`: a devolução "ontem 18h, Atrasada" do QXA-4B21 sai da agenda de 07 out; a única devolução atrasada do seed é a LOC-2790 (Rafael).
- [divergência] Contratos, para o arquiteto: os exemplos de `devolucoes_semana` em `docs/api/painel.md` e de `GET /api/vistorias/agenda/` em `docs/api/vistorias.md` usam a LOC-2841 como devolução atrasada de 06 out. Trocar pela LOC-2790 (Rafael, `devolucao_atrasada`).
- [divergência] Dados falsos, para o frontend: `falso-frota.ts` já tem `alugado` e 18.950 km, mas a ficha mostra "Atrasado" por seguir a Frota; passa a "Alugado" (tom `solido`), LOC-2841 de 23 set a 28 out. `falso-painel.ts` tira a LOC-2841 das devoluções da semana e da agenda (como em `painel.md` e `vistorias.md`).
- [divergência] `Manutencao-Desktop` (para o design-system, T-028): a OS-119 do QXA-4B21 aparece "Agendada, automática por km" com 950 km faltando, mas a `MAN-03` só cria a OS automática quando faltam 500 km. Em 07 out ela ainda não existe; a ficha só mostra "próxima: troca de óleo aos 19.900 km".

Levantadas pelo backend em T-015 (09 out 2026):

- (T-091) As 2 divergências foram resolvidas na T-106 e as 5 decisões aprovadas pelo dono em 09/10, todas na opção A; regra na T-110 (PR #110) e código na T-111.
- (T-104) As telas de referência com a LOC-2836 antiga ("Devolve hoje" em 07 out) são corrigidas pelo design-system na T-107.
- (T-015) O preço da LOC-2836 foi decidido em 09 out 2026 pelo dono do produto: opção A. A LOC-2836 é confirmada em 01 out, com início em 30 set, e paga R$ 329,00 pela tabela da Street a partir de 01 out (`LOC-15`); a tabela não muda. Os dados de referência mudam na T-097 e o teste do CA-015-15 na T-098.

Levantadas pelo backend em T-091 (09 out 2026), para o produto. O código segue o que está entre parênteses:


Levantadas pelo backend em T-016 parte 1 (09 out 2026):

- [divergência] (qa, T-105) A carteira de outubro (`docs/qa/carteira-outubro/locacoes.csv` e `tests/aceitacao/carteira.py`) traz a LOC-2856 como `ativa` desde 07 out 09:00. O CA-016-08 (e o CA-016-01) a quer `aguardando_retirada`, com retirada às 09:15. (O teste da agenda tira a LOC-2856 da carteira e cria a do critério.)

Levantadas pelo backend em T-109 (09 out 2026). O código segue o que está entre parênteses:

- (T-109) As duas decisões (ordem da caução no `DEV-02` e parcela do dia no `DEV-01`) e a devolução antes do fim sem encerramento aprovado foram decididas em 09 out 2026 pelo dono do produto: `DEV-02` opção A com o ajuste (a parcela que não cabe inteira vai para `renegociada` e entra na conta única do saldo), `DEV-01` opção B e a nova `DEV-07` (opção A). Regra e critérios na T-113 (CA-016-13, 22, 23 e 24); o código muda numa tarefa do backend (handoff da T-113).
- [divergência] (qa, T-019) O seed de teste não tem o preço do litro da Filial Centro (R$ 5,50), a vistoria de saída da LOC-2836 (cheio, 18.402 km; a PNB7C04 está com 21.870 km) nem a caução paga da LOC-2841 e da LOC-2812. (Os testes da T-109 gravam esses dados na fixture.)

Levantadas pelo arquiteto na revisão da T-114 (09 out 2026), para o produto:

- (T-114) A devolução depois do dia aprovado no encerramento antecipado foi decidida em 10 out 2026 pelo dono do produto: opção B, com o ajuste. Vale o dia da devolução: as parcelas que vencem até esse dia entram no acerto, e a multa e o crédito são recalculados nesse dia; a aprovação não cancela parcelas (`DEV-07`, `LOC-12`). Regra e critério (CA-016-25) na T-116; o código muda numa tarefa do backend (handoff da T-116).

Levantadas pelo backend em T-117 (10 out 2026), para o produto. O código segue o que está entre parênteses:

- (T-117) O encerramento antecipado aprovado com a devolução no dia do fim previsto ou depois foi decidido em 10 out 2026 pelo dono do produto: opção A. A devolução não é antecipada: não há multa nem crédito da `LOC-12`, e passando do prazo cobra o atraso da `LOC-10` (`DEV-07`). Regra e caso de referência na T-118; o código da T-117 já faz assim; teste na T-119.

Levantadas pelo produto em T-118 (10 out 2026), para o dono do produto:

- (T-118) O status final da locação com o encerramento antecipado aprovado e a devolução no dia do fim previsto ou depois foi decidido em 10 out 2026 pelo dono do produto: opção A. A locação termina `encerrada` (`DEV-06`), como numa devolução comum, e o pedido aprovado fica registrado, sem efeito (`DEV-07`). O código da T-117 a deixava `cancelada`; muda na T-119.

Levantadas pelo backend em T-111 (09 out 2026), para o produto. O código segue o que está entre parênteses:

- (T-111) O extra desativado antes da renovação foi decidido em 09 out 2026 pelo dono do produto: opção A. O extra continua nas locações que já o têm, renovações incluídas, pelo último valor do cadastro (`LOC-08`). Regra e critério (CA-015-27) na T-115; o código da T-111 já faz assim.

Levantadas pelo backend em T-092 (10 out 2026), para o produto:

- (T-092) As 5 dúvidas da troca de veículo foram decididas em 10 out 2026 pelo dono do produto, com a 6ª levantada pelo produto: (1) preço da nova categoria pelo dia do pedido, guardado na troca (A, com o ajuste); (2) taxa de combustível por veículo (A); (3) parcela refeita inteira pelo preço novo, com todos os descontos e o plano contando desde o começo (B); (4) rota para cancelar a troca pendente (B); (5) renovação permitida e cancelamento recusado com 409 `troca_pendente`; (6) diferença proporcional dos dias restantes do período em curso no acerto final, crédito se a categoria for mais barata (B). Regras (`LOC-08`, `LOC-09`, `LOC-12`, `DEV-01`, `DEV-02`) e caso "Troca de veículo LOC-2836" na T-121; contrato na T-122; código na T-123.

Levantadas pelo arquiteto em T-122 (10 out 2026), para o produto:

- (T-122) As 2 dúvidas do contrato da troca foram decididas em 10 out 2026 pelo dono do produto, com as opções do contrato: (1) cancelar a troca com a saída do veículo novo já concluída é recusado com 409 `troca_saida_concluida`; (2) no mensal em 4 semanais, a diferença do período em curso desconta o que as parcelas refeitas já subiram (`ja_refeito_centavos`). O estado `descartada` da vistoria entrou na tabela de estados. Regras na T-124 (`LOC-09`); o contrato da T-122 já segue as duas; código na T-123.

Levantadas pelo backend em T-017 (12 out 2026), para o produto:

- (T-017) As 3 dúvidas da T-017 foram decididas em 12 out 2026 pelo dono do produto, com as recomendações do produto, e viraram regra na T-147: (1) histórico da análise com o atraso pela `FIN-03` e o cliente novo `ok` "Cliente novo na empresa" (`CLI-04`, B); (2) semana de segunda a domingo e caução fora das abas e da lista geral (`FIN-15`, A); (3) bloqueio uma vez por conta e textos da régua reescritos, com e-mail (`AUT-03`, `CLI-05`, `AUT-05`, B). Código na T-148.

## Fase 0 · Fundação

### T-001 · Esqueleto do backend
- **Agente:** backend
- **Depende de:** T-003
- **Regras:** convenções de `CLAUDE.md`
- **Pronto quando:** `backend/` com projeto Django 5, settings divididos (base, dev, test, prod), django-tenants configurado com schema público e de empresa, DRF, drf-spectacular servindo `/api/schema/`, pytest rodando, `make backend-check` verde. Inclui `backend/comum/`: model base com código sequencial por empresa (`LOC-2856`), campos de dinheiro em centavos, erro de negócio com código de regra e o registro de evento de auditoria (AUD-01), para que todo módulo já nasça auditado.

### T-002 · Esqueleto do frontend
- **Agente:** frontend
- **Depende de:** T-003
- **Pronto quando:** `frontend/` com Next.js App Router, TypeScript estrito, Tailwind lendo os tokens de `src/design-system/tokens.ts`, grupos de rota `(publico)`, `(empresa)`, `(plataforma)`, ESLint e Vitest verdes.

### T-003 · Ambiente de desenvolvimento
- **Agente:** devops
- **Pronto quando:** `docker compose up` sobe Postgres 16, Redis, backend, worker Celery, beat e frontend; `.env.example` completo; `make up`, `make down`, `make check`.

### T-004 · Portar o design system para código
- **Agente:** design-system
- **Depende de:** T-002
- **Pronto quando:** `frontend/src/design-system/` com tokens (claro e escuro), variáveis `--brand`, `--brand-soft`, `--on-brand` trocáveis em tempo de execução, e os 12 componentes de `docs/design-system/components/` como componentes React com página de preview.

### T-005 · CI
- **Agente:** devops
- **Depende de:** T-001, T-002
- **Pronto quando:** os 5 pontos para o devops do handoff da T-001 resolvidos (desvio do Makefile, `MSYS_NO_PATHCONV`, CORS fora do `.env.example`, proxy de mesma origem `/api/`); GitHub Actions roda lint, testes e build do backend e do frontend em todo PR; gera o OpenAPI e falha se `docs/api/openapi.yaml` estiver desatualizado.

### T-006 · ADRs iniciais revisadas
- **Agente:** arquiteto
- **Pronto quando:** as ADRs de `docs/decisoes/` revisadas e o modelo de dados das 25 entidades desenhado em `docs/decisoes/modelo-de-dados.md`, com schema (público ou empresa) de cada uma.

### T-030 · Contratos da API de plataforma e filiais
- **Agente:** arquiteto
- **Depende de:** T-006
- **Regras:** PLT-01, PLT-03, PLT-08, PLT-09, USR-07
- **Pronto quando:** `docs/api/plataforma.md` e `docs/api/filiais.md` com endpoints, payloads, erros e permissões por perfil. Destrava T-010 e T-012.

### T-031 · Responder as dúvidas de regra da T-006
- **Agente:** produto
- **Depende de:** T-006
- **Pronto quando:** as cinco `[decisão]` levantadas pelo arquiteto (status não listados, `cancelada` na venda, venda aberta, arredondamento, chassi único) analisadas com recomendação em "Pontos em aberto" de `docs/regras-de-negocio.md`, para o dono do produto aprovar.

### T-032 · Revisão de segurança do desenho da fundação
- **Agente:** seguranca
- **Depende de:** T-006
- **Pronto quando:** ADRs 0008 a 0012 e o modelo de dados revisados, com atenção a campos mascarados na auditoria (0010), guarda de `plataforma.ContaPagamento.chave_api_cifrada` e token de suporte (0008). Relatório em `docs/seguranca/`; achados altos viram tarefas.

### T-033 · Dados sensíveis na fundação: cifra, hash de busca e classificação da auditoria
- **Agente:** backend
- **Depende de:** T-001
- **Regras:** CLI-01, AUD-01, AUD-04, AUD-06 · **ADR:** 0014 (itens 2 e 3) · **Segurança:** S-05, S-06, S-07
- **Pronto quando:** `comum/cripto.py`, `CampoCifrado`, `CampoHashBusca`, `CAMPOS_AUDITORIA` aplicado por `comum.auditoria` e o teste de arquitetura de campos sensíveis; os testes obrigatórios da ADR 0014 que não dependem de cliente ou sessão; `cryptography` registrada no PR e os três segredos no `.env.example`. Inclui C-01 (diff da auditoria calculado antes da máscara) e C-02 (tarefa com schema apagado não cai no public) da T-039, e o ator de quem disparou a tarefa em `na_empresa` (ADR 0018 item 3, ponto 1 da T-045). Bloqueia T-011 e T-014.

### T-034 · Auditoria e Celery endurecidos
- **Agente:** backend (papéis do banco com ADR do arquiteto e configuração do devops)
- **Depende de:** T-001
- **Regras:** AUD-01, AUD-02 · **Segurança:** S-10, S-11, C-03 (IP real atrás do proxy por `X-Forwarded-For`, só quando `REMOTE_ADDR` está em `GIRO_REDES_PROXY`, contando `GIRO_PROXIES_CONFIAVEIS` da direita, ADR 0018 item 4), C-05 (trigger sem `TRUNCATE`, mesmo que S-10)
- **Pronto quando:** critério do item "[média] Auditoria e Celery endurecidos" de `docs/seguranca/2026-10-07-fundacao.md` (trigger também em `TRUNCATE`, expurgo só com mais de 5 anos, `na_empresa` restaura ator e schema, `task_prerun`/`task_postrun` voltam ao public, cache com `make_key`, `@tarefa_de_empresa` recusa `public` e schema inexistente, tasks recebem só ids).
- **Também:** R-01 (média: cifra e hash falham dentro de `na_empresa` e `@tarefa_de_empresa`; usar `tenant_context`) e R-04 da T-050, antes da T-017.

### T-035 · Endurecimento de produção
- **Agente:** devops
- **Depende de:** T-001, T-002
- **ADR:** 0016 (papéis de banco separados, S-10) · **Segurança:** S-16, S-17, S-18, C-04 (`wsgi.py`, `asgi.py` e `config/celery.py` sem padrão `dev`; falha se `DJANGO_SETTINGS_MODULE` não vier em produção)
- **Pronto quando:** `SHOW_PUBLIC_IF_NO_TENANT_FOUND = False` em `prod.py`; HSTS com preload, `Referrer-Policy`, `X-Frame-Options: DENY`, CSP no front; `/api/schema/` e `/api/docs/` fechados em produção (ponto 5 da T-045; ajuste no backend junto); `GIRO_PROXIES_CONFIAVEIS` e `GIRO_REDES_PROXY` por ambiente e `X-Forwarded-For` no proxy de mesma origem (ADR 0018); `SIMPLE_JWT["SIGNING_KEY"]` com variável própria. Precisa estar pronta antes do primeiro deploy de homologação.

### T-036 · Contratos da API de contas, veículos e clientes
- **Agente:** arquiteto
- **Depende de:** T-030
- **Regras:** USR-01 a USR-07, VEI-01 a VEI-07, CLI-01 a CLI-08, AUD-04, AUD-05 · **ADRs:** 0013, 0014
- **Pronto quando:** `docs/api/contas.md` (inclui sessões, 2 etapas e convite), `docs/api/veiculos.md` e `docs/api/clientes.md` no padrão de `docs/api/README.md`. Destrava T-011, T-013 e T-014.

### T-037 · Dúvidas da T-030 e critérios de aceite de T-010 a T-014
- **Agente:** produto
- **Depende de:** T-030, T-031
- **Pronto quando:** recomendação para as `[decisão]` da T-030 (campos da tela Filial sem regra, desativação de filial com operação) em "Pontos em aberto"; critérios de aceite com números do seed para T-010, T-011, T-012, T-013 e T-014, no formato que o qa transforma em teste.

### T-038 · Contratos da API de locações, vistorias e devolução
- **Agente:** arquiteto
- **Depende de:** T-036
- **Regras:** LOC-01 a LOC-15, VIS-01 a VIS-05, DEV-01 a DEV-06 · **Segurança:** S-09 (marcadores fechados do `ModeloContrato`, `url_fetcher`), S-15 (token de assinatura)
- **Pronto quando:** `docs/api/locacoes.md` (reserva, contrato, ciclo de status, assinatura) e `docs/api/vistorias.md` (saída, devolução e acerto) no padrão de `docs/api/README.md`, com o caso LOC-2836 = R$ 183,00 descrito no exemplo de resposta do acerto. Destrava T-015 e T-016.

### T-039 · Revisão de segurança do código da T-001
- **Agente:** seguranca
- **Depende de:** T-001
- **Pronto quando:** `comum/autenticacao.py`, `comum/auditoria.py` (máscaras), o trigger de `apps/auditoria/migrations/0002_trigger_imutavel.py`, settings e rotas revisados contra as ADRs 0008 a 0013; relatório em `docs/seguranca/`; achados viram tarefas.

### T-040 · Cobertura de regras e esqueleto dos testes de aceitação de T-010 a T-014
- **Agente:** qa
- **Depende de:** T-001, T-037
- **Pronto quando:** `docs/qa/cobertura-de-regras.md` com a tabela regra → teste → status para todas as regras com código; em `backend/tests/aceitacao/`, um teste por critério de `docs/qa/criterios/T-010.md` a `T-014.md`, com o código da regra no nome, marcados `xfail` (motivo: tarefa ainda não implementada) até o backend entregar. Os testes rodam no CI sem quebrar.

### T-041 · Critérios de aceite de T-015 a T-018
- **Agente:** produto
- **Depende de:** T-037, T-038
- **Pronto quando:** `docs/qa/criterios/T-015.md` a `T-018.md` com números do seed (LOC-2836 = R$ 183,00, caixa de 07 out = gaveta R$ 281,00 e os demais casos da tabela de referência), apontados no "Pronto quando" das tarefas.

### T-042 · Componente de código de 6 dígitos (OTP)
- **Agente:** design-system
- **Depende de:** T-004, T-026
- **Pronto quando:** componente `CodigoVerificacao` em `frontend/src/design-system/` como na tela `Ativar-2FA` (6 casas, colar o código inteiro, avanço e volta com teclado, estado de erro, `autocomplete="one-time-code"`, acessível), com preview e testes. Usado pela T-020.

### T-043 · Contratos da API de financeiro e auditoria
- **Agente:** arquiteto
- **Depende de:** T-038
- **Regras:** FIN-01 a FIN-08, AUD-01 a AUD-03, AUD-09 · **Segurança:** S-14 (webhooks)
- **Pronto quando:** `docs/api/financeiro.md` (contas a receber, caixa do dia, baixa, interface de pagamentos para a T-029) e `docs/api/auditoria.md`, com o caso do caixa de 07 out (gaveta R$ 281,00). Inclui alinhar `vistorias.md` (fórmula do combustível da DEV-01, exemplo com chegada em 3/4) e `locacoes.md` (renovação e troca decididas: LOC-08, LOC-09) às decisões da T-041. Destrava T-017 e T-018.

### T-044 · Contrato da API de importação por planilha
- **Agente:** arquiteto
- **Depende de:** T-036
- **Regras:** IMP-02 e o passo "importar dados" do assistente de implantação, VEI-01, CLI-01
- **Pronto quando:** `docs/api/importacao.md` (envio da planilha, validação linha a linha com os erros da tela `Onboarding-Importar`, confirmação, relatório), com os campos cifrados da ADR 0014. Destrava T-027.

### T-045 · Conferir decisões de implementação da T-001 contra as ADRs
- **Agente:** arquiteto
- **Depende de:** T-001
- **Pronto quando:** as "Decisões de implementação (Arquiteto, confira)" do handoff da T-001 conferidas contra as ADRs 0008 a 0012 e o modelo de dados; o que divergir vira ajuste de ADR ou tarefa para o backend, sem bloquear a T-033.

### T-046 · Componentes pedidos pela T-020
- **Agente:** design-system
- **Depende de:** T-004
- **Pronto quando:** seletor de filial, diálogo e gaveta (shadcn/ui por cima dos tokens, se fizer sentido; registrar no PR) e `KpiTile` com valor longo no celular, com preview e testes. Usados pela T-020 e pela T-021.

### T-047 · Menu por permissão e agregados do painel
- **Agente:** arquiteto (com o produto para o início por perfil)
- **Depende de:** T-036
- **Pronto quando:** `docs/api/contas.md` devolve `menu` (módulos liberados) em `GET /api/eu/`, para a tela não inferir de `pode`; rota inicial por perfil definida com o produto (vistoriador, vendedor, gerente, financeiro); `docs/api/painel.md` com os contadores do menu e os indicadores da tela `Main`. Resolve as três `[decisão]` da T-020.

### T-050 · Revisão de segurança do código da T-033
- **Agente:** seguranca
- **Depende de:** T-033
- **Pronto quando:** `comum/cripto.py`, `CampoCifrado`, `CampoHashBusca`, `CAMPOS_AUDITORIA`, `na_empresa` e o teste de arquitetura revisados contra a ADR 0014 (itens 2 e 3), a ADR 0018 (item 3) e os achados S-05, S-06, S-07, C-01 e C-02; relatório em `docs/seguranca/`; achados viram tarefas.

### T-065 · Login trata o 401 e o 429 da T-058
- **Agente:** frontend
- **Depende de:** T-058
- **Pronto quando:** as telas de acesso tratam as respostas novas de `docs/api/plataforma.md` (entrar sem código responde 401 em vez de 400; 429 do bloqueio de 5 senhas e 429 `muitas_requisicoes`), com mensagem nas palavras das telas, nos dados falsos, e com teste.

## Fase 1 · MVP

Propostas pela segurança na T-024 (12 out 2026, `tarefas/handoffs/T-024-seguranca.md`), numeradas pelo orquestrador; nenhuma alta. A T-155 (M-01) entra no PR #160 antes do merge:

### T-155 · (M-01) Vistoriador sem os preços dos planos especiais (média)
- **Agente:** backend · **Depende de:** T-136 · **Regras:** USR-09 · **Pronto quando:** `GET /api/planos-especiais/` responde 403 ao vistoriador (hoje, na branch do PR #160, devolve `preco_centavos` e `desconto_pct`; `PlanosEspeciaisView` usa as permissões padrão no GET); o GET passa a usar a lista de quem lê locações (`LEEM_A_LISTA`); teste `test_usr_09_vistoriador_nao_ve_planos_especiais`. Pode entrar no próprio PR #160 antes do merge.

### T-157 · (M-03) Produção recusa e-mail no console e armazenamento falso (média)
- **Agente:** backend · **Depende de:** — · **Pronto quando:** `config/settings/prod.py` recusa subir com `EMAIL_BACKEND` de console, locmem ou arquivo (o padrão de `base.py` é o console, e os e-mails de senha, convite e assinatura levam o token) e com `GIRO_ARMAZENAMENTO` diferente de `s3`, como já faz com as chaves; pagamentos e WhatsApp `falso` entram na mesma trava quando as integrações reais existirem (T-029); teste que importa `prod.py` com o ambiente montado. Antes de homologação.

### T-158 · (M-04) Configuração do proxy reverso: tamanho do corpo e cabeçalhos `X-Forwarded-*` (média)
- **Agente:** devops, com o backend · **Depende de:** — · **Pronto quando:** a configuração do proxy de homologação e produção está em `infra/`, com limite de corpo de 12 MB (os uploads só são conferidos por `comum/arquivos.validar` depois de recebidos inteiros, e o Django não limita arquivo em multipart), `X-Forwarded-Host`, `X-Forwarded-Proto` e `X-Forwarded-For` sempre sobrescritos pelo proxy (o `TenantMainMiddleware` escolhe a empresa por `get_host()`, que segue o `X-Forwarded-Host` com `USE_X_FORWARDED_HOST = True`) e rate limit de borda em `/api/auth/` e no webhook; no backend, `USE_X_FORWARDED_HOST` só em `prod.py`; checklist no `infra/README.md`. Antes de homologação.

### T-156 · (M-02) Custo e rendimento do veículo fora da ficha do vendedor (média) `[decisão]`
- **Agente:** produto (decisão), depois backend · **Depende de:** T-136 · **Regras:** tabela de perfis, USR-09, VEI-05 · **Pronto quando:** o produto decide se o vendedor recebe `indicadores_financeiros` (`rendeu_no_ano_centavos`, `custo_manutencao_ano_centavos`) em `GET /api/veiculos/{id}/` (hoje recebe; o checklist da segurança pede que o vendedor não receba custo nem margem, e a regra não diz); proposta: só administrador, gerente e financeiro, com a chave ausente para os demais, como no D-25; teste `test_usr_09_vendedor_sem_custo_do_veiculo`.

### T-159 · (M-05) Login não revela e-mail com convite pendente (baixa)
- **Agente:** backend · **Depende de:** — · **Regras:** USR-01, USR-06 · **Pronto quando:** em `POST /api/auth/entrar/`, quem tem convite pendente e ainda não tem senha recebe o mesmo 401 `credenciais_invalidas` (e o mesmo tempo) de um e-mail que não existe; hoje o 403 `convite_pendente` sai antes de conferir a senha e permite saber quem foi convidado; o 403 só depois da senha certa; teste `test_usr_06_convite_pendente_nao_revela_email`.

### T-160 · (M-06) API navegável do DRF desligada em produção (baixa)
- **Agente:** backend · **Depende de:** — · **Pronto quando:** `prod.py` deixa em `DEFAULT_RENDERER_CLASSES` só o `comum.renderizacao.JSONRenderer` (hoje o `BrowsableAPIRenderer` de `base.py` mostra formulários e descrições das views no navegador, o que o S-17 fechou para o OpenAPI); teste que confere a lista em produção.

- **Nota da T-012 (08/10):** a S-12 (SVG do logo sanitizado e exibido só por `<img>`) vale para `ConfiguracaoEmpresa.logo` (app `empresas`), e não para a filial. Entra na tarefa da marca da empresa (`Admin-Marca`), a criar.

### T-093 · Momentos em UTC na API
- **Agente:** backend · **Depende de:** T-088 · **ADRs:** 0020 · **Pronto quando:** `comum/renderizacao.py` ligado no `REST_FRAMEWORK` como na ADR 0020; os 3 testes de `backend/tests/test_formato_das_datas.py` passam sem `xfail` e a lista de pendentes do teste de varredura fica vazia; contas, aprovações, plataforma, veículos, filiais e clientes saem em `AAAA-MM-DDTHH:MM:SSZ` sem mexer nos serializers; OpenAPI sem mudança. Passos em `tarefas/handoffs/T-088-arquiteto.md`.

### T-091 · Locação: renovação, atraso, cancelamento e encerramento
- **Agente:** backend · **Depende de:** T-090 · **Regras:** LOC-08, LOC-10 a LOC-13, FIL-03, APR-02, AUT-02 · **Pronto quando:** CA-015-17 e 19 a 24 e o estorno do CA-015-25 passam, com o código da regra no nome do teste: renovação com aditivo; atraso com `calcular_atraso` e `aut_02`; cancelamento e encerramento antecipado com APR-02, reembolso e comissão estornada.

### T-153 · Escrita da marca (backend)
- **Agente:** backend · **Depende de:** T-129 · **ADR:** 0022 · **Contrato:** `docs/api/empresas.md` ("Escrita da marca") · **Regras:** IMP-05, S-12 · **Pronto quando:** `empresas/logo.py` com `limpar_logo` pela ADR 0022 (`defusedxml`, dependência nova com motivo no PR; listas fechadas em constantes iguais às da ADR; recusa do conteúdo ativo com `WARNING` sem conteúdo no log); `empresas.services.salvar_marca` numa transação com `select_for_update`, evento `empresa.alterar_marca` (categoria `configuracoes`, `CAMPOS_AUDITORIA` com `nome_exibicao`, `cor_marca` e `logo`), e no `on_commit` apaga a chave `marca:<schema>` e o arquivo antigo (e o novo se a transação falhar), e chama `registrar_passo_implantacao("marca")`; `PATCH /api/marca/` (multipart e JSON, só administrador, 403 ao suporte e à empresa sem operação, 30 por hora por usuário) e `POST /api/marca/simular/` (120 por minuto por usuário), com as mensagens do contrato; sem mudança idempotente não grava evento nem muda a `versao`; PNG responde 400 "Envie o logo em SVG." até a `[decisão]` da Segurança (se aceito antes da entrega, implementa o item 6 da ADR); OpenAPI regenerado e `api:gerar` no frontend; testes `test_s_12_*` (um por vetor da ADR, e os que passam), `test_imp_05_salvar_marca_marca_o_passo`, `test_marca_simular_seis_cores` (tabela "As seis cores do `Onboarding-Marca`"), `test_marca_patch_invalida_cache_e_versao` (`ETag` novo; `If-None-Match` com a versão antiga recebe 200), `test_marca_patch_so_administrador`.
- **Contrato pronto (12 out 2026, arquiteto):** `docs/api/empresas.md`, seção "Escrita da marca (T-130)" (`POST /api/marca/simular/` e `PATCH /api/marca/`), e ADR 0022 (sanitização do logo). Cor padrão pela saída (b) de `cores-da-marca.md` (valores fixos do `wl-theme.css` para `#C8F04A`), como o código da T-129 já faz. Handoff: `tarefas/handoffs/T-130-arquiteto.md`.
- [decisão] **(Segurança) O logo aceita PNG além de SVG?** A tela diz "PNG ou SVG, fundo transparente, até 2 MB"; o modelo de dados dizia só SVG. O desenho para os dois casos está na ADR 0022 (item 6: PNG reconferido e codificado de novo pelo Pillow, até 4.096 px, sem metadados, servido com `nosniff`). A favor do PNG: Gmail e Outlook não mostram SVG em e-mail, e as mensagens ao cliente saem com o logo da locadora (seção "Tarefas automáticas" das regras); muita locadora pequena só tem o logo em PNG. Contra: mais um formato a tratar. Recomendação do arquiteto: aceitar, com o tratamento da ADR 0022. Até a decisão, o backend aceita só SVG e a ajuda da tela diz "SVG, fundo transparente, até 2 MB". Quem responde: **seguranca**; avise o orquestrador e o arquiteto.

### T-154 · Tela Empresa e marca e passo Marca do assistente (frontend)
- **Agente:** frontend · **Depende de:** T-153 · **Contrato:** `docs/api/empresas.md` · **Telas:** Admin-Marca, Onboarding-Marca · **Pronto quando:** `/admin/marca` com o bloco "Marca" (logo com Trocar e Remover, Cor principal, Nome que aparece para clientes) e a "Prévia", ligados a `GET /api/marca/`, `POST /api/marca/simular/` e `PATCH /api/marca/`; os blocos "Dados da empresa" e "Endereço do sistema" ficam fora (sem contrato); no assistente, só "Logo" e "Cor de destaque" com as seis cores, ligados às mesmas rotas, se a casca do assistente existir (senão, o componente fica pronto para ela); a prévia usa só as cores da simulação (nenhuma conta de cor no frontend; o script das telas de referência é desenho), e o logo não salvo aparece por `URL.createObjectURL` em `<img>`, nunca inline; depois de salvar, a consulta `marca` recebe o corpo e é invalidada, e a casca troca as cores; erro 400 no campo com a `mensagem` da API; ajuda do logo conforme a `[decisão]` do PNG; testes do componente (prévia com `#2F6FED` → `cor_sobre` `#FFFFFF` e `cor_suave` `#DBF3FF` vindos da API mockada; logo por `<img>`; Remover mostra as iniciais).

### T-142 · Data de referência do relógio no desenvolvimento (backend)
- **Agente:** backend (com aval do devops no `Makefile` e no `.env.example`) · **Depende de:** T-135 · **ADR:** 0021 · **Contrato:** `docs/api/README.md`, seção "Ambiente" · **Pronto quando:** `GIRO_DATA_REFERENCIA` (`AAAA-MM-DD`) lida só em `config/settings/dev.py` (vazia ou ausente = desligada; formato errado não sobe), `None` em `base.py` e `test.py`, e `prod.py` recusa subir com ela não vazia; `comum.relogio.agora()` devolve a data de referência com a hora real de São Paulo e `hoje()` a segue; `GET /api/ambiente/` e `GET /api/plataforma/ambiente/` públicas (`hoje`, `data_simulada`, `no-store`); cabeçalho `X-Giro-Data-Simulada` em toda resposta com a data ligada; aviso `giro.W001` no `check` e `WARNING` ao subir backend, worker e beat; `.env.example` com `GIRO_DATA_REFERENCIA=2026-10-07` e comentário; alvo `make relogio` (recria backend, worker e beat); `docs/agentes/retomada.md` diz como mudar a data; OpenAPI e cliente do frontend regerados; testes `test_adr_0021_*` (ligada, desligada, vazia, produção recusa, rota e cabeçalho nos dois urlconfs). Com o seed da T-127 e a data em 07 out, o painel mostra os números das regras (em atraso 164640, entra hoje 262580).

### T-143 · Faixa "Data simulada" e o "hoje" das telas pela API
- **Agente:** frontend · **Depende de:** T-142 · **ADR:** 0021 · **Pronto quando:** com `data_simulada: true` em `GET /api/ambiente/` (ou `/api/plataforma/ambiente/` no painel da plataforma), uma faixa fixa no topo de todas as telas, inclusive login, com "Data simulada: 07/10/2026. Ambiente de desenvolvimento." no tom de aviso do design system, sem botão de fechar; sem a faixa com `false`; toda tela que precisa de "hoje" (agenda, filtros "vence hoje", data padrão de formulário) usa o `hoje` da rota, nunca a data do navegador; teste do componente da faixa nos dois casos.

### T-136 · Permissões por perfil na API e nas rotas
- **Agente:** backend, depois frontend; revisão da seguranca · **Depende de:** T-017 · **Regras:** tabela de perfis, USR-08, USR-09, AUD-04 · **Pronto quando:** (D-25) a API não devolve valor nem dado de pagamento ao vistoriador (clientes, veículos, locações: `_centavos`, diária, total pago), e a tela esconde o que vier ausente; (D-26) toda rota do frontend que o menu do perfil não mostra responde com "Seu perfil não tem acesso" e a API responde 403 para o que o perfil não pode ver, não só o menu; (D-27, D-28, D-29, `USR-09`) o financeiro vê a ficha da locação só para leitura, com as ações de receber e de marcar reembolso como feito, e a ficha do cliente com contato, locações e o financeiro do cliente (total pago, em aberto, parcelas atrasadas com dias, pagamentos), sem documentos, endereço e análise do cadastro, e com Cobrar como única ação; o vistoriador não abre lista nem ficha do cliente (403 e "Seu perfil não tem acesso") e recebe do cliente, com a vistoria, só nome, celular e se a retirada está liberada (`CLI-02`, `CLI-03`); testes por perfil (vistoriador e financeiro) na API e no frontend, com `usr_09` no nome. Levantada em a conferência das telas do fim da T-127 (12 out 2026, `C:/Users/Jota/Documents/giro-produto/conferencia-telas.md`, fora do git; o handoff de cada tarefa copia os itens que resolver).
- **Inclui (12 out 2026, T-141, `USR-05`):** (backend) `menu_completo` por perfil como em `docs/api/contas.md`: na variante `vistoriador`, igual ao `menu_inicio` (Vistorias de hoje, Consultar veículo, Avarias abertas), sem `inicio` e sem `locacoes`; `locacoes` só com `locacoes_criar`; o rótulo de `inicio` é o do início do perfil (Visão geral, Visão da filial, Início); `barra_celular` com `veiculos` quando há `consultar_veiculo`; teste `test_usr_05_menu_completo_do_vistoriador` (João: sem "Visão geral" e sem "Locações"). (frontend) `gruposDaRota` em `frontend/src/lib/menu.ts` usa o `menu_inicio` também nas rotas que os itens dele abrem (só o caminho, com sub-rotas), e não só em `/inicio`: João em `/vistorias` e em `/vistorias/avarias` vê o mesmo menu do início, com "Vistorias de hoje" ativo na agenda; Lúcia (financeiro) em `/financeiro/receber` mantém o menu do perfil e em `/clientes` vê o completo; teste com `usr_05` no nome.

### T-140 · Dias de atraso do bloqueio e km de saída da devolução
- **Agente:** backend · **Depende de:** — · **Regras:** CLI-05, DEV-08, FIN-03 · **Pronto quando:** (D-03) no bloqueio automático, `bloqueio.descricao` de `GET /api/clientes/{id}/` é montada na leitura com os dias de atraso de hoje (dia corrido em `America/Sao_Paulo`, como a lista e a locação): Rafael em 12 out, "Conta com 30 dias de atraso desde 12/09/2026"; em 07 out, 25 dias; o evento de auditoria do bloqueio continua com o número do dia em que aconteceu; teste `test_cli_05_dias_de_atraso_de_hoje`. (D-12) o comparativo da devolução (`saida` de km e combustível em `vistorias.selectors`) usa o km e o combustível de saída gravados na locação, o mesmo `km_saida` da ficha; na troca, os do veículo que volta; LOC-2836 mostra 21.870 km na saída nas duas telas; teste `test_dev_08_km_de_saida_igual_na_ficha_e_na_devolucao`. Levantada na T-139 (`tarefas/handoffs/T-139-produto.md`).

### T-149 · Suíte do backend mais rápida no CI
- **Agente:** qa (fixture do seed), depois devops (paralelismo) · **Depende de:** T-145 · **Pronto quando:** a suíte do backend no CI volta para perto do tempo de antes dos testes do seed (de 11 min para uns 4 min ou menos), sem perder teste: (1) medir com `pytest --durations=25` no CI e registrar os mais lentos no handoff; (2) os testes do seed (`tests/aceitacao/test_t127_seed.py`) rodam `seed_moto_rapida` uma vez por módulo ou sessão e compartilham o resultado, com limpeza no fim; (3) se ainda passar de 5 min, `pytest-xdist` com um banco por worker, motivo da dependência no PR; (4) opcional, ruff e mypy em job próprio, em paralelo. Sugestões do handoff `tarefas/handoffs/T-145-devops.md`. Aprovada pelo dono em 12 out 2026.

### T-146 · Status do caixa como enum no painel
- **Agente:** backend · **Depende de:** T-017 · **Regras:** FIN-07, FIN-08 · **Pronto quando:** `status` de `caixa_hoje` e de `caixas_do_dia` em `GET /api/painel/inicio/` é `ChoiceField` com `aberto`, `aguardando_aprovacao`, `fechado` e `fechado_sem_conferencia` (hoje é `CharField` e o OpenAPI sai `string`, sem o enum para o cliente tipado); `openapi.yaml` regenerado; teste com o caixa de hoje `fechado` aparecendo em `caixa_hoje` (`test_fin_07_caixa_hoje_em_qualquer_status`). Levantada na T-144 (`tarefas/handoffs/T-144-arquiteto.md`).

### T-148 · Código das decisões da T-017: histórico, bloqueio uma vez por conta e textos da régua
- **Agente:** backend · **Depende de:** T-147 · **Regras:** CLI-04, CLI-05, AUT-03, AUT-05, FIN-03, FIN-15 · **Pronto quando:** (1, `CLI-04`) `financeiro.leituras.montar_historico` conta o atraso pela `FIN-03` (dia do pagamento, ou hoje se em aberto, menos o mais tarde entre o vencimento e a data em que a conta nasceu, em `America/Sao_Paulo`), sem caução, e devolve `ok` "Cliente novo na empresa" para o cliente sem conta (em vez de `None`); "Sem histórico" fica só para o módulo financeiro desligado; caso "Histórico da análise em 07 out" (Juliana `ok`, Carlos e Rafael `problema`, Lucas `ok`, cliente novo `ok`; Juliana `ok` também em 01 out antes de pagar); testes `test_cli_04_historico_conta_que_nasce_vencida_nao_e_atraso` e `test_cli_04_historico_cliente_novo_ok`. (3a, `AUT-03`, `CLI-05`) campo `bloqueio_pedido_em` em `ContaReceber` (migração): `regua_de_cobranca` publica `financeiro.parcela_atrasou` com 15 dias ou mais só quando ele está vazio e grava a data ao publicar; 1, 3 e 7 dias continuam; CA-017-11 continua passando; testes `test_cli_05_desbloqueio_manual_nao_volta_a_bloquear` (Rafael desbloqueado pelo Rodrigo em 12 out continua `ativo` depois da régua de 13 out às 09:00) e `test_aut_03_bloqueio_recupera_dia_perdido` (conta de 23 set, tarefa sem rodar em 08 out, bloqueio em 09 out com 16 dias). Se o arquiteto preferir a alternativa sem migração (o assinante de `clientes` ignora o evento depois do desbloqueio manual), registra em ADR antes. (3b, `AUT-03`, `AUT-05`) `cobrar` e `_enviar_recibo` com os textos de `docs/api/financeiro.md` ("Régua de cobrança: textos"): um texto por momento (D-1 "vence amanhã", D0 "vence hoje" com Pix, em atraso com o valor do dia), a conta descrita pelo tipo ("a parcela 2 de 5 da locação LOC-2841", "a cobrança de acerto da locação LOC-2841"), a frase sem Pix quando os recebimentos estão desligados, e o recibo com a forma e o dia; e-mail com o mesmo texto quando o cliente tem e-mail, uma vez por conta por dia contando os dois canais; testes com os textos exatos do Carlos: `test_aut_03_texto_d_menos_1`, `test_aut_03_texto_d0_com_pix`, `test_aut_03_texto_d_mais_7_valor_do_dia` (R$ 306,09), `test_aut_03_texto_acerto` (R$ 365,37), `test_aut_03_email_mesmo_texto`, `test_aut_05_recibo_texto` ("recebemos R$ 306,09 por Pix em 07/10"). O envio de e-mail ao cliente já existe: `contratos/tasks.py` usa `django.core.mail.send_mail` com `DEFAULT_FROM_EMAIL` (link de assinatura); a régua usa o mesmo caminho, com o nome da locadora no remetente. Contrato já atualizado na T-147 (`financeiro.md` e `clientes.md`). (2, `FIN-15`) nada a mudar na regra; conferir as `contagens` com `?cliente=`: a lista traz a caução e as contagens não (Lucas: 2 linhas, "Todas" 1); a forma de mostrar é do arquiteto. Caso novo "Contas a receber da semana em 07 out" (`?periodo=semana`: Todas 36, A vencer 13, Pagas 15) com teste `test_fin_15_semana_de_segunda_a_domingo`. Levantada na T-147 (`tarefas/handoffs/T-147-produto.md`).

### T-150 · Filial nos eventos de movimento de caixa
- **Agente:** backend · **Depende de:** T-018 · **Regras:** FIN-07, AUD-01, AUD-02 · **Decisão:** arquiteto, 12 out 2026 (a ação continua `movimento_caixa.sangria`, objeto `movimentocaixa`, padrão `<objeto>.<verbo>`) · **Pronto quando:** os eventos `movimento_caixa.*` (entrada, saída, sangria, estorno, `estorno_motivo`) gravam o `filial_id` do caixa: `registrar_evento` e `auditar` em `comum/auditoria.py` aceitam `filial_id: int | None = None` (keyword; quando vier, vale ele, senão `getattr(objeto, "filial_id", None)`; sem mudança de schema); `_registrar_movimento` e o `registrar_evento("movimento_caixa.estorno_motivo", ...)` de `estornar_movimento` em `financeiro/services.py` passam `filial_id=caixa.filial_id`; em `auditoria/textos.py` o detalhe da `movimento_caixa.sangria` vira "Caixa da <filial>" (consulta `filiais`) e sai a entrada `caixa.sangria`, que nenhum serviço grava; sem migração de dados (eventos imutáveis, ADR 0010; o seed é recriado). Testes: `test_fin_07_sangria_audita_com_filial_do_caixa` (seed em 07 out: a sangria de R$ 500,00 da Bruna em `GET /api/auditoria/eventos/?filial=<Filial Centro>` com `resumo` "Fez sangria de R$ 500,00", `detalhe` "Caixa da Filial Centro" e `objeto.filial` "Filial Centro"); `test_fin_07_movimentos_e_estorno_auditam_com_filial` (entrada, saída e estorno com o `filial_id` do caixa; filtro por outra filial não os traz); os testes da auditoria de objetos com `filial_id` próprio passam sem mudança. Contrato em `docs/api/auditoria.md` já ajustado na T-151.

### T-019 · Seed Moto Rápida
- **Agente:** qa · **Depende de:** T-013 a T-017 · **Pronto quando:** `make seed` cria a empresa de exemplo e todos os casos da tabela "Dados de referência para testes" passam.
- **Placas do seed (T-028):** PQD-6E21 (Pop do Rafael, LOC-2790), RJD-5B38 (Biz do Marcos, LOC-2850), RKP-3D26 (Kwid do Diego, LOC-2848); reserva do Kwid LOC-2857.
- **Critérios (T-152):** `docs/qa/criterios/T-019.md`. Corrige dois pontos do seed da T-138: as locações geradas com o 1º vencimento de outubro em 07 out ou depois começam um período antes, sem pagar as parcelas de 07 out (item D-21, CA-019-18), e as 9 reservas retiram de 03 a 13 nov, para não mudar os números de outubro (CA-019-19).

### T-026 · Desenhar telas que faltam para o MVP
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** "Esqueci a senha" e "Ativar verificação em 2 etapas" (desktop e celular) em `docs/telas/html/`, no mesmo padrão das telas de acesso, e no índice. Bloqueia a parte de 2FA de T-020.

### T-027 · Importação de veículos e clientes por planilha
- **Agente:** backend · **Depende de:** T-013, T-014 · **Regras:** IMP (passo de importar) · **Telas:** Onboarding-Importar · **Por quê:** critério de pronto do MVP "dados antigos migrados e conferidos".
- **Critérios (T-152):** `docs/qa/criterios/T-027.md` (planilha de 86 linhas: 83 prontas, 3 com erro, 86 depois de corrigir; limite do plano; suporte; dados temporários).

### T-028 · Limpar dados de exemplo das telas
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** os números das telas batem com as regras e o seed. Já se sabe de: Patrícia (LOC-2812) aparece em Contas a receber com parcela de R$ 279,00 (plano Entregador, placa SAB-2K90), mas é mensal NMax SBC-0J44 nas outras telas; Marcos (LOC-2850) aparece com a placa SBC-0J44; ficha do veículo QXA-4B21 mostra "Plano padrão Semanal R$ 299,40" (Street agora é R$ 329,00); Juliana aparece "em dia" em Clientes e com parcela atrasada em Contas a receber; Financeiro mostra "3 clientes com 7+ dias R$ 1.299,40". Corrigir no canvas e em `docs/telas/html/`. Inclui `Despesas-Desktop` e `Despesas-Mobile`: aguardando aprovação é R$ 1.200,00 (não R$ 1.386,40) e o IPVA de R$ 186,40 nasce `a_pagar` (FIN-05), apontado pelo qa na T-040.
- **Estado do QXA-4B21 (T-112, decisão do dono em 09/10, opção A):** corrigir Frota, Veiculo, Main, Vistoriador e a OS-119 em Manutencao conforme o caso "Estado do QXA-4B21 em 07 out" dos dados de referência e as divergências levantadas pelo produto em T-112 (acima, em Pontos em aberto): Alugado no tom `solido` (não azul) e "Colocar à venda" só em veículo `disponivel`.
- **Da T-152 (12 out 2026):** `Financeiro` (desktop e celular) sem "Saldo em contas", "Fluxo de caixa previsto", "Conciliar", "Aprovar despesa", "Pagar OS-0193", "Cobrar 2 clientes" em Para hoje e o seletor de período; "Sai hoje" e o contador "Contas a pagar" pelo seed (0 em 07 out); `Receber` sem "Exportar"; no menu das telas, "Locações" é 51 no seed (42 da carteira e 9 reservas) e "Usuários" não tem número (nenhum convite pendente).

### T-029 · Integração com o Asaas (sandbox)
- **Agente:** backend · **Depende de:** T-017 · **Segurança:** `WebhookRecebido` com `evento_id` único e conferência na API do Asaas, throttle (S-14, S-17) · **Regras:** FIN-01 a FIN-04, AUT-04, AUT-05 · **Pronto quando:** `backend/integracoes/pagamentos/asaas.py` implementa a interface de pagamentos (criar subconta da empresa, cobrança Pix e boleto, assinatura recorrente, webhook de baixa com verificação e idempotência), testado contra o sandbox; a implementação falsa continua sendo a padrão em testes.
- **Critérios (T-152):** `docs/qa/criterios/T-029.md` (testes de contrato com respostas gravadas no CI; sandbox só local, sem chave no repositório).

### T-020 · Telas de acesso e casca do app (sidebar e menu do celular)
- **Agente:** frontend · **Depende de:** T-002, T-004, T-011 · **Telas:** Login, Acesso-Senha, Convite, Main, Menu, e a navegação padrão descrita em `docs/telas/README.md`

### T-021 · Telas de veículos e clientes
- **Agente:** frontend · **Depende de:** T-020, T-013, T-014 · **Telas:** Frota, Veiculo, Clientes, Cliente · **Nota:** pode começar com dados falsos de `docs/api/veiculos.md` e `clientes.md`, como a T-020

### T-023 · Telas do financeiro básico
- **Agente:** frontend · **Depende de:** T-020, T-017 · **Telas:** Receber, Caixa, Financeiro
- **Critérios (T-152):** `docs/qa/criterios/T-023.md`. Divergências das telas no CA-023-25 e no CA-023-26 (para a T-028).

### T-025 · Testes ponta a ponta do fluxo de locação
- **Agente:** qa · **Depende de:** T-022, T-023 · **Pronto quando:** Playwright cobre login → nova locação → vistoria de saída → devolução → baixa no caixa, no desktop e no celular.
- **Critérios (T-152):** `docs/qa/criterios/T-025.md` (LOC-2858: R$ 629,00 na retirada; acerto de R$ 80,00 recebido no caixa em 14 out). Relógio com data e hora controladas no ambiente do E2E: qa com o arquiteto.

## Dúvidas abertas da T-020 (frontend)

- Resolvido na T-047: **Menu por permissão.** `eu.pode` não traz uma chave por item de menu; o frontend mapeia item -> chave em `frontend/src/lib/menu.ts` (ex.: Comissões e Conciliação por `financeiro_pagar`, Relatórios por `painel`, Locações por `locacoes_criar || vistorias_fazer`). Proposta: a API devolver `menu` (lista de módulos liberados) para a tela não inferir. Dono: arquiteto + produto (USR-05).
- Resolvido na T-047: **Início por perfil.** Vistoriador tem `painel: "nao"`; a T-020 mostra um aviso no lugar da visão geral. Falta definir a rota inicial de vistoriador, vendedor, gerente e financeiro (telas de início por perfil).
- Resolvido na T-047: **Contadores do menu e tela Main** vêm de `relatorios` (agregados), sem contrato em `docs/api/`. Hoje são dados falsos. Dono: arquiteto.
- **Pedido ao design-system:** seletor de filial com lista (USR-07, "Todas as filiais" para administrador); diálogo/gaveta para o menu do celular; KPI com valor longo ("R$ 18,4 mil") quebra em 3 linhas a 390px.

## Fase 2 em diante

Vendas e aprovações (VEN, APR), despesas, comissões e conciliação (FIN-05 a FIN-13), manutenção (MAN), automações (AUT), implantação self-service (IMP), cobrança da assinatura (PLT), relatórios e DRE, exportação e cancelamento (AUD-06 a AUD-08). Da exportação (`AUD-07`), o MVP tem só a auditoria em CSV (T-018); a fase 2 traz os outros itens (clientes, veículos, locações e contratos, financeiro, vistorias e fotos), a planilha (.xlsx, dependência nova registrada no PR), o backup completo em ZIP com as 2 etapas recentes, o backup mensal (`AUT-11`) com o cartão da tela, a exportação da plataforma (`/api/plataforma/exportacoes/`), o pedido do titular (`AUD-06`, à mão até lá) e o prazo após o cancelamento (`AUD-08`), decisão do dono de 12 out 2026 (T-151). O orquestrador quebra em tarefas quando a fase 1 fechar.
