# T-230 · MEI e empresário individual no apagamento (`AUD-08`)

**Data:** 15 out 2026 · **Agente:** segurança · **Regras:** AUD-08, PLT-06, PLT-14, PLT-15, AUD-02, AUD-04, AUD-09 · **ADR:** 0025
**Base:** `AUD-08` na branch `t-229-regras-cancelar-pausar` (PR #230), `docs/api/cancelamento.md` ("O que fica no `public`"), `docs/api/assinatura.md` (dados fiscais, NFS-e), `docs/api/plataforma.md` (`Empresa`), `backend/apps/plataforma/models.py`.
**Método:** leitura das regras, dos contratos e do modelo. Nada de código foi executado; não há código do apagamento ainda (T-195).

## Resposta curta

1. **É dado pessoal.** O empresário individual e o MEI não têm personalidade separada da pessoa: razão social, CNPJ e endereço identificam uma pessoa natural (LGPD, art. 5º, I). O Giro é **controlador** desses dados, porque são do contrato de assinatura entre o Giro e a locadora, e não dos clientes da locadora.
2. **Podem ficar só o que a obrigação legal pede, e só enquanto ela durar** (art. 16, I, e art. 7º, II; para a fatura atrasada, art. 7º, VI). O registro fiscal é a fatura e a nota, não a linha da `Empresa`. "Reconhecer quem volta" não é obrigação legal, e para isso o CNPJ basta (art. 6º, III, e art. 10, § 1º).
3. **Recomendo a opção B, igual para todas as empresas:** depois do apagamento, a linha da `Empresa` fica com o CNPJ, sem razão social, nome de exibição e endereço; quem guarda o tomador (razão social, CNPJ e endereço como foram na nota) é a própria fatura, e esse dado sai junto com ela, no prazo que o dono e o contador definirem. Hoje a fatura **não** guarda o tomador (achado M-01), então a opção B depende de um ajuste no contrato.
4. **Sem tratar o MEI à parte.** O Giro não sabe a natureza jurídica de quem compra, e a razão social de muita Ltda também traz o nome de um sócio ("João da Silva Locações Ltda"). Uma regra só, para todas, é mais simples e cobre os dois casos.

Sobre a premissa da tarefa: o CNPJ do MEI não contém o CPF; é outro número. O CPF aparece na **razão social** de MEIs mais antigos (nome seguido do CPF); nos mais novos, a razão social costuma vir com a raiz do CNPJ e o nome. Nos dois casos, o CNPJ leva à pessoa pela consulta pública da Receita, e dado público continua protegido: o uso tem de respeitar a finalidade e a necessidade (art. 7º, §§ 3º e 4º).

## O que a LGPD pede, aplicado ao caso

| Ponto | O que a lei diz | Consequência no Giro |
| --- | --- | --- |
| Fim do tratamento (art. 15) | O tratamento acaba quando a finalidade se esgota ou o titular pede. | O contrato de assinatura acaba com a empresa `cancelada`; os 90 dias da `AUD-08` são o período de devolução e de reativação. |
| Eliminação e conservação (art. 16) | Depois do fim, elimina-se, e só se conserva para obrigação legal ou regulatória (I), entre outras hipóteses que não se aplicam aqui. | Fica o que a lei fiscal pede: a fatura e a nota com o tomador. O resto sai. |
| Exercício regular de direitos (art. 7º, VI) | Pode-se guardar o necessário para cobrar ou se defender. | Fatura `atrasada` de antes do cancelamento continua devida (`PLT-06`): o tomador dela fica enquanto ela estiver em aberto. |
| Necessidade (art. 6º, III) e legítimo interesse (art. 10, § 1º) | Só o mínimo, e no legítimo interesse só o estritamente necessário. | Reconhecer quem volta e reservar o subdomínio pedem o CNPJ e o subdomínio, não o nome nem o endereço. |
| Direito do titular (art. 18, IV e VI) | O titular pode pedir eliminação, salvo o que o art. 16 autoriza guardar. | Se o MEI pedir, a resposta é: o que ficou é a fatura e a nota, por obrigação fiscal, até o prazo de guarda. |

O prazo de guarda das faturas não é desta revisão (fica com o dono e o contador, "Pontos em aberto" das regras). A conclusão aqui é só **o que pode ficar e preso a quê**: o dado do tomador vive e sai com a fatura.

## Achados

### M-01 · A fatura não guarda o tomador · média

**Onde:** `docs/api/assinatura.md`, "Nota fiscal da assinatura": `emitir_nota_fatura` pede a NFS-e "com o tomador da `Empresa`"; a `FaturaAssinatura` guarda só a situação, o número e o link da nota.
**Problema:** o registro fiscal do Giro depende da linha da `Empresa`, que muda (a razão social e o endereço são editáveis, `PLT-15`) e que o apagamento limpa. Hoje, se o administrador muda o endereço, a fatura antiga já não diz para quem a nota saiu; e a opção B não é possível sem perder o tomador.
**Sugestão:** a fatura guarda o tomador como ele foi: `tomador_razao_social`, `tomador_cnpj`, `tomador_endereco` (o mesmo formato do endereço da filial), gravados quando a nota é pedida ao parceiro; sem nota (emissão desligada, `GIRO_NFSE_ASSINATURA_ATIVA=false`), gravados na baixa, com o que foi para o pagador da cobrança. Depois de gravado, não muda (como a nota emitida). Isso também conserta o histórico enquanto a empresa está ativa.

### M-02 · A linha da empresa apagada guarda mais do que precisa · média

**Onde:** `AUD-08` (PR #230) e `cancelamento.md`, "O que fica no `public`": razão social, CNPJ e endereço ficam na linha da `Empresa`, sem prazo.
**Problema:** no MEI e no empresário individual, isso é nome (às vezes com CPF) e, muitas vezes, o endereço de casa, guardados sem prazo e sem obrigação que peça a linha (a obrigação é da fatura). O `nome_exibicao` também pode ser o nome da pessoa e não está na lista do que se limpa.
**Sugestão:** opção B: no apagamento, limpar também `razao_social`, `nome_exibicao` e `endereco_*`. Ficam CNPJ, status, datas (`cancelada_em`, `apagada_em`), plano, ciclo e preço contratado, cidade e UF (não identificam mais que o CNPJ e servem às contagens), `subdominio` e `schema_name` reservados. O painel mostra "Dados apagados" com o CNPJ.
Quando a última fatura sair pelo prazo de guarda, o CNPJ também sai da linha; ficam só `id`, `subdominio` e `schema_name` reservados (a reserva protege o endereço antigo contra uso por outra locadora, e o subdomínio sozinho não precisa do CNPJ).

### M-03 · A auditoria da plataforma guarda endereço e contato por 5 anos · média

**Onde:** `assinatura.md`: `empresa.dados_fiscais` no `public` "com antes e depois" (razão social, endereço e e-mail de cobrança); `empresa.criar` e o que mais registrar o responsável.
**Problema:** a auditoria do `public` fica 5 anos (`AUD-02`) e o apagamento não a alcança (ADR 0025, item 4). Os mesmos dados que a `AUD-08` limpa da linha continuam nos eventos. É o mesmo caso do CPF e da CNH no evento (`AUD-04`, `AUD-09`, ADR 0014, nota de 12 out 2026).
**Sugestão:** no `public`, os eventos da empresa guardam quais campos mudaram, sem o valor: razão social, endereço, e-mail de cobrança, nome, e-mail e telefone do responsável aparecem como "alterado". O antes e depois completo fica no evento da auditoria da empresa (no schema dela), que já é gravado nos dois lugares e sai com o schema. CNPJ, plano, valores e datas continuam com o valor (a equipe precisa deles e eles já ficam na fatura).

### B-01 · O pagador no parceiro fica com o contato · baixa

**Onde:** `criar_ou_atualizar_pagador` (conta principal, `financeiro.md` e `assinatura.md`); o contrato do apagamento não fala do pagador.
**Problema:** o Giro é controlador do cadastro da empresa como pagador na sua conta do Asaas (razão social, CNPJ, e-mail, endereço). O apagamento limpa o banco do Giro, mas não esse cadastro.
**Sugestão:** no passo (c) do `apagar_empresa`, tirar do pagador o e-mail e o telefone (ou removê-lo, se o parceiro deixar com cobranças no histórico) e desligar as notificações do parceiro para ele. As cobranças e as notas no parceiro são do parceiro e da prefeitura, e ficam. Conferir na documentação do Asaas o que a API permite.

### B-02 · CNPJ único bloqueia a volta depois do apagamento · baixa

**Onde:** `Empresa.cnpj` com `unique=True` (`models.py`) e o 409 `cnpj_em_uso` na criação (`plataforma.md`).
**Problema:** não é de LGPD, mas aparece com a opção B: a linha apagada continua com o CNPJ, e a mesma empresa, se comprar de novo depois dos 90 dias, recebe `cnpj_em_uso`. "Reconhecer quem volta" vira impedir quem volta.
**Sugestão:** a unicidade vale só para empresas não apagadas (restrição parcial, `apagada_em` nulo); a compra de uma empresa com CNPJ apagado cria uma `Empresa` nova (outro `id`, schema e subdomínio, ADR 0013) e a equipe vê no painel que ela já foi cliente. Fica com o produto dizer se a compra nesse caso tem algo diferente (teste de novo, por exemplo).

### Fatura atrasada no dia do apagamento · ponto para o produto

No caso (c) dos dados de referência, a empresa `inadimplente` cancela com a FAT-0001 `atrasada` e devida. Se ela continuar atrasada no 90º dia, a linha perde o contato (`email_cobranca` e responsável) e o Giro fica sem como cobrar. Duas saídas, as duas aceitas pela LGPD (art. 7º, VI): (a) a fatura atrasada guarda o `email_cobranca` junto do tomador, até a baixa ou o fim do prazo de guarda; (b) o Giro não cobra mais depois do apagamento e a fatura fica só como registro. Recomendo (a), porque a dívida não some com o cancelamento (`PLT-06`). É decisão de negócio: vai como `[decisão]` para o produto.

## Ajustes propostos (sem número de tarefa)

**Regra `AUD-08`, "O que fica depois do apagamento" (produto, opção B):**
> Só no painel da plataforma: a linha da empresa, `cancelada` e marcada como apagada, com o CNPJ, sem razão social, nome, endereço e dados de contato; as faturas da assinatura (`PLT-14`), cada uma com o tomador como foi na nota (razão social, CNPJ e endereço), registro de cobrança e fiscal do próprio Giro; e a auditoria da plataforma (`AUD-02`, 5 anos), que guarda quais dados da empresa mudaram, sem os valores. O tomador sai com a fatura, no prazo de guarda; depois da última fatura, sai também o CNPJ da linha, e ficam reservados o subdomínio e o schema. Vale igual para toda empresa, MEI ou não.

E na `PLT-14`: "A fatura guarda o tomador (razão social, CNPJ e endereço) como foi na nota, ou na cobrança quando não há nota; mudar os dados fiscais depois não muda faturas já emitidas."

**Contrato `cancelamento.md`, "O que fica no `public`" (arquiteto):** limpar também `razao_social`, `nome_exibicao` e `endereco_*`; tirar e-mail e telefone do pagador no parceiro (B-01); `cnpj` único só entre não apagadas (B-02); depois da última fatura sair, limpar o `cnpj`. Teste com o código: `test_aud_08_linha_apagada_so_com_cnpj`.

**Contrato `assinatura.md` (arquiteto):** `FaturaAssinatura.tomador_*` gravados ao pedir a nota (ou na baixa, sem nota) e imutáveis depois (M-01); `emitir_nota_fatura` lê o tomador da fatura, não da `Empresa`. Teste: `test_plt_14_fatura_guarda_tomador`.

**Contrato `auditoria.md` (arquiteto):** no `public`, os eventos `empresa.*` com razão social, endereço e contato guardam "alterado" no lugar do valor; o valor completo fica no evento do schema da empresa (M-03). Teste: `test_aud_08_auditoria_publica_sem_endereco`.

**Para a T-195 (backend):** entra junto, se o produto aprovar a opção B antes do código.

## O que não muda

- O apagamento do schema, dos arquivos e da `ContaPagamento` (ADR 0025) já cobre os dados dos clientes da locadora, de que o Giro é operador.
- A revisão da ADR 0025 (conexão de migração, backups depois do 90º dia) continua na T-199.
- O prazo de guarda das faturas continua com o dono e o contador.
