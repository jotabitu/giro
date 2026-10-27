# Contas: acesso, usuários, sessões e suporte

**Dono:** arquiteto · **Versão:** 21 out 2026 (T-346, reconfirmar as 2 etapas, ADR 0032); 16 out 2026 (T-287, `pode.veiculos = ver` para vendedor e financeiro e Veículos no menu dos dois); 15 out 2026 (T-249, copiar link do convite e `acoes` do usuário; T-201, nome curto da filial; T-036) · **App:** `contas` (schema da empresa; o mesmo app atende a plataforma, ver `plataforma.md`) · **Regras:** USR-01 a USR-07, PLT-03, PLT-06, PLT-07, AUD-01, S-15 · **ADRs:** 0008, 0013, 0014, 0032 · **Telas:** Login, Acesso-Senha, Convite, Admin-Usuarios (e "Esqueci a senha" e "Ativar verificação em 2 etapas", da T-026) · **Critérios:** `docs/qa/criterios/T-248.md` (CA-248-12 a 16)

Convenções gerais em `docs/api/README.md`. Modelo: `contas.Usuario`, `Convite`, `Sessao`, `filiais.UsuarioFilial` em `docs/decisoes/modelo-de-dados.md`. Base: `<subdominio>.<dominio>/api/`.

## Tokens e sessão (resumo das ADRs 0013 e 0014)

| Token | Onde vai | Vida | Serve para |
| --- | --- | --- | --- |
| access | corpo da resposta; só em memória no frontend | 5 min | toda a API, com `Authorization: Bearer` |
| refresh | cookie `__Host-giro_refresh` (`HttpOnly`, `Secure`, `SameSite=Strict`, host-only, `Path=/`) | até o fim da sessão | `auth/renovar/` e `auth/sair/`, com o cabeçalho `X-Requested-With: giro` |
| `pre_2fa` | corpo | 5 min | só `auth/2fa/configurar/` e `auth/2fa/verificar/` |
| `suporte` | fragmento da URL de entrada | até o fim do acesso | ver "Modo suporte" |

- Todo token leva `schema`, `empresa_id` e `amr`; access e refresh levam também `sid` (sessão).
- Sessão: 12 h sem uso no desktop, 30 dias no celular (`USR-06`), contados do último uso. O frontend informa o tipo no login (`aparelho`).
- 401 com `codigo`: `nao_autenticado` (sem token, vencido ou de outra empresa), `sessao_encerrada` (sessão revogada ou expirada), `2fa_obrigatorio` (token sem `otp` de quem precisa de 2 etapas). Em qualquer 401 depois de um `renovar` que falhou, o frontend vai para o login.

## Quem precisa de 2 etapas (USR-02)

`exige_2fa` é calculado pela API: perfis `administrador` e `financeiro`; todos, se o administrador ligou "exigir para todos" em `ConfiguracaoEmpresa`; e quem ativou por conta própria. O frontend não decide; ele segue a `etapa` que a API devolve.

## Permissões calculadas (`pode`)

`GET /api/auth/eu/` devolve `pode` com o resultado da tabela de perfis das regras mais as permissões extras (`USR-03`). O frontend usa só isso para montar menu e botões (`USR-05`: sem permissão o item não aparece).

| Chave | Valores | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- | --- |
| `painel` | `todas_filiais`, `filial`, `proprios`, `nao` | `todas_filiais` | `filial` | `proprios` | `nao` | `todas_filiais` |
| `veiculos` | `editar`, `km_e_avarias`, `ver`, `nao` | `editar` | `editar` | `ver` | `km_e_avarias` | `ver` |
| `clientes_cadastrar` | bool | sim | sim | sim | — | — |
| `locacoes_criar` | bool | sim | sim | sim | — | — |
| `vistorias_fazer` | bool | sim | sim | sim | sim | — |
| `locacoes_cancelar` | `sim`, `aprova`, `pede`, `nao` | `sim` | `aprova` | `pede` | `nao` | `nao` |
| `desconto_acima_limite` | `sim`, `aprova`, `pede`, `nao` | `sim` | `aprova` | `pede` | `nao` | `nao` |
| `vendas_criar` | bool | sim | sim | sim | — | — |
| `caixa_receber` | bool | sim | sim | sim | — | sim |
| `caixa_abrir_fechar` | bool | sim | sim | sim (sua filial) | — | sim |
| `despesas_lancar` | `todas`, `manutencao`, `nao` | `todas` | `todas` | `todas` | `manutencao` | `todas` |
| `despesas_aprovar` | bool | sim | sim | — | — | — |
| `despesas_exportar` | bool | sim | — | — | — | sim |
| `financeiro_pagar` | bool | sim | — | — | — | sim |
| `lancamento_avulso` | bool | sim | sim | — | — | sim |
| `os_abrir` | bool | sim | sim | — | sim | — |
| `movimentacoes` | `gerir`, `levar`, `nao` | `gerir` | `gerir` | `levar` | `levar` | `nao` |
| `administracao` | bool | sim | — | — | — | — |

`movimentacoes` (T-286, `MOV-02`): `gerir` cria, agenda, inicia, cancela e cria local de apoio (administrador e gerente, pelo escopo de filial); `levar` só registra as chegadas das movimentações que a pessoa leva; `nao`, nada. Detalhes em `movimentacoes.md`.

`lancamento_avulso` (T-162) é a linha "Lançamento avulso em contas a receber (multa, avaria, outro), cancelar, renegociar, estornar" da tabela de perfis (T-232) e de `financeiro.md` ("Quem pode"): o botão "Novo lançamento" de contas a receber e o `POST /api/financeiro/contas-receber/` seguem a mesma lista. A permissão extra `cancelar_contrato` não muda essa chave.

Permissões extras (`USR-03`) somam e nunca tiram: `aprovar_desconto` muda `desconto_acima_limite` para `aprova`; `cancelar_contrato` muda `locacoes_cancelar` para `aprova`; `relatorios_todas_filiais` muda `painel` para `todas_filiais`. Quem pediu não aprova o próprio pedido (`APR-09`); isso é checado no pedido, não aqui.

---

## Login

