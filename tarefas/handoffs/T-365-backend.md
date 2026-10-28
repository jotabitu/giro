# T-365 · Reativar a empresa cancelada · backend → orquestrador, qa, seguranca

**O que foi feito:**
- `plataforma.services.reativar_empresa(empresa, por=POR_EQUIPE, motivo)`: com a `Empresa` travada, a `cancelada` volta a `ativa` na hora e perde o cancelamento, o apagamento marcado e o aviso dele (`cancelamento_pedido_em`, `motivo_cancelamento`, `acesso_ate`, `cancelada_em`, `apagar_em`, `aviso_apagamento_enviado_em`). Nasce uma mensalidade pelo plano, ciclo e preço contratado atuais:
  - com o período pago ainda correndo, vence no dia seguinte ao fim dele, e o `dia_vencimento` não muda (CA-ASS-49);
  - senão, vence hoje, e o dia passa a ser o de hoje (CA-ASS-46).
  A conta fica em `calendario.vencimento_da_reativacao`, função pura. A fatura nasce sem forma (a forma sai com o cancelamento), e o administrador escolhe ao entrar (`PLT-13`). Com vencimento em até 5 dias, a emissão é tentada na hora e devolve `sem_forma`.
- Recusas, sem mudar nada:
  - sem motivo: `ErroDeValidacao` `{"motivo": ["Informe o motivo."]}`;
  - fora da `cancelada`: 409 `transicao_empresa` "Só a empresa cancelada pode ser reativada.";
  - no dia do apagamento ou depois (`apagar_em` ≤ hoje): 409 `transicao_empresa` "O apagamento dos dados desta empresa já começou. Não dá para reativar.";
  - já apagada: 409 `transicao_empresa` "Os dados desta empresa já foram apagados.";
  - com fatura `atrasada`: 409 `fatura_em_atraso` "Receba a fatura em atraso antes de reativar.".
- **B-02 da T-199:** `apagar_empresa` agora apaga os arquivos (passo a) com a `Empresa` travada e conferida. Uma reativação ao mesmo tempo espera a trava e depois é recusada, porque `apagar_em` já chegou. Não precisou de campo novo nem de migração.
- `encerrar_forma_pagamento` não mexe na forma da empresa que já não é `cancelada`, e devolve `reativada`. A tarefa tenta de novo por 24 h com o parceiro fora do ar, e sem essa guarda apagaria a forma escolhida por quem já voltou.
- `Empresa.TRANSICOES`: `cancelada → ativa`.
- Django Admin, `Empresa`: ação "Reativar a empresa cancelada", só para o dono (`has_reativar_permission`), com o campo Motivo ao lado do seletor de ações. Ela chama o serviço, mostra a recusa na mensagem e audita com o usuário da equipe. A lista ganhou a coluna `apagar_em`.
- Auditoria `empresa.reativar` no `public` e na empresa, com o motivo; `antes` com status, `cancelada_em`, `apagar_em` e dia de vencimento; `depois` com o dia de vencimento, a fatura e `por`. Também `empresa.ativa`, pela transição.

**Onde:** `backend/apps/plataforma/services.py` (`reativar_empresa`, `apagar_empresa`, `encerrar_forma_pagamento`), `calendario.py`, `models.py`, `admin.py`.

**Contrato:** sem rota nova; `assinatura.md`, "Mudança de ciclo e reativação pela equipe", e `plataforma.md`, "Faturas de todas as empresas". O OpenAPI não muda.

**Regras cobertas:** PLT-06, AUD-08. Testes:
- `test_plt_06_reativar_so_com_atrasada_paga` (CA-ASS-46): era `xfail` e agora é teste comum;
- `test_plt_06_reativar_no_periodo_pago` (CA-ASS-49);
- `test_plt_06_reativar_audita_nos_dois_lugares`, `test_plt_06_reativar_recusas`;
- `test_aud_08_reativar_recusa_o_apagamento_comecado`, `test_aud_08_reativada_perde_o_aviso_do_apagamento`;
- `test_plt_06_reativada_antes_do_fim_da_forma_fica_com_ela`;
- `test_plt_06_admin_reativa_pelo_servico`, `test_plt_06_so_o_dono_reativa_no_admin`;
- `test_plt_06_vencimento_da_reativacao` (função pura);
- `test_aud_08_nao_apaga_reativada` passa a reativar pelo serviço.

**O que ficou de fora:**
- A reativação da `suspensa` pela rota da plataforma (`plataforma.md`, ação `reativar`, fase 2). A `suspensa` volta sozinha ao pagar.
- O `plano_proximo` agendado antes do cancelamento continua como estava. A fatura da reativação usa o plano atual, como manda o contrato.

**Próximo passo para quem recebe:**
- QA: o CA-ASS-46 e o CA-ASS-49 estão cobertos; atualizar a cobertura de regras (os 7 `xfail` viram 6).
- Segurança: B-02 resolvido sem `apagamento_iniciado_em`; a trava no passo (a) e a recusa por `apagar_em` ≤ hoje fecham a corrida.
