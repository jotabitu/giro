# T-163 · Multa e juros no valor de hoje da parcela atrasada · backend → qa, frontend, orquestrador

**O que foi feito:** a divergência (c) da T-023 era defeito do seed, e não da conta nem da regra. A `FIN-03` diz "sem cláusula no contrato, não cobra juros", e o código segue isso: `devido_ate` (`backend/apps/financeiro/selectors.py`) só cobra multa e juros quando `permite_juros` acha o contrato vigente da locação com `clausula_juros`. A carteira do seed (`backend/seed/carteira.py`) grava as locações direto nos models, e a LOC-2836 passa pelos serviços mas só registra a assinatura na locação: nenhuma tinha `Contrato`. Por isso, no compose, a parcela 2 do Carlos (LOC-2841, R$ 299,40, 30 set) vinha com `cobra_juros: false` e `valor_hoje` igual ao principal. Os testes da T-016 e da T-017 não pegavam: eles criam o contrato com a cláusula à mão (`_contrato_com_juros`).

Correção: no seed de desenvolvimento (`conferencia=True`), cada locação retirada (as 42 da carteira, inclusive a LOC-2836) ganha o contrato assinado com a versão publicada do modelo de locação, que tem a cláusula de 2% + 1% ao mês. O texto sai com os marcadores preenchidos e a data da assinatura (início da locação; na LOC-2836, a retirada em 01 out). Gravado direto, como a locação: sem PDF nem link de assinatura (`pdf_disponivel: false`). As 9 reservas (`aguardando_retirada`) continuam sem contrato. A carteira crua dos testes (`conferencia=False`) não muda.

Não é carência, nem regra de tipo de conta, nem data de referência: os 12 dias vêm do relógio de verdade em 12 out (30 set + 12), e a branch não precisa do relógio da T-142 (parti da `origin/main`).

**Números do seed (Carlos, LOC-2841, parcela 2):**
- 07 out, 7 dias: 299,40 + multa 5,99 + juros 0,70 = **R$ 306,09** (o mesmo do caso "Devolução antecipada LOC-2841").
- 12 out, 12 dias: 299,40 + multa 5,99 + juros 1,20 = **R$ 306,59** (o caso do compose).
- Rafael, LOC-2790 (R$ 1.347,00, 12 set), em 07 out: multa 26,94 + juros 11,23 = R$ 1.385,17.

**Onde:** `backend/seed/carteira.py` (`_contrato_assinado`), teste em `backend/tests/aceitacao/test_t127_seed.py`.
**Contrato:** sem mudança na API nem no OpenAPI.
**Regras cobertas:** FIN-03 (teste: `test_fin_03_seed_163_01_parcela_atrasada_cobra_multa_e_juros`).
**Efeito no compose:** depois de recriar o seed, tudo que usa a `FIN-03` cobra multa e juros das locações do seed: `valor_hoje` em Contas a receber, o valor do Pix e do boleto, a baixa no caixa (receber só o principal agora dá 422), o acerto da devolução e a régua de cobrança (`AUT-03`). Os totais do painel e da aba "Em atraso" seguem pelo principal (R$ 1.646,40), como nas regras. O seed não reescreve banco já semeado: no compose, é preciso apagar o banco e rodar o seed de novo.
**O que ficou de fora:** a aba Contrato da locação mostra o contrato assinado sem PDF; gerar o PDF no seed (WeasyPrint) não fazia parte.
**Próximo passo para quem recebe:** qa confere o caso nos dados de referência (Carlos em 07 out R$ 306,09, a baixa de R$ 306,09 no caixa e a devolução antecipada R$ 365,37) num banco semeado de novo; frontend não precisa mudar nada (a tela já mostra o que a API devolve); orquestrador abre o PR.
