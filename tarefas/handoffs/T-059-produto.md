# T-059 · Números da carteira de outubro e textos da T-010 · produto → orquestrador, qa, design-system, arquiteto, backend

**O que foi feito:**
- **Carteira de outubro registrada** em "Dados de referência para testes", na linha "Contas a receber de outubro em 07 out". Números em 07 out (`FIN-15`):
  - Previsto: R$ 52.002,10 em 128 parcelas.
  - Recebido: R$ 13.401,70 em 30 parcelas (25,77%).
  - Vence hoje: R$ 2.625,80 em 6 parcelas.
  - A vencer: R$ 35.974,60 em 92 parcelas.
  - Em atraso: R$ 1.646,40 (2 clientes, 2 parcelas).
  - Abas: Todas 130, Em atraso 2, Vencem hoje 6, A vencer 92, Pagas 30.

  Os números são diferentes dos da T-056 por causa de duas correções, explicadas abaixo. Conferi com os CSV da T-056 já com as duas correções.
- **Composição das 35 locações geradas e premissas do qa:** confirmadas como estão. Nenhuma regra fixa a mistura de planos.
- **Divergências do qa:**
  - **LOC-2841 (parcela 2 de 5):** vale o que dizem a tela e os critérios, não a carteira. A locação começa em 23 set, e não em 30 set. Pela `LOC-05`, a 1ª parcela é paga na retirada, e locação sem 1º pagamento fica `aguardando_retirada`. Por isso a parcela de 30 set só pode ser a 2 de 5. As 5 semanas vão até 28 out, e o preço de R$ 299,40 se mantém (`LOC-15`). Mudaram o caso "Preço antigo LOC-2841" das regras e o CA-015-05.
  - **LOC-2790 (R$ 1.347,00):** fica como valor dado do seed. Ela equivale a 30 diárias Urbana e não sai de parcela da tabela, mas os casos "Em aberto dos clientes" e "Bloqueio" dependem dela. Está registrada na nota de mudança.
  - **Cartão de R$ 179,70:** decidido pelo dono do produto em 08/10 (opção A). Vira a renovação de 1 diária do Kwid do Diego, R$ 109,00 (`LOC-08`). O caixa de 07 out passa de R$ 1.182,60 para R$ 1.111,90, e a gaveta continua R$ 281,00. Mudaram o caso "Caixa de 07 out" das regras e o CA-017-13.
  - **Pix de R$ 44,90:** é a diária Urbana retirada hoje (LOC-2826 da carteira), como o qa propôs. Não é do Marcos, que é mensal e pagou em 01 out.
- **CNPJ da Messejana** 12.345.678/0003-57 e da Caucaia 12.345.678/0002-76 no CA-012-04, o único lugar das regras e dos critérios onde a Messejana aparece. Conferi o dígito verificador dos dois.
- **`PLT-08`:** 5 senhas erradas seguidas bloqueiam por 15 minutos, como no `USR-06`. Durante o bloqueio, nem a senha e o código certos entram. Entrar com sucesso zera as contagens. Critério novo **CA-010-18** em `docs/qa/criterios/T-010.md`, marcado para a T-058.
- **Decisões de 08 out 2026:** seção nova nas regras com a base do Recebido, o cartão do Diego, o CNPJ da Messejana e o bloqueio por senha.

**Textos da T-010 (quem troca no código é o backend):**

| Onde | Hoje | Proposta | Por quê |
| --- | --- | --- | --- |
| `backend/apps/plataforma/selectors.py`, `FAIXA_AVISO["inadimplente"]` | Há uma fatura da assinatura em atraso. Pague para evitar a suspensão. | sem mudança | segue a tabela de estados e a `PLT-02` |
| `FAIXA_AVISO["suspensa"]` | Sua empresa está suspensa. Você pode ver e exportar os dados até regularizar. | Sua empresa está suspensa. Você pode ver e exportar os dados, mas não criar locações, vendas nem cobranças. Ao pagar, o acesso volta na hora. | diz o que fica bloqueado e como sair (tabela de estados) |
| `FAIXA_AVISO["pausada"]` | Sua empresa está pausada. Você pode ver e exportar os dados. | Sua empresa está pausada. Você pode ver os dados. Para voltar a operar, retome a assinatura. | pela tabela de estados, `pausada` é "só ver": exportar só aparece em `suspensa` |
| `backend/apps/plataforma/tasks.py`, e-mail do limite de 90%, assunto | {empresa}: limite do plano em 90% | sem mudança | |
| e-mail do limite de 90%, corpo | Sua empresa usa {usado} de {limite} {item} do plano. Ao chegar a {limite}, não será possível cadastrar novos {item}. Para aumentar o limite, mude de plano. | Sua empresa usa {usado} de {limite} {item} do plano. Ao chegar a {limite}, não dá para cadastrar mais {item}, e o que já está cadastrado continua funcionando. Para aumentar o limite, mude de plano em Assinatura. | "novos filiais" sai errado para filiais; a `PLT-03` diz que a operação do que existe nunca para |
| `backend/apps/contas/tasks.py`, e-mail do convite, assunto | {marca}: seu convite de acesso | sem mudança | |
| e-mail do convite, corpo | Olá, {nome}. Você foi convidado para acessar o sistema da {marca}. Crie sua senha em: {link} O link vale por 7 dias. | Olá, {nome}. A {marca} convidou você para acessar o sistema. Crie sua senha em: {link} O link vale por 7 dias. | "convidado" supõe o gênero da pessoa |

Os textos propostos usam "você", são curtos e não têm exclamação nem a marca Giro: o convite e o aviso de 90% saem com o nome da locadora.

**Onde:** `docs/regras-de-negocio.md` (`PLT-08`, casos "Preço antigo LOC-2841", "Caixa de 07 out" e "Contas a receber de outubro em 07 out", notas de mudança, "Decisões de 08 out 2026"), `docs/qa/criterios/T-010.md` (CA-010-18), `T-012.md` (CA-012-04), `T-015.md` (CA-015-05), `T-017.md` (CA-017-13), `tarefas/backlog.md` (seção "Levantadas pelo produto em T-059"), `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum código, teste ou CSV mudou, e nenhum teste lê estes arquivos. O `test_fin_15_*` da T-056 continua passando contra os CSV antigos até o qa aplicar as duas correções; não rodei o `make backend-check`, porque esta branch não muda nada do backend.

**O que ficou de fora:** os CSV e o `gerar.py` da carteira, as telas e os contratos da API ficam com os donos deles; os pedidos estão no backlog.

**Próximo passo para quem recebe:**
- **QA:** em `gerar.py`, LOC-2841 desde 23 set (sai a parcela de 28 out, entra a de 23 set paga) e LOC-2848 com R$ 109,00 pagos em 07 out; atualizar README e `test_fin_15_*` com os números acima. CA-010-18 entra como `xfail` até a T-058.
- **Design-system (T-060):** números do `Receber` e do `Financeiro` pela linha nova das regras (R$ 52,0 mil em 128, R$ 13,4 mil e 26%, abas 130 / 2 / 6 / 92 / 30), e o `Caixa`, as `Locacoes` e as `Comissoes` como no backlog. O README da T-056 está desatualizado nesses números.
- **Arquiteto:** caixa de exemplo em `financeiro.md` e `painel.md` (111190, saldo 106390) e LOC-2841 em `veiculos.md`.
- **Backend:** os três textos acima; o bloqueio por senha da `PLT-08` na T-058.
