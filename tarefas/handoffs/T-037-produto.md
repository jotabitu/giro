# T-037 · Decisões da T-030 e critérios de aceite da fase 1 · produto → orquestrador, arquiteto, qa

## Parte 1 · Dúvidas da T-030 (aguardam o dono do produto)

**O que foi feito:** recomendação para as duas `[decisão]` da T-030, nos itens 6 e 7 de "Pontos em aberto" de `docs/regras-de-negocio.md`. O backlog aponta para eles, e a T-028 ganhou duas divergências da tela `Filial`.
**Resumo:**
- **6. Campos da tela Filial:** gerente responsável vem dos usuários (só leitura na tela). Ficam fora: vagas no pátio, tabela de preço padrão (já é a categoria por filial), centro de custo (a filial já é), nota fiscal e "Rascunho". Três itens precisam do dono:
  - Conta de recebimento: A) por empresa (padrão) ou B) por filial na fase 2.
  - Devolução em outra filial e frota compartilhada: A) só na filial da locação (padrão) ou B) devolução em qualquer filial com transferência automática.
  - Feriados: A) lista de datas fechadas por filial, com os nacionais sugeridos (padrão), porque mexe no atraso de `LOC-11`; ou B) sem feriados no MVP.
- **7. Desativar filial com operação:** aceitar a proposta (veículos fora de `vendido`/`baixado`, locações abertas, caixa `aberto`/`aguardando_aprovacao`). Contas a receber em aberto e despesas a pagar não impedem.
**Impacto no contrato enquanto não há resposta:** nenhum. `docs/api/filiais.md` já está no padrão. Se o dono escolher A nos feriados, entra um campo novo (lista de datas) na T-012.

## Parte 2 · Critérios de aceite

Pendente: começa depois do aval do orquestrador.

## Decisão S-02 (07 out 2026)

O dono do produto decidiu, e virou a regra `AUD-09`: o suporte Giro vê CPF e CNH mascarados dentro da empresa, nunca completos. A `PLT-07` cita a nova regra. A linha `[decisão]` original está no backlog da branch `t-032-revisao-fundacao` (Seguranca), não nesta; no merge, tire essa linha e fique com a nota desta branch.

## Dúvidas da T-036 (contas)

Itens 8, 9 e 10 de "Pontos em aberto":
- 8: 2 etapas vale como na `USR-02`; correção da tela na T-028.
- 9: e-mail obrigatório e celular opcional (WhatsApp no convite); correção da tela na T-028.
- 10: "Manter conectado" precisa do dono do produto: A) tirar, que é o padrão; B) estender o desktop para 30 dias, exceto administrador e financeiro.

As linhas `[decisão]` ficaram no backlog da branch do Arquiteto (T-036).

## Dúvidas da T-036 (clientes)

Itens 11, 12 e 13 de "Pontos em aberto":
- 11: ordem do botão da `CLI-07` como na tela; sem impacto.
- 12: desbloqueio manual precisa do dono do produto: A) gerente e administrador desbloqueiam direto, que é o padrão recomendado; B) só o administrador, como na proposta do arquiteto.
- 13: inativar cliente como na proposta, e reativar volta a `ativo` ou `incompleto`.

## Decisões dos itens 6 a 10 (07 out 2026)

O dono do produto aprovou todos na opção recomendada, e eles viraram regra:
- **Nova seção Filiais**, com `FIL-01` (cadastro, sem rascunho, uma matriz), `FIL-02` (gerentes vêm dos usuários), `FIL-03` (feriados por filial, com os nacionais sugeridos), `FIL-04` (preço por categoria, recebimento por empresa, sem nota fiscal), `FIL-05` (frota por filial, devolução na filial da locação) e `FIL-06` (desativação).
- `LOC-11`: feriado conta como dia fechado, e o atraso não corre.
- `VEI-04`: a transferência é o único jeito de um veículo mudar de filial.
- `USR-01`: e-mail obrigatório, celular opcional. `USR-06`: sem "manter conectado".
- A T-028 recebeu as correções de tela de `Login`, `Convite`, `Admin-Usuarios` e `Filial`.
- Os itens 11 a 13 (clientes) continuam em "Pontos em aberto". O 12 espera o dono; o contrato já segue o padrão A.

**Achado para o arquiteto:** o CPF de exemplo da Juliana em `docs/api/clientes.md` (`05221833012`) não passa no dígito verificador. O válido que mantém a máscara `***.218.330-**` é `05221833018`.
