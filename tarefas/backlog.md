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

- [decisão] (qa, T-019) Troca de óleo da QXA-4B21 (CA-019-10: última aos 18.900 km, próxima aos 19.900) não tem onde morar: `apps/manutencao` é só README (`MAN-03`). `xfail` em `test_man_03_seed_019_10_proxima_troca_de_oleo_aos_19900`; o seed ganha o dado quando o módulo existir.
- [decisão] (qa, T-019) Sem módulo no backend, os casos da fase 2 (CA-019-31) seguem `xfail`: venda VEN-0177, comissões, conciliação e DRE de setembro. Orquestrador: criar as tarefas de backend desses módulos; o seed ganha os dados com cada um.
- [decisão] (arquiteto, T-193) **Reativar a empresa `cancelada` com fatura em atraso** (`PLT-06`). A regra diz que a reativação pela equipe volta "como na volta da pausa" (`ativa`, fatura nova no dia), e que a fatura em atraso de antes do cancelamento continua devida, mas não diz o que acontece com ela na volta: A) a equipe só reativa depois de receber a atrasada; B) reativa, e a atrasada volta à régua (a empresa vira `inadimplente` no dia seguinte). Até a resposta, o contrato recusa (A). Para o produto.
- [decisão] (arquiteto, T-193) **Endereço da empresa para a NFS-e da assinatura** (`PLT-15`). A nota leva o endereço, mas a compra não pede endereço e o seed da Moto Rápida não tem um. O contrato deixa o endereço nulo até o administrador preencher em dados fiscais e segura a nota sem ele. Falta: A) a compra (`Compra-Checkout`) passa a pedir o endereço; B) fica só nos dados fiscais (e o assistente avisa); e qual endereço entra no seed. Para o produto.
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

- (T-017) As 3 dúvidas da T-017 foram decididas em 12 out 2026 pelo dono do produto, com as recomendações do produto, e viraram regra na T-147: (1) histórico da análise com o atraso pela `FIN-03` e o cliente novo `ok` "Cliente novo na empresa" (`CLI-04`, B); (2) semana de segunda a domingo e caução fora das abas e da lista geral (`FIN-15`, A); (3) bloqueio uma vez por conta e textos da régua reescritos, com e-mail (`AUT-03`, `CLI-05`, `AUT-05`, B). Código na T-148 (feita, PR a abrir).

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

Propostas pela segurança na T-024 (12 out 2026, `tarefas/handoffs/T-024-seguranca.md`), numeradas pelo orquestrador; nenhuma alta. A T-155 (M-01) entrou no PR #160 (ver `feito.md`).

### T-157 · (M-03) Produção recusa e-mail no console e armazenamento falso (média)
- **Agente:** backend · **Depende de:** — · **Pronto quando:** `config/settings/prod.py` recusa subir com `EMAIL_BACKEND` de console, locmem ou arquivo (o padrão de `base.py` é o console, e os e-mails de senha, convite e assinatura levam o token) e com `GIRO_ARMAZENAMENTO` diferente de `s3`, como já faz com as chaves; pagamentos e WhatsApp `falso` entram na mesma trava quando as integrações reais existirem (T-029); teste que importa `prod.py` com o ambiente montado. Antes de homologação.

### T-158 · (M-04) Configuração do proxy reverso: tamanho do corpo e cabeçalhos `X-Forwarded-*` (média)
- **Agente:** devops, com o backend · **Depende de:** — · **Pronto quando:** a configuração do proxy de homologação e produção está em `infra/`, com limite de corpo de 12 MB (os uploads só são conferidos por `comum/arquivos.validar` depois de recebidos inteiros, e o Django não limita arquivo em multipart), `X-Forwarded-Host`, `X-Forwarded-Proto` e `X-Forwarded-For` sempre sobrescritos pelo proxy (o `TenantMainMiddleware` escolhe a empresa por `get_host()`, que segue o `X-Forwarded-Host` com `USE_X_FORWARDED_HOST = True`) e rate limit de borda em `/api/auth/` e no webhook; no backend, `USE_X_FORWARDED_HOST` só em `prod.py`; checklist no `infra/README.md`. Antes de homologação.

### T-156 · (M-02) Custo e rendimento do veículo fora da ficha do vendedor (média)
- **Agente:** backend, depois frontend · **Depende de:** T-136 · **Regras:** tabela de perfis, USR-09, VEI-05 · **Decisão:** opção A do dono do produto em 12 out 2026 (regra na T-156 do produto) · **Pronto quando:**
  - (backend) em `GET /api/veiculos/{id}/`, a chave `indicadores_financeiros` (`rendeu_no_ano_centavos`, `custo_manutencao_ano_centavos`) só vem para administrador, gerente e financeiro, pela mesma checagem do `valor_compra_centavos` em `veiculos/selectors.representacao` com o financeiro incluído; para vendedor e vistoriador a chave vem **ausente** (não `null`, não zero), como no D-25; OpenAPI com a chave opcional; teste `test_usr_09_vendedor_sem_custo_do_veiculo`;
  - CA: dado a Bruna (vendedora), quando faz `GET /api/veiculos/{id}/` de um veículo da filial dela, então a resposta não tem `indicadores_financeiros`, e o resto da ficha (situação, ocupação, km, documentos, preços) vem como antes;
  - CA: dado o Rodrigo (gerente), a Mariana (administradora) ou a Lúcia (financeiro), quando fazem a mesma leitura, então recebem `rendeu_no_ano_centavos` e `custo_manutencao_ano_centavos` com os mesmos valores de hoje;
  - CA: dado o João (vistoriador), nada muda: o bloco continua ausente (D-25);
  - (frontend) na ficha do veículo (`Veiculo`, desktop e celular), os cartões "Rendeu no ano" e "Custo de manutenção" só aparecem quando a API manda o bloco; logada como Bruna, a fileira de indicadores mostra só ocupação e km, sem cartão vazio, traço ou espaço reservado. A tela não decide pelo perfil, só pela chave.