### POST /api/auth/entrar/
Público.
Corpo: `{ email, senha, aparelho: "desktop" | "celular" }`. Não existe "manter conectado" (`USR-06`).
200, quando não precisa de 2 etapas: `{ "etapa": "pronto", "access": "<jwt>", "usuario": { ...igual a eu... } }` e o cookie do refresh.
200, quando precisa: `{ "etapa": "verificar_2fa", "token_pre_2fa": "<jwt>" }` (tem autenticador) ou `{ "etapa": "configurar_2fa", "token_pre_2fa": "<jwt>" }` (precisa de 2 etapas e ainda não tem).
401 `{ "codigo": "credenciais_invalidas", "mensagem": "E-mail ou senha incorretos" }`.
429 `{ "codigo": "USR-06", "mensagem": "Acesso bloqueado por 15 minutos depois de 5 tentativas erradas", "detalhes": { "tentar_de_novo_em": "..." } }`. A 5ª tentativa errada (senha ou código, somados) bloqueia, grava evento `seguranca` e avisa os administradores.
429 `muitas_requisicoes` (formato em `README.md`): mesmos limites do `entrar` da plataforma, 10 por minuto e 50 por hora por IP e por e-mail, com `comum.limites` (T-058). Os demais endpoints de `auth/` têm 30 por minuto por IP.
403 `{ "codigo": "usuario_inativo", "mensagem": "Seu acesso foi desativado. Fale com o administrador." }`; `convite_pendente` recebe `{ "codigo": "convite_pendente", "mensagem": "Use o link do convite para criar seu acesso" }`.
Regras: USR-02, USR-06.

### POST /api/auth/2fa/verificar/
`Authorization: Bearer <token_pre_2fa>`. Corpo: `{ codigo }` (6 dígitos) **ou** `{ codigo_recuperacao }`.
200: `{ "etapa": "pronto", "access": "...", "usuario": { ... } }` e cookie. Quando o autenticador acabou de ser configurado, vem também `"codigos_recuperacao": [8 códigos]`, mostrados só esta vez.
401 `{ "codigo": "codigo_invalido", "mensagem": "Código incorreto. Confira o horário do celular e tente de novo." }`; 429 `USR-06`.

### POST /api/auth/2fa/configurar/
`Authorization: Bearer <token_pre_2fa>`, ou access de quem quer ativar por conta própria.
200: `{ "otpauth_uri": "otpauth://totp/<Empresa>:<email>?secret=<...>&issuer=<Empresa>", "chave": "JBSW Y3DP EHPK 3PXP" }`. O `issuer` é o nome da locadora (white label), nunca "Giro". `chave` é para "Sem câmera? Digite a chave". Chamar de novo troca a chave enquanto não for confirmada.
A confirmação é o `2fa/verificar/` (com `pre_2fa`) ou, para quem já está logado, `POST /api/auth/2fa/ativar/` `{ codigo }` → 200 `{ "codigos_recuperacao": [...] }`.

### POST /api/auth/2fa/desativar/
Access com `otp`. Corpo: `{ senha }`. 204. 422 `{ "codigo": "USR-02", "mensagem": "Seu perfil exige a verificação em 2 etapas" }` para quem `exige_2fa` por perfil ou configuração.

### POST /api/auth/2fa/codigos-recuperacao/
Access com `otp`. Corpo: `{ senha }`. 200: `{ "codigos_recuperacao": [8 novos] }`; os antigos deixam de valer.

### POST /api/auth/2fa/reconfirmar/ (reconfirmar as 2 etapas, T-346)

Para as ações que pedem 2 etapas recentes (403 `2fa_recente`): cancelar a assinatura (`cancelamento.md`, `PLT-06`) e, na fase 2, o backup completo (`auditoria.md`, `S-15`). Confirma o código sem sair do sistema e devolve um access com `auth_time` novo. ADR 0032.

Access de qualquer usuário. Token de suporte: 403 `PLT-07`, como as outras rotas da própria conta. Corpo: `{ codigo }` (6 dígitos) **ou** `{ codigo_recuperacao }`, nunca os dois, como em `2fa/verificar/`.

200, com `Cache-Control: no-store`:
```json
{ "access": "<jwt>" }
```

- **O token:** é só um access novo, com o mesmo `sid`, `schema`, `empresa_id` e `amr` do token que chamou (`["pwd", "otp"]` para quem tem autenticador) e `auth_time` = agora. A vida é a de qualquer access (5 min). **Não abre sessão, não emite refresh e não grava cookie:** a sessão e o refresh vigente continuam os mesmos, e um `renovar` de outra aba não é afetado.
- **Quanto vale:** `dois_fatores_recente` aceita esse access por 15 minutos a partir do `auth_time`, enquanto ele não vencer. O `renovar` continua sem levar o `auth_time` (T-345), então o access renovado volta a responder `2fa_recente`. A tela repete o pedido logo depois de reconfirmar (abaixo) e não guarda o access para usar mais tarde.
- **Bloqueio:** o mesmo do login, pela mesma função (`dois_fatores.verificar_codigo`, com a linha do usuário travada). Código errado conta como tentativa errada da `USR-06` (5 erros somando senhas e códigos bloqueiam por 15 minutos, gravam `usuario.bloqueado` e avisam os administradores). Durante o bloqueio, responde 429 `USR-06` antes de olhar o código, mesmo com o código certo. A contagem é a do login: o bloqueio também vale para o próximo `auth/entrar/`. O acerto zera a contagem. A sessão aberta continua nos dois casos.
- **Código de recuperação:** aceito e gasto, como no login: o mesmo código não serve de novo, e `codigos_recuperacao_restantes` do `eu` cai 1.
- **Sem autenticador:** 409 `{ "codigo": "2fa_inativo", "mensagem": "Ative a verificação em 2 etapas primeiro." }`, antes de contar tentativa. Essa pessoa continua recebendo `2fa_recente` nas ações sensíveis até ativar. Hoje ninguém chega a esse caso nas ações sensíveis: elas são do administrador, e a `USR-02` obriga o administrador a ter 2 etapas.
- **Auditoria** (categoria `seguranca`, regra `USR-02`, objeto o próprio usuário, **sem o código**):
  - `usuario.reconfirmar_2fa`, "Confirmou o código do autenticador";
  - `usuario.reconfirmar_2fa_falhou`, "Errou o código do autenticador", com o motivo `código` ou `código de recuperação`;
  - também, quando for o caso, os eventos que já existem: `usuario.usar_codigo_recuperacao` e `usuario.bloqueado`.
- **Limite:** o das rotas de `auth/` (30 por minuto por IP), além do bloqueio.

| Status | `codigo` | Quando |
| --- | --- | --- |
| 400 | `validacao` | sem código, com os dois campos, `codigo` fora de 6 dígitos, ou código errado. O erro vem no campo enviado: `{ "campos": { "codigo": ["Código incorreto. Confira o horário do celular e tente de novo."] } }`. Não é 401, para o cliente HTTP não tentar renovar a sessão |
| 403 | `PLT-07` | token de suporte |
| 409 | `2fa_inativo` | quem não tem autenticador |
| 429 | `USR-06` | bloqueado, ou esta tentativa atingiu o limite; `detalhes.tentar_de_novo_em` |

