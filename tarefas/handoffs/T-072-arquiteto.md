# T-072 · Token do convite e da redefinição fora do caminho da URL · arquiteto → backend, frontend, qa, seguranca, orquestrador

**O que foi feito** (P-09 de `docs/seguranca/2026-10-08-codigo-t010.md`):
- **Convite na empresa (`docs/api/contas.md`):** `GET /api/convites/{token}/` virou `POST /api/convites/consultar/` com `{ token }`. `POST /api/convites/{token}/aceitar/` virou `POST /api/convites/aceitar/` com `{ token, nome, senha, aparelho }`. As respostas e os erros não mudaram; o 404 `nao_encontrado` passou a ser citado também no aceitar.
- **Convite na plataforma (`docs/api/plataforma.md`):** o mesmo, em `POST /api/plataforma/convites/consultar/` `{ token }` e `POST /api/plataforma/convites/aceitar/` `{ token, senha }`.
- **Links:** o token vai no fragmento, que o navegador não manda ao servidor nem ao proxy:

  | Link | Endereço |
  | --- | --- |
  | Convite da locadora | `https://<subdominio>.<dominio>/convite#<token>` |
  | Convite da plataforma | `https://admin.<dominio>/convite#<token>` |
  | Redefinir senha | `https://<subdominio>.<dominio>/entrar/redefinir#<token>` |

  A página lê o fragmento, apaga-o da barra (`history.replaceState`) e guarda o token só em memória, no mesmo padrão do `/suporte/entrar#<token>`.
- `POST /api/auth/senha/redefinir/` já levava o token no corpo; ficou só escrito que ele nunca vai na URL.

**Onde:** `docs/api/contas.md`, `docs/api/plataforma.md`, `tarefas/em-andamento.md`.

**Check:** só documentação; nenhum arquivo de `backend/` ou `frontend/` mudou, então não rodei os checks de código.

**O que ficou de fora:**
- A rota da plataforma no código fica com o backend (T-069); as rotas da empresa entram na T-069.
- As páginas `/convite` e `/entrar/redefinir` ficam com o frontend (T-073).
- O `docs/api/openapi.yaml` muda junto com o código, gerado pelo backend.
- `docs/qa/criterios/T-010.md` (linha 94) ainda cita `GET /api/plataforma/convites/{token}/`: fica para o qa trocar para `POST .../consultar/`.

**Próximo passo para quem recebe:**
- **Backend (T-069):** rotas novas nos dois urlconfs, com o token lido do corpo, e as antigas removidas (sem rota de compatibilidade, porque nada usa em produção); o e-mail do convite e do redefinir com o link no fragmento; o comando `convidar_equipe_plataforma` imprime `https://admin.<dominio>/convite#<token>`; limite `AcessoPorIP` nos dois endpoints.
- **Frontend (T-073):** `(publico)/convite/[token]` vira `(publico)/convite` lendo `location.hash`; o mesmo em `/entrar/redefinir`.
- **Segurança:** confere o fechamento do P-09 quando a T-069 e a T-073 entrarem.