### T-159 · (M-05) Login não revela e-mail com convite pendente (baixa)
- **Agente:** backend · **Depende de:** — · **Regras:** USR-01, USR-06 · **Pronto quando:** em `POST /api/auth/entrar/`, quem tem convite pendente e ainda não tem senha recebe o mesmo 401 `credenciais_invalidas` (e o mesmo tempo) de um e-mail que não existe; hoje o 403 `convite_pendente` sai antes de conferir a senha e permite saber quem foi convidado; o 403 só depois da senha certa; teste `test_usr_06_convite_pendente_nao_revela_email`.

### T-160 · (M-06) API navegável do DRF desligada em produção (baixa)
- **Agente:** backend · **Depende de:** — · **Pronto quando:** `prod.py` deixa em `DEFAULT_RENDERER_CLASSES` só o `comum.renderizacao.JSONRenderer` (hoje o `BrowsableAPIRenderer` de `base.py` mostra formulários e descrições das views no navegador, o que o S-17 fechou para o OpenAPI); teste que confere a lista em produção.

- **Nota da T-012 (08/10):** a S-12 (SVG do logo sanitizado e exibido só por `<img>`) vale para `ConfiguracaoEmpresa.logo` (app `empresas`), e não para a filial. Entra na tarefa da marca da empresa (`Admin-Marca`), a criar.

### T-153 · Escrita da marca (backend)
- **Agente:** backend · **Depende de:** T-129 · **ADR:** 0022 · **Contrato:** `docs/api/empresas.md` ("Escrita da marca") · **Regras:** IMP-05, S-12 · **Pronto quando:** `empresas/logo.py` com `limpar_logo` pela ADR 0022 (`defusedxml`, dependência nova com motivo no PR; listas fechadas em constantes iguais às da ADR; recusa do conteúdo ativo com `WARNING` sem conteúdo no log); `empresas.services.salvar_marca` numa transação com `select_for_update`, evento `empresa.alterar_marca` (categoria `configuracoes`, `CAMPOS_AUDITORIA` com `nome_exibicao`, `cor_marca` e `logo`), e no `on_commit` apaga a chave `marca:<schema>` e o arquivo antigo (e o novo se a transação falhar), e chama `registrar_passo_implantacao("marca")`; `PATCH /api/marca/` (multipart e JSON, só administrador, 403 ao suporte e à empresa sem operação, 30 por hora por usuário) e `POST /api/marca/simular/` (120 por minuto por usuário), com as mensagens do contrato; sem mudança idempotente não grava evento nem muda a `versao`; PNG pelo item 6 da ADR 0022 e a nota de 13 out 2026 (sem o 400 "Envie o logo em SVG."); OpenAPI regenerado e `api:gerar` no frontend; testes `test_s_12_*` (um por vetor da ADR, e os que passam), `test_imp_05_salvar_marca_marca_o_passo`, `test_marca_simular_seis_cores` (tabela "As seis cores do `Onboarding-Marca`"), `test_marca_patch_invalida_cache_e_versao` (`ETag` novo; `If-None-Match` com a versão antiga recebe 200), `test_marca_patch_so_administrador`, e os do PNG: `test_s_12_png_passa_sem_metadados`, `test_s_12_png_em_paleta_mantem_cores_e_transparencia`, `test_s_12_png_acima_de_4096_recusado_sem_decodificar`, `test_s_12_png_assinatura_forjada`, `test_s_12_png_truncado`, `test_s_12_png_poliglota`, `test_s_12_png_animado_grava_primeiro_quadro` e `test_s_12_png_servido_com_nosniff`.
- **Contrato pronto (12 out 2026, arquiteto):** `docs/api/empresas.md`, seção "Escrita da marca (T-130)" (`POST /api/marca/simular/` e `PATCH /api/marca/`), e ADR 0022 (sanitização do logo). Cor padrão pela saída (b) de `cores-da-marca.md` (valores fixos do `wl-theme.css` para `#C8F04A`), como o código da T-129 já faz. Handoff: `tarefas/handoffs/T-130-arquiteto.md`.
- **Decisão (13 out 2026, seguranca): PNG aceito** (`C:/Users/Jota/Documents/giro-produto/decisao-t153-seguranca.md`, fora do git; nota no item 6 da ADR 0022 e mensagem nova em `docs/api/empresas.md`). Condições: assinatura completa nos 8 primeiros bytes e `format == "PNG"` depois de abrir; 2 MB conferidos antes de abrir; lado até 4.096 px e área até 4.096 × 4.096 conferidos em `size` antes do `load()`, sem mudar `Image.MAX_IMAGE_PIXELS` global; `verify()`, reabertura e conferência de novo; `convert("RGBA")` e gravação nova sem `pnginfo`, `exif`, `icc_profile` nem `save_all` (não reaproveitar `comum.arquivos.sem_metadados`, que perde a paleta); APNG só com o primeiro quadro; o PNG novo também até 2 MB; erro de leitura com "Não conseguimos ler este PNG. Exporte o logo de novo pelo seu programa de desenho." e `WARNING` sem conteúdo, nunca 500. Testes: `test_s_12_png_passa_sem_metadados`, `test_s_12_png_em_paleta_mantem_cores_e_transparencia`, `test_s_12_png_acima_de_4096_recusado_sem_decodificar`, `test_s_12_png_assinatura_forjada`, `test_s_12_png_truncado`, `test_s_12_png_poliglota`, `test_s_12_png_animado_grava_primeiro_quadro` e `test_s_12_png_servido_com_nosniff`.

