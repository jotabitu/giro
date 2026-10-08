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

Contas de teste do frontend (dados falsos até a T-011), senha `senhaforte123`:

| E-mail | Perfil | 2 etapas |
| --- | --- | --- |
| `mariana@motorapida.com.br` | administradora | código `123456` |
| `rodrigo@motorapida.com.br` | gerente | não pede |
| `financeiro@motorapida.com.br` | financeiro | ativa com `123456` |

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
- **Validar celular** no portal "Giro Celular" ou com Playwright em 390 px. O Edge headless não abre janela menor que 492 px.

## 5. Onde paramos

O estado de cada tarefa está em `tarefas/em-andamento.md` e `tarefas/feito.md`, e os detalhes de cada entrega em `tarefas/handoffs/`. Os PRs abertos estão no GitHub (`gh pr list`). A próxima leva quando o time voltar da pausa:

- **Frontend:** T-048 (ler `eu.navegacao` e o painel da T-047).
- **Backend:** a primeira tarefa de negócio da fase 1 sem dependência pendente (T-010, depois T-012, T-011, T-013, T-014). T-034 se ainda não tiver sido entregue.
- **QA:** T-019 (seed Moto Rápida) quando o backend de T-013 a T-017 existir.
- **Design System:** T-028 se ainda não tiver sido entregue; depois o que o frontend pedir.
- **Seguranca:** revisar cada entrega de backend que toca dados pessoais, dinheiro ou acesso.
