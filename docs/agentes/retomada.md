# Retomar o time em outra máquina

Tudo o que o time precisa está no GitHub: código, regras, contratos, quadro e handoffs. Só três coisas viviam na máquina antiga e estão descritas aqui: os papéis no Maestri, os worktrees de cada agente e as lições de funcionamento.

## 1. Preparar a máquina

- Git, GitHub CLI (`gh auth login` com a conta que acessa `jotabitu/giro`), Docker Desktop, Node 22, Python 3.12.
- Claude Code e Maestri instalados.
- No Windows, use Git Bash ou WSL para o `make`.

```
git clone https://github.com/jotabitu/giro.git
cd giro
cp .env.example .env
docker compose up        # sobe db, redis, backend, worker, beat e frontend
```

Para ver só o frontend: `cd frontend && npm ci && npm run dev` e abrir http://localhost:3000. Rode `npm ci` de novo sempre que um PR mudar `package.json`.

Contas de desenvolvimento (T-127): o login é real, e o `make seed` (comando `seed_moto_rapida`, idempotente) cria a empresa Moto Rápida. Entre em http://motorapida.localhost:3000/entrar. Senha de todas: `giro-dev-2026`.

| E-mail | Perfil | 2 etapas |
| --- | --- | --- |
| `mariana@motorapida.com.br` | administradora | exige o código |
| `rodrigo@motorapida.com.br` | gerente | não pede |
| `bruna@motorapida.com.br` | vendedora | não pede |
| `joao@motorapida.com.br` | vistoriador | não pede |
| `lucia@motorapida.com.br` | financeiro | exige o código |

O código de 2 etapas de agora sai de `docker compose exec backend python manage.py seed_moto_rapida --codigo mariana@motorapida.com.br` (a semente do autenticador é fixa, só para desenvolvimento). O seed não roda com as configurações de produção. O que depende do financeiro da T-017 (contas a pagar, caixa, baixas, vendas e comissões) fica para a T-019. O seed congela o relógio em 07 out 2026 só enquanto roda; depois o sistema usa a data de verdade, então "vence hoje" e "atrasada" das telas seguem o dia real.

## 2. Um worktree por agente

A cópia principal (`giro/`) é do orquestrador. Cada agente trabalha num worktree irmão, numa branch por tarefa. Crie as pastas a partir da `main` e deixe cada agente criar a branch da tarefa dele:

```
git worktree add ../giro-backend   -b espera-backend   origin/main
git worktree add ../giro-frontend  -b espera-frontend  origin/main
git worktree add ../giro-design    -b espera-design    origin/main
git worktree add ../giro-arquiteto -b espera-arquiteto origin/main
git worktree add ../giro-produto   -b espera-produto   origin/main
git worktree add ../giro-qa        -b espera-qa        origin/main
git worktree add ../giro-devops    -b espera-devops    origin/main
git worktree add ../giro-seguranca -b espera-seguranca origin/main
git worktree add ../giro-integracao -b espera-integracao origin/main   # do orquestrador, para juntar branches
```

Para retomar uma tarefa que já tem branch no remoto: `git -C ../giro-backend checkout -B t-034-auditoria-celery origin/t-034-auditoria-celery`.

## 3. Papéis e terminais no Maestri

O papel de cada terminal é o arquivo `.claude/agents/<funcao>.md` mais o rodapé abaixo. O orquestrador cria os papéis e recruta um terminal por agente, com o nome da função (o protocolo endereça os agentes por esse nome):

```
maestri role create "Backend" "<conteúdo de .claude/agents/backend.md + rodapé>"
maestri recruit "Backend" --preset "Claude Code" --role "Backend"
```

Modelo por agente: Opus para Orquestrador, Produto, Arquiteto, Backend e Seguranca; Sonnet para Frontend, Design System, QA e DevOps. Para trocar o modelo de um terminal sem perder as conexões:

```
maestri recruit --command "claude --model claude-sonnet-5-5" --replace "Frontend"
```

Conexões entre agentes (além de todos com o orquestrador): Produto com Arquiteto, Backend, Frontend, QA e Design System; Arquiteto com Backend, Frontend, DevOps e Seguranca; Backend com Frontend, QA, DevOps e Seguranca; Frontend com Design System, QA e DevOps; QA com DevOps e Seguranca. Use `maestri connect "A" "B"`.

Portais para ver o frontend: `maestri portal create http://localhost:3000/entrar "Giro Web"` e `maestri portal create http://localhost:3000/entrar "Giro Celular" --size 390x844`.

Rodapé do papel (troque `<funcao>` e `<worktree>`):