### T-154 · Tela Empresa e marca e passo Marca do assistente (frontend)
- **Agente:** frontend · **Depende de:** T-153 · **Contrato:** `docs/api/empresas.md` · **Telas:** Admin-Marca, Onboarding-Marca · **Pronto quando:** `/admin/marca` com o bloco "Marca" (logo com Trocar e Remover, Cor principal, Nome que aparece para clientes) e a "Prévia", ligados a `GET /api/marca/`, `POST /api/marca/simular/` e `PATCH /api/marca/`; os blocos "Dados da empresa" e "Endereço do sistema" ficam fora (sem contrato); no assistente, só "Logo" e "Cor de destaque" com as seis cores, ligados às mesmas rotas, se a casca do assistente existir (senão, o componente fica pronto para ela); a prévia usa só as cores da simulação (nenhuma conta de cor no frontend; o script das telas de referência é desenho), e o logo não salvo aparece por `URL.createObjectURL` em `<img>`, nunca inline; depois de salvar, a consulta `marca` recebe o corpo e é invalidada, e a casca troca as cores; erro 400 no campo com a `mensagem` da API; ajuda do logo "PNG ou SVG, fundo transparente, até 2 MB" e `accept="image/png,image/svg+xml,.png,.svg"`; testes do componente (prévia com `#2F6FED` → `cor_sobre` `#FFFFFF` e `cor_suave` `#DBF3FF` vindos da API mockada; logo por `<img>`; Remover mostra as iniciais).

### T-140 · Dias de atraso do bloqueio e km de saída da devolução
- **Agente:** backend · **Depende de:** — · **Regras:** CLI-05, DEV-08, FIN-03 · **Pronto quando:** (D-03) no bloqueio automático, `bloqueio.descricao` de `GET /api/clientes/{id}/` é montada na leitura com os dias de atraso de hoje (dia corrido em `America/Sao_Paulo`, como a lista e a locação): Rafael em 12 out, "Conta com 30 dias de atraso desde 12/09/2026"; em 07 out, 25 dias; o evento de auditoria do bloqueio continua com o número do dia em que aconteceu; teste `test_cli_05_dias_de_atraso_de_hoje`. (D-12) o comparativo da devolução (`saida` de km e combustível em `vistorias.selectors`) usa o km e o combustível de saída gravados na locação, o mesmo `km_saida` da ficha; na troca, os do veículo que volta; LOC-2836 mostra 21.870 km na saída nas duas telas; teste `test_dev_08_km_de_saida_igual_na_ficha_e_na_devolucao`. Levantada na T-139 (`tarefas/handoffs/T-139-produto.md`).

### T-146 · Status do caixa como enum no painel
- **Agente:** backend · **Depende de:** T-017 · **Regras:** FIN-07, FIN-08 · **Pronto quando:** `status` de `caixa_hoje` e de `caixas_do_dia` em `GET /api/painel/inicio/` é `ChoiceField` com `aberto`, `aguardando_aprovacao`, `fechado` e `fechado_sem_conferencia` (hoje é `CharField` e o OpenAPI sai `string`, sem o enum para o cliente tipado); `openapi.yaml` regenerado; teste com o caixa de hoje `fechado` aparecendo em `caixa_hoje` (`test_fin_07_caixa_hoje_em_qualquer_status`). Levantada na T-144 (`tarefas/handoffs/T-144-arquiteto.md`).

### T-150 · Filial nos eventos de movimento de caixa
- **Agente:** backend · **Depende de:** T-018 · **Regras:** FIN-07, AUD-01, AUD-02 · **Decisão:** arquiteto, 12 out 2026 (a ação continua `movimento_caixa.sangria`, objeto `movimentocaixa`, padrão `<objeto>.<verbo>`) · **Pronto quando:** os eventos `movimento_caixa.*` (entrada, saída, sangria, estorno, `estorno_motivo`) gravam o `filial_id` do caixa: `registrar_evento` e `auditar` em `comum/auditoria.py` aceitam `filial_id: int | None = None` (keyword; quando vier, vale ele, senão `getattr(objeto, "filial_id", None)`; sem mudança de schema); `_registrar_movimento` e o `registrar_evento("movimento_caixa.estorno_motivo", ...)` de `estornar_movimento` em `financeiro/services.py` passam `filial_id=caixa.filial_id`; em `auditoria/textos.py` o detalhe da `movimento_caixa.sangria` vira "Caixa da <filial>" (consulta `filiais`) e sai a entrada `caixa.sangria`, que nenhum serviço grava; sem migração de dados (eventos imutáveis, ADR 0010; o seed é recriado). Testes: `test_fin_07_sangria_audita_com_filial_do_caixa` (seed em 07 out: a sangria de R$ 500,00 da Bruna em `GET /api/auditoria/eventos/?filial=<Filial Centro>` com `resumo` "Fez sangria de R$ 500,00", `detalhe` "Caixa da Filial Centro" e `objeto.filial` "Filial Centro"); `test_fin_07_movimentos_e_estorno_auditam_com_filial` (entrada, saída e estorno com o `filial_id` do caixa; filtro por outra filial não os traz); os testes da auditoria de objetos com `filial_id` próprio passam sem mudança. Contrato em `docs/api/auditoria.md` já ajustado na T-151.

### T-162 · Flag `lancamento_avulso` em `pode`
- **Agente:** backend, depois frontend · **Depende de:** T-023 · **Regras:** tabela de perfis, FIN-07 · **Pronto quando:** `pode` (contas, `docs/api/contas.md`) devolve `lancamento_avulso` para quem pode fazer lançamento avulso no caixa pela tabela de perfis (hoje o frontend usa `despesas_aprovar || financeiro_pagar`, que dá administrador, gerente e financeiro); contrato atualizado e teste por perfil; o frontend troca a condição do botão "Novo lançamento" pela flag. Se a tabela de perfis não disser quem faz o lançamento avulso, `[decisão]` para o produto antes do código. Levantada pelo frontend na T-023 (divergência b).

