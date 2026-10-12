# T-139 · Decisões de visibilidade e conferência de cálculos da conferência · produto → backend, frontend, qa, orquestrador

**O que foi feito:** decidi e escrevi nas regras os itens de produto da conferência das telas do fim da T-127 (`C:/Users/Jota/Documents/giro-produto/conferencia-telas.md`, fora do git) e conferi contra as regras e o código os três de cálculo, com o dono de cada um.
**Onde:** `docs/regras-de-negocio.md` (`USR-08`, nova `USR-09`, `CLI-05`, nova `DEV-08`, caso "Bloqueio" dos dados de referência, notas de mudança de 12 out 2026); `tarefas/backlog.md` (nova T-140; T-136, T-137 e T-138 ganharam os itens).
**Regras cobertas:** USR-08, USR-09, CLI-05, DEV-08.

## Itens da conferência

| Item | O que era | Resposta | Dono |
| --- | --- | --- | --- |
| D-02 | Início do financeiro quebra | O conteúdo já estava na `USR-08` e em `docs/api/painel.md` (variante `financeiro`). Esclareci o MVP: entra hoje e em atraso aparecem; caixas do dia vazio e "Para hoje" só com reembolsos enquanto não há caixa e despesas. A tela quebrada é do frontend | frontend, T-137 |
| D-03 | Ficha do Rafael diz 25 dias, lista e locação 30 | O atraso conta pelo dia real (`FIN-03`). Os 25 são a descrição gravada no bloqueio (`clientes.services.bloquear_por_atraso`, seed de 07 out) e ficam parados. `CLI-05` agora diz que a ficha mostra os dias de hoje; o número do dia do bloqueio fica na auditoria. O caso "Bloqueio" dos dados de referência passou a dizer "em 07 out" | backend, T-140 |
| D-12 | "Km na saída" vazio na devolução da LOC-2836 | O seed grava `locacao.km_saida` (`registrar_vistoria_saida`), mas não cria a vistoria de saída do app `vistorias`, de onde o comparativo lê (`vistorias.selectors`, `saida.km`). Criada a `DEV-08`: o "Saída" da devolução é o que a locação gravou, o mesmo da ficha | backend (T-140) e qa (T-138) |
| D-18 | Receita da semana antes do financeiro | Entra: sai das contas a receber pagas (`FIN-15`), que já existem e nascem com a locação; nada é estimado (regra do MVP de `painel.md`). Escrito na `USR-08`. Se o número parece estranho, é o seed: a T-138 confere as datas de pagamento e o teste confere o valor | qa, T-138 |
| D-19 | "Primeiros passos 1 de 3" com dois itens que pareciam feitos | A conta da API está certa: `concluidos` soma os itens com `concluido`. "Configuração inicial" só conclui com conta, filial, ramo, preços e contrato gravados em `passos_implantacao`; o detalhe lista o que foi feito (marca, filial, preços, contrato) e parece concluído, mas faltava passo no seed. E a Mariana, com 42 locações, nem devia ver o `Pos-Dashboard` (`IMP-01`): resolvido pela T-131 (PR #143) com o seed confirmando pelo serviço. Falta o seed gravar todos os passos | qa, T-138 |
| D-27 | Financeiro abre a ficha da locação inteira | Pode, só leitura. Ações só de dinheiro (receber, marcar reembolso feito) | backend e frontend, T-136 |
| D-28 | Financeiro vê só o resumo do cliente | Passa a ver contato, locações e o financeiro do cliente; sem documentos, endereço e análise do cadastro | backend e frontend, T-136 |
| D-29 | Vistoriador abre a ficha do cliente | Não abre. Recebe do cliente, com a vistoria, só nome, celular e se a retirada está liberada | backend e frontend, T-136 |

## Decisões minhas (padrão mais restrito coerente com a tabela de perfis)

1. **Financeiro na ficha da locação (D-27):** leitura inteira, porque cobrar e receber pede o contexto (cliente, veículo, período, contrato); ações só as que a tabela de perfis dá a ele (receber pagamento, reembolso). Nenhuma ação de operação.
2. **Financeiro na ficha do cliente (D-28):** vê o que precisa para cobrar (contato, locações, financeiro do cliente) e nada além. Documentos, fotos, endereço e análise do cadastro ficam de fora, pela minimização da LGPD: a cobrança automática (`AUT-03`) e o Asaas usam os dados do cadastro sem que o financeiro precise vê-los. Ação única: Cobrar (`CLI-07`); bloquear e desbloquear continuam com gerente e administrador (`CLI-05`).
3. **Vistoriador e a ficha do cliente (D-29):** a tabela diz "só vistorias e veículos"; o que a vistoria precisa do cliente (nome, celular, retirada liberada por `CLI-02` e `CLI-03`) vem com a vistoria. É o mais restrito sem travar a retirada.
4. **Receita da semana (D-18):** aparece já, porque a fonte existe e é real. Esconder até o módulo financeiro completo tiraria um número certo da tela do gerente.
5. **Dias de atraso no bloqueio (D-03):** os dias de hoje na ficha, o número do bloqueio na auditoria. Não muda cálculo nenhum, só a descrição.

Nenhum item muda o que um perfil faz (só o que vê), então não abri `[decisão]` para o dono do produto. Se ele quiser o financeiro vendo documentos ou endereço do cliente, é só trocar a lista da `USR-09`.

**O que ficou de fora:** nada dos itens da T-139. Os demais itens da conferência estão na T-136, T-137 e T-138.

**Próximo passo para quem recebe:**
- **Backend:** T-140 (`CLI-05` e `DEV-08`, testes com o código no nome); na T-136, a `USR-09` (serializer por perfil para cliente e locação, 403 do vistoriador em `/api/clientes/`, dados do cliente na vistoria).
- **Frontend:** T-137 (D-02 com o conteúdo da `USR-08`); na T-136, as rotas e os botões da `USR-09`.
- **QA:** T-138 com D-12, D-18 e D-19; critérios de aceite da `USR-09` na T-136 (financeiro e vistoriador do seed: Lúcia e João).
- **Orquestrador:** abrir o PR.
