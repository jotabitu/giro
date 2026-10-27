# T-354 · Contratos e telas da fase 1 sem implementação · arquiteto → orquestrador

**O que foi feito:** conferi o que está pronto, sem alterar nenhum contrato. Comparei a `main` em 626d432 em três frentes:
- as rotas citadas em `docs/api/*.md` com o `docs/api/openapi.yaml`, que o CI compara com o backend a cada PR;
- as telas de `docs/telas/README.md` com as páginas em `frontend/src/app`;
- as rotas do backend com as chamadas do frontend, para achar as telas parciais.

Os scripts de conferência ficaram fora do git. A fase 2 seguiu `MEMORY.md`, `plano.md`, as marcas "fase 2" dos contratos e a tabela "Rotas do menu".

**Resumo:**
- **Backend:** quase toda a fase 1 está pronta. Falta a rota de conectar os recebimentos: o serviço `plataforma.services.conectar_recebimentos` existe, mas não tem rota nem contrato. Sem ela, nenhuma empresa liga Pix e boleto em produção.
- **Frontend:** faltam quatro telas com contrato e backend prontos (Tabelas de preço, Modelos de contrato, Minha conta e segurança, Reembolsos). Faltam também os 5 passos do assistente sem tela e algumas ações dentro de telas que já existem.

Legenda: **pronto** (rotas e tela existem), **parcial** (falta parte), **falta**, **fase 2** (fica de fora pelas decisões do dono).

## 1. Contratos (backend)

| Contrato | Estado | O que falta / observação |
| --- | --- | --- |
| `aprovacoes.md` | pronto | — |
| `assinatura.md` | pronto | NFS-e (`PLT-15`) segue `[bloqueada]` na T-197 (contador e cadastro municipal) |
| `auditoria.md` | pronto | `zip` (backup completo) e backup automático: fase 2 |
| `cancelamento.md` | pronto | — |
| `clientes.md` | pronto | Exportar clientes, LGPD do titular (`exportar-dados`, `anonimizar`) e leitura da CNH-e: fase 2 (contrato e `CLI-11`, padrão fase 2) |
| `configuracoes.md` | pronto | Cartões `integracoes` e `notificacoes`: fase 2 |
| `contas.md` | pronto | — |
| `contratos.md` | pronto | — |
| `empresas.md` | pronto | — |
| `filiais.md` | pronto | — |
| `financeiro.md` | pronto | O webhook do Asaas existe em `urls_publico`, que fica fora do OpenAPI de propósito |
| `importacao.md` | pronto | — |
| `locacoes.md` | pronto | — |
| `movimentacoes.md` | pronto | — |
| `painel.md` | pronto | — |
| `plataforma.md` | **parcial** | **Recebimentos:** `conectar_recebimentos` existe sem rota HTTP e sem contrato. O contrato também não diz que ação marca os passos `precos` e `equipe`: nenhum serviço chama `registrar_passo_implantacao` para eles. Equipe interna, planos editáveis, ações sobre a empresa, adicionais e atividades: fase 2 |
| `veiculos.md` | pronto | Exportar veículos: fase 2. `transferir` saiu (ADR 0028). Lista de vistorias por veículo: "quando a tela pedir" |
| `vistorias.md` | pronto | — |
| Relatórios | **falta** | Não há contrato nem rota. O app `relatorios` só tem os cartões de Configurações, e o módulo está fora de `GIRO_MODULOS_ATIVOS`, por isso o menu o esconde. A fase não está decidida: `plano.md` põe Relatórios fora do núcleo, e os critérios do MVP não o pedem |
| Vendas, Manutenções, Comissões, Conciliação | fase 2 | Apps vazios (`vendas`, `manutencao`), sem contrato; "Rotas do menu" marca fase 2 |

## 2. Telas da empresa (frontend)