### T-165 · Fotos da vistoria em PNG com paleta perdem as cores (baixa)
- **Agente:** backend · **Depende de:** — · **Regras:** VIS-02 · **Pronto quando:** `comum.arquivos.sem_metadados` mantém as cores de um PNG em modo `P` (com paleta e `tRNS`): hoje faz `Image.new(imagem.mode, ...)` + `paste`, e a imagem nova sai sem a paleta. Converter para `RGBA` (ou copiar a paleta) antes de gravar, sem voltar a gravar metadados; teste com PNG em paleta comparando os pixels. Não é falha de segurança. Levantada pela segurança na decisão do PNG da T-153 (12 out 2026, `C:/Users/Jota/Documents/giro-produto/decisao-t153-seguranca.md`, fora do git).

### T-170 · Tela de Administração › Assinatura
- **Agente:** frontend · **Depende de:** — · **Regras:** PLT · **Telas:** Admin-Assinatura (desktop e celular) · **Contrato:** `docs/api/plataforma.md` e `empresas.md` (`/api/assinatura/`) · **Pronto quando:** `/admin/assinatura` igual a `docs/telas/html/Admin-Assinatura-*.dc.html`, ligada à API real, só com o que o contrato tem (pausar e cancelar entram no MVP pela T-190, em tarefa própria; até lá, o botão não aparece; o que faltar vira `[decisão]`); só o administrador; testes. Pedida pelo dono em 13 out 2026.

### T-183 · Contrato da Assinatura completa
- **Agente:** arquiteto · **Depende de:** T-170, T-029 · **Regras:** PLT-01 a PLT-05, AUT-13 · **Telas:** Admin-Assinatura (desktop e celular) · **Estado:** contrato escrito, PR a abrir (`docs/api/assinatura.md`, ADR 0023, modelo de dados). Decisão do dono em 14 out 2026: a tela entra inteira no MVP. Cancelar e pausar (`PLT-06`) ficam com o produto.
- **Tarefas (numeradas pelo orquestrador em 14 out 2026):**
  - **T-184 · backend · Faturas da assinatura e conta principal no parceiro.** `FaturaAssinatura` (com `tipo`, período, `plano`), `FormaPagamentoAssinatura`, `Empresa.email_cobranca`; 1ª fatura em `criar_empresa` (vence `teste_fim + 1`, `PLT-01`: Moto Rápida em 22 out, 44900) e no seed; conta principal na interface de pagamentos (pagador, `cobrar_cartao_salvo`, cartão em `SituacaoCobranca`, ADR 0023) e webhook da conta principal baixando a fatura. Testes `test_plt_01_primeira_fatura_dia_seguinte_ao_teste`, webhook idempotente da fatura. Sandbox: confirmar como o parceiro devolve o token do cartão.
  - **T-185 · backend · Rotas da Assinatura (`docs/api/assinatura.md`).** Campos novos do `GET /api/assinatura/`, `planos/`, `mudanca-plano/` (simular, confirmar, desfazer), `forma-pagamento/`, `faturas/` (lista, detalhe, pagar), `dados-fiscais/`; só administrador, token de suporte só lê, `suspensa` paga (exceção ao `somente_leitura`); serviço único `mudar_plano` também na ação da plataforma. Testes `test_plt_04_downgrade_nao_cabe` (Moto Rápida → Essencial: 86 de 30, 5 de 3), `test_plt_04_upgrade_em_teste`, `test_plt_04_upgrade_proporcional` (30484, se [D-3] for A). OpenAPI regenerado. Depende das [D-1] a [D-9] só nos trechos marcados.
  - **T-186 · backend · Régua e estados da assinatura (`AUT-13`, `PLT-02`).** Tarefas `gerar_faturas` e `aut_13_regua_assinatura`: emissão N dias antes [D-7], lembretes D-3/D0/D+3/D+7, cartão recusado com nova tentativa no dia seguinte, `inadimplente` em D+1, `suspensa` em D+15 e no fim do teste sem forma [D-1], `ativa` ao pagar; auditoria nos dois schemas. Testes com o relógio de referência (ADR 0021).
  - **T-187 · frontend · Assinatura completa.** Completa a tela da T-170: "Mudar de plano" e "Comparar planos" (lista, simular, confirmar, aviso do downgrade que não cabe), forma de pagamento (Pix automático com QR do copia e cola, cartão pela página do parceiro com volta à tela, boleto), tabela de faturas com "Pagar" e recibo, dados fiscais com edição, cartão da `oferta`; "a partir de 22 out" pela `proxima_fatura`. Depende da tarefa das rotas.
  - **T-188 · design-system · Telas da assinatura.** `Admin-Assinatura-*`: "a partir de 22 out" (`PLT-01`), descrição da fatura pelo período, cartão do plano Completo sem NF-e nem portal até [D-10]; `Compra-Checkout-*` sem campos de cartão (ADR 0023).
  - **T-189 · segurança · Revisão do cartão e da conta principal.** ADR 0023 (token cifrado, nada de cartão no Giro), webhook da conta principal, exceção da `suspensa` ao `somente_leitura`, escrita barrada ao suporte.
- **[D-1] a [D-10] respondidas na T-190 (14 out 2026):** regras `PLT-01` a `PLT-06` e `PLT-11` a `PLT-15`, tabela "Decisões de 14 out 2026". Muda o que o contrato recomendava em [D-1] (a forma de pagamento não ativa a empresa; só a 1ª fatura paga) e [D-10] (o cartão do Completo sem domínio próprio e API, título "Precisa de mais veículos ou filiais?"); as outras seguem o contrato. T-185 e T-186 seguem a tabela de estados nova; o ajuste do contrato é a proposta 2 da T-190.

