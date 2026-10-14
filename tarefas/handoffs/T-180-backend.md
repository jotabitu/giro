# T-180 · Auditoria nos módulos ativos · backend → orquestrador, frontend

**O que foi feito:** `auditoria` entrou no padrão de `GIRO_MODULOS_ATIVOS` (`backend/config/settings/base.py`). Com isso, o item "Auditoria" (`apps/contas/navegacao.py`, só para quem tem `administracao`) passa a vir no menu da administradora, e a guarda de rota da tela da T-171 (PR #190) libera `/admin/auditoria`. Foi esquecimento: a T-018 entregou a API de auditoria e não acrescentou o módulo. O comentário da lista agora diz o que fica fora e por quê.
**Onde:** `backend/config/settings/base.py`, `backend/tests/aceitacao/test_t011_contas.py`.
**Contrato:** sem mudança no OpenAPI (só configuração; o `navegacao` do `GET /api/eu/` já tinha o item).
**Regras cobertas:** USR-05. Teste `test_usr_05_menu_do_administrador_tem_auditoria`: com os módulos padrão, a Administração da Mariana é `filiais`, `usuarios`, `assinatura`, `auditoria`, e o Rodrigo (gerente) e a Lúcia (financeiro) não veem o item.

**Conferidos e mantidos fora, de propósito:**
- `empresas` (itens "Configurações" e "Empresa e marca"): na `main` não existe nenhuma das duas telas. A marca é a T-153 (backend) e a T-154 (tela), ambas no backlog; Configurações é a T-173, ainda sem contrato. Ligar agora levaria a duas telas que não existem. **Atenção:** os dois itens dependem da mesma chave `empresas`. Quando a T-154 ligar o módulo, "Configurações" aparece junto, sem tela. Sugestão para o arquiteto: dar a "Configurações" uma chave própria (por exemplo, `configuracoes`) antes da T-154.
- `relatorios`: é da fase 2 (backlog, "Fase 2 em diante": relatórios e DRE), e não há tela `/relatorios`. O painel do início (`/api/painel/...`) responde sem a chave, como diz `apps/relatorios/api/urls.py`.
- `vendas`, `manutencao` e `conciliacao`: fase 2, sem mudança.

**O que ficou de fora:** nada da tarefa.
**Antes do push:** ruff, ruff format, mypy e os testes afetados (`test_t011_contas`, `test_t081_aprovacoes`, `test_t131_primeira_locacao`, `test_t129_painel_e_marca`, `apps/contas`): 85 passaram. OpenAPI sem mudança, então não há `api:gerar`.
**Próximo passo para quem recebe:**
- **Orquestrador:** o item aponta para `/admin/auditoria`, que só existe com o PR #190. Convém fazer o merge do #190 antes deste, ou junto. Se este entrar primeiro, a administradora vê o item e cai numa página que não existe até o #190 entrar.