```
## No Maestri

Você é o agente **<funcao>** do projeto Giro, num terminal do canvas Maestri.
Trabalhe SOMENTE no seu worktree (<worktree>). Nunca rode git, npm, pip nem docker na cópia principal giro/.
Ao iniciar: leia CLAUDE.md, .claude/agents/<funcao>.md, tarefas/README.md, tarefas/backlog.md e docs/agentes/protocolo.md.
Rode `maestri list` para ver os colegas. Fale com eles por `maestri ask "Nome" "[T-NNN] <funcao> → destino ..."`.
Dúvida de regra vai para Produto; técnica entre apps, para Arquiteto; prioridade ou bloqueio, para Orquestrador.
Só pegue tarefa que está no quadro. Pedido direto de outro agente que vire trabalho novo: avise o Orquestrador antes.
Antes de continuar uma branch, faça git fetch e git merge origin/main.
Ao terminar: commit no formato do CLAUDE.md, handoff em tarefas/handoffs/, push (confira a saída do git push) e avise o Orquestrador. PR quem abre é o Orquestrador.
```

## 4. Lições de funcionamento

- **Nunca npm ou git na cópia principal.** Um `npm install` lá apagou dependências do `package-lock.json` e o frontend passou a mostrar só HTML sem estilo.
- **Conferir o push.** Um push recusado (a branch remota tinha commits novos) foi dado como enviado. Sempre `git status -sb` depois do push.
- **Check completo antes de entregar.** Backend: `ruff check`, `ruff format --check`, `mypy`, `pytest` (o `make backend-check`). Frontend: lint, typecheck, testes e build. O CI roda os mesmos passos em todo PR.
- **Conflito no quadro (`tarefas/*.md`): linha a linha.** Escolher um lado inteiro já apagou registros de outro agente.
- **Merge de PR com commit de merge, não squash**, porque há PRs empilhados. Só com o aval do dono do produto.
- **Limpar o contexto de um agente:** `MSYS_NO_PATHCONV=1 maestri ask "Nome" "/clear"` (sem a variável, o Git Bash troca `/clear` por um caminho do Windows). Depois mande um resumo de retomada: tarefa, worktree, branch, último commit e estas regras.
- **Contexto em 50%.** O orquestrador confere a barra de contexto de cada agente (rodapé do terminal, lido com `maestri check "Nome"`) a cada entrega e antes de mandar tarefa nova. Chegou a 50%: entre tarefas, `/clear` e resumo de retomada, porque tudo o que importa está no repositório; no meio de uma tarefa, `/compact` com foco na tarefa, para não perder o raciocínio em curso. Pedido do dono do produto em 08/10.
- **Validar celular** no portal "Giro Celular" ou com Playwright em 390 px. O Edge headless não abre janela menor que 492 px.
- **Terminal aberto no worktree.** Recrute cada agente com `--dir` no worktree dele, por exemplo `maestri recruit "Backend" --command "claude --model claude-opus-5-5" --role "Backend" --dir 'C:\Users\Jota\Documents\giro-backend' --replace "Backend"`. Aberto na cópia principal, o Claude Code pede permissão a cada leitura fora do diretório e o agente trava.
- **`.env` e Postgres.** Se as permissões negarem acesso a `.env`, o dono do produto cria o arquivo (`cp ../giro-integracao/.env.example ../giro-integracao/.env`). O compose sobe uma vez só, a partir de `giro-integracao` (`docker compose -p giro up -d --build`); os agentes não sobem outro. Para o pytest antes disso, o backend usa um Postgres descartável na porta 55432, com `infra/postgres` montado, e o remove no fim (comando no handoff da T-010).

## 5. Onde paramos

Pausa de 08/10, depois da T-012 (PR #35). O estado de cada tarefa está em `tarefas/em-andamento.md` e `tarefas/feito.md`, os detalhes em `tarefas/handoffs/` e os PRs abertos em `gh pr list`. A próxima leva quando o time voltar:

- **Backend:** T-058 (P-01 a P-04 da revisão T-057), antes de qualquer ambiente com dados reais; depois T-011, T-013 e T-014.
- **Produto:** T-059 (carteira de outubro, textos da T-010, `PLT-08` e CNPJ da Messejana).
- **Design System:** T-060 (telas do Receber e do Financeiro; FleetBar conferido no navegador a 390 px).
- **Frontend:** T-061 (rotas do menu da T-055).
- **Arquiteto:** conferir as 5 decisões de implementação do handoff da T-012.
- **DevOps:** limite de requisições no proxy (P-03, S-17) quando houver homologação.
- **QA:** T-019 (seed Moto Rápida) quando o backend de T-013 a T-017 existir.
- **Seguranca:** revisar cada entrega de backend que toca dados pessoais, dinheiro ou acesso; a T-012 ainda não foi revisada.