### T-190 · Regras das decisões do dono de 14 out 2026
- **Agente:** produto · **Depende de:** T-183 · **Regras:** PLT-01 a PLT-06, PLT-11 a PLT-15, FIL-01, DEV-01, APR-08, APR-12, AUT-03, AUD-07, AUD-08 · **Estado:** regras e critérios escritos, PR a abrir. O dono aprovou o padrão nos 18 itens da "Lista única" (U1 a U18, análise do produto fora do git, `C:/Users/Jota/Documents/giro-produto/analise-decisoes-telas.md`), inclusive nas divergências: U1, U10 e U11 pelo produto (U10 com ADR do arquiteto), U4 e U13 pelo arquiteto. Critérios: `docs/qa/criterios/assinatura.md` (CA-ASS-01 a 39), `aprovacoes.md` (CA-APR-01 a 10) e `filiais.md` (CA-FIL-01 a 06). `plano.md`: planos, cobrança, cancelar e pausar saem da fase 3 para o MVP. Três pontos em aberto com padrão nas regras (downgrade agendado que deixa de caber, início da pausa, desfazer o cancelamento).
- **Tarefas da T-190 (numeradas pelo orquestrador em 14 out 2026):**
  1. **T-192 · arquiteto · ADR dos módulos por plano (`PLT-12`).** `GIRO_MODULOS_ATIVOS` passa a valer por empresa (plano e ramo da implantação); tabela de app por plano; o código da recusa da rota de módulo desligado; navegação (`contas.navegacao`) e Configurações pelo conjunto da empresa; recusa do downgrade com o que está aberto em cada módulo (como a `FIL-06`); `AUT-03` só por e-mail e passo 10 fora no Essencial; `plataforma.md`, "Planos": sem `dominio_proprio` e `api_integracoes` nos `recursos` (`PLT-11`). CA-ASS-20 a 25.
  2. **T-193 · arquiteto · Contrato da assinatura pelas decisões.** `assinatura.md` sem as marcas [D-n]: a forma não ativa a empresa e `forma_pagamento.prazo` (U1), uma tentativa só do cartão (U8), NFS-e pelo parceiro depois de paga e o e-mail de cobrança (U9, `PLT-15`), `oferta` com o título "Precisa de mais veículos ou filiais?" e os textos da `PLT-11` (U11), mudança no teste com a 1ª fatura já paga (`PLT-04`), ciclo e reativação da cancelada pela equipe; `plataforma.md`: faturas de todas as empresas pelo Django Admin até a `Plat-Cobranca` (U13). Avisar T-184 a T-189 do que mudar. CA-ASS-01 a 21 e 26 a 29. **Estado (14 out 2026):** contrato ajustado, PR a abrir (`assinatura.md` com "O que muda para as tarefas abertas", `plataforma.md` "Faturas de todas as empresas", modelo de dados); handoff `tarefas/handoffs/T-193-arquiteto.md`.
  3. **T-194 · arquiteto · Contrato de cancelar e pausar (`PLT-06`, `AUD-08`).** Rotas (cancelar com motivo e nome digitado, pausar por 1 a 3 meses, voltar da pausa), `acoes.cancelar` e `acoes.pausar` e as datas de acesso e de pausa no `GET /api/assinatura/`, faturas canceladas, régua parada, os três pontos em aberto pelo padrão, a tarefa que apaga no 90º dia e o aviso de 7 dias. CA-ASS-30 a 39.
  4. **T-195 · backend · Cancelar, pausar e apagamento** (depois da T-194). `test_plt_06_*`, `test_aud_08_*`, CA-ASS-30 a 39. O apagamento tem de existir antes do 90º dia do primeiro cancelamento real.
  5. **T-196 · backend · Módulos por plano** (depois da T-192). `test_plt_12_*`, CA-ASS-22 a 25.
  6. **T-197 · backend · NFS-e da assinatura (`PLT-15`).** Emissão pelo parceiro depois da baixa; `[bloqueada]` até o contador confirmar e o cadastro municipal do Giro existir. CA-ASS-29.
  7. **T-198 · frontend · Cancelar assinatura e pausa** (depois da T-195). `Admin-Cancelar` (motivo, oferta de pausar só na `ativa` e de mudar para o Essencial, "O que acontece" pela API, nome digitado) e pausa e volta na `Admin-Assinatura`. CA-ASS-30, 31, 35 a 38.
  8. **T-199 · segurança · Revisão do cancelamento, da pausa e do apagamento.** Quem pode, 2 etapas recentes para cancelar e trocar a forma de pagamento, apagamento sem cruzar empresas e com evento na plataforma. Junto com a T-189, se ainda aberta.
  9. **T-200 · design-system · Telas de referência pelas decisões** (complementa a T-188). `Compra-Planos-*` e `Plat-Planos-*` com o catálogo da `PLT-11` (sem NF-e, assinatura digital como extra, domínio próprio, portal do cliente, API; `Plat-Planos` sem o bloco de adicionais); `Admin-Assinatura-*` (cartão "Precisa de mais veículos ou filiais?"; sai "Você pode exportar todos os seus dados"); `Admin-Cancelar-*` (sem pausar em teste; "Exportar dados antes" diz o que se baixa e que o resto é pedido à equipe); `Compra-Checkout-*` com 22 out; `Filial-*` (preço do litro no bloco Operação; nome curto; horário por dia com até 2 intervalos; Telefone no celular; "O recebimento é da empresa; o preço pode ser da empresa ou da filial"; no limite, "mude de plano"); `Admin-Usuarios-*` (rótulos neutros, "da pessoa", "A pessoa sai do sistema na hora", redefinir 2 etapas, sessões, reativar e cancelar convite no painel, gaveta no celular); `Admin-Auditoria-*` (chip Suporte sem número); `Aprovacoes-*` (aba Meus pedidos, sem a frase das 4 horas); `Config-*` ("Baixe a auditoria em CSV"); assistente ("Corrigir aqui" dentro da lista; não pôr "Passo 7 de 8" e "6 de 10 passos" lado a lado).
  10. **T-201 · arquiteto · Contratos das telas resolvidas.** `filiais.md` com `nome_curto` (`FIL-01`); `aprovacoes.md` com os números da `APR-12` (indicadores e contagens por aba), o bloco `resumo` por tipo (células prontas: `APR-01` preço de tabela, com desconto, desconto e o limite de quem pediu; `APR-02` plano, dias restantes, multa e estimativa; `APR-03` fornecedor, veículo, valor, vencimento e forma; `APR-04` esperado, contado e diferença; `APR-05` motivo do bloqueio e situação das contas; `APR-06` km atual e km pedido) e "Meus pedidos"; `auditoria.md` com o evento "Mudou a tabela de preço" de 01 out no seed (10 eventos em "Últimos 7 dias", 2 em `?categoria=configuracoes`) e o tom ou `destaque` por evento; o andamento dos passos do assistente (no `eu` ou numa rota do assistente); `configuracoes.md` com o nome curto no resumo de Filiais. CA-APR-01 a 10, CA-FIL-01 a 06.
  11. **T-202 · backend · Telas resolvidas** (depois da T-201). `nome_curto` da filial (`test_fil_01_nome_curto`); números e contagens da `APR-12` (`test_apr_12_*`) e o `resumo`; evento de 01 out no seed; andamento do assistente.
  12. **T-203 · frontend · Telas resolvidas** (depois da T-202). Usuários ("Escolha as filiais da pessoa", "A pessoa sai do sistema na hora"); Filial (preço do litro no bloco Operação, só para o administrador; nome curto; horário por dia com até 2 intervalos); seletor e listas pelo nome curto, sem cortar "Filial "; Aprovações (indicadores, contagens das abas, células do `resumo`; "Ver proposta" some até a venda ter tela); Importar (passos feitos quando a API mandar). CA-FIL-01 a 05, CA-APR-01 a 10.
  13. **T-204 · qa · Seed e critérios das decisões.** Horas dos dois pedidos aprovados (caso "Números da tela Aprovações em 07 out"); evento de 01 out na auditoria (CA-018-09 passa a 10 eventos, 2 em configurações); testes de aceitação de `assinatura.md` com o relógio de referência, à medida que as tarefas de código fecharem.

