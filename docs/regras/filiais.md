# Filiais

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

A empresa tem ao menos uma filial ativa, e uma delas é a matriz. Veículos, locações, caixa do dia, vistorias e ordens de serviço são de uma filial; clientes, marca, modelos de contrato e usuários são da empresa (cada usuário com acesso escolhido por filial, `USR-07`). Telas: `Filiais`, `Filial`, `Onboarding-Filial`.

**Regras**

- `FIL-01` Cadastro: nome (único na empresa), nome curto (opcional; sem ele, vale o nome), CNPJ e inscrições (opcionais), endereço, contato, horário por dia da semana (até 2 intervalos por dia, para quem fecha no almoço) e feriados (`FIL-03`). A filial é ativa ou inativa, sem rascunho: só salva com os campos obrigatórios. A primeira filial é sempre a matriz, e só existe uma matriz. O nome curto aparece no seletor de filial, nas listas curtas (filiais da pessoa em `Admin-Usuarios`) e no resumo de Configurações (Moto Rápida: "Filial Centro", nome curto "Centro"); as outras telas usam o nome. O preço do litro do combustível (`DEV-01`) é da filial e fica no bloco Operação da tela `Filial`.
- `FIL-02` Os gerentes da filial são os usuários com perfil gerente ligados a ela (`USR-07`), e não um campo da filial. Avisos e tarefas "para o gerente" vão a todos os gerentes da filial.
- `FIL-03` Feriados: cada filial tem uma lista de datas em que fica fechada, cadastrada pelo administrador. A cada ano o sistema sugere os feriados nacionais, e o administrador confirma ou acrescenta os locais. Em dia de feriado a filial conta como fechada para `LOC-11`.
- `FIL-04` O preço pode ser da empresa ou de uma filial, pela categoria (`LOC-01`, tela `Precos`). Não há "tabela de preço padrão", vagas no pátio nem centro de custo na filial: a própria filial é o centro de custo (DRE por filial, `FIN-13`). O recebimento é da empresa, numa única subconta do parceiro de pagamento (Decisões de 07 out 2026). O sistema não emite nota fiscal.
- `FIL-05` A frota é de cada filial. A devolução é feita na filial da locação, e não há frota compartilhada: para usar o veículo de outra filial, ele é transferido antes (`VEI-04`).
- `FIL-06` Desativar filial: só o administrador, com motivo. É recusado quando a filial é a matriz (escolher outra antes), quando é a última filial ativa, ou quando ainda tem operação. Operação aqui é: veículos fora de `vendido` e `baixado`; locações em `rascunho`, `aguardando_retirada`, `ativa` ou `devolucao_atrasada`; caixa do dia `aberto` ou `aguardando_aprovacao`. A recusa mostra quanto falta em cada grupo. Contas a receber em aberto e despesas a pagar não impedem: continuam na régua de cobrança (`AUT-03`), podem ser pagas por Pix ou boleto (`FIN-04`) ou no caixa de outra filial, e mantêm a filial de origem para relatório e DRE. Nada é apagado; reativar respeita o limite do plano (`PLT-03`).

*Criada em 07 out 2026 (T-037), a partir da tela `Filial` e das dúvidas da T-030 decididas pelo dono do produto.*
