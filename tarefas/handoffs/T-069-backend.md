# T-069 · Usuários e convite da empresa · backend → frontend, qa, seguranca, arquiteto, orquestrador

**O que foi feito:**
- **Usuários** (`/api/usuarios/`, só o administrador, contrato `docs/api/contas.md`):
  - lista com `plano`, `contagens` e os filtros `situacao`, `perfil`, `filial` e `busca`;
  - detalhe com `permissoes_extras` (`marcada`, `padrao_do_perfil`) e `entrou_em`;
  - `PATCH` de perfil, filiais e permissões extras;
  - `convites/`, `reenviar-convite`, `cancelar-convite`, `desativar`, `reativar`, `redefinir-2fa`, `sessoes` e `sessoes/{sid}/encerrar`.
- **Convite da empresa:** `POST /api/convites/consultar/` e `POST /api/convites/aceitar/`, públicos e com o token no corpo.
  - Sai depois do commit, por e-mail e, quando a pessoa tem celular, também por WhatsApp, com a marca da locadora.
  - Vale 7 dias e conta no plano (`exigir_limite` e `atualizar_uso` na mesma transação).
  - Ao aceitar, quem não precisa de 2 etapas recebe `pronto` e fica `ativo`. Quem precisa recebe `configurar_2fa` e só fica `ativo` ao confirmar o código.
  - Quando o administrador da compra fica `ativo`, marca o passo `conta` da implantação.
- **P-06:** um convite novo, reenviado ou aceito invalida os outros da mesma pessoa. O link antigo responde 410.
- **P-09:** o link sai como `/convite#<token>`, também no comando da equipe da plataforma. A plataforma passou para `POST /api/plataforma/convites/consultar/` e `aceitar/`, com o token no corpo, como na T-072. As rotas antigas, com o token no caminho, saíram.
- **`Lower(email)` único:** restrição `usuario_email_unico_sem_caixa` (migração `contas/0006`). O convite com "Bruna@MotoRapida" responde 409 `email_em_uso`.
- **F-03:** a troca de filiais da pessoa:
  - grava `usuario.alterar_filiais` (`seguranca`), com antes e depois em id e nome;
  - desativa o vínculo (`UsuarioFilial.ativo`, migração `filiais/0002`) em vez de apagar;
  - recusa filial acrescentada inexistente ou inativa com 422 `filial_invalida`, como no contrato.
- **`X-Filial: todas` para o financeiro:** ele vê todas as filiais ativas, e `/filiais/minhas/` devolve `pode_escolher_todas: true` (`comum.permissoes.PERFIS_QUE_VEEM_TODAS`). Em `GET /filiais/{id}/`, uma filial fora do escopo (desativada) continua só para o administrador.
- **`relatorios_todas_filiais`:** com essa extra, `X-Filial: todas` só vale nas views que declaram `escopo_de_relatorio = True` (painel e relatórios). Nas outras, 403 `USR-07`.
- **Administradores:**
  - `ultimo_administrador` (os administradores ativos ficam travados, para que dois rebaixamentos ao mesmo tempo não deixem a empresa sem nenhum);
  - `desativar_a_si_mesmo`;
  - desativar revoga as sessões na mesma transação;
  - `reativar` só aceita quem está `desativado` (convite pendente → 409 `transicao_usuario`) e confere o plano.
- **WhatsApp:** fica atrás de `integracoes/whatsapp` (`GIRO_PROVEDOR_WHATSAPP`). Por enquanto só existe a implementação falsa, que guarda as mensagens em `caixa_de_saida`. Não entrou dependência nova.

**Onde:** `backend/apps/contas/` (`api/usuarios.py`, `api/plataforma.py`, `api/urls.py`, `services.py`, `selectors.py`, `tasks.py`, `models.py`, migração `0006`), `backend/apps/filiais/` (`services.py`, `selectors.py`, `models.py`, `api/views.py`, migração `0002`), `backend/comum/permissoes.py`, `backend/integracoes/whatsapp/`, `config/settings/base.py` e os READMEs de contas e filiais.