### T-171 · Telas de Auditoria da empresa e Exportar dados
- **Agente:** frontend · **Depende de:** T-018, T-151 · **Regras:** AUD-01 a AUD-04, AUD-07 · **Telas:** Admin-Auditoria e Admin-Exportar (desktop e celular) · **Contrato:** `docs/api/auditoria.md` (`/api/auditoria/eventos/`, `{id}/`, `pessoas/`, `/api/exportacoes/`, `{id}/baixar/`) · **Pronto quando:** `/admin/auditoria` igual a `docs/telas/html/Admin-Auditoria-*.dc.html` e a exportação igual a `Admin-Exportar-*.dc.html`, ligadas à API real; a exportação mostra só a auditoria em CSV (decisão da T-018, opção A, seção "O que existe no MVP" do contrato); só o administrador; testes. Pedida pelo dono em 13 out 2026.

### T-173 · Tela de Configurações
- **Agente:** arquiteto (contrato), depois backend e frontend · **Depende de:** — · **Regras:** IMP, LOC · **Telas:** Config (desktop e celular) · **Pronto quando:** (arquiteto) confere o que `docs/telas/html/Config-*.dc.html` mostra e o que já tem contrato (a API não tem rota de configurações hoje; marca é a T-153/T-154, preços em `/api/precos/`, modelos de contrato em `/api/contratos/`), escreve o contrato do que faltar e propõe as tarefas de backend, sem número; (frontend) `/admin/configuracoes` igual à referência, ligada à API real. Pedida pelo dono em 13 out 2026.
- **Contrato pronto (13 out 2026, arquiteto):** `docs/api/configuracoes.md` (`GET /api/configuracoes/`, em `relatorios`: os cartões com título e resumo prontos e a faixa da implantação); rotas dos cartões em `docs/telas/README.md`. Integrações e Notificações não vêm no MVP (sem tela nem contrato); o botão "Continuar implantação" espera o contrato do assistente. Handoff: `tarefas/handoffs/T-173-arquiteto.md`.
- Resolvido na T-190: texto do cartão "Exportar dados" no MVP fica "Baixe a auditoria em CSV", como o contrato (U18, nota de 14 out 2026 na auditoria).
- **Fora da T-173, sem contrato (orquestrador):** as "Regras de cobrança" da tela `Precos` e do passo `Onboarding-Precos` (tolerância, combustível, desconto do vendedor; a tela do assistente pede também franquia de km e km excedente, que as regras não têm) são citadas em `veiculos.md` como "contrato de empresas", mas `empresas.md` não as tem; e `exige_2fa_todos` ("exigir 2 etapas para todos", `contas.md`) não aparece em nenhuma tela da empresa. Os dois pedem tela ou contrato antes de tarefa.

