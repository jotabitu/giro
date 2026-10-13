# T-151 · Decisões da T-018: CPF na auditoria, exportação e contrato da sangria · arquiteto, produto → orquestrador, backend, frontend, qa

**O que foi feito:** registrei as decisões do dono do produto de 12 out 2026 sobre os dois pontos do backend na T-018, as duas pela opção A da análise do produto (`C:/Users/Jota/Documents/giro-produto/analise-t018.md`, fora do git; posição do arquiteto em `analise-t018-arquiteto.md`).

**Parte do arquiteto (commit e02f08b):**
- `docs/decisoes/0014-sessoes-e-dados-sensiveis.md`: nota datada no item 3. A máscara de CPF e CNH vale para campos não cifrados, telas, listas e exportações de cadastro (`AUD-04`, `AUD-09`); no evento de auditoria todo `CampoCifrado` é omitido (`{"alterado": true}`), sem exceção.
- `docs/api/auditoria.md`: exemplo do CA-018-06 com `{"alterado": true}` e o endereço só com cidade e UF (o resto `"***"`); sangria como `movimento_caixa.sangria`, objeto `movimentocaixa` com a filial do caixa, e a nota dos movimentos de caixa (código na T-150).

**Parte do produto:**
- `docs/qa/criterios/T-018.md`: CA-018-06 reescrito (CPF e CNH `{"alterado": true}`, endereço só cidade e UF, busca por `05221833018` sem achar nada); CA-018-13 ajustado à opção A (só a auditoria em CSV; outro item, `planilha` ou `zip` → 422 `exportacao_indisponivel`; o 403 `2fa_recente` do backup completo passa para a fase 2); `AUD-07` no cabeçalho.
- `docs/regras-de-negocio.md`: nota de 12 out 2026 (T-151) no fim da seção "Auditoria, LGPD e exportação": o que da `AUD-07` é MVP, o pedido do titular (`AUD-06`) atendido à mão pela equipe Giro até a fase 2, e CPF e CNH omitidos no evento.
- `tarefas/backlog.md`: a seção da T-151 saiu (a T-150 fica); a lista "Fase 2 em diante" detalha o resto da exportação.
- `tarefas/feito.md`: linha da T-151 com o PR #159.

**Regras cobertas:** AUD-04, AUD-06, AUD-07, AUD-09.

## Decisões

| # | Ponto | Opção | O que muda |
| --- | --- | --- | --- |
| 1 | CPF e CNH no `antes`/`depois` da auditoria | A | nada no código; critério, contrato e nota na ADR 0014 |
| 2 | Exportação no MVP (`AUD-07`) | A | só a auditoria em CSV; a tela `Admin-Exportar` mostra só ela; o resto na fase 2 |

Nenhum número do seed muda.

**O que ficou de fora:**
- **Arquiteto:** a seção "Exportação" de `docs/api/auditoria.md` ainda não cita o 422 `exportacao_indisponivel` nem como a API diz à tela o que está disponível no MVP (a tela não deve mostrar os outros itens, nem desabilitados). Detalhe de contrato, sem mudança de regra; o backend já responde 422.
- **Frontend (quando fizer `Admin-Exportar`):** só "Auditoria", "CSV", o período e "Exportações recentes"; sem o cartão "Backup automático".
- **Orquestrador:** a exportação completa vira tarefa da fase 2 (lista no backlog).

**Próximo passo:** orquestrador abre o PR #159; o backend segue com a T-150.
