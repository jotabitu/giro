# T-181 · Resumo da tela de Configurações · backend → frontend, qa

**O que foi feito:** `GET /api/configuracoes/` com os cartões prontos (título e resumo) e a faixa da implantação, como em `docs/api/configuracoes.md`. Só quem tem `pode.administracao`; os outros perfis recebem 403 `{ "codigo": "permissao", "mensagem": "Seu perfil não tem acesso a esta página" }`. Token de suporte: os mesmos cartões, sem `auditoria` e `exportar` (PLT-07). Empresa suspensa, pausada ou cancelada: responde. Sem cache.

**Onde:**
- `backend/apps/relatorios/configuracoes.py`: textos (função pura).
- `backend/apps/relatorios/selectors.py`: `configuracoes(usuario, suporte)`, só pelos selectors da tabela "Fontes".
- `backend/apps/relatorios/api/` (view, serializer, rota).
- Selectors novos: `filiais.selectors.resumo_das_filiais_ativas`, `contas.selectors.convites_pendentes` (agora também o contador `usuarios` do painel), `veiculos.selectors.categorias_ativas`, `locacoes.selectors.planos_especiais_ativos`, `contratos.selectors.resumo_dos_modelos`.
- `contas/navegacao.py`: item `config` com a chave própria `configuracoes`; `modulos_ativos()`.
- `config/settings/base.py`: `configuracoes` no padrão de `GIRO_MODULOS_ATIVOS`.

**Contrato:** `GET /api/configuracoes/` (`docs/api/openapi.yaml`, schema `Configuracoes`).

**Decisão do arquiteto (14 out):** o item `config` do menu ganhou a chave própria `configuracoes`, já no padrão. `marca` (item do menu e cartão) continua em `empresas`, fora do padrão até a T-153 e a T-154. A rota responde sempre, como o painel. Na T-192, `configuracoes` entra em todos os planos. Ajustados `configuracoes.md` e `contas.md`.

**Regras cobertas** (testes em `backend/tests/aceitacao/test_t181_configuracoes.py`):
- USR-05: `test_usr_05_configuracoes_seed_moto_rapida`, `test_usr_05_configuracoes_so_cartoes_de_apps_ativos` (inclui `marca` fora com `empresas` desligado e o padrão do backend), `test_usr_05_configuracoes_so_administrador`, `test_usr_05_configuracoes_no_maximo_10_queries`, `test_usr_05_configuracoes_textos_dos_cartoes`.
- PLT-03: `test_plt_03_configuracoes_usuarios_conta_convites` ("7 de 10 usuários · 2 convites").
- PLT-07: `test_plt_07_configuracoes_suporte_sem_auditoria`.
- IMP-01 e IMP-05: `test_imp_05_configuracoes_faixa_da_implantacao` (6 de 10 sem botão; 9 de 10 com `nova_locacao`).
- IMP-04: `test_imp_04_configuracoes_sem_modelo_publicado` e `test_imp_04_configuracoes_rascunho_e_sem_modelo_publicado` ("2 modelos · 1 rascunho").
- LOC-01: `test_loc_01_configuracoes_planos_especiais` ("4 categorias · 2 planos especiais").

Com todos os cartões são 8 consultas de dados; o teste não conta o `SET search_path` que o django-tenants repete a cada cursor. Mais filiais e mais modelos não aumentam a contagem.

**Diferenças em relação ao contrato:**
- O selector das filiais se chama `resumo_das_filiais_ativas()`, porque `resumo_das_filiais(usuario)` já existia (o `eu` e a lista de usuários). A tabela "Fontes" do contrato foi corrigida.
- `[decisão]` para o produto: empresa sem filial ativa mostra "Nenhuma filial ativa" no cartão Filiais. O contrato não cobre esse caso; o texto segue o padrão de "Nenhuma categoria cadastrada".
- Sem plano, o cartão Assinatura mostra só a situação.

**O que ficou de fora:** `integracoes` e `notificacoes` (fase 2); `acao` com `destino: "implantacao"` (espera o contrato do assistente).

**Próximo passo para quem recebe:**
- Frontend (T-182): ligar `/admin/configuracoes` a `GET /api/configuracoes/`, com `chave` → rota pela tabela "Rotas dos cartões". No padrão do backend o menu mostra Configurações, e Empresa e marca só aparece quando `empresas` for ligado.
- QA: com o seed e todos os apps ativos, conferir os 8 cartões do primeiro exemplo do contrato.