### T-182 · Tela de Configurações (frontend)
- **Agente:** frontend · **Depende de:** T-181 · **Contrato:** `docs/api/configuracoes.md` · **Telas:** Config (desktop e celular) · **Pronto quando:** `/admin/configuracoes` igual a `docs/telas/html/Config-Desktop.dc.html` e `Config-Mobile.dc.html`, ligada a `GET /api/configuracoes/`: um cartão por item de `cartoes`, na ordem da API, com `titulo` e `resumo` como vêm e o link pela tabela "Rotas dos cartões" (`chave` → rota, ícone no frontend); cartão que não vem não aparece; a faixa da implantação só com `implantacao` diferente de `null` (no celular, como a referência, sem a faixa), com o botão só quando `acao` vier; só o administrador (guarda de rota pelo menu, T-136); testes do componente (seed: 8 cartões e sem faixa; faixa com 6 de 10 e sem botão; `acao` `nova_locacao` leva a `/locacoes/nova`).

### T-028 · Limpar dados de exemplo das telas
- **Agente:** design-system · **Depende de:** T-004 · **Pronto quando:** os números das telas batem com as regras e o seed. Já se sabe de: Patrícia (LOC-2812) aparece em Contas a receber com parcela de R$ 279,00 (plano Entregador, placa SAB-2K90), mas é mensal NMax SBC-0J44 nas outras telas; Marcos (LOC-2850) aparece com a placa SBC-0J44; ficha do veículo QXA-4B21 mostra "Plano padrão Semanal R$ 299,40" (Street agora é R$ 329,00); Juliana aparece "em dia" em Clientes e com parcela atrasada em Contas a receber; Financeiro mostra "3 clientes com 7+ dias R$ 1.299,40". Corrigir no canvas e em `docs/telas/html/`. Inclui `Despesas-Desktop` e `Despesas-Mobile`: aguardando aprovação é R$ 1.200,00 (não R$ 1.386,40) e o IPVA de R$ 186,40 nasce `a_pagar` (FIN-05), apontado pelo qa na T-040.
- **Estado do QXA-4B21 (T-112, decisão do dono em 09/10, opção A):** corrigir Frota, Veiculo, Main, Vistoriador e a OS-119 em Manutencao conforme o caso "Estado do QXA-4B21 em 07 out" dos dados de referência e as divergências levantadas pelo produto em T-112 (acima, em Pontos em aberto): Alugado no tom `solido` (não azul) e "Colocar à venda" só em veículo `disponivel`.
- **Da T-152 (12 out 2026):** `Financeiro` (desktop e celular) sem "Saldo em contas", "Fluxo de caixa previsto", "Conciliar", "Aprovar despesa", "Pagar OS-0193", "Cobrar 2 clientes" em Para hoje e o seletor de período; "Sai hoje" e o contador "Contas a pagar" pelo seed (0 em 07 out); `Receber` sem "Exportar"; no menu das telas, "Locações" é 51 no seed (42 da carteira e 9 reservas) e "Usuários" não tem número (nenhum convite pendente).
- **Da T-176 (13 out 2026):** `Despesas-Desktop` e `Despesas-Mobile` com "Vencimento" e "Já paguei em dinheiro, pelo caixa" no formulário, "Foto da nota" obrigatória, o diálogo do detalhe (pagar, aprovar, recusar com motivo) e "Despesa por veículo" R$ 82,17 (não R$ 82); "Exportar" e a busca ficam. Regras `FIN-05`, `FIN-06`, `FIN-16`.

### [decisão] Pix Automático: quando cobrar a parcela (AUT-04, levantada na T-029)
- **Para:** produto · **Contexto:** o contrato (`docs/api/financeiro.md`, "Cobrança recorrente") diz que `aut_04_cobranca_recorrente` cobra "no vencimento de cada parcela". Pela documentação do Asaas, a cobrança do Pix Automático tem de ser criada **de 2 a 10 dias úteis antes do vencimento**, e a autorização só fica ativa depois que o cliente paga a primeira cobrança pelo QR. Falta decidir: quantos dias antes a tarefa cria a cobrança da parcela, o que acontece com a parcela que vence antes de a autorização ficar ativa, e se a locação diária ou quinzenal pode ter Pix Automático (o Asaas aceita semanal, mensal, trimestral, semestral e anual). O provedor já está pronto (`asaas.py`, T-029); o fluxo na locação espera esta decisão (handoff `tarefas/handoffs/T-029-backend.md`, item 1).


## Dúvidas abertas da T-020 (frontend)

- Resolvido na T-047: **Menu por permissão.** `eu.pode` não traz uma chave por item de menu; o frontend mapeia item -> chave em `frontend/src/lib/menu.ts` (ex.: Comissões e Conciliação por `financeiro_pagar`, Relatórios por `painel`, Locações por `locacoes_criar || vistorias_fazer`). Proposta: a API devolver `menu` (lista de módulos liberados) para a tela não inferir. Dono: arquiteto + produto (USR-05).
- Resolvido na T-047: **Início por perfil.** Vistoriador tem `painel: "nao"`; a T-020 mostra um aviso no lugar da visão geral. Falta definir a rota inicial de vistoriador, vendedor, gerente e financeiro (telas de início por perfil).
- Resolvido na T-047: **Contadores do menu e tela Main** vêm de `relatorios` (agregados), sem contrato em `docs/api/`. Hoje são dados falsos. Dono: arquiteto.
- **Pedido ao design-system:** seletor de filial com lista (USR-07, "Todas as filiais" para administrador); diálogo/gaveta para o menu do celular; KPI com valor longo ("R$ 18,4 mil") quebra em 3 linhas a 390px.

- Resolvido na T-190: (T-169, Usuários) rótulos neutros e "a pessoa" nos textos ("Escolha as filiais da pessoa", "A pessoa sai do sistema na hora"); sem busca e filtros no MVP; painel com redefinir 2 etapas, sessões, reativar e cancelar convite e a gaveta no celular aprovados; textos de apoio revisados. Propostas 9 e 12 da T-190.

