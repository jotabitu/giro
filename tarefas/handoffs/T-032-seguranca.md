# T-032 · Revisão de segurança do desenho da fundação · seguranca → orquestrador, arquiteto, backend

**O que foi feito:** apliquei o checklist de segurança às ADRs 0008 a 0012 e a `docs/decisoes/modelo-de-dados.md`, e conferi a configuração atual da T-001 (`config/settings/base.py`, `config/urls*.py`). Foram 18 achados: 9 altos, 8 médios e 1 grupo de baixos. Os altos que afetavam a T-001 foram avisados na hora ao Backend e ao Arquiteto.

**Onde:** `docs/seguranca/2026-10-07-fundacao.md` (relatório), `tarefas/backlog.md` (seção "Achados de segurança da fundação (T-032)" e uma `[decisão]` para o produto).

**Já resolvido no desenho:**
- S-01 (claim `schema` nas views de token), S-02 (token de suporte), S-03 (2FA com JWT), S-04 (Admin só no public com OTP), S-08 (cookie `__Host-` e mesma origem): ADR 0013 do Arquiteto (commit `26c731a`). Aceitei o `Path=/` exigido pelo prefixo `__Host-` e o cabeçalho `X-Requested-With: giro`.
- O Backend aplica S-01 e S-04 na T-001; S-02, S-03 e S-08 na T-011.
- S-05, S-06, S-07 e S-13: ADR 0014 (commit `00ddbf4`). S-09: restrição no `ModeloContrato`, com detalhe no contrato da T-015.

**Em aberto (viraram itens no backlog, esperando número):**
- Nenhum alto ficou sem decisão de desenho.
- Médios: trigger com `TRUNCATE` e papéis do banco (S-10); Celery sem vazar ator, schema ou cache (S-11); SVG do logo (S-12); webhooks (S-14); links com prazo (S-15); host desconhecido e cabeçalhos em produção (S-16, S-17).
- Baixa: pepper do HMAC derivado por empresa, já aplicado na 0014.

**O que ficou de fora:** revisão de código. Isto foi revisão de desenho; a revisão do código da T-001 e da T-011 fica para depois da entrega (sugiro antes da T-024).

**Próximo passo para quem recebe:**
- Orquestrador: numerar e priorizar os 4 itens médios do backlog. Garantir que o que a 0014 manda para a T-001 (`comum/cripto.py`, `CampoCifrado`, classificação da auditoria) entre antes de T-011 e T-014. Levar a `[decisão]` do suporte ao produto.
- Seguranca: revisar o código da T-001 e da T-011 contra as ADRs 0013 e 0014 quando forem entregues.
