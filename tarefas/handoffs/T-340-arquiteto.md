# T-340 · Contratos das perguntas da T-202 · arquiteto → orquestrador, backend, frontend, qa

**O que foi feito:** respondi aos itens 1 e 2 do handoff da T-202 (`tarefas/handoffs/T-202-backend.md`, PR #369). Nenhum dos dois pede decisão do produto.

1. **`acao.passo` da Configurações: chegou a hora.** A casca da T-335 tem `/implantacao/[passo]` para os 8 passos, e o passo sem tela abre com "Esta etapa ainda não está disponível aqui." e "Pular por agora". Então o botão não leva a lugar quebrado. Em `configuracoes.md`:
   - com o `proximo` de `GET /api/implantacao/` preenchido: `{ "rotulo": "Continuar implantação", "destino": "implantacao", "passo": "<proximo>" }`;
   - com os 8 passos do assistente feitos e `primeira_locacao` aberto: `nova_locacao`, como hoje;
   - nenhum dos dois: `null`;
   - `implantacao` leva a `/implantacao/{passo}`. O `proximo` vem dos passos já lidos, e o teto continua em 11 queries.
   - A faixa conta 10 passos (6 de 10), e o assistente conta 8 (5 de 8). Isso já estava decidido (T-200). O botão só usa a chave do passo.
2. **Placa com hífen: não é regra nova, é convenção de contrato.** O dono já decidiu mostrar a placa "como nas telas" (13 out 2026, PR #187, CSV das despesas, `FIN-16`), e a auditoria já segue isso. Em `docs/api/README.md` (Convenções), toda placa dentro de um texto montado pela API sai com hífen (`PMZ-3E17`). O campo `placa` sozinho continua sem hífen, e a tela formata. O contrato e o CA-APR-11 estão certos, e o código é que muda. Isso vale para todos os textos, então pede uma tarefa própria do backend (no quadro, dentro da T-340, "a numerar").

**Onde:** `docs/api/configuracoes.md`, `docs/api/plataforma.md` (nota do `GET /api/implantacao/`), `docs/api/README.md`, `docs/api/veiculos.md` (campo `placa`), `tarefas/backlog.md` (T-340).
**Regras cobertas:** `IMP-05`, `PLT-12`, `FIN-16` (nenhuma regra muda).
**O que ficou de fora:** o código. O backend acerta o `acao` e o formatador de placa numa tarefa só. O frontend não muda.
**Próximo passo para quem recebe:** orquestrador numera a tarefa do backend descrita na T-340. Ela pode entrar na T-202 (PR #369) se o PR ainda estiver aberto. O qa confere o CA-APR-11 com `PMZ-3E17` e o botão "Continuar implantação" levando a `/implantacao/contrato` no exemplo de 6 de 10. Branch `t-340-contratos-t202`, sem PR.
