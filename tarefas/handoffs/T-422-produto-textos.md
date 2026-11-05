# T-422 · Textos da referência FIPE · produto → arquiteto, orquestrador, backend, frontend

**O que foi feito:** confirmei e ajustei os textos que o arquiteto propôs no contrato (PR #479, `docs/api/veiculos.md`, seção "Referência FIPE"). Ficam registrados na `VEN-01`, com nota de mudança na seção Vendas.

Não mexi em `veiculos.md`, porque a seção ainda não está na `develop`. **O arquiteto passa os textos para o contrato no próprio #479.**

| Caso | Proposta do arquiteto | Agora |
| --- | --- | --- |
| Rótulo com o mês (`situacao` `ok`, origem `fipe`) | "Referência FIPE · outubro de 2026" | confirmado |
| Rótulo da origem `manual` | "Referência FIPE · informada à mão" | confirmado |
| Valor antigo (API fora do ar, versão fora da tabela) | sem aviso; só o mês no rótulo | sem aviso com um mês de atraso, que é normal. Com o mês do preço dois ou mais meses antes do mês corrente, `aviso` "Esta referência é de agosto de 2026 e não foi atualizada." |
| `aguardando` | "A referência FIPE chega na próxima atualização." | "A referência FIPE chega na próxima atualização, feita de madrugada." |
| `sem_versao` (antes da primeira rodada) | `aviso` `null` | o mesmo texto do `aguardando` |
| `escolher_versao` (sem versão escolhida) | "Escolha a versão FIPE para ver a referência." | igual para quem tem `acoes.escolher_versao_fipe`; para os outros, "Falta escolher a versão FIPE. O gerente ou o administrador escolhe." |
| `nao_encontrado` | "Versão FIPE não encontrada. Escolha a versão ou digite o código." | igual para quem escolhe; para os outros, "Versão FIPE não encontrada. O gerente ou o administrador escolhe a versão ou digita o código." |
| 400 de `fipe` (versão fora da lista) | "Escolha uma versão da lista FIPE." | confirmado |
| 400 de `fipe.codigo_fipe` | "Digite o código FIPE como 811134-0." | "Digite o código FIPE no formato 811134-0." |
| Consulta por placa indisponível (`disponivel: false`) | nada na tela | depois de "Buscar pela placa", em tom de informação: "A busca pela placa não está disponível agora. Preencha pelo CRLV-e ou escolha a versão na lista FIPE." O motivo não aparece. |

**Por quê:**
- **Valor antigo:**
  - A tabela vira no começo do mês, e a rotina leva dias para trazer os preços. Então ter só o preço do mês anterior é normal.
  - Com dois meses ou mais de atraso, algo parou: a API saiu do ar ou a versão saiu da tabela. Só o mês no rótulo passa despercebido na hora de pôr preço de venda.
  - A conta do aviso é da API (mês do preço contra o mês corrente em `America/Sao_Paulo`). A tela não calcula.
- **Variante por perfil:** o vendedor e o financeiro veem a referência mas não escolhem a versão. "Escolha a versão" pedia a eles algo que não podem fazer.
- **`sem_versao`:** sem aviso, a ficha ficava sem referência e sem explicação até a primeira rodada.
- **Placa indisponível:**
  - O dono pediu "sem erro para a pessoa". Por isso o texto é informativo e diz o caminho, sem o tom de erro.
  - Sem texto nenhum, o botão parece quebrado.
  - Não sai o motivo (cota, limite, API), que não ajuda a pessoa e expõe detalhe do parceiro.

**O que muda no contrato (para o arquiteto, no #479):**
- `aviso` passa a depender de `acoes.escolher_versao_fipe` em `escolher_versao` e `nao_encontrado`.
- `aviso` deixa de ser `null` em `sem_versao`.
- Em `ok`, `aviso` ganha o caso do mês dois ou mais meses antes do corrente. "Não há erro nem aviso a mais" muda para valer só até um mês de atraso.
- A mensagem do 400 de `codigo_fipe` muda.
- Na consulta por placa, o texto da tela com `disponivel: false` é fixo do frontend (a resposta continua `{ "disponivel": false }`). Se o arquiteto preferir, pode mandar uma `mensagem` na resposta.

**Próximo passo:**
- **Backend:** montar os avisos como acima, com teste `test_ven_01_*` para o mês antigo e a variante por perfil.
- **Frontend:** o texto da placa indisponível e o `aviso` como vem.
