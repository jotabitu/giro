# Memória do Giro

Histórico e contexto do projeto, consultado sob demanda. Regras fixas ficam no `CLAUDE.md`. Entradas mais recentes primeiro; nada aqui é apagado (ver "Manutenção da Memória" no `CLAUDE.md`).

## Decisões de Design

### [2026-10-29] Telas do canvas entram por importação
- **Contexto:** as telas são desenhadas no canvas do Claude Design e copiadas à mão para `docs/telas/html`. Os dois lados foram editados em separado: na T-409 as telas da locadora no canvas já eram mais antigas que as do repositório. Os agentes só leem o repositório, e nada conferia a página do app contra a tela.
- **Decisão (dono, T-424):** vale a tela do repositório na `develop`. Mudança no canvas entra por tarefa de importação, com carimbo `<!-- origem: canvas, <data>, T-NNN -->`; ajuste feito no repositório ganha `<!-- ajustada no repositório: <data>, T-NNN -->`, e tela do canvas mais antiga não o sobrescreve. A página segue textos, ordem, hierarquia, estados e componentes, não o pixel nem os números de exemplo. O frontend põe capturas lado a lado no handoff, e o design-system revisa antes do merge.
- **Alternativas descartadas:** o canvas como fonte da verdade (os ajustes por regra feitos no repositório se perderiam); comparação automática por pixel (números e componentes mudam de propósito).
- **Consequências:** `docs/agentes/telas-do-canvas.md`, `frontend.md`, `design-system.md` e `docs/telas/README.md`; conferência automática com o Playwright na T-425. O Claude Design avulso fecha em 14 dez 2026: importar o canvas inteiro antes disso.