Testes: `test_usr_02_reconfirmar_devolve_access_na_mesma_sessao`, `test_usr_02_reconfirmar_libera_o_cancelamento`, `test_usr_06_reconfirmar_conta_tentativas_e_bloqueia`, `test_usr_02_reconfirmar_com_codigo_de_recuperacao`, `test_usr_02_reconfirmar_sem_autenticador`, `test_plt_07_reconfirmar_recusa_suporte` e `test_usr_02_reconfirmar_evento_sem_o_codigo` (ver "O que muda para as tarefas (T-346)").

#### Como a tela trata o 403 `2fa_recente`

1. A tela manda a ação normalmente. Ela não pergunta antes se as 2 etapas estão recentes, porque quem decide é a API.
2. No 403 `2fa_recente`, abre um diálogo:
   - o texto do diálogo é a `mensagem` do 403 ("Confirme o código do autenticador para cancelar a assinatura.");
   - o campo de 6 dígitos usa as mesmas palavras da etapa do código no `Login`;
   - o link "Usar um código de recuperação" troca o campo, como no login.
   - O que a pessoa já preencheu na tela fica como está. Nada recarrega.
3. "Confirmar" chama `POST /api/auth/2fa/reconfirmar/`. No 200, troca o access da sessão em memória (`definirAccess`) e **repete o mesmo pedido uma vez**, com o mesmo corpo.
4. Se a repetição voltar 403 `2fa_recente` de novo, mostra a mensagem e não repete outra vez (sem laço).
5. Os erros da reconfirmação:
   - 400: mostra o erro no campo, e o diálogo fica aberto;
   - 429: mostra a `mensagem` com o horário de `tentar_de_novo_em` e fecha o diálogo, sem a ação;
   - 409 `2fa_inativo`: mostra a `mensagem`.
6. "Cancelar" fecha o diálogo sem enviar nada.
7. O código não fica no estado depois do envio, nem no cache do TanStack Query, nem em log.
8. Um 401 na reconfirmação segue o caminho de sempre do cliente HTTP (renovar e, se falhar, ir para o login).

### POST /api/auth/renovar/
Sem corpo; cookie + `X-Requested-With: giro`. 200: `{ "access": "..." }` e cookie novo (rotação). 401 `sessao_encerrada` ou `nao_autenticado`.

### POST /api/auth/sair/
Sem corpo; cookie + `X-Requested-With: giro`. 204. Revoga a sessão (`motivo_revogacao = saiu`) e apaga o cookie.

### GET /api/auth/eu/
Qualquer usuário (e token de suporte, ver abaixo).
200:
```json
{
  "id": 2, "nome": "Rodrigo Pinheiro", "email": "rodrigo@motorapida.com.br", "celular": "85998124410",
  "perfil": "gerente", "permissoes_extras": ["aprovar_desconto"],
  "filiais": [ { "id": 1, "nome": "Filial Centro", "nome_curto": "Centro" } ],
  "dois_fatores": { "ativo": true, "obrigatorio": false, "codigos_recuperacao_restantes": 8 },
  "pode": { "painel": "filial", "veiculos": "editar", "...": "..." },
  "suporte": null,
  "empresa": { "nome_exibicao": "Moto Rápida", "status": "em_teste", "somente_leitura": false }
}
```
`filiais[].nome_curto` é o nome a mostrar nas listas curtas (`FIL-01`, T-201): o nome curto da filial, ou o nome quando ela não tem; vale também na lista e no detalhe de Usuários ("Centro" nas filiais da pessoa em `Admin-Usuarios`, CA-FIL-01). Vem de `resumo_das_filiais` (`filiais.md`, "Nome a mostrar").

Marca (nome, logo e cores) vem de `GET /api/marca/` (`empresas.md`), pública, a mesma antes e depois do login. `empresa.nome_exibicao` daqui é o mesmo nome de lá.

#### Menu e início (USR-05, USR-08, T-047)

`GET /api/auth/eu/` também devolve a navegação pronta. O frontend não decide o que mostrar a partir de `pode`; ele desenha o que vem aqui e mapeia cada `chave` para a rota e o ícone dele.

```json
"navegacao": {
  "inicio": { "rota": "/inicio", "variante": "gerente" },
  "menu_inicio": [
    { "grupo": null, "itens": [
        { "chave": "inicio", "rotulo": "Visão da filial", "contador": null },
        { "chave": "aprovacoes", "rotulo": "Aprovações", "contador": "aprovacoes" },
        { "chave": "veiculos", "rotulo": "Veículos", "contador": "veiculos" } ] },
    { "grupo": "Operação", "itens": [
        { "chave": "locacoes", "rotulo": "Locações", "contador": "locacoes" },
        { "chave": "clientes", "rotulo": "Clientes", "contador": null } ] },
    { "grupo": "Filial", "itens": [ { "chave": "caixa", "rotulo": "Caixa da filial", "contador": null } ] }
  ],
  "menu_completo": [ { "grupo": null, "itens": [ "..." ] }, { "grupo": "Operação", "itens": [ "..." ] } ],
  "barra_celular": ["inicio", "veiculos", "nova_locacao", "locacoes", "mais"]
}
```

- `inicio.variante` (`USR-08`): `implantacao` (administrador antes da 1ª locação ou venda, `IMP-01`), `geral` (administrador depois), `gerente`, `vendedor`, `vistoriador`, `financeiro`. A rota é sempre `/inicio`; o conteúdo vem de `GET /api/painel/inicio/` (`docs/api/painel.md`). No modo suporte, a variante é a do administrador.
- `menu_inicio` é o menu do perfil: vale no início e nas telas próprias do perfil, que são as rotas que os itens dele abrem (comparando só o caminho, sem a query, e incluindo as sub-rotas). `menu_completo` vale nas demais rotas (`USR-05`, T-141). Itens sem permissão **não vêm**; nunca vêm desabilitados.
- `contador` é a chave em `GET /api/painel/contadores/`, ou `null` quando o item não tem contador.
- `barra_celular`: os cinco destinos da barra inferior, já filtrados (`nova_locacao` só para quem cria locação).
- Um item só aparece quando valem as três condições: a permissão da pessoa (tabela abaixo), o recurso ligado na empresa (`plataforma.selectors.recursos_da_empresa()`: os `recursos` do plano menos o que o ramo não pede, `PLT-12`, ADR 0024) e a atividade da empresa (`ConfiguracaoEmpresa.atividade`: aluga, vende ou os dois). Além disso, a API esconde os módulos ainda não entregues (configuração `GIRO_MODULOS_ATIVOS` do backend, global), para o menu nunca levar a uma tela que não existe. Item escondido pelo plano tem a rota recusada com 403 `PLT-12` (`plataforma.md`, "Módulos por plano"); item escondido por `GIRO_MODULOS_ATIVOS` não tem tela.

