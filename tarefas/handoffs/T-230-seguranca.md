# T-230 · MEI e empresário individual no apagamento · segurança → orquestrador, produto, arquiteto

**O que foi feito:** revisei o que fica no `public` depois do apagamento (`AUD-08` da T-229, `cancelamento.md`, ADR 0025) quando a empresa é MEI ou empresário individual. Branch `t-230-revisao-mei`, a partir da `origin/t-229-regras-cancelar-pausar` (PR #230).

**Onde:** `docs/seguranca/2026-10-15-t230-mei-apagamento.md`; `[decisão]` nova em `tarefas/backlog.md` (antes da T-028); estado da T-230 no backlog; linha em `tarefas/feito.md`.

**Conclusão:**
- Razão social, CNPJ e endereço do MEI e do empresário individual são dados pessoais, e o Giro é controlador (contrato de assinatura). Depois do fim do tratamento, só fica o que a obrigação legal pede (LGPD art. 16, I), e o registro fiscal é a fatura e a nota, não a linha da `Empresa`.
- O CNPJ do MEI não contém o CPF; o CPF aparece na razão social de MEIs antigos.
- Recomendação: **opção B, igual para toda empresa** (a razão social de Ltda também traz nome de sócio, e o Giro não sabe a natureza jurídica). A linha apagada fica só com o CNPJ; a fatura guarda o tomador como foi na nota e ele sai com ela; a auditoria do `public` guarda "alterado" no lugar de endereço e contato.
- Sem achados altos. Médios: M-01 (a fatura não guarda o tomador; a NFS-e lê a `Empresa`), M-02 (a linha guarda mais do que precisa, inclusive `nome_exibicao`), M-03 (auditoria do `public` com endereço e contato por 5 anos). Baixos: B-01 (pagador no Asaas com contato), B-02 (`cnpj` único bloqueia a volta depois do apagamento). Ponto de negócio: fatura atrasada no 90º dia.

**Regras cobertas:** AUD-08, PLT-14, PLT-15, PLT-06, AUD-02, AUD-04, AUD-09.

**O que ficou de fora:** o prazo de guarda das faturas (dono e contador); a revisão da ADR 0025 e dos backups (T-199).

**Próximo passo para quem recebe:**
- **Produto:** levar ao dono a `[decisão]` (opção A ou B e a fatura atrasada) e, se B, ajustar `AUD-08` e `PLT-14` com o texto proposto no relatório.
- **Arquiteto:** com a B aprovada, `cancelamento.md` (limpar `razao_social`, `nome_exibicao`, `endereco_*`; pagador no parceiro; `cnpj` único parcial), `assinatura.md` (`FaturaAssinatura.tomador_*`) e `auditoria.md` (valores omitidos no `public`). Testes sugeridos no relatório.
- **Orquestrador:** abrir o PR; as tarefas de contrato e de código saem depois da decisão, sem número por enquanto. Se a T-195 começar antes, ela segue o contrato atual e a mudança entra como ajuste.
