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

- **Nota da T-012 (08/10):** a S-12 (SVG do logo sanitizado e exibido só por `<img>`) vale para `ConfiguracaoEmpresa.logo` (app `empresas`), e não para a filial. Entra na tarefa da marca da empresa (`Admin-Marca`), a criar.

### T-093 · Momentos em UTC na API
- **Agente:** backend · **Depende de:** T-088 · **ADRs:** 0020 · **Pronto quando:** `comum/renderizacao.py` ligado no `REST_FRAMEWORK` como na ADR 0020; os 3 testes de `backend/tests/test_formato_das_datas.py` passam sem `xfail` e a lista de pendentes do teste de varredura fica vazia; contas, aprovações, plataforma, veículos, filiais e clientes saem em `AAAA-MM-DDTHH:MM:SSZ` sem mexer nos serializers; OpenAPI sem mudança. Passos em `tarefas/handoffs/T-088-arquiteto.md`.

### T-091 · Locação: renovação, atraso, cancelamento e encerramento
- **Agente:** backend · **Depende de:** T-090 · **Regras:** LOC-08, LOC-10 a LOC-13, FIL-03, APR-02, AUT-02 · **Pronto quando:** CA-015-17 e 19 a 24 e o estorno do CA-015-25 passam, com o código da regra no nome do teste: renovação com aditivo; atraso com `calcular_atraso` e `aut_02`; cancelamento e encerramento antecipado com APR-02, reembolso e comissão estornada.