| Tela | Rota | Estado | O que falta |
| --- | --- | --- | --- |
| Login, Esqueci a senha, Convite | `/entrar`, `/entrar/esqueci`, `/entrar/redefinir`, `/convite` | pronto | — |
| Ativar 2 etapas | `/entrar` (no login) e `(empresa)/perfil/seguranca` | **parcial** | Só existe no login (`Ativar2fa`). Falta a rota `/perfil/seguranca` |
| Minha conta (perfil, senha, sessões, 2 etapas) | — | **falta** | Nenhuma tela chama `auth/senha/trocar/`, `auth/sessoes/*`, `2fa/ativar/`, `2fa/desativar/` nem `2fa/codigos-recuperacao/`. Só existe tela de referência da ativação (`Ativar-2FA`); "meu perfil" está em "Telas que ainda faltam" do `plano.md` |
| Início (todas as variantes), Dashboard, Menu Mais | `/inicio`, `/mais` | pronto | O item `para_hoje` do financeiro leva a `/financeiro/reembolsos`, que não existe (ver Reembolsos) |
| Aprovações | `/aprovacoes`, `/aprovacoes/[id]` | pronto | — |
| Clientes, Novo cliente, Detalhe do cliente | `/clientes`, `/clientes/novo`, `/clientes/[id]` | **parcial** | O detalhe não chama `bloquear`, `desbloquear`, `inativar` nem `reativar` (`CLI-03`, `CLI-05`). A análise do cadastro já vem dentro do detalhe, então não usar `GET /analise/` não é falta |
| Locações, Nova locação, Detalhe | `/locacoes`, `/locacoes/nova`, `/locacoes/[id]` | pronto | — |
| Vistoria de saída, Devolução | `/locacoes/[id]/vistoria`, `/locacoes/[id]/devolucao` | pronto | — |
| Agenda e avarias do vistoriador | `/vistorias`, `/vistorias/avarias` | pronto | — |
| Caixa do dia | `/financeiro/caixa` | **parcial** | Falta estornar movimento (`POST caixas/{id}/movimentos/{mid}/estornar/`, `FIN`) |
| Contas a receber | `/financeiro/receber` | **parcial** | Falta renegociar (`POST contas-receber/renegociar/`) |
| Despesas | `/financeiro/despesas`, `/financeiro/despesas/[id]` | pronto | — |
| Reembolsos (`DEV-02`) | `/financeiro/reembolsos` | **falta** | O backend existe (`GET reembolsos/`, `POST {id}/feito/`), e o início já leva para lá. Não há tela de referência nem rota |
| Pendências do pagamento (webhook) | — | **falta** | O backend existe (`pendencias-pagamento/`, resolver). Não há tela de referência, rota nem destino definido |
| Configurações | `/admin/configuracoes` | pronto | — |
| Empresa e marca | `/admin/marca` | pronto | Domínio próprio: fase 2 (`PLT-11`) |
| O que a empresa faz | `/admin/ramo` | pronto | — |
| Filiais, Nova filial | `/admin/filiais`, `/admin/filiais/nova`, `/admin/filiais/[id]` | pronto | — |
| Usuários | `/admin/usuarios` | pronto | — |
| Tabelas de preço (`Precos`) | `/admin/precos` | **falta** | O contrato e o backend estão prontos (`veiculos.md` "Categorias e preços"; `locacoes.md` "Planos especiais"; `/api/categorias/*`, `/api/extras/*`, `/api/planos-especiais/*`, `/api/precos/historico/`). O cartão de Configurações já aponta para a rota, que dá 404 |
| Modelos de contrato | `/admin/contratos` | **falta** | O contrato e o backend estão prontos (`contratos.md`, `/api/contratos/modelos*`, `marcadores`). O cartão já aponta para a rota, que dá 404 |
| Assinatura, Cancelar | `/admin/assinatura`, `/admin/assinatura/cancelar` | pronto | — |
| Auditoria, Exportar | `/admin/auditoria`, `/admin/exportar` | pronto | A Auditoria diz "Você pode bloquear o acesso do suporte nas configurações", mas não há onde fazer isso (ver Controle do suporte) |
| Controle do suporte (`PLT-07`) | — | **falta** | O backend existe (`GET /api/suporte/`, bloquear, liberar, revogar). Não há cartão em `configuracoes.md`, tela de referência nem rota |
| Modo suporte (faixa, `/suporte/entrar#token`, Sair) | — | **falta** | O contrato existe (`contas.md`, "Modo suporte"), mas o frontend não tem a página de entrada nem a faixa, e não chama `auth/suporte/sair/`. Depende de como a equipe abre o acesso no MVP, porque as telas `Plat-*` são da fase 2 |
| Assinar contrato (cliente final) | `/assinar` | pronto | — |
| Integrações | `/admin/integracoes` | fase 2 | — |
| Relatórios | `/relatorios` | falta / a decidir | Sem contrato (seção 1). Escondido do menu |
| Vendas, Nova venda, Manutenções, Comissões, Conciliação | — | fase 2 | — |

