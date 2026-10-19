# T-282 · Envio do convite com o link já invalidado (B-01 da T-252) · backend → seguranca, qa

**O que foi feito:** a tarefa `contas_enviar_convite` para antes de gerar o token quando o convite já venceu (`expira_em` até agora). O link copiado, um reenvio ou um convite novo vencem os anteriores na hora (`_invalidar_convites`, P-06), então o e-mail ou o WhatsApp ainda na fila, ou repetido por ela, não sai mais com um link morto. O convite morto também não recebe token novo.

**Onde:** `backend/apps/contas/tasks.py`; testes em `backend/tests/aceitacao/test_t252_seguranca_convite.py`.

**Contrato:** sem mudança de rota nem de OpenAPI.

**Regras cobertas:** USR-01, P-06 (`test_usr_01_email_de_convite_invalidado_nao_sai`, agora sem `xfail` e conferindo também o WhatsApp e o token; `test_usr_01_convite_valendo_ainda_sai`, o controle). t011 e t250 seguem passando.

**O que ficou de fora:** nada.

**Observação para quem roda os testes:** o banco de teste reaproveitado pode ter a coluna `atividade` da migração da T-262 (branch `t-262-cartao-ramo`); numa branch sem ela, rode com `--create-db`.

**Próximo passo para quem recebe:** (seguranca) dar o B-01 da T-252 por fechado.