Itens do `menu_completo`, na ordem:

| Grupo | `chave` | Rótulo | Aparece para quem | Recurso do plano | Atividade |
| --- | --- | --- | --- | --- | --- |
| — | `inicio` | o do início do perfil: Visão geral (administrador), Visão da filial (gerente), Início (vendedor e financeiro) | todos menos o vistoriador | — | — |
| — | `aprovacoes` | Aprovações | quem decide pedidos (gerente, administrador, permissões extras) | — | — |
| — | `veiculos` | Veículos | `pode.veiculos` ≠ `nao` | — | — |
| Operação | `locacoes` | Locações | `locacoes_criar` (o vistoriador não lista locações, `locacoes.md`; chega à vistoria pela agenda) | `locacoes_vistoria` | aluga |
| Operação | `vendas` | Vendas | `vendas_criar` | `vendas_comissoes` | vende |
| Operação | `clientes` | Clientes | `clientes_cadastrar` ou `caixa_receber` | — | — |
| Operação | `manutencoes` | Manutenções | `os_abrir` | `manutencao_despesas` | — |
| Operação | `movimentacoes` | Movimentações | `pode.movimentacoes` = `gerir`; para `levar`, só com uma movimentação `agendada`, `em_transito` ou `no_local` que a pessoa leva (contador: quantas) | — | — |
| Financeiro | `caixa` | Caixa do dia | `caixa_receber` ou `caixa_abrir_fechar` | `contas_receber` | — |
| Financeiro | `receber` | Contas a receber | `caixa_receber` | `contas_receber` | — |
| Financeiro | `despesas` | Despesas | `despesas_lancar` ≠ `nao` | `manutencao_despesas` | — |
| Financeiro | `reembolsos` | Reembolsos | administrador, gerente e financeiro, os perfis de `reembolsos/` em `financeiro.md` (T-358) | `locacoes_vistoria` | aluga |
| Financeiro | `pendencias_pagamento` | Pendências do pagamento | `financeiro_pagar` (administrador e financeiro, T-358) | `recebimento_parceiro` | — |
| Financeiro | `comissoes` | Comissões | `financeiro_pagar` | `vendas_comissoes` | — |
| Financeiro | `conciliacao` | Conciliação | `financeiro_pagar` | `conciliacao` | — |
| Financeiro | `relatorios` | Relatórios | `painel` é `todas_filiais` ou `filial` | `relatorios` | — |
| Administração | `config`, `marca`, `filiais`, `usuarios`, `assinatura`, `auditoria` | como na tela | `administracao` | — | — |

Os `menu_inicio` de cada variante seguem as telas `Gerente`, `Vendedor`, `Vistoriador` e `Financeiro`, com os mesmos filtros (T-071):

| Variante | Grupos e itens, na ordem |
| --- | --- |
| `gerente` | — `inicio` ("Visão da filial"), `aprovacoes`, `veiculos` · Operação: `locacoes`, `vendas`, `clientes`, `manutencoes`, `movimentacoes` · Filial: `caixa` ("Caixa da filial"), `relatorios` |
| `vendedor` | — `inicio` ("Início") · Operação: `locacoes`, `veiculos`, `clientes`, `movimentacoes` · Vendas: `propostas`, `minhas_vendas`, `veiculos_a_venda`, `minhas_comissoes` |
| `vistoriador` | — `agenda`, `consultar_veiculo`, `avarias`, `movimentacoes` |
| `financeiro` | — `inicio` ("Início"), `receber`, `contas_a_pagar`, `caixa_e_bancos`, `veiculos`, `comissoes` |

- Itens próprios do início: `agenda` e `avarias` pedem `vistorias_fazer`, o recurso `locacoes_vistoria` e a atividade aluga. `consultar_veiculo` pede `pode.veiculos` ≠ `nao`. Os quatro do vendedor pedem `vendas_criar`, o recurso `vendas_comissoes` e a atividade vende. `contas_a_pagar` pede `financeiro_pagar` e o recurso `manutencao_despesas`. `caixa_e_bancos` pede `caixa_abrir_fechar` e o recurso `contas_receber`.
- `movimentacoes` (T-314) nos menus do perfil, com o mesmo filtro do `menu_completo`: no gerente, sempre (`gerir`); no vendedor e no vistoriador (`levar`), só enquanto houver uma movimentação aberta que a pessoa leva, com o contador (`MOV-02`). No fim da Operação do gerente e do vendedor e no fim do menu do vistoriador: as telas `Gerente`, `Vendedor` e `Vistoriador` não têm o item, e o fim do grupo não desloca nada do que elas mostram. O financeiro (`nao`) não tem o item.
- `despesas` só traz `contador` para quem aprova despesas (`despesas_aprovar`); para quem só lança, `contador: null`, como em `painel.md`.
- `barra_celular`: `inicio` e `mais` sempre; `veiculos` quando `veiculos` ou `consultar_veiculo` está no `menu_completo`; `locacoes` quando o item está no `menu_completo`; `nova_locacao` quando `locacoes` está e a pessoa tem `locacoes_criar`.
- Exemplo do Essencial (CA-ASS-22): administrador de empresa que aluga e vende vê Início, Aprovações, Veículos, Locações, Clientes, Caixa do dia, Contas a receber e a Administração; não vê Vendas, Manutenções, Despesas, Comissões, Conciliação nem Relatórios.
- `GIRO_MODULOS_ATIVOS` lista os apps entregues (vale para todas as empresas; o que é de cada empresa são os recursos). Item e app: `aprovacoes` → `aprovacoes`; `veiculos` e `consultar_veiculo` → `veiculos`; `locacoes` → `locacoes`; `vendas`, `comissoes` e os do vendedor → `vendas`; `clientes` → `clientes`; `manutencoes` → `manutencao`; `caixa`, `receber`, `despesas`, `conciliacao`, `contas_a_pagar` e `caixa_e_bancos` → `financeiro`; `relatorios` → `relatorios`; `agenda` e `avarias` → `vistorias`; `config` → `configuracoes` (chave própria, T-181); `marca` → `empresas`; `filiais` → `filiais`; `usuarios` → `contas`; `assinatura` → `plataforma`; `auditoria` → `auditoria`; `movimentacoes` → `movimentacoes` (entra na lista com as telas da T-289, para o menu não levar a uma tela que não existe). `inicio` vem sempre. O padrão é o de `config/settings/base.py` (hoje `aprovacoes,clientes,configuracoes,contas,contratos,filiais,financeiro,locacoes,plataforma,veiculos,vistorias`); `empresas` entra com a T-153 e a T-154.
- Enquanto `ConfiguracaoEmpresa.atividade` não existe, a atividade conta como os dois (aluga e vende).
- A variante `implantacao` vale até o passo `primeira_locacao` da implantação (`IMP-01`). As variantes `geral` e `implantacao` usam o `menu_completo`. Na variante `vistoriador`, o `menu_completo` é igual ao `menu_inicio` (`agenda`, `consultar_veiculo`, `avarias` e, quando leva, `movimentacoes`): o vistoriador tem um menu só (`USR-05`, T-141). Itens próprios do início: `agenda` ("Vistorias de hoje"), `avarias` ("Avarias abertas") e `consultar_veiculo` (vistoriador); `propostas`, `minhas_vendas`, `veiculos_a_venda` e `minhas_comissoes` (vendedor, fase 2); `contas_a_pagar` e `caixa_e_bancos` (financeiro).