### Assistente de implantação (`/implantacao/[passo]`)

| Passo | Estado | O que falta |
| --- | --- | --- |
| Marca, Ramo, Importar | pronto | — |
| Primeira filial | falta (tela) | O backend marca o passo (`filiais.services`); falta a tela no assistente |
| Tabela de preços | falta (tela e contrato) | Nenhuma ação marca `precos`; o contrato não diz qual. Depende de a tela `Precos` existir |
| Modelo de contrato | falta (tela) | O backend marca o passo (`contratos.services`); falta a tela no assistente |
| Recebimentos | falta (rota, contrato e tela) | `conectar_recebimentos` sem rota (seção 1). Não entra no Essencial (`PLT-12`) |
| Convidar equipe | falta (tela e contrato) | Nenhuma ação marca `equipe`; o contrato não diz qual |

`MEMORY.md` (21 out) registra que a entrada desses 5 passos no MVP é decisão pendente do dono.

### Compra e painel da plataforma

Todas as telas `Compra-*` e `Plat-*` são da fase 2 (`MEMORY.md`, 14 out 2026). Hoje `/plataforma` é um texto provisório. No backend já existem o login e as 2 etapas da plataforma, os planos (só a lista), as empresas (lista, detalhe e acessos de suporte) e a auditoria.

### Telas de Veículos (só o estado, sem tarefa nova)

| Tela | Rota | Estado |
| --- | --- | --- |
| Frota, Ficha do veículo, Cadastrar veículo, Editar | `/veiculos`, `/veiculos/[id]`, `/veiculos/novo`, `/veiculos/[id]/editar` | pronto, com ações sem botão: nenhuma tela chama `baixar`, `bloquear`, `desbloquear`, `colocar-a-venda`, `voltar-para-frota`, `corrigir-km` nem `documentos/historico/` |
| Movimentações, Nova movimentação, Chegada, Parada | `/veiculos/movimentacoes`, `.../nova`, `.../[id]/chegada`, `.../[id]/parada` | pronto; os locais de apoio não têm inativar nem reativar na tela |

O `docs/telas/README.md` ainda marca as movimentações como "fase 2" e com rota "proposta". Pelo `plano.md`, elas estão no MVP desde 16 out, e o app existe. Isso é uma correção de texto para o design-system quando as telas de Veículos forem liberadas.

## 3. O que precisa de contrato, ADR ou decisão antes do código

1. **Recebimentos (contrato, arquiteto).** Rota para conectar a subconta (`conectar_recebimentos`) e ler o estado dela (`pendente`, aprovada, recusada), com os campos do formulário `Onboarding-Recebimentos`, os erros `parceiro_recusou`, `recebimentos_conectados` e parceiro fora do ar, quem pode, o 403 `PLT-12` do Essencial, o suporte e a auditoria. A ADR 0007 já cobre a integração: não pede ADR nova. **É o item mais importante:** sem ele, o critério do MVP "gerar cobranças e dar baixa" só funciona no caixa.
2. **Passos `precos` e `equipe` (contrato, arquiteto).** Que ação marca cada um. Por exemplo, a primeira categoria com preço vigente e o primeiro convite enviado. Precisa de confirmação do produto se a regra `IMP` não disser.
3. **Controle do suporte e Modo suporte (decisão do dono e contrato).**
   - Onde o administrador bloqueia o suporte: cartão em Configurações ou bloco na Auditoria.
   - Como a equipe abre o acesso no MVP sem o painel da plataforma: pelo Django Admin, que chama o mesmo serviço, ou adiando o suporte para a fase 2.
   - Se o suporte entra no MVP, faltam a faixa e a página de entrada no frontend.
