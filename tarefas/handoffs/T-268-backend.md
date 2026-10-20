# T-268 · Aviso do parceiro gravado sem o token do cartão (M-01 da T-189) · backend → seguranca, devops, orquestrador

**O que foi feito:**
- `integracoes.pagamentos.base.aviso_sem_cartao(corpo)`: o corpo do aviso sem `payment.creditCard` (número final, bandeira e token), sem mudar o original. É o único ponto usado pelos dois: `plataforma.services.registrar_webhook_principal` (conta principal, `public`) e `financeiro.services.registrar_webhook` (subcontas, schema da empresa). O token só existe cifrado na forma de pagamento (ADR 0023, item 2).
- Migração de dados `comum/0003_aviso_sem_cartao`: limpa os `WebhookRecebido` já gravados que têm `bruto.payment.creditCard`. Como `comum` está nos dois schemas, ela roda no `public` e em cada empresa. A regra vai copiada na migração, para não depender do código de hoje. Não tem volta (noop), porque o token não deve voltar.

**Onde:** `backend/integracoes/pagamentos/base.py`, `apps/plataforma/services.py`, `apps/financeiro/services.py`, `comum/migrations/0003_aviso_sem_cartao.py`, `tests/aceitacao/test_t189_seguranca_cartao.py`.

**Regras cobertas:** ADR 0023, S-14. `test_adr_0023_aviso_guardado_sem_o_token_do_cartao` passa sem o `xfail`, e o novo `test_adr_0023_aviso_sem_cartao_e_a_limpeza_dos_ja_gravados` cobre a regra e a migração. Os testes de pagamentos (T-029, T-186b, T-017) e `comum` passam. O `xfail` do M-02 continua lá, para a T-269. ruff, ruff format --check e mypy estão limpos no backend inteiro.

**Para o devops:** a migração roda em todos os schemas no próximo `migrate_schemas`. São só os avisos com cartão, então é rápida.

**O que ficou de fora:** nada.
