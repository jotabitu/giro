# T-269 · Subconta sem chave nunca usa a chave da conta principal (M-02 da T-189) · backend → seguranca, orquestrador

**O que foi feito:** `Asaas._chave` usa a chave do ambiente (`GIRO_ASAAS_CHAVE_API`) só para a conta principal: sem conta, ou com `conta_externa_id == CONTA_PRINCIPAL`. A subconta usa só a chave dela; se a chave voltar vazia, levanta `ParceiroIndisponivel` antes de chamar o parceiro. Assim, a cobrança da locadora nunca vai para a conta do Giro (ADR 0007).

**Onde:** `backend/integracoes/pagamentos/asaas.py`, `backend/tests/aceitacao/test_t189_seguranca_cartao.py`.

**Regras cobertas:** ADR 0007. `test_adr_0007_subconta_sem_chave_nunca_usa_a_chave_principal` passa sem o `xfail`. O novo `test_adr_0007_conta_principal_e_subconta_com_chave` cobre a principal com a chave do ambiente, a subconta com a dela e a recusa sem chamada. Os testes de pagamentos (T-029, `tests/integracoes`, T-186b, T-185b) passam; ruff, ruff format --check e mypy estão limpos no backend inteiro.

**Junto com a T-268:** as duas mexem no `test_t189_seguranca_cartao.py`. Cada uma tira só o próprio `xfail`, e a docstring do arquivo só muda na T-268. Mas as duas acrescentam um teste no fim do arquivo (e uma linha no fim do `feito.md`), então o merge da segunda dá conflito ali. A resolução é manter os dois lados: os dois testes novos e as duas linhas.

**O que ficou de fora:** nada.