4. **Reembolsos e pendências do pagamento (contrato de tela, arquiteto, e design-system).** A rota de destino e o que cada lista mostra. Hoje não há tela de referência para nenhuma das duas.
5. **Relatórios (decisão do dono, depois contrato).** Fase 1 ou 2. Se for fase 1, falta tudo: contrato, backend e tela.
6. **Minha conta (design-system e contrato de tela).** Desenho de "meu perfil" (dados, senha, sessões, 2 etapas). O contrato da API já existe em `contas.md`.

## 4. Sugestões de tarefa (sem número)

| Agente | Pronto quando | Depende de |
| --- | --- | --- |
| frontend | `/admin/precos` (`Precos`, desktop e celular): categorias com preço vigente e histórico, extras e planos especiais, pelas rotas de `veiculos.md` e `locacoes.md`, com ativar e desativar; o cartão de Configurações abre a tela. Testes vitest | — |
| frontend | `/admin/contratos` (`Contratos-Modelos`): lista, modelos prontos, edição com marcadores, prévia, publicar e arquivar, por `contratos.md`. Testes vitest | — |
| frontend | `/financeiro/caixa`: estornar movimento; `/financeiro/receber`: renegociar, pelos contratos de `financeiro.md` e com `acoes` da API | — |
| frontend | Detalhe do cliente: bloquear, desbloquear, inativar e reativar (com o 422 `cliente_com_pendencia`), por `clientes.md` | — |
| frontend | Assistente: passos Primeira filial e Modelo de contrato, com as rotas que já marcam o passo | decisão do dono sobre os 5 passos |
| arquiteto | Contrato da rota de recebimentos (item 3.1) e da marcação de `precos` e `equipe` (item 3.2) em `plataforma.md` | produto, se a `IMP` não cobrir a marcação |
| backend | Rota de recebimentos e marcação de `precos` e `equipe`, com `test_imp_05_*`, `test_plt_12_*` e OpenAPI | o contrato acima |
| frontend | Assistente: passos Tabela de preços, Recebimentos e Convidar equipe | backend acima, tela `/admin/precos` |
| design-system | Telas de referência de Reembolsos, Pendências do pagamento, Minha conta e Controle do suporte | decisão do item 3.3 para o suporte |
| arquiteto | Contrato de tela de Reembolsos e Pendências do pagamento (destino do início, filtros, ações) | design-system acima |
| frontend | `/financeiro/reembolsos` e pendências do pagamento; `/perfil/seguranca` (senha, sessões, 2 etapas, códigos de recuperação) | as telas e o contrato acima |
| frontend | Modo suporte: `/suporte/entrar#token`, faixa e Sair; controle do suporte no lugar decidido | decisão do item 3.3 |

**Regras cobertas:** nenhuma muda. O levantamento cita `IMP-05`, `PLT-07`, `PLT-12`, `CLI-03`, `CLI-05`, `DEV-02`, `FIN` e `USR-02`.
**O que ficou de fora:**
- Não conferi o conteúdo das telas prontas contra as telas de referência: a conferência foi por rota e por chamada à API.
- Não conferi as telas de Veículos para tarefas, como pedido.
- O lado das regras é a T-353, do produto.

**Próximo passo para quem recebe:** o orquestrador numera as tarefas e leva as três decisões ao dono (os 5 passos do assistente, o suporte no MVP e a fase dos Relatórios). Branch `t-354-fase1-sem-implementacao`, sem PR.