### [2026-10-29] Fluxo com a branch develop
- **Contexto:** com a fase 1 fechada e a fase 2 por começar, o dono quis uma camada de integração antes da `main`. O CI só roda em pull request e só nas áreas tocadas, então o conjunto da `main` nunca passava inteiro pelo CI, e o E2E não roda no CI.
- **Decisão (dono):** a branch da tarefa sai da `origin/develop` e o PR vai para a `develop`. A `develop` vai para a `main` por lote, num PR com o aval do dono, depois de o QA conferir o lote na `develop`. Correção urgente do que já está na `main`: `t-<numero>-hotfix-<slug>` a partir da `main`, PR para a `main` e, depois, a `main` entra na `develop`. A `main` fica protegida no GitHub: só PR, com CI verde. A `develop` nasceu da `origin/main` em 7822c922 (PR #448).
- **Alternativas descartadas:** promover só no fim da fase (a `main` ficaria parada por semanas); promover toda semana (lote sem conferência); hotfix sempre pela `develop` (lento para o que já está no ar).
- **Consequências:** `CLAUDE.md`, `tarefas/README.md` ("Fluxo de branches") e `docs/agentes/retomada.md` atualizados na T-423; os rodapés dos papéis no Maestri e os worktrees dos agentes precisam passar para a `develop` antes da primeira tarefa da fase 2. Substitui "Sem branch develop" de 09 out.

### [2026-10-29] Preço FIPE pela Parallelum gratuita, sem token, com rotina mensal
- **Contexto:** o catálogo de modelos já vem da Parallelum (ADR 0031), mas sem preço; o campo `referencia_fipe_centavos` existe e nada o preenche. A FIPE licenciada (T-338) segue sem pedido de cotação. A Parallelum tem preço por marca, modelo e ano e por código FIPE: 500 pedidos por dia sem cadastro, 1.000 com token gratuito, e o plano Pro (R$ 59/mês para novos assinantes) sem limite.
- **Decisão (dono):** usar a Parallelum no gratuito, sem token, com uma rotina mensal no servidor. O risco de licença é o mesmo aceito na ADR 0031 e vale enquanto não houver contrato com a FIPE. Tarefa T-422, que pede ADR nova (o servidor passa a chamar a API, o que a 0031 evitava).
- **Detalhes decididos no mesmo dia:** a rotina atualiza todos os veículos ativos; o código FIPE dos já cadastrados vem pelo casamento automático, e a ficha pede para escolher a versão quando houver mais de uma; a consulta por placa (Alpha, 15 por mês sem token) entra como recurso em teste, desligado por padrão, pronto para o plano Pro.
- **Quando rever:** se o volume passar dos 500 pedidos por dia (token gratuito ou Pro) ou quando sair o contrato com a FIPE.

### [2026-10-29] Fase 2 aberta sem atividade iniciada
- **Contexto:** o dono escreveu 11 notas na aba Notas do painel "Progresso do Giro" (documentos `notas/*` do banco do artifact FqWd6) e pediu que virassem tarefas.
- **Decisão (dono):** a fase 2 está aberta, mas nenhuma tarefa começa até ele liberar. As notas viraram as tarefas T-410 a T-420 no backlog ("Notas do dono de 29 out 2026"), com as respostas dele: locação confirmada reserva o veículo e as parcelas só vencem depois da retirada; copiar link em contrato, cobrança, recibo da devolução e fatura; faixa fixa da suspensa em todas as telas, sem pop-up; galeria própria de fotos do veículo e fotos da vistoria para ver e baixar; escolher a versão no CRLV-e; categorias próprias de despesa do veículo; catálogo interno e depois vitrine pública; loca-compra com prazo fixo e transferência ao quitar.
- **Revisão de decisão:** a tela de Veículos (ficha e editar) está liberada para a fase 2, inclusive os botões parados da ficha. Revê a entrada de 20 out "Sem tarefas na tela de Veículos por enquanto".
- **Fonte das notas:** o painel guarda as notas na coleção `notas` (leitura e escrita só de quem edita o artifact); ler com `ArtifactData list` antes de abrir novas tarefas a partir delas.

### [2026-10-28] Fase 1 fechada no ambiente de desenvolvimento
- **Contexto:** o fechamento começou em 25 out ("Escopo de fechamento da fase 1") e seguiu com as decisões de 28 out ("O que já existe e é da fase 2 fica como está"). Entre 25 e 28 out entraram as tarefas T-356 a T-407, até o PR #445, com dois agentes de backend e a Segurança pegando tarefas de backend de segurança.
- **Decisão (dono):** a fase 1 está fechada com o código pronto e testado no ambiente de desenvolvimento. O E2E da T-375, parte 2 (`tarefas/handoffs/T-375-qa-e2e.md`), passou nos critérios de pronto do `plano.md`: implantação do zero com os cinco passos, locação, devolução, cobrança, caixa, 2 etapas, aceite do convite, modo suporte, controle do suporte, Reembolsos e Pendências do pagamento com dados, celular e os CRLV-e reais. Os agentes param até o dono abrir a fase 2.
- **O que fica para a fase 2:** a seção "Fechamento da fase 1" do backlog lista tudo. Em resumo: subida e contas de produção (T-373), Completo fora da venda e preço do Profissional (T-378), NFS-e (T-197), FIPE licenciada (T-338), remetente do WhatsApp, os botões da ficha do veículo e um ajuste visual da busca.
- **Lições do fechamento:**
  - o CI instala as dependências do zero (pytest 9.2, T-395);
  - a ordem dos merges importa quando um PR de backend muda uma enum que o frontend exige (o #437 só passou depois do #436);
  - o harness do `npm run e2e` apaga o banco `giro`, então o E2E roda numa stack isolada;
  - depois de um merge com pasta nova, o frontend do Compose precisa de `docker compose restart frontend`.

### [2026-10-28] O que já existe e é da fase 2 fica como está
- **Contexto:** a decisão D2 de 25 out ("Escopo de fechamento da fase 1") jogou a comissão de locação para a fase 2, e a T-377 começou a desligar a comissão que já existia no código. A T-378 tiraria o Completo da venda, com um campo novo no plano.
- **Decisão (dono):** funcionalidade que já está pronta e foi marcada como fase 2 fica como está, e na fase 2 só se continua dela. Desligar custa trabalho agora e de novo na volta. Como a fase 1 fecha no ambiente de desenvolvimento e ninguém compra plano antes da produção, a T-378 e o preço do Profissional também vão para a fase 2.
- **Alternativas descartadas:** desligar a comissão na fase 1 (a parte (a) da T-377) e tirar o Completo da venda já na fase 1.
- **Consequências:**
  - a comissão de locação continua sendo lançada; o downgrade da fase 1 continua recusado só por despesas abertas (`PLT-12`);
  - a T-377 fica só com os textos da T-391;
  - a T-378 está na seção "Fase 2 em diante" do backlog, junto com a resposta sobre o preço e os limites do Profissional;
  - nas próximas decisões de escopo, o que já existe é escondido da tela quando preciso, não removido do backend.

### [2026-10-28] CI e imagem local com versões diferentes do pytest
- **Contexto:** o CI do backend instala as dependências do zero a cada rodada e passou a pegar o pytest 9.2.0; a imagem local `giro-backend:latest` tinha o 9.1.1. O `monkeypatch.setattr(connection, "in_atomic_block", False)` de um teste da T-196 trocava o atributo no proxy `django.db.connection`. No 9.2, desfazer a troca apaga o atributo da conexão, e todos os testes seguintes do mesmo processo do xdist erraram (460 erros no CI do #418), com a conferência local verde.
- **Decisão:** o teste troca o atributo em `connections["default"]`, a conexão de verdade (T-395, PR #421).
- **Consequências:** quando o CI do backend falhar e a conferência local passar, compare as versões do "Successfully installed" no log do CI com o `pip list` da imagem, e reproduza com `pip install pytest==<versão do CI>` dentro do `docker run`. O `requirements-dev.txt` não fixa o teto do `pytest`.

### [2026-10-25] Contas de produção ficam para a fase 2
- **Contexto:** a ADR 0033 (opção B, uma VPS) e a ADR 0034 (WhatsApp real, proposta) listam o que o dono precisa contratar: domínio, VPS, bucket de backup, Asaas de produção, WhatsApp pela Meta, e-mail transacional e Sentry.
- **Decisão (dono):** as contratações e a subida de homologação e produção ficam para a fase 2. A fase 1 fecha com o código pronto e testado no ambiente de desenvolvimento.
- **Consequências:**
  - a T-373 entra só com o que não depende da conta (PR #399);
  - o E2E do fechamento (T-375) roda no ambiente de desenvolvimento;
  - a ADR 0034 continua proposta, e a escolha da opção e do remetente (T-387) espera a conta da Meta;
  - o provedor real do WhatsApp entra na fase 2, e na fase 1 os avisos usam o provedor falso e o e-mail.

### [2026-10-25] Escopo de fechamento da fase 1
- **Contexto:** os levantamentos da T-353 (produto), da T-354 (arquiteto) e da T-355 (segurança), sobre a `main` em 626d432, mostraram que o núcleo da fase 1 funciona. Pôr uma locadora real em uso ainda esbarra em quatro coisas: a implantação não fecha pela tela, os módulos por plano estão pela metade, o catálogo dos planos promete módulos da fase 2 e não há produção.
- **Decisão (dono, pelas recomendações do produto e do orquestrador):**
  - **D1:** na fase 1 se vendem só o Essencial e o Profissional. O texto do Profissional lista só o que existe, e o Completo não é vendido até ter o que o diferencia. O preço do Profissional fica com o dono.
  - **Para a fase 2:** a comissão de locação (`FIN-09`, `FIN-10`, `AUT-10`, D2), a tela Minha conta (D3), o expurgo de 5 anos (`AUT-16`, D4), o aviso de implantação parada (`AUT-14`, `IMP-06`, D6) e os Relatórios.
  - **D5:** a NFS-e da assinatura é emitida à mão no portal da prefeitura até a T-197 destravar.
  - **D7:** a hospedagem e as contas de produção se decidem já, pela ADR da T-357.
  - **Implantação:** os 5 passos do assistente que faltam (Primeira filial, Tabela de preços, Modelo de contrato, Recebimentos, Convidar equipe) entram na fase 1.
  - **Suporte Giro no MVP:** a equipe abre o acesso pelo Django Admin, que chama o mesmo serviço. O administrador bloqueia o suporte num cartão em Configurações, e a página de entrada e a faixa do modo suporte entram na fase 1.
- **Alternativas descartadas:** em D1, vender os três planos com o texto atual (contraria a `PLT-11`) ou trazer vendas para a fase 1. Para o suporte, adiá-lo inteiro para a fase 2.
- **Consequências:** as tarefas T-356 a T-375 (backlog, seção "Fechamento da fase 1"). As regras ganham as marcas de fase na T-356. `docs/qa/cobertura-de-regras.md` (de 07 out) está desatualizada e é refeita no fechamento, pelo QA.

### [2026-10-25] Janela das 2 etapas recentes fica em 5 minutos na prática
- **Contexto:** cancelar a assinatura (`PLT-06`) e o backup completo (`S-15`) pedem as 2 etapas recentes (`DOIS_FATORES_RECENTE` = 15 min, T-345). Como o `renovar` não leva o `auth_time`, a janela dura só o primeiro access do login, que vive 5 minutos (achado do Arquiteto na T-346). Depois disso, a tela pede o código de novo pela reconfirmação (ADR 0032, T-347 e T-348).
- **Decisão (Segurança na T-349, PR #386, mesclada com o aval do dono):** manter assim, sem ADR nova e sem mudança no backend. `DOIS_FATORES_RECENTE` = 15 min fica como teto, e a regra não passa a dizer 5 minutos (USR-02, PLT-06 e S-15 não fixam número).
- **Alternativas descartadas:** levar o `auth_time` pela rotação do refresh até completar os 15 minutos. Quem roubasse o refresh nos 15 minutos depois do login ganharia as 2 etapas recentes sem o autenticador, e o reuso (P-07) só derruba a sessão até 5 minutos depois, tempo suficiente para pedir o backup completo.
- **Consequências:** toda ação que pedir as 2 etapas recentes deve usar `useReconfirmar2fa` e `DialogoReconfirmar2fa` (T-348), inclusive o download do backup completo na fase 2. Os contratos dizem que a janela efetiva é de 5 minutos (T-351).

### [2026-10-21] Cancelar a ativa com o período pago já vencido: o acesso termina na hora
- **Contexto:** a `PLT-06` dá acesso até o fim do período pago, mas não dizia o que fazer quando a `ativa` cancela no dia do vencimento da fatura seguinte, ainda sem pagá-la (T-195, PR #375).
- **Decisão (dono, opção A, recomendação do Produto):** a empresa vira `cancelada` no mesmo dia, e a fatura do dia é cancelada no parceiro e não fica devida; a tela mostra "termina agora". Se o cartão já foi cobrado antes do cancelamento, vale o caso comum: acesso até o fim do período pago. Registro nas regras pela T-343.
- **Alternativas descartadas:** B, acesso até o fim do período se a fatura for paga, que cobraria um mês de quem está saindo e contraria o "sem cobrança futura" da `PLT-06`.
- **Consequências:** o caso segue a `inadimplente` e a pausa; na reativação, a fatura nova vence no dia da volta. Teste `test_plt_06_acesso_que_ja_acabou_termina_agora`.

### [2026-10-20] Fonte provisória do catálogo de veículos: API aberta da Parallelum
- **Contexto:** o cadastro de veículos precisa de um catálogo de marcas, modelos e versões (`VEI-08`). A fonte definitiva escolhida pelo dono, a FIPE licenciada (opção B), ainda não está contratada.
- **Decisão:** usar provisoriamente a API aberta da Parallelum (projeto `parallelum/fipe-go`), com o risco aceito pelo dono. ADR 0031 (aceita, provisória); a ADR 0030 (FIPE licenciada) segue proposta. A carga é a T-339: script fora do servidor, sem dependência nova, carro e moto, 1 pedido por segundo, com a lista própria juntada na carga.
- **Alternativas descartadas:** ficar sem catálogo até contratar a FIPE licenciada. As outras opções da T-337 além da B: [A CONFIRMAR].
- **Consequências:** é fonte de terceiro, sem garantia; a troca pela FIPE licenciada deve ser uma nova ADR que substitua a 0031. Observe o limite de pedidos e mudanças na API aberta.

### [2026-10-20] CRLV-e com um layout só para todos os estados
- **Contexto:** dúvida se a leitura do CRLV-e precisaria de variações por estado.
- **Decisão (dono):** o layout é o mesmo em todo o país. Só muda o cabeçalho com o nome e o logotipo do Detran do estado, que não interfere nos dados.
- **Alternativas descartadas:** um modelo por UF, desnecessário pela resposta do dono.
- **Consequências:** a leitura não precisa tratar variantes por estado. Tarefa de origem: [A CONFIRMAR].

### [2026-10-20] Parte do time de agentes no Gemini (Antigravity)
- **Contexto:** o limite semanal do Claude foi atingido em 20/10, e o dono quis dividir a carga entre provedores.
- **Decisão:** QA, Frontend e Design System rodam no Gemini 4 Argon (High) pelo Antigravity CLI (`agy --effort high --add-dir <worktree>`), recrutados pelo Maestri. Orquestrador, Backend, Arquiteto, Segurança e Produto ficam no Opus; DevOps no Sonnet. No agy, `toolPermission: "always-proceed"` (escolha do dono).
- **Alternativas descartadas:** trocar também o Backend (o dono quis manter no Opus).
- **Consequências:** o Gemini não lê `.claude/agents/` sozinho; a primeira mensagem deve mandar ler `CLAUDE.md`, `.claude/agents/<funcao>.md`, `tarefas/README.md` e `docs/agentes/retomada.md`. As entregas desses agentes passam pela mesma conferência das outras.

### [2026-10-14] Compra pública e painel da plataforma ficam para a fase 2
- **Contexto:** a fase 1 priorizou o sistema da locadora, incluindo assinatura, cancelamento e pausa (`PLT-01` a `PLT-15`, decisão do dono na T-190).
- **Decisão:** no MVP, a equipe Giro cria empresas pelo Django Admin, que chama o mesmo serviço `plataforma.services.criar_empresa` (`docs/api/plataforma.md`). As telas `Compra-*` e `Plat-*` não têm rota no frontend; `/plataforma` é um texto provisório.
- **Alternativas descartadas:** compra self-service já na fase 1 (exige a rota pública, proteção contra abuso e revisão da Segurança).
- **Consequências:** em 21/10 o backend já tinha login e 2 etapas da plataforma, planos (só lista), empresas (lista e detalhe), acessos de suporte e auditoria; faltam a rota pública de compra, cobrança, implantações, equipe interna e planos editáveis. Antecipar alguma parte é decisão pendente do dono.

### [2026-10-12] Repositório público por enquanto
- **Contexto:** a cota gratuita do GitHub Actions esgotou em 12/10 e só voltaria em 01/11. O CI já rodava só nas áreas alteradas (T-120).
- **Decisão (dono, opção D):** tornar `jotabitu/giro` público, com Actions ilimitado.
- **Alternativas descartadas:** orçamento pago e runner próprio (a máquina tem pouca memória).
- **Consequências:** nunca commitar segredo, `.env` nem dado pessoal real. Perguntar ao dono, perto de 01/11, se o repositório volta a ser privado.

### [2026-10-09] Sem branch develop [SUBSTITUÍDA por 2026-10-29 "Fluxo com a branch develop"]
- **Contexto:** o dono cogitou o fluxo `main` ← `develop` ← `t-xxx`, com CI nas duas etapas.
- **Decisão:** "deixe como está por enquanto": a branch da tarefa sai da `origin/main` e o PR vai para a `main`.
- **Alternativas descartadas:** `develop`, que dobraria PRs e avales.
- **Consequências:** se voltar, criar a `develop`, o CI com push nela (DevOps), atualizar `tarefas/README.md` e `CLAUDE.md` e avisar os agentes.

### [2026-10-08] Contexto dos agentes limpo a partir de 50%
- **Contexto:** pedido do dono para controlar o custo e a qualidade dos agentes no Maestri.
- **Decisão:** com 50% de contexto, `/clear` entre tarefas (com o resumo de retomada depois) e `/compact` no meio de uma tarefa.
- **Alternativas descartadas:** compactar sempre, que é mais caro; limpar é seguro porque tudo fica no repositório (handoff, quadro, regras).
- **Consequências:** conferir a barra de contexto a cada entrega e antes de mandar tarefa nova.

## Log de Bugs Resolvidos

### [2026-10-25] Seed em banco limpo com `config.settings.test` parava em `veiculos_veiculo does not exist` (T-281)
- **Sintoma:** `seed_moto_rapida` num banco novo, com as configurações de teste, falhava na 1ª rodada (a 2ª passava).
- **Causa raiz:** com `CELERY_TASK_ALWAYS_EAGER`, o convite agendado no commit roda na conexão do seed, e o sinal de limpeza de `comum/worker.py` (S-11, ADR 0012) devolvia a conexão ao public.
- **Correção:** a tarefa eager guarda o schema e o ator de quem chamou e os devolve no fim; o worker real limpa como antes. Teste `tests/test_seed_banco_limpo.py`.

### [2026-10-20] Contêineres de teste do backend que nunca saem
- **Sintoma:** vários contêineres de pé em `docker ps`, presos em "Aguardando o Postgres em db...", sem sair mesmo com `--rm`.
- **Causa raiz:** o entrypoint da imagem espera o host `db` do compose quando o contêiner avulso roda sem `-e POSTGRES_HOST`.
- **Correção:** rodar com `-e POSTGRES_HOST=giro-backend-pg` na rede `giro-backend-teste`; para ruff e mypy, `--entrypoint sh`; conferir `docker ps` depois de cada rodada. Dois órfãos (um do orquestrador, um do QA) foram removidos.
- **Pistas falsas:** parecia trabalho em andamento dos agentes.

### [2026-10-20] Cópia principal com 135 telas "modificadas"
- **Sintoma:** `docs/telas` aparecia com 135 arquivos alterados na cópia principal, sugerindo telas novas a commitar.
- **Causa raiz:** a cópia estava parada no PR #54. Das 135, 42 eram iguais à `main`, 83 eram versões antigas e 10 nunca entraram na `main` (8 mais antigas e as 2 do Gerente com números antigos do seed).
- **Correção:** nada foi commitado; stash, avanço da cópia para a `main` e descarte do stash com o aval do dono.
- **Pistas falsas:** a tela do Gerente parecia uma versão nova, mas era praticamente a mesma da `main`.

### [2026-10-20] Agentes no Gemini parando a cada comando
- **Sintoma:** o agy pedia aprovação em cada comando; `--model gemini-4-argon-high` era ignorado com aviso.
- **Causa raiz:** a permissão padrão do Antigravity pede aprovação; o modelo padrão já é o Gemini 4 Argon, e o nível sai do `--effort`.
- **Correção:** `"toolPermission": "always-proceed"` em `~/.gemini/antigravity-cli/settings.json` e `--effort high` no comando.
- **Pistas falsas:** o nome do modelo com `-high`.

### [2026-10-20] Textos cortados pelo PowerShell
- **Sintoma:** `gh pr create --body` e `maestri ask` chegavam com o texto cortado; `stash@{0}` dava erro.
- **Causa raiz:** o PowerShell interpreta aspas duplas e chaves dentro do argumento.
- **Correção:** `--body-file`, mensagens pelo Bash com `"$(cat arquivo)"` e `'stash@{0}'` entre aspas simples.
- **Pistas falsas:** nenhuma registrada.

### [2026-10-20] Comando do Maestri digitado e não enviado
- **Sintoma:** depois de `/clear` ou `/compact`, o texto ficava na caixa do agente (às vezes como `[Pasted text #N]`), e o agente ficava parado por horas (16/10 e 20/10).
- **Causa raiz:** o envio seguinte chega antes de o agente voltar a aceitar entrada. [A CONFIRMAR]
- **Correção:** conferir com `maestri check` depois de cada `/clear`; se ficou colado, mandar `--raw "\r"`; se ficou digitado, limpar com Esc e `\x15` e mandar de novo numa linha só. Conferir se a barra de contexto caiu.
- **Pistas falsas:** o `ask` volta sem erro, como se tivesse sido entregue.

### [2026-10-19] NotNullViolation nos testes de uma branch sem migração nova
- **Sintoma:** testes falhando com `NotNullViolation` numa coluna que a branch não conhece (coluna `atividade`, da T-262).
- **Causa raiz:** o banco de teste é reaproveitado entre branches e ficou com a migração de outra branch.
- **Correção:** rodar com `--create-db`.
- **Pistas falsas:** parecia defeito no código da branch.

### [2026-10-19] Script Python no Windows estragando arquivos
- **Sintoma:** byte NUL de verdade num `.py`, `replace` com acento falhando em silêncio e arquivo inteiro convertido para CRLF.
- **Causa raiz:** o Python do Windows lê o stdin e grava texto no código de página e no fim de linha do Windows, e o Bash mexe nos escapes do heredoc.
- **Correção:** usar a ferramenta de edição; para script, escrever o `.py` em arquivo, gravar com `newline="\n"` e conferir `s.count(velho) == 1` antes de cada troca.
- **Pistas falsas:** nenhuma registrada.

## Contexto de Negócio

### [2026-10-21] Django Admin do desenvolvimento sem usuário com acesso
- O seed cria `dono@giro.example` com 2 etapas, mas com `is_staff` desligado, e por isso ninguém entra em `http://localhost:8000/admin/`. Hoje o acesso se libera à mão no banco de desenvolvimento; ajustar o seed é uma tarefa possível, ainda não pedida.

### [2026-10-21] Assistente de implantação incompleto
- A casca do assistente (T-335) está pronta, e 3 dos 8 passos funcionam: Marca, Ramo e Importar. Primeira filial, Tabela de preços, Modelo de contrato, Recebimentos e Convidar equipe mostram "Esta etapa ainda não está disponível aqui." e não têm contrato nem tarefa. Se entram no MVP é decisão pendente do dono.

### [2026-10-20] Sem tarefas na tela de Veículos por enquanto [SUBSTITUÍDA por 2026-10-29 "Fase 2 aberta sem atividade iniciada"]
- O dono pediu: "não quero nenhuma tarefa por agora de alterar ou corrigir a Veiculos-Desktop e mobile". Não abrir tarefa nessas telas até ele liberar.

### [2026-10-20] Cancelar a assinatura ativa no dia do vencimento sem pagar (T-195) [SUBSTITUÍDA por 2026-10-21 "Cancelar a ativa com o período pago já vencido"]
- Ponto em aberto, com recomendação pedida ao Produto: A, o acesso termina na hora (padrão); B, o acesso vai até o fim do período, se pago. [A CONFIRMAR] O PR da T-195 espera a revisão de Segurança T-199 antes do merge.

### [2026-10-20] Máquina de desenvolvimento com pouca memória
- O sistema chegou a matar jobs em segundo plano; só o `giro-frontend-1` usa cerca de 2,7 GB. Rodar conferências uma por vez.

### [2026-10-20] Time de agentes
- Oito agentes no Maestri, cada um no próprio worktree: backend, frontend, qa, design-system, arquiteto, produto, devops e seguranca, além do orquestrador na cópia principal. Fluxo de entrega: o agente entrega na branch, o orquestrador confere em ambiente próprio, abre o PR, acerta o quadro na branch e mescla com o aval do dono.