### T-017 · Contas a receber, caixa do dia, baixa
- **Agente:** backend · **Depende de:** T-015 · **Regras:** FIN-01 a FIN-08 · **Telas:** Receber, Caixa, Financeiro · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-017.md` (CA-017-01 a 23) passam, com o código da regra no nome do teste. · **Inclui:** usar o `juros_pro_rata` de `comum/dinheiro.py`, que vem da T-114 (CA-017-08: Carlos 70, Rafael 1123)

### T-018 · Tela e consulta da auditoria
- **Agente:** backend · **Depende de:** T-011 · **Regras:** AUD-01 a AUD-03 (o registro dos eventos já vem de T-001) · **Telas:** Admin-Auditoria, Plat-Auditoria · **Pronto quando:** todos os critérios de `docs/qa/criterios/T-018.md` (CA-018-01 a 16) passam, com o código da regra no nome do teste.

### T-130 · Edição da marca da empresa (Admin-Marca)
- **Agente:** arquiteto (contrato), depois backend e frontend · **Depende de:** T-129 · **Telas:** Admin-Marca, Onboarding-Marca · **Segurança:** S-12 · **Pronto quando:** o administrador da empresa envia o logo, escolhe a cor e o nome de exibição; o upload passa pela sanitização da S-12 com limite de tamanho, e a Segurança decide se aceita PNG além de SVG (a tela diz "PNG ou SVG, até 2 MB", o modelo de dados dizia só SVG); a troca invalida o cache de `GET /api/marca/` pela `versao`; auditoria da mudança; a prévia na tela usa as cores calculadas pela API, sem conta no frontend. Levantada na T-128 (`tarefas/handoffs/T-128-arquiteto.md`); a nota da T-012 sobre marca continua valendo. Não bloqueia o piloto: sem marca configurada, a API devolve o padrão.


### T-134 · Frontend: painel, marca e ficha do cliente na API nova
- **Agente:** frontend · **Depende de:** T-129 · **Pronto quando:** o início e os contadores do menu vêm de `GET /api/painel/inicio/` e `/contadores/` (bloco `null` não aparece, KPI com `valor: null` esconde o cartão, a variante decide o layout); a marca vem de `GET /api/marca/` no login, convite, primeiro acesso, esqueci a senha, entrada do suporte e na casca (logo sempre em `<img>`, cores pela API, sem conta no frontend); a ficha do cliente usa `pagamento.pago_centavos` e `veiculo.tipo` da linha de locação e o resumo `financeiro` do cliente quando vier, e deixa de somar o detalhe de cada locação; some `pago_detalhe`; a ficha do veículo esconde Manutenções e a do cliente a linha do tempo (handoff da T-128). Itens do "Frontend" nos handoffs da T-128 e da T-129.

### T-135 · Data de referência do relógio no desenvolvimento
- **Agente:** arquiteto · **Depende de:** T-127 · **Pronto quando:** ADR ou nota curta que decide como o ambiente de desenvolvimento (compose e seed) roda com uma data de referência fixa (ex.: 07 out 2026) para "vence hoje", atrasos, agenda e a devolução da LOC-2836 baterem com os números das regras, sem afetar produção (`comum.relogio`); quem liga e desliga, como o frontend mostra que a data é simulada, e a tarefa de backend ou devops que implementa. Levantada na T-127 (item 1 das divergências).

### T-136 · Permissões por perfil na API e nas rotas
- **Agente:** backend, depois frontend; revisão da seguranca · **Depende de:** T-017 · **Regras:** tabela de perfis, USR-08, USR-09, AUD-04 · **Pronto quando:** (D-25) a API não devolve valor nem dado de pagamento ao vistoriador (clientes, veículos, locações: `_centavos`, diária, total pago), e a tela esconde o que vier ausente; (D-26) toda rota do frontend que o menu do perfil não mostra responde com "Seu perfil não tem acesso" e a API responde 403 para o que o perfil não pode ver, não só o menu; (D-27, D-28, D-29, `USR-09`) o financeiro vê a ficha da locação só para leitura, com as ações de receber e de marcar reembolso como feito, e a ficha do cliente com contato, locações e o financeiro do cliente (total pago, em aberto, parcelas atrasadas com dias, pagamentos), sem documentos, endereço e análise do cadastro, e com Cobrar como única ação; o vistoriador não abre lista nem ficha do cliente (403 e "Seu perfil não tem acesso") e recebe do cliente, com a vistoria, só nome, celular e se a retirada está liberada (`CLI-02`, `CLI-03`); testes por perfil (vistoriador e financeiro) na API e no frontend, com `usr_09` no nome. Levantada em a conferência das telas do fim da T-127 (12 out 2026, `C:/Users/Jota/Documents/giro-produto/conferencia-telas.md`, fora do git; o handoff de cada tarefa copia os itens que resolver).

### T-137 · Correções das telas da conferência
- **Agente:** frontend · **Depende de:** T-134 · **Pronto quando:** (D-02) o início do financeiro abre sem erro, com o conteúdo da `USR-08` (entra hoje e em atraso; caixas do dia vazio e "Para hoje" só com reembolsos enquanto não há caixa e despesas); valor `null` da API aparece como "—" ou some, nunca como R$ 0 (D-04, D-06); (D-15) o aviso de pedir o encerramento ao gerente só aparece para quem não pode encerrar; (D-16) o acerto sem nível de combustível pede o nível em vez de mostrar R$ 0,00; (D-22) a coluna Pagamento usa o mesmo vocabulário; (D-23) rótulos de "Precisam de ação" e "Pagamentos atrasados" distinguem locações de parcelas; (D-30) o texto de cobrança só aparece depois do plano; (D-32) alvos de 44 px nas caixas de marcar; (D-33) itens do menu inferior com a mesma largura; e a suspeita de corrida na primeira requisição depois do login. Levantada em a conferência das telas do fim da T-127 (12 out 2026, `C:/Users/Jota/Documents/giro-produto/conferencia-telas.md`, fora do git; o handoff de cada tarefa copia os itens que resolver).
- **Inclui (12 out 2026, aprovado pelo dono):** (a) aberto sem subdomínio de empresa (`localhost`, `admin.localhost`, `127.0.0.1`), o frontend não mostra o login da empresa, que falha com 404: mostra "Este endereço não é de uma locadora. Entre pelo endereço da sua empresa." (ou o painel da plataforma, quando existir); (b) o erro "No queryFn was passed" da consulta `["eu"]` no console (32 vezes numa sessão), provável causa do "Não foi possível carregar sua conta" logo depois do login.

### T-138 · Ajustes do seed da conferência
- **Agente:** qa · **Depende de:** T-127 · **Pronto quando:** (D-01) há locação aguardando retirada para cada veículo `reservado`, e a vistoria de saída dá para abrir; (D-05) os planos e valores do seed batem com as tabelas (LOC-01, LOC-05); (D-07) só o Rafael com cadastro incompleto, os demais com documentos; (D-08, D-09) nomes e veículos menos genéricos onde a tela mostra; (D-10) veículo em manutenção com a OS ou sem o estado; (D-13) histórico nas datas reais do caso; (D-21) a 1ª parcela não nasce atrasada; (D-24) locações divididas entre vendedores; (D-12, `DEV-08`) toda locação ativa com vistoria de saída concluída, com o km e o combustível que a locação mostra (LOC-2836: 21.870 km, tanque cheio); (D-18) a receita da semana do gerente sai só das contas pagas do seed (`FIN-15`), com as datas de pagamento da carteira, e o teste confere o valor e a comparação com a semana anterior; (D-19) o seed grava todos os passos da implantação que a Moto Rápida fez (`IMP-05`: conta, marca, filial, ramo, preços, contrato, importar, equipe e `primeira_locacao`, este pela T-131), e a Mariana cai no início `geral` (`IMP-01`); e um caminho documentado para reproduzir o acerto de R$ 183,00 com o relógio real ou com a data de referência da T-135 (D-17). Seed continua idempotente e fictício (repositório público). Levantada em a conferência das telas do fim da T-127 (12 out 2026, `C:/Users/Jota/Documents/giro-produto/conferencia-telas.md`, fora do git; o handoff de cada tarefa copia os itens que resolver).

### T-140 · Dias de atraso do bloqueio e km de saída da devolução
- **Agente:** backend · **Depende de:** — · **Regras:** CLI-05, DEV-08, FIN-03 · **Pronto quando:** (D-03) no bloqueio automático, `bloqueio.descricao` de `GET /api/clientes/{id}/` é montada na leitura com os dias de atraso de hoje (dia corrido em `America/Sao_Paulo`, como a lista e a locação): Rafael em 12 out, "Conta com 30 dias de atraso desde 12/09/2026"; em 07 out, 25 dias; o evento de auditoria do bloqueio continua com o número do dia em que aconteceu; teste `test_cli_05_dias_de_atraso_de_hoje`. (D-12) o comparativo da devolução (`saida` de km e combustível em `vistorias.selectors`) usa o km e o combustível de saída gravados na locação, o mesmo `km_saida` da ficha; na troca, os do veículo que volta; LOC-2836 mostra 21.870 km na saída nas duas telas; teste `test_dev_08_km_de_saida_igual_na_ficha_e_na_devolucao`. Levantada na T-139 (`tarefas/handoffs/T-139-produto.md`).

### T-019 · Seed Moto Rápida
- **Agente:** qa · **Depende de:** T-013 a T-017 · **Pronto quando:** `make seed` cria a empresa de exemplo e todos os casos da tabela "Dados de referência para testes" passam.
- **Placas do seed (T-028):** PQD-6E21 (Pop do Rafael, LOC-2790), RJD-5B38 (Biz do Marcos, LOC-2850), RKP-3D26 (Kwid do Diego, LOC-2848); reserva do Kwid LOC-2857.

### T-026 · Desenhar telas que faltam para o MVP
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** "Esqueci a senha" e "Ativar verificação em 2 etapas" (desktop e celular) em `docs/telas/html/`, no mesmo padrão das telas de acesso, e no índice. Bloqueia a parte de 2FA de T-020.

### T-027 · Importação de veículos e clientes por planilha
- **Agente:** backend · **Depende de:** T-013, T-014 · **Regras:** IMP (passo de importar) · **Telas:** Onboarding-Importar · **Por quê:** critério de pronto do MVP "dados antigos migrados e conferidos".

### T-028 · Limpar dados de exemplo das telas
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** os números das telas batem com as regras e o seed. Já se sabe de: Patrícia (LOC-2812) aparece em Contas a receber com parcela de R$ 279,00 (plano Entregador, placa SAB-2K90), mas é mensal NMax SBC-0J44 nas outras telas; Marcos (LOC-2850) aparece com a placa SBC-0J44; ficha do veículo QXA-4B21 mostra "Plano padrão Semanal R$ 299,40" (Street agora é R$ 329,00); Juliana aparece "em dia" em Clientes e com parcela atrasada em Contas a receber; Financeiro mostra "3 clientes com 7+ dias R$ 1.299,40". Corrigir no canvas e em `docs/telas/html/`. Inclui `Despesas-Desktop` e `Despesas-Mobile`: aguardando aprovação é R$ 1.200,00 (não R$ 1.386,40) e o IPVA de R$ 186,40 nasce `a_pagar` (FIN-05), apontado pelo qa na T-040.
- **Estado do QXA-4B21 (T-112, decisão do dono em 09/10, opção A):** corrigir Frota, Veiculo, Main, Vistoriador e a OS-119 em Manutencao conforme o caso "Estado do QXA-4B21 em 07 out" dos dados de referência e as divergências levantadas pelo produto em T-112 (acima, em Pontos em aberto): Alugado no tom `solido` (não azul) e "Colocar à venda" só em veículo `disponivel`.

### T-029 · Integração com o Asaas (sandbox)
- **Agente:** backend · **Depende de:** T-017 · **Segurança:** `WebhookRecebido` com `evento_id` único e conferência na API do Asaas, throttle (S-14, S-17) · **Regras:** FIN-01 a FIN-04, AUT-04, AUT-05 · **Pronto quando:** `backend/integracoes/pagamentos/asaas.py` implementa a interface de pagamentos (criar subconta da empresa, cobrança Pix e boleto, assinatura recorrente, webhook de baixa com verificação e idempotência), testado contra o sandbox; a implementação falsa continua sendo a padrão em testes.

### T-020 · Telas de acesso e casca do app (sidebar e menu do celular)
- **Agente:** frontend · **Depende de:** T-002, T-004, T-011 · **Telas:** Login, Acesso-Senha, Convite, Main, Menu, e a navegação padrão descrita em `docs/telas/README.md`

### T-021 · Telas de veículos e clientes
- **Agente:** frontend · **Depende de:** T-020, T-013, T-014 · **Telas:** Frota, Veiculo, Clientes, Cliente · **Nota:** pode começar com dados falsos de `docs/api/veiculos.md` e `clientes.md`, como a T-020

### T-023 · Telas do financeiro básico
- **Agente:** frontend · **Depende de:** T-020, T-017 · **Telas:** Receber, Caixa, Financeiro

### T-024 · Revisão de segurança do MVP
- **Agente:** seguranca · **Depende de:** T-011, T-014, T-018 · **Pronto quando:** checklist de `.claude/agents/seguranca.md` aplicado, achados viram tarefas.

### T-025 · Testes ponta a ponta do fluxo de locação
- **Agente:** qa · **Depende de:** T-022, T-023 · **Pronto quando:** Playwright cobre login → nova locação → vistoria de saída → devolução → baixa no caixa, no desktop e no celular.

## Dúvidas abertas da T-020 (frontend)

- Resolvido na T-047: **Menu por permissão.** `eu.pode` não traz uma chave por item de menu; o frontend mapeia item -> chave em `frontend/src/lib/menu.ts` (ex.: Comissões e Conciliação por `financeiro_pagar`, Relatórios por `painel`, Locações por `locacoes_criar || vistorias_fazer`). Proposta: a API devolver `menu` (lista de módulos liberados) para a tela não inferir. Dono: arquiteto + produto (USR-05).
- Resolvido na T-047: **Início por perfil.** Vistoriador tem `painel: "nao"`; a T-020 mostra um aviso no lugar da visão geral. Falta definir a rota inicial de vistoriador, vendedor, gerente e financeiro (telas de início por perfil).
- Resolvido na T-047: **Contadores do menu e tela Main** vêm de `relatorios` (agregados), sem contrato em `docs/api/`. Hoje são dados falsos. Dono: arquiteto.
- **Pedido ao design-system:** seletor de filial com lista (USR-07, "Todas as filiais" para administrador); diálogo/gaveta para o menu do celular; KPI com valor longo ("R$ 18,4 mil") quebra em 3 linhas a 390px.

## Fase 2 em diante

Vendas e aprovações (VEN, APR), despesas, comissões e conciliação (FIN-05 a FIN-13), manutenção (MAN), automações (AUT), implantação self-service (IMP), cobrança da assinatura (PLT), relatórios e DRE, exportação e cancelamento (AUD-06 a AUD-08). O orquestrador quebra em tarefas quando a fase 1 fechar.