- Resolvido na T-190: (T-168, Filiais) nome curto entra (`FIL-01`); o preço do litro entra no bloco Operação, editado pelo administrador (`DEV-01`, D11); feriados só ao editar e "Ver painel da filial" aprovados; o horário precisa ser por dia com até 2 intervalos (`FIL-01`); Telefone no celular. Propostas 9, 10 e 12 da T-190.
- Resolvido na T-190: (T-172, Importar) o arquiteto expõe o andamento dos passos; Voltar, Salvar e sair e Continuar provisórios aprovados; `/implantacao/...` sem menu aprovado; "Corrigir aqui" dentro da lista; download da planilha com login a conferir no compose (devops). Propostas 9, 10 e 12 da T-190.
- Resolvido na T-190: (T-175, Aprovações) indicadores e contagens das abas entram com a `APR-12` (D12); o pedido ganha o bloco `resumo` por tipo; a frase das 4 horas sai (`APR-08`, fase 2); "Meus pedidos" aprovado; "Ver proposta" some até a venda ter tela. Propostas 9 a 12 da T-190.
- Resolvido na T-190: (T-183, Assinatura) [D-1] a [D-10] respondidas nas regras `PLT-01` a `PLT-06` e `PLT-11` a `PLT-15` (ver a seção da T-183). Cancelar e pausar (`PLT-06`) entram no MVP: propostas 3, 4 e 7 da T-190.
- [decisão] (T-181, Configurações) Empresa sem filial ativa: o contrato não diz o resumo do cartão Filiais; o backend usa "Nenhuma filial ativa" (como "Nenhuma categoria cadastrada" em Tabelas de preço). Produto: confirmar ou trocar o texto.

### T-205 · Caução na busca do caixa (D-01 da T-025)
- **Agente:** backend · **Depende de:** — · **Regras:** FIN-15 · **Critérios:** CA-023-15 · **Pronto quando:** a busca do caixa por locação traz a caução a receber (`financeiro/selectors.py::_recortar` considera `?busca=`), e a caução pode ser recebida pela tela do caixa; teste `test_fin_15_busca_do_caixa_traz_caucao`. O QA troca o contorno do E2E (`e2e/`) pela tela.

### T-206 · Mensagens da API nas telas de saída e de caixa (D-02 e D-03 da T-025)
- **Agente:** frontend · **Depende de:** — · **Regras:** VEI-01, FIN-01 · **Critérios:** CA-025-09 · **Pronto quando:** (D-02) km de saída menor que o do veículo mostra a mensagem da API ("O km informado é menor que o atual…"), em vez de deixar o botão desligado com "Informe a quilometragem"; (D-03) sem caixa aberto, a tela diz "Abra o caixa do dia para receber"; testes.

### T-207 · Vistoriador sem 403 ao abrir a vistoria (D-05 da T-025)
- **Agente:** backend (com o frontend, se a chamada não for necessária) · **Depende de:** — · **Regras:** USR-09 · **Pronto quando:** o João (vistoriador) abre a vistoria sem 403: ou a tela deixa de chamar `GET /api/clientes/{id}/` e usa o que a vistoria já traz, ou a API devolve ao vistoriador só o que a USR-09 permite; teste com o perfil do vistoriador.

### T-208 · Enviar contrato e página pública de assinatura (lacuna da T-025)
- **Agente:** frontend · **Depende de:** — · **Regras:** LOC-04 · **Contrato:** `docs/api/contratos.md` (`POST /api/locacoes/{id}/contrato/` e as rotas públicas de assinatura) · **Telas:** as de assinatura em `docs/telas/html` · **Pronto quando:** botão para gerar e enviar o contrato na locação e página pública `/assinar` (sem login, celular), ligadas à API real; testes. O QA troca o contorno do CA-025-05 pela tela.

### T-209 · Ajustes de cadastro e caixa achados no E2E (lacunas da T-025)
- **Agente:** frontend · **Depende de:** — · **Regras:** CLI-01, FIN-01 · **Pronto quando:** (b) as fotos do cliente podem ser enviadas antes do primeiro "Salvar cliente", para "Salvar e iniciar locação" já ter as fotos; (c) o CEP preenche rua, bairro e cidade; (e) no celular o caixa mostra "N recebimentos"; testes. O item (d), a vendedora sem acesso à Frota, vai ao produto como divergência.

### T-210 · Fotos no desenvolvimento sem bloqueio da CSP (D-06 da T-025)
- **Agente:** devops (com o backend) · **Depende de:** — · **Pronto quando:** em desenvolvimento as URLs assinadas das fotos apontam para um endereço que o navegador alcança e a CSP permite (sem `arquivos.invalid`); as fotos da comparação da devolução aparecem e o console fica limpo; o E2E deixa de tolerar o erro da CSP.

## Fase 2 em diante

Vendas e aprovações (VEN, APR), despesas, comissões e conciliação (FIN-05 a FIN-13), manutenção (MAN), automações (AUT), implantação self-service (IMP), relatórios e DRE, exportação (AUD-06, AUD-07). A cobrança da assinatura, cancelar e pausar e a `AUD-08` entraram no MVP em 14 out 2026 (T-183, T-190); continuam aqui a `Plat-Cobranca` e os adicionais. Da exportação (`AUD-07`), o MVP tem só a auditoria em CSV (T-018); a fase 2 traz os outros itens (clientes, veículos, locações e contratos, financeiro, vistorias e fotos), a planilha (.xlsx, dependência nova registrada no PR), o backup completo em ZIP com as 2 etapas recentes, o backup mensal (`AUT-11`) com o cartão da tela, a exportação da plataforma (`/api/plataforma/exportacoes/`), o pedido do titular (`AUD-06`, à mão até lá) e o prazo após o cancelamento (`AUD-08`), decisão do dono de 12 out 2026 (T-151). O orquestrador quebra em tarefas quando a fase 1 fechar.
