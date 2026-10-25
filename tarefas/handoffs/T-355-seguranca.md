# T-355 · Revisão de segurança de fechamento da fase 1 · segurança → orquestrador, backend, devops, arquiteto

**O que foi feito:** passei pelas regras de segurança e LGPD (`USR-xx`, `PLT-07`, `PLT-08`, `AUD-xx`), pelos `S-xx` da fundação e pelos relatórios de `docs/seguranca/`, conferindo cada achado no código atual. Relatório: `docs/seguranca/2026-10-25-t355-fechamento-fase-1.md`. Nenhum código mudou.
**Testes rodados** (contêiner descartável, banco `giro_seg`, `--create-db`): `test_t189_seguranca_cartao.py`, `test_t317_varredura_suporte.py` e `test_permissoes_das_rotas.py`, 164 passed. `pip-audit -r requirements.txt`: 37 avisos no Pillow 12.3.0. Não parei o `giro-backend-pg`.

**Correção ao pedido:** os `xfail` estritos da T-189 e da T-317 já saíram. A T-268 e a T-269 fecharam os da T-189, e na T-317 o `QUEBRADAS` está vazio desde a T-324. Os dois arquivos passam na `main`.

**Resultado:** nenhum alto antigo aberto. Um alto novo (A-01, Pillow) e quatro médios bloqueiam a produção. Os baixos podem entrar depois do piloto.

**Tarefas sugeridas, para numerar** (detalhe e "pronto quando" no relatório):

| Item | Gravidade | Agente | Tarefa |
| --- | --- | --- | --- |
| A-01 | alta | backend | Pillow 13 e `pip-audit` limpo (junto, a T-160) |
| M-01 | média | devops | `DATABASE_URL_MIGRACAO` só num worker próprio do apagamento `AUD-08`, conferida no teste de subida |
| M-02 | média | arquiteto, depois devops | ADR do ambiente de produção: backup cifrado com retenção compatível com a `AUD-08`, restauração testada, Django só pelo proxy, cofre |
| M-03 | média | backend | Comandos `exportar_titular` e `anonimizar_titular` para a equipe Giro atender a `AUD-06` até a fase 2, com auditoria |
| M-04 | média | devops | `make auditoria-deps` (`pip-audit` e `npm audit`) no deploy |
| B-01 | baixa | backend | T-159, já no backlog (confirmada aberta em `contas/api/acesso.py:374-378`) |
| B-02 | baixa | backend | T-160, já no backlog (confirmada aberta em `config/settings/base.py:185-188`) |
| B-03 | baixa | backend | `ParceiroRecusou` no webhook vira resultado (B-02 da T-189) |
| B-04 | baixa | backend | Na tarefa da reativação: recusar a empresa com o apagamento começado (B-02 da T-199) |
| B-05 | baixa | backend | Fase 2: `cnh_digital` na `AUD-06` (B-05 da T-247) |

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar o A-01 e os médios no topo do backlog. Os baixos novos (B-03) entram depois do piloto. O B-04 e o B-05 vão como critério das tarefas que já os cobrem.
- **Arquiteto:** o M-02 começa por uma ADR. Se preferir que o M-03 nasça como a rota da fase 2, só para o administrador, diga antes de o backend começar.
- **Produto:** opcional. Decidir se a retenção máxima dos backups (M-02) aparece no texto do cancelamento (`AUD-08`).
