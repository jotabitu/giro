# T-147 · Regras das decisões da T-017 · produto → backend, arquiteto, qa, orquestrador

**O que foi feito:** escrevi nas regras as 3 `[decisão]` da T-017, com as opções que o dono do produto aprovou em 12 out 2026 (as recomendações da análise do produto, `C:/Users/Jota/Documents/giro-produto/analise-t017.md`, fora do git), e fixei os textos da régua no contrato.
**Onde:** `docs/regras-de-negocio.md` (`CLI-04`, `CLI-05`, `FIN-15`, `AUT-03`, `AUT-05`, notas de mudança de 12 out 2026, duas linhas novas nos dados de referência, tabela "Decisões de 12 out 2026"); `docs/api/financeiro.md` (seção "Régua de cobrança: textos", evento `financeiro.parcela_atrasou`, rota `cobrar`); `docs/api/clientes.md` (item `historico`); `tarefas/backlog.md` (as 3 `[decisão]` saíram; nova T-148).
**Regras cobertas:** CLI-04, CLI-05, FIN-15, AUT-03, AUT-05.

## Decisões

| # | Decisão | Opção | O que mudou |
| --- | --- | --- | --- |
| 1 | Item histórico da análise (`CLI-04`) | B | quatro situações e textos; atraso pela `FIN-03` (conta que nasce vencida e é paga no dia não é atraso); sem conta → `ok` "Cliente novo na empresa"; atraso pago marcado em qualquer época |
| 2 | Semana do `Receber` e caução (`FIN-15`) | A | semana de segunda a domingo da semana de hoje, sem período o mês; caução fora das abas e da lista geral, na lista de um cliente ou de uma origem. É o que o código já faz |
| 3 | Bloqueio e textos da régua (`AUT-03`, `CLI-05`, `AUT-05`) | B | bloqueio pedido uma vez por conta, recuperando o dia perdido; desbloqueio manual vale até outra conta completar 15 dias; textos por momento, iguais no WhatsApp e no e-mail; recibo com forma e dia |

## Números novos (dados de referência)

- **Histórico da análise em 07 out:** Juliana `ok` "Sem atraso na empresa"; Carlos e Rafael `problema` "Conta em atraso na empresa"; Lucas `ok`; cliente novo `ok` "Cliente novo na empresa".
- **Contas a receber da semana em 07 out** (05 a 11 out), conferida contra `docs/qa/carteira-outubro/parcelas.csv`: Previsto R$ 14.247,50 em 34; Recebido R$ 5.882,50 em 15 (41,29%); Vence hoje R$ 2.625,80 em 6; A vencer R$ 5.739,20 em 13; Em atraso R$ 1.646,40 (2); abas Todas 36, Em atraso 2, Vencem hoje 6, A vencer 13, Pagas 15. Bate com a coluna A da análise.

Nenhum caso existente muda.

## Decisões minhas (detalhe de texto, dentro da opção B)

- "Cobrar" manual fora de D-1, D0, D+3 e D+7 usa o texto do momento mais próximo: antes do vencimento, "vence em 14/10"; em atraso, o texto de D+3 e D+7.
- Conta de tipo `outro`: "a cobrança da locação LOC-2841"; `multa` e `avaria` como o `acerto`.
- Atraso sem multa e juros (contrato sem a cláusula): "O valor é R$ 299,40.", sem "com multa e juros".
- O recibo (`AUT-05`) continua só no WhatsApp, como na regra; o e-mail é da régua (`AUT-03`).
- "Uma vez por conta por dia" conta os dois canais juntos.

**O que ficou de fora:** a forma de mostrar a caução na lista filtrada por cliente, que as `contagens` não contam (Lucas: 2 linhas, "Todas" 1). É detalhe de contrato, para o arquiteto; não muda regra. Está na T-148 como conferência.

**Próximo passo para quem recebe:**
- **Backend:** T-148 (`montar_historico`, `bloqueio_pedido_em` na conta, textos por momento, recibo com forma e dia, e-mail; testes com o código no nome). O envio de e-mail ao cliente já existe (`contratos/tasks.py`, `send_mail`).
- **Arquiteto:** confirmar o campo `bloqueio_pedido_em` (ou registrar a alternativa sem migração em ADR) e decidir como a lista por cliente mostra a caução fora das contagens.
- **QA:** os dois casos novos dos dados de referência no seed e nos testes de aceitação.
- **Orquestrador:** abrir o PR.
