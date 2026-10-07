# Protocolo de colaboração entre agentes

## Ordem de trabalho de um módulo

Cada módulo (veículos, locação, financeiro...) passa pelas mesmas etapas. Uma etapa só começa quando a anterior tem handoff.

```
produto ─► arquiteto ─► backend ─┬─► frontend ─► qa ─► orquestrador fecha
  critérios   contrato da API     │     (usa o contrato e as telas)
  de aceite   e modelo de dados   └─► qa (testes de regra do backend)
design-system entra quando o frontend pedir componente novo
seguranca revisa módulos com dados pessoais, dinheiro ou acesso
```

1. **produto** escreve os critérios de aceite da tarefa com números do seed e aponta divergências entre tela e regra.
2. **arquiteto** escreve `docs/api/<modulo>.md` e atualiza o modelo de dados. A partir daqui, backend e frontend podem andar em paralelo.
3. **backend** implementa e publica o OpenAPI. **frontend** pode começar com dados falsos gerados do contrato e trocar pela API real quando o backend entregar.
4. **qa** valida com o seed e os testes ponta a ponta.
5. **orquestrador** lê os handoffs, fecha a tarefa e libera a próxima.

## Mensagens entre agentes

No Maestri os agentes podem mandar mensagem direto uns aos outros. Use sempre este formato, curto:

```
[T-015] backend → frontend
Entreguei a API de locações. Contrato: docs/api/locacoes.md. Handoff: tarefas/handoffs/T-015-backend.md.
Pode começar T-022.
```

```
[T-016] backend → produto  [decisão]
DEV-01 não diz o preço do litro quando a filial não cadastrou. Opções: A) bloquear o acerto até cadastrar; B) usar o último preço da empresa. Sugiro B.
```

Regras:

- Toda mensagem cita a tarefa. O que importa fica escrito em arquivo (handoff, backlog, regra); a mensagem só avisa.
- Pergunta de regra vai para o **produto**; técnica entre apps, para o **arquiteto**; prioridade ou bloqueio, para o **orquestrador**.
- Não espere parado: depois de perguntar, pegue outra tarefa.

## Conflitos de arquivo

- Cada agente escreve só na sua pasta (tabela em `AGENTS.md`).
- Arquivos compartilhados (`tarefas/*.md`) recebem edições pequenas e pontuais; releia antes de escrever.
- Cada tarefa tem a própria branch. Se o Maestri estiver com vários agentes na mesma cópia do repositório, prefira um `git worktree` por agente (`git worktree add ../giro-backend t-015-locacoes`).