### PATCH /api/auth/eu/
Corpo: `{ nome?, celular? }`. E-mail e perfil não mudam por aqui. 200: igual ao `GET`.

### Senha

**POST /api/auth/senha/trocar/** · access com `otp` quando exigido · `{ senha_atual, senha_nova }` → 204. As outras sessões da pessoa são encerradas; a atual continua.
**POST /api/auth/senha/esqueci/** · público · `{ email }` → 202 sempre, exista ou não o e-mail (não revela quem tem conta). Envia o link `https://<subdominio>.<dominio>/entrar/redefinir#<token>`, com validade de 1 hora e uso único. A página lê o fragmento, apaga-o da barra de endereço (`history.replaceState`) e guarda o token só em memória, como em `/suporte/entrar#<token>`. O fragmento não vai ao servidor nem ao proxy, então o token não cai em log de acesso nem no Sentry (P-09 da T-057, T-072). Limite: 3 pedidos por e-mail por hora.
**POST /api/auth/senha/redefinir/** · público · `{ token, senha_nova }` → 204 (o token vai no corpo, nunca na URL). Encerra todas as sessões da pessoa. 410 `{ "codigo": "link_expirado", "mensagem": "Este link venceu. Peça outro." }`. Não desliga as 2 etapas: quem tem autenticador continua precisando do código.

Validação de senha (400 `validacao`, campo `senha_nova` ou `senha`): 12 caracteres ou mais, com letras e números, diferente do e-mail e do nome da empresa, fora da lista de senhas comuns do Django (tela `Acesso-Senha`). A resposta de cada validador vem como texto pronto.

---

## Sessões (ADR 0014)

### GET /api/auth/sessoes/
Qualquer usuário. As sessões ativas da própria pessoa.
200: `{ "resultados": [ { "id": 41, "tipo": "desktop", "aparelho": "Chrome no Windows", "ip": "177.12.34.0/24", "criada_em": "...", "ultimo_uso": "...", "atual": true } ] }`. O IP sai mascarado (/24).

### POST /api/auth/sessoes/{id}/encerrar/
204. Revoga (`revogada_pelo_usuario`); o access daquela sessão para de valer na requisição seguinte.

### POST /api/auth/sessoes/encerrar-outras/
204. Revoga todas menos a atual.

---

## Primeiro acesso e convite (USR-01)

O link do e-mail ou WhatsApp abre `https://<subdominio>.<dominio>/convite#<token>` no frontend. A página lê o fragmento, apaga-o da barra de endereço (`history.replaceState`) e guarda o token só em memória, como em `/suporte/entrar#<token>`. O fragmento não vai ao servidor nem ao proxy, então o token não cai em log de acesso nem no Sentry (P-09 da T-057, T-072). A API recebe o token sempre no corpo, nunca no caminho nem na query. O administrador da compra (etapa 4 da implantação, tela `Acesso-Senha`) usa o mesmo fluxo: `criar_empresa` cria o convite dele.

### POST /api/convites/consultar/
Público. Corpo: `{ token }`. Não muda nada: só lê o convite para a tela (pode ser chamado de novo).
200:
```json
{ "empresa": "Moto Rápida", "email": "rodrigo@motorapida.com.br", "nome": "Rodrigo Pinheiro",
  "perfil": "gerente", "filiais": [ { "id": 1, "nome": "Filial Centro" } ],
  "convidado_por": "Mariana Costa", "expira_em": "2026-10-14T23:59:59Z",
  "exige_2fa": false }
```
404 `nao_encontrado` (token que não existe ou já usado). 410 `{ "codigo": "convite_expirado", "mensagem": "Este convite venceu. Peça um novo ao administrador." }`.

### POST /api/convites/aceitar/
Público. Corpo: `{ token, nome, senha, aparelho }` (`nome` pode corrigir o que veio no convite).
200: igual ao `auth/entrar/`: `etapa: "pronto"` com tokens, ou `etapa: "configurar_2fa"` com `token_pre_2fa` quando o perfil exige 2 etapas. O usuário vira `ativo` no `pronto` ou na confirmação do código.
Para o administrador da compra, `pronto` marca o passo `conta` da implantação (`registrar_passo_implantacao`).
400 `validacao` (senha); 404 `nao_encontrado`; 410 `convite_expirado`.

Os dois endpoints têm o limite de 30 por minuto por IP (429 `muitas_requisicoes`, `README.md`).

---

## Usuários (Administração)

Perfil: administrador (`pode.administracao`). Desativados nunca são apagados.

### GET /api/usuarios/
Query: `?situacao=ativos|convites|desativados`, `?perfil=`, `?filial=<id>`, `?busca=` (nome, e-mail).
200:
```json
{
  "plano": { "usado": 5, "limite": 10, "aviso": false, "bloqueado": false },
  "contagens": { "todos": 6, "ativos": 3, "convites": 2, "desativados": 1 },
  "resultados": [
    { "id": 2, "nome": "Rodrigo Pinheiro", "email": "rodrigo@motorapida.com.br", "celular": null,
      "perfil": "gerente", "filiais": [ { "id": 1, "nome": "Filial Centro", "nome_curto": "Centro" } ], "todas_filiais": false,
      "status": "ativo", "dois_fatores_ativo": true,
      "ultimo_acesso_em": "2026-10-07T10:12:00Z", "convite_expira_em": null, "eu": false,
      "acoes": { "reenviar_convite": false, "copiar_link_convite": false, "cancelar_convite": false } }
  ],
  "proximo": null, "anterior": null
}
```
`plano` é o item `usuarios` de `GET /api/assinatura/`; conta `ativo` e `convite_pendente`. Administrador tem `todas_filiais: true`.

`acoes` (T-249): os três botões do convite no painel da pessoa, `true` só com o usuário `convite_pendente` (vencido ou não) e pedido pelo administrador com token próprio; com token de suporte (`PLT-07`), todos `false`. A tela mostra "Reenviar convite", "Copiar link do convite" e "Cancelar convite" por eles, sem regra de status na tela. Os outros botões do painel continuam como estão.

### GET /api/usuarios/{id}/
200: o item da lista mais:
```json
{ "permissoes_extras": [
    { "chave": "aprovar_desconto", "marcada": true, "padrao_do_perfil": true },
    { "chave": "cancelar_contrato", "marcada": false, "padrao_do_perfil": false },
    { "chave": "relatorios_todas_filiais", "marcada": false, "padrao_do_perfil": false } ],
  "entrou_em": "2026-10-07T09:20:00Z" }
```
`padrao_do_perfil: true` = o perfil já dá isso; a tela mostra marcado e travado ("Padrão do perfil Gerente").

### POST /api/usuarios/convites/
Corpo: `{ email, nome?, celular?, perfil, filiais: [ids], permissoes_extras: [] }`.
`email` é obrigatório (é o login, `USR-06`); `celular` é opcional. O convite sai sempre por e-mail e, quando há celular, também por WhatsApp (`USR-01`, decisão do produto na T-037). `filiais` obrigatório (ao menos 1) para quem não é administrador; ignorado para administrador.
201: o usuário (status `convite_pendente`). O convite vale 7 dias e sai depois do commit, com a marca da locadora.
409 `{ "codigo": "email_em_uso", "mensagem": "Já existe um usuário com este e-mail" }`.
422 `PLT-03` (limite de usuários).
Regras: USR-01, PLT-03.

### POST /api/usuarios/{id}/reenviar-convite/
Só `convite_pendente`. Sem corpo. Reenvia pelos mesmos canais. 200: usuário com `convite_expira_em` novo (mais 7 dias); o link anterior deixa de valer. 409 `{ "codigo": "transicao_usuario" }` em outro status.

### POST /api/usuarios/{id}/link-convite/ (copiar link do convite)

Só o administrador, com token próprio (`USR-01`, decisão do dono de 15 out 2026, T-248; CA-248-12 a 16). Sem corpo. Gera um link novo de convite e o devolve **uma vez**, para a tela copiar e o administrador mandar por outro canal.

200, com `Cache-Control: no-store`:
```json
{ "link": "https://motorapida.girolocadoras.com.br/convite#<token>",
  "expira_em": "2026-10-16T23:59:59Z",
  "aviso": "O link anterior deixa de valer.",
  "usuario": { ...item da lista, com convite_expira_em novo... } }
```

- **O que faz** (`contas.services.gerar_link_convite(usuario, por)`, numa transação, com o usuário travado): invalida todo `Convite` ainda válido da pessoa (o do e-mail, o do reenvio e os links copiados antes), cria um `Convite` novo de 7 dias a partir de agora e devolve o token em claro, que só existe nesta resposta (o banco guarda o hash, ADR 0014). É a mesma função interna do reenviar, sem o envio: `reenviar-convite/` passa a ser `gerar_link_convite` + e-mail e WhatsApp. Por isso o reenvio invalida o link copiado, e o link copiado invalida o do reenvio (CA-248-13).
- **Não envia nada:** nem e-mail nem WhatsApp (CA-248-12). O link tem o mesmo formato do e-mail, com o token no fragmento (`#`), e abre o mesmo fluxo de `consultar/` e `aceitar/`.
- **Não muda o status nem o plano:** a pessoa continua `convite_pendente`, e a contagem do plano não muda (o convite já contava). Funciona com o convite vencido (CA-248-14: em 15 out, o link novo vence em 22 out).
- **Status:** só `convite_pendente`; `ativo` e `desativado`: 409 `{ "codigo": "transicao_usuario", "mensagem": "Só dá para copiar o link de um convite pendente." }` (CA-248-15).
- **Quem:** administrador (`pode.administracao`); outro perfil, 403 `permissao`; token de suporte, 403 `PLT-07`, com qualquer permissão de acesso (é rota de escrita em `usuarios`, abaixo em "Modo suporte").
- **Limite** (`comum.limites`, número do arquiteto pedido na T-248): **5 por hora por pessoa convidada** e **20 por hora por administrador**, o que vier primeiro. Acima, 429 `muitas_requisicoes` (`README.md`) e nenhum link é gerado, nem o anterior é invalidado (o limite é conferido antes da transação). O de 5 cobre quem erra o canal algumas vezes; mais que isso é sinal de link vazando, e o reenvio por e-mail continua disponível. O de 20 cobre a implantação, em que o administrador convida a equipe de uma vez (o Profissional tem até 10 usuários).
- **Auditoria** (`USR-01`, `AUD-01`): evento `usuario.copiar_link_convite`, categoria `seguranca`, objeto o usuário convidado, ator quem copiou, com `convite_expira_em` novo; **sem o link nem o token** (o `Convite` já tem `token_hash` omitido, ADR 0014). Texto pronto: "Copiou o link do convite". O link também não vai para log: a view não registra o corpo da resposta, e o Sentry já roda com `send_default_pii=False` (`config/settings/base.py`) e não manda corpo de resposta; a T-252 confere.
- **Não volta depois:** `GET /api/usuarios/{id}/` nunca traz o link nem o token; para ter outro, copia de novo (CA-248-16).
- Testes com o código: `test_usr_01_copiar_link_invalida_o_anterior` (CA-248-12 e 13), `test_usr_01_copiar_link_convite_vencido` (CA-248-14), `test_usr_01_copiar_link_so_administrador` (CA-248-15, perfis, suporte e status), `test_usr_01_copiar_link_limite_por_hora` (CA-248-15, 429) e `test_usr_01_copiar_link_evento_sem_token` (CA-248-16).

### POST /api/usuarios/{id}/cancelar-convite/
Só `convite_pendente`. 200: usuário `desativado`; sai da contagem do plano.

### PATCH /api/usuarios/{id}/
Corpo: `{ perfil?, filiais?, permissoes_extras? }`. 200: detalhe.
Mudar o perfil para um que exige 2 etapas faz o próximo uso dos tokens sem `otp` da pessoa responder `2fa_obrigatorio` (ADR 0013).
422 `{ "codigo": "ultimo_administrador", "mensagem": "A empresa precisa de ao menos um administrador ativo" }` ao tirar o perfil do último administrador.
Auditoria: `usuario.alterar_perfil`, `usuario.alterar_filiais`, `usuario.alterar_permissoes` (categoria `seguranca`).

### POST /api/usuarios/{id}/desativar/
Corpo: `{ motivo? }`. 200: usuário `desativado`. Na mesma transação revoga todas as sessões (`usuario_desativado`); a pessoa sai na requisição seguinte. Sai do limite do plano. O histórico continua (`USR-04`).
422 `ultimo_administrador`; 422 `{ "codigo": "desativar_a_si_mesmo", "mensagem": "Peça a outro administrador para desativar seu acesso" }`.

### POST /api/usuarios/{id}/reativar/
Só para `desativado` (409 `transicao_usuario` nos outros). Reativar depende de a pessoa já ter chegado a `ativo` (`USR-04`):
- quem já foi `ativo` volta `ativo`, sem convite;
- quem nunca chegou a `ativo` (convite cancelado, mesmo com a senha já criada) volta para `convite_pendente`, com convite novo de 7 dias pelos mesmos canais (`USR-01`). A senha anterior e os links antigos deixam de valer: o link novo cria a senha.

200: o usuário, como em `GET /api/usuarios/{id}/` (`status` `ativo` ou `convite_pendente`, com `convite_expira_em`). Nos dois casos volta a contar no plano: 422 `PLT-03` se o plano estiver no limite, e nesse caso a pessoa continua `desativado` e nenhum convite sai. Auditoria `seguranca`: `usuario.reativar` ou `usuario.reativar_convite`.

### POST /api/usuarios/{id}/redefinir-2fa/
Corpo: `{ motivo }`. 200. Apaga o autenticador e os códigos de recuperação da pessoa e encerra as sessões dela; no próximo login ela configura de novo. Para quem perdeu o celular e os códigos. Auditoria `seguranca`.

### GET /api/usuarios/{id}/sessoes/ · POST /api/usuarios/{id}/sessoes/{sid}/encerrar/
Iguais aos de `auth/sessoes/`, para o administrador ver e encerrar as sessões de qualquer usuário (`revogada_pelo_administrador`).

---

## Modo suporte (PLT-07, ADR 0013)

A plataforma abre o acesso (`plataforma.md`) e manda o navegador para `https://<subdominio>.<dominio>/suporte/entrar#<token>`. A página lê o fragmento, apaga-o da barra de endereço e guarda o token em memória.

- Com o token de suporte, `GET /api/auth/eu/` devolve `perfil: "administrador"`, `filiais` = todas, `pode` de administrador (ou só as chaves de leitura, quando `ver`) e:
  ```json
  "suporte": { "acesso_suporte_id": 31, "nome": "Diego Santos", "permissao": "ver", "fim": "2026-10-07T15:30:00Z", "motivo": "Chamado #1042" }
  ```
  O frontend mostra a faixa "Modo suporte" sempre que `suporte` não for `null`.
- Mesmo com `ver_editar`, o suporte nunca recebe CPF, CNH e documentos completos (`AUD-09`): os endpoints com dados pessoais devolvem a representação resumida para o token de suporte.
- Não há refresh: no `fim` qualquer requisição responde 401 `PLT-07`, e o frontend mostra "O acesso de suporte terminou".
- Com `permissao = "ver"`, rota não liberada para leitura do suporte responde 403 `{ "codigo": "PLT-07", "mensagem": "No modo só ver você não pode fazer isto" }`.
- Token de suporte em `auth/entrar`, `renovar`, `sessoes`, `usuarios` (escrita, inclusive `link-convite/`, T-249) ou `convites` → 403 `PLT-07`.

#### Página de entrada e faixa no frontend (fase 1, T-358; telas `Modo-Suporte`, T-360)

No MVP, o link vem do Django Admin (`plataforma.md`, "Abrir o acesso de suporte pelo Django Admin").

1. **Página `/suporte/entrar`** (rota pública, fora da casca da empresa). Ela:
   - lê o token do fragmento e apaga o fragmento com `history.replaceState` antes de qualquer chamada;
   - guarda o token só em memória, como o access: nunca em `localStorage`, `sessionStorage`, cookie nem estado persistido do TanStack Query;
   - chama `GET /api/auth/eu/` com ele;
   - com 200 e `suporte` preenchido, entra no início (`navegacao.inicio.rota`);
   - sem fragmento, com 401 `PLT-07` ou com 401 de outra empresa, mostra "O acesso de suporte terminou" e nenhum botão de login: o suporte não tem login na empresa.
   O mesmo navegador pode ter a sessão de uma pessoa da empresa em outra aba. O token de suporte vale só na aba que abriu o link e não toca no cookie de refresh.
2. **Cliente HTTP com o token de suporte:** um 401 **não** tenta `auth/renovar/`, porque não há refresh. Qualquer 401 `PLT-07` leva à mesma mensagem e apaga o token da memória. O 403 `PLT-07` mostra a `mensagem` da API no lugar da ação, sem sair do modo suporte.
3. **Faixa** no topo de todas as telas da casca enquanto `eu.suporte` não for `null`. Ela é fixa, não fecha e usa a cor de aviso do design system. O conteúdo vem de `eu.suporte`, com os textos prontos que este contrato acrescenta:
   ```json
   "suporte": { "acesso_suporte_id": 31, "nome": "Diego Santos", "permissao": "ver", "fim": "2026-10-07T15:30:00Z",
                "motivo": "Chamado #1042", "permissao_rotulo": "Só ver", "fim_rotulo": "Expira às 15:30" }
   ```
   - `permissao_rotulo` é "Só ver" ou "Ver e editar".
   - `fim_rotulo` traz a hora em `America/Sao_Paulo`.
   - A tela mostra "Modo suporte", o nome, "Equipe Giro", o motivo, `permissao_rotulo`, `fim_rotulo` e o botão "Sair do suporte".
   - O "restam 42 min" da tela de referência não entra no MVP: a tela não calcula tempo, e o fim vale pelo 401.
4. **"Sair do suporte"** chama `POST /api/auth/suporte/sair/` (204), apaga o token e mostra "Você saiu do modo suporte". Se a resposta for 401, mostra a mesma mensagem.
5. **Menu e telas:** com o token de suporte, o frontend esconde do menu e das Configurações o que a API já não manda. Por exemplo, os cartões `auditoria`, `exportar`, `ramo` e `suporte` não vêm. A tela não decide nada pelo modo suporte além da faixa e do 401.

Testes do frontend (vitest):
- o fragmento é apagado antes da chamada, e o token não vai para nenhum armazenamento;
- o 401 `PLT-07` não chama `renovar`;
- a faixa aparece com os rótulos;
- "Sair do suporte" chama a rota e limpa a memória.

Teste do backend: `test_plt_07_eu_traz_rotulos_do_suporte`.

### POST /api/auth/suporte/sair/
Token de suporte. 204. O `AcessoSuporte` vai para `encerrado`; evento nas duas auditorias.

### Controle do administrador

Implementados no app `plataforma`, servidos no host da empresa. Perfil: administrador.

**GET /api/suporte/** → `{ "bloqueado": false, "acessos": [ { "id": 31, "nome": "Diego Santos", "motivo": "...", "permissao": "ver", "inicio": "...", "fim": "...", "status": "ativo" } ] }` (últimos 90 dias).
**POST /api/suporte/bloquear/** e **POST /api/suporte/liberar/** · `{ motivo? }` → 200 `{ "bloqueado": true|false }`. Bloquear revoga na hora os acessos `ativo` (status `revogado`).
**POST /api/suporte/acessos/{id}/revogar/** → 200; status `revogado`.

#### Tela `Admin-Suporte` (`/admin/suporte`, fase 1, T-358; tela da T-360)

O `GET /api/suporte/` ganha o que a tela mostra, sem mudar o que já existe:
```json
{ "bloqueado": false,
  "situacao_rotulo": "Acesso do suporte liberado",
  "contagens": { "todos": 3, "ativos": 1, "encerrados": 2 },
  "acessos": [ { "id": 31, "nome": "Diego Santos", "motivo": "Chamado #1042", "permissao": "ver",
                 "permissao_rotulo": "Só ver", "inicio": "2026-10-07T14:30:00Z", "fim": "2026-10-07T15:30:00Z",
                 "status": "ativo", "status_rotulo": "Ativo agora", "acoes": { "revogar": true } } ] }
```

- **Filtros:** `?situacao=todos|ativos|encerrados` (padrão `todos`). `encerrados` junta `encerrado` e `revogado`. As contagens não dependem do filtro.
- **Rótulos:**
  - `status_rotulo`: "Ativo agora", "Encerrado" ou "Revogado".
  - `situacao_rotulo`: "Acesso do suporte liberado" ou "Acesso do suporte bloqueado".
- **`acoes.revogar`:** `true` só no `ativo`.
- **E-mail do operador:** a tela de referência mostra, mas **não vem**. O e-mail da equipe Giro não é dado da empresa, e o nome basta.
- **Botões:** "Bloquear suporte Giro" (com `bloqueado: false`) e "Liberar suporte Giro" (com `true`) chamam `bloquear/` e `liberar/`, com motivo opcional. A tela avisa antes de bloquear: "Revoga na hora qualquer acesso ativo".
- **Os três blocos de explicação** da tela (dados protegidos, tempo limitado, auditoria) são texto fixo da tela. A tela troca "Cada clique, tela vista" por "Cada alteração": a auditoria registra as ações, não as telas vistas (`AUD-01`).
- **Quem:** administrador. Token de suporte, 403 `PLT-07`. Auditoria: `suporte.bloquear`, `suporte.liberar` e `suporte.revogar` (já existem).
- Testes: `test_plt_07_controle_do_suporte_contagens_e_filtro` e `test_plt_07_controle_do_suporte_sem_email_do_operador`.

---

## Interface interna para os outros apps

| Função | Uso |
| --- | --- |
| `contas.selectors.pode(usuario, chave)` | o mesmo cálculo de `eu.pode`. `comum` não importa `contas` (ADR 0011): `contas` registra esta função em `comum.permissoes` no `AppConfig.ready()`, e `filiais` registra `filiais_do_usuario` do mesmo jeito. |
| `contas.selectors.administradores()` | destinatários dos avisos ao administrador (`USR-06`, `PLT-03`). |
| `contas.services.convidar(...)` | usado por `plataforma.criar_empresa` para o administrador da compra. |

**Filiais do usuário.** `UsuarioFilial` é do app `filiais`, que fica abaixo de `contas` na ordem da ADR 0011. Por isso `contas` não grava o vínculo: o serviço publica `contas.filiais_do_usuario_definidas(usuario_id, filial_ids)` e o assinante em `filiais/eventos.py` grava, na mesma transação. Filial inexistente ou inativa faz o assinante levantar `ErroDeRegra` → 422 `{ "codigo": "filial_invalida" }` e nada é gravado. Para montar as respostas (`filiais: [{id, nome}]`), `contas` usa a função `filiais_do_usuario` que o app `filiais` registra em `comum.permissoes`, sem importar `filiais`.

## O que muda para as tarefas (T-249)

- **T-250 (backend):** `gerar_link_convite` em `contas.services`, usada pelo `reenviar-convite/` e pela rota nova `POST /api/usuarios/{id}/link-convite/`; os dois limites em `comum.limites`; o evento `usuario.copiar_link_convite` e o texto; `acoes` nos itens de `GET /api/usuarios/` e no detalhe. Testes `test_usr_01_copiar_link_*` acima (o backlog chama dois deles; os outros três cobrem o vencido, o limite e o evento). OpenAPI regenerado.
- **T-251 (frontend):** "Copiar link do convite" por `acoes.copiar_link_convite`, com o `aviso` da resposta antes de copiar e o link copiado para a área de transferência; o link não fica guardado no estado da tela depois de copiado, nem em cache do TanStack Query (a mutação não grava o link em nenhuma consulta). CA-248-12 a 16.
- **T-252 (segurança):** a rota, o limite, o evento sem token e a tela.

## O que muda para as tarefas (T-346)

- **Backend:** a rota `POST /api/auth/2fa/reconfirmar/` (view `Logada`, serializer do `2fa/verificar/`). Uma função em `comum.autenticacao` emite o access reconfirmado a partir das claims do token atual, com `auth_time`, sem refresh e sem sessão nova. A docstring de `CLAIM_AUTH_TIME` passa a citar o login e a reconfirmação. Os dois eventos e os textos em `auditoria.textos`. Os testes acima, mais um que confere que o `renovar` depois da reconfirmação continua sem `auth_time`. OpenAPI regenerado.
- **Frontend:** o diálogo de "Como a tela trata o 403 `2fa_recente`", num ponto só, reaproveitável pelo backup completo da fase 2, usado na `Admin-Cancelar` (T-198) no "Cancelar assinatura".
