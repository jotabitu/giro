# Handoff · T-370 · Ações que faltam no caixa, no receber e no cliente (frontend)

- **Agente:** frontend
- **Branch:** `t-370-acoes-caixa-receber-cliente`
- **Contratos:** `docs/api/financeiro.md` (estornar movimento, renegociar), `docs/api/clientes.md` (bloquear, desbloquear, inativar, reativar)
- **Regras:** FIN-01, FIN-07, CLI-03, CLI-05, CLI-09, APR-05

## O que foi entregue

1. **Caixa do dia, estornar movimento** (`DialogoEstornarMovimento.tsx`, `CaixaDoDia.tsx`, `financeiro.estornarMovimento`):
   - A lista de movimentos ganha o botão "Estornar" (tabela no desktop, linha no celular) com a coluna só para quem estorna.
   - O diálogo pede o motivo, avisa que o estorno não se desfaz e confirma na própria tela.
   - O estorno aparece com a marca "Estorno" e o original com "Estornado"; nenhum dos dois tem o botão (CA-017-17).
2. **Contas a receber, renegociar** (`DialogoRenegociarConta.tsx`, `DetalheDaConta.tsx`, `financeiro.renegociar`):
   - O botão "Renegociar conta" aparece quando `acoes.renegociar` vem verdadeiro.
   - O diálogo mostra o valor devido hoje que a API devolveu, deixa montar uma ou mais contas novas (vencimento e valor) e pede o motivo. A conta nova começa com o `valor_hoje.total_centavos` da API.
   - A soma e o status são conferidos pela API: o 422 `FIN-01` e o 409 aparecem com o texto dela.
3. **Detalhe do cliente** (`AcoesDoCliente.tsx`, `DetalheDoCliente.tsx`, `clientes.bloquear|desbloquear|inativar|reativar`):
   - Um painel "Situação do cadastro" no desktop e no celular, só com os botões que cabem na situação e no perfil. Cada ação abre um diálogo com motivo obrigatório.
   - O 202 do vendedor (pedido `APR-05`) vira o aviso "Pedido de desbloqueio enviado".
   - O 422 `cliente_com_pendencia` mostra a mensagem da API e as linhas "Tem locação em andamento.", "Tem R$ X em aberto." e "Tem venda em andamento." (CLI-09).
4. **Falsos:** `falso-financeiro.ts` (`estornarMovimento`, `renegociar`, com ajuste da gaveta) e `falso-clientes.ts` (as quatro ações, com `reiniciarClientesFalsos`).

## Pontos para o orquestrador e o produto

- **Nenhuma dessas rotas devolve `acoes` por movimento nem por cliente.** Só a conta tem `acoes.renegociar`. Para o resto usei o perfil e a situação:
  - estornar movimento: `eu.pode.lancamento_avulso` (administrador, gerente e financeiro, a mesma linha de "cancelar, renegociar, estornar" da tabela de quem pode) com o caixa `aberto`;
  - cliente: administrador e gerente bloqueiam, inativam e reativam; o vendedor só pede o desbloqueio (202).
  Se a API passar a devolver `acoes`, a troca é local (`acoesDoCliente` e `estornavel`).
- **Estorno de movimento de conta recebida.** O contrato diz que estornar a entrada de uma conta recebida usa `contas-receber/{id}/estornar/`. Mantive o botão em todo movimento e deixei a API recusar o que não cabe, com um texto no diálogo apontando para o estorno da conta. Se o produto preferir esconder o botão nas entradas ligadas a uma conta, preciso de um campo na API que diga isso (`origem` hoje não distingue).
- **Desbloquear bloqueio automático.** O contrato diz que o bloqueio por atraso some quando o cliente quita, mas também permite desbloquear manualmente. A tela oferece "Desbloquear cliente" em qualquer cliente bloqueado.
- **Renegociar várias contas de uma vez.** A API aceita N originais; a tela renegocia uma conta por vez, a partir do detalhe dela.

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 77 arquivos, 720 testes passando.
- Testes novos: `components/financeiro/AcoesFinanceiras.test.tsx`, `components/clientes/AcoesDoCliente.test.tsx` e `lib/api/acoes-t370.test.ts` (rotas, corpos, 200 x 202).
- Os testes rodam em `node`, sem DOM: os diálogos estão cobertos pelo markup e pelo contrato, não por clique. Vale uma passada manual ou do QA a 1440px e 390px.
- Esta branch parte da `origin/main` sem a T-376 (#405): o `node_modules` é o do lock antigo.
- Nenhuma tela de Veículos foi tocada.
