# T-020 · Telas de acesso e casca do app · frontend → orquestrador, qa, backend (T-011)

**O que foi feito (com dados falsos, a API real não existe):**
- Login com 2 etapas (`/entrar`): e-mail e senha, `etapa` devolvida pela API (`pronto`, `verificar_2fa`, `configurar_2fa`), código do aplicativo ou de recuperação, bloqueio de 15 min mostrado como a API manda (USR-06). Sem "Manter conectado". O aviso de 2 etapas diz "administrador e financeiro" (USR-02).
- Esqueci a senha (`/entrar/esqueci`, `/entrar/redefinir?token=`): resposta sempre igual, link vencido, nova senha com a lista de regras. Ativar 2 etapas (`Ativar2fa`): QR gerado de `otpauth_uri`, chave para digitar, código de 6 dígitos, 8 códigos de recuperação (baixar, confirmação "Guardei").
- Convite (`/convite/[token]`): dados do convite, nome e senha, link vencido (410) e convite inexistente.
- Casca do app `(empresa)`: sidebar de 280px (Operação, Financeiro, Administração) com `componenteLink={Link}`; no celular, cabeçalho com gaveta, barra inferior (Início, Veículos, +, Locações, Mais) e a tela Mais (`/mais`). Menu só com o que `pode` libera (sem itens desabilitados, USR-05); contadores vêm da API.
- Main (`/inicio`): saudação, KPIs, frota por status, devoluções da semana, pendências, caixa de hoje. Nada é calculado no cliente.
**Onde:** `frontend/src/components/{acesso,casca}/`, `frontend/src/app/(publico)/{entrar,convite}`, `frontend/src/app/(empresa)/{inicio,mais,layout.tsx}`, `frontend/src/lib/{menu,sessao,senha,formatos,erros,marca-empresa,provedores}.ts(x)`.
**Troca pela API real:** tudo o que é falso está em `frontend/src/lib/api/falso.ts` (e os tipos temporários em `tipos.ts`). Reescreva `contas`, `relatorios` e `marcaDaEmpresa` em `lib/api/index.ts` com o cliente gerado e apague `falso.ts`. O comentário no topo lista as contas de teste (senha `senhaforte123`; código `123456`; convites `convite-rodrigo`, `convite-financeiro`, `convite-vencido`; redefinir com `token=link-valido`). Token de acesso só em memória; o "cookie de refresh" falso é o `sessionStorage`.
**Contrato:** `docs/api/contas.md` (versão de `giro-arquiteto`). Regras: USR-02, USR-05, USR-06, USR-07 (parcial, ver abaixo).
**Testes:** `menu.test.ts` (USR-05 por perfil), `senha.test.ts`, `formatos.test.ts`, `RegrasDeSenha.test.tsx`. Lint, typecheck, 53 testes e build verdes no host. Conferi no Edge (CDP) login, 2 etapas, Main e Mais a 1440 e 390 px.
**Dependências novas (motivo):** `react-hook-form`, `zod`, `@hookform/resolvers` (formulários, pedidos pela função); `@tanstack/react-query` (sessão e dados da tela); `qrcode.react` (QR do autenticador, gerado no navegador, a chave nunca sai da página).
**Também entrou na branch:** o commit do `CodigoVerificacao` (T-042, design-system), por cherry-pick, e usado nas duas telas de 2 etapas.
**O que ficou de fora:**
- Seletor de filial funcional e "Todas as filiais" (USR-07): o Sidebar só mostra a primeira filial. Sem sino de notificações (não há contrato).
- Ativar 2 etapas por conta própria (logado, `2fa/ativar/`): a tela é a mesma, falta a rota de configurações (T-0xx de Admin/perfil).
- Início por perfil (vistoriador, vendedor, gerente, financeiro): ver backlog. Rotas do menu além de `/inicio` e `/mais` ainda dão 404 (telas das T-021 a T-023).
- Faixa "Modo suporte" (`eu.suporte`) e sessões ativas: fora do escopo da tarefa.
- Painel direito do login sem números de exemplo (antes do login não há dado real); só a frase e as etiquetas.
- Link "Esqueci a senha" fica abaixo do campo nos dois tamanhos (o campo do design system não tem slot no rótulo).
- Dúvidas registradas em `tarefas/backlog.md` (menu por permissão, início por perfil, contrato dos agregados).
**Próximo passo para quem recebe:** backend (T-011) ajusta `contas.md` se algo do uso real divergir; qa pode usar as contas falsas até a API sair; frontend troca `falso.ts` pelo cliente gerado quando o OpenAPI existir.