**Contrato:** `docs/api/openapi.yaml` regerado com `--validate`, sem aviso. Há quatro pontos fora do `contas.md` para o Arquiteto conferir:
1. `POST /usuarios/convites/` devolve 201 com o detalhe completo, o mesmo corpo de `GET /usuarios/{id}/`. O contrato diz só "o usuário".
2. `reenviar-convite`, `cancelar-convite`, `desativar`, `reativar` e `redefinir-2fa` também devolvem o detalhe.
3. `filial_invalida` sai com a mensagem "Escolha só filiais ativas". O contrato não define o texto.
4. Rebaixar um administrador sem mandar `filiais` responde 400 `validacao` no campo `filiais`, porque a pessoa ficaria sem filial. O contrato não fala desse caso.

**Regras e testes:** `tests/aceitacao/test_t011_contas.py`.
- Passam CA-011-01, 02, 12 (agora pela rota, com a auditoria `usuario.alterar_perfil`), 14 a 18, 21 (detalhe), 22 a 24 e 28 (`test_aud_01_ca_011_28_eventos_da_administracao_de_usuarios`).
- Outros testes novos:
  - `test_usr_01_convite_novo_invalida_o_anterior` (P-06);
  - `test_usr_01_convite_com_limite_por_ip`;
  - `test_usr_07_troca_de_filiais_da_pessoa_vai_para_a_auditoria` (F-03);
  - `test_usr_07_financeiro_escolhe_todas_as_filiais`;
  - `test_usr_03_relatorios_todas_filiais_so_em_painel_e_relatorios`;
  - `test_usr_04_administrador_ve_e_encerra_sessoes_de_outro`;
  - `test_usr_01_usuario_da_empresa_a_nao_aparece_na_b` (isolamento).
- Saíram os xfail de T-069:
  - os dois `xfail(strict=False)` do limite por IP em `test_t058_seguranca.py`, que agora passam como testes normais;
  - o `xfail(strict=True)` do CA-010-15 em `test_t010_plataforma.py`.
- O teste de P-05 da plataforma (`test_t011_seguranca.py`) usa a rota nova.

**Mudei dois testes de outras tarefas (QA, conferir):**
- `test_t012_filiais.py`, CA-012-12: Lúcia (financeiro) agora recebe 200 na filial Caucaia, que não está ligada a ela. É o que diz a USR-07 corrigida na T-067: o financeiro vê todas as filiais ativas. O texto do CA-012-12 ("fora do escopo → 404") continua certo, porque a Caucaia agora está no escopo dela.
- `test_t010_plataforma.py`, CA-010-02: o e-mail traz `/convite#`, não `/convite/`.

**Check:**
- Ruff check, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `337 passed, 45 xfailed`, sem xpassed. Restam só os `xfail` de T-070 e os de outros módulos.
- Rodei no Postgres descartável (`giro-backend-pg`, porta 55432), com `--rm` e `POSTGRES_HOST`, e montei `docs/` no container para os testes da T-056.

**O que ficou de fora:**
- O provedor real de WhatsApp: só existe o falso. A integração precisa de uma tarefa própria, e o devops configura o `GIRO_PROVEDOR_WHATSAPP` quando ela existir.
- **[decisão] para o Produto:** quem teve o convite cancelado e depois é reativado volta como `ativo`, sem senha, e precisa usar "Esqueci a senha". A outra opção seria voltar para `convite_pendente` com um convite novo, mas a tabela de transições da USR-04 não prevê `desativado → convite_pendente`. Mantive `ativo` e não inventei a transição.
- Modo suporte (T-070) e navegação do `eu` (T-071).

**Para a Seguranca revisar:**
- O link substituído responde 410, "convite vencido", e não 404. O CA-011-16 aceita os dois.
- O `consultar` revela a quem pertence um token válido (e-mail, nome e perfil). É o que a tela precisa, e o token é aleatório, de 32 bytes.

**Próximo passo para quem recebe:**
- **Frontend:**
  - telas `Convite` e `Admin-Usuarios`: rotas reais em `openapi.yaml`;
  - o convite usa o token do fragmento, com `consultar` e `aceitar` no corpo (T-073);
  - na lista, `plano.bloqueado` desabilita "Convidar";
  - no detalhe, `padrao_do_perfil: true` mostra a permissão marcada e travada.
- **QA:** conferir as duas mudanças nos testes da T-010 e da T-012. Os CAs da T-070 continuam `xfail`.
