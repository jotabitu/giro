# Plataforma

**Dono:** arquiteto · **Versão:** 08 out 2026 (T-055; T-030) · **App:** `plataforma` (+ `contas` no schema `public`, ADR 0008) · **Regras:** PLT-01, PLT-03, PLT-04, PLT-07, PLT-08, PLT-09, IMP-05 · **Telas:** Plat-Login, Plat-Empresas, Plat-Empresa-Detalhe, Plat-Planos, Plat-Equipe, Admin-Assinatura

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (itens 1 a 5 e apoio do public).

## Fases

| Fase | O que entra | Tarefa |
| --- | --- | --- |
| 1 (MVP) | login da equipe com 2 etapas, `eu`, convite da equipe por comando, leitura de planos e empresas, serviço `criar_empresa` (chamado pelo Django Admin), uso do plano visto pela empresa e a checagem de limite usada pelos outros apps | T-010 |
| 2 | criar empresa pela tela, estender teste, mudar plano, suspender, editar planos, equipe interna pela tela, entrar como suporte, faturas e cobrança | a definir |

Os endpoints da fase 2 já estão descritos para o frontend planejar as telas; o backend só os implementa quando a tarefa existir. Endpoint de fase 2 chamado antes disso responde 404.

## Funções e permissões (PLT-09)

A API devolve em `eu.pode` o que a pessoa pode fazer; o frontend usa isso para mostrar ou esconder menu e botões (`USR-05`), sem repetir a tabela abaixo.

| Permissão (`pode.*`) | Dono | Suporte | Financeiro | Sucesso |
| --- | --- | --- | --- | --- |
| `ver_empresas` | sim | sim | sim | sim |
| `entrar_como_suporte` | sim | sim | — | sim |
| `estender_teste_e_mudar_plano` | sim | — | — | sim |
| `cobranca_e_faturas` | sim | — | sim | — |
| `suspender_empresa` | sim | — | sim | — |
| `planos_e_precos` | sim | — | — | — |
| `equipe_interna` | sim | — | — | — |

Sem a permissão: 403 `{ "codigo": "PLT-09", "mensagem": "Sua função não permite esta ação" }`.

---

## Autenticação da equipe (fase 1)

Base: `admin.<dominio>/api/plataforma/auth/`. 2 etapas obrigatórias para todos (`PLT-08`). Fluxo, claims e cookie na ADR 0013.

**Tokens.** O access vai no corpo e fica só em memória no frontend. O refresh vai no cookie `__Host-giro_refresh` (`HttpOnly`, `Secure`, `SameSite=Strict`, host-only, `Path=/`) e nunca aparece no corpo. `renovar` e `sair` exigem o cabeçalho `X-Requested-With: giro`. Todo token leva `schema`, `empresa_id`, `sid` (sessão, ADR 0014) e `amr`; aqui é sempre `amr: ["pwd", "otp"]`. Sessão encerrada ou revogada responde 401 `{ "codigo": "sessao_encerrada" }` já na requisição seguinte.

### POST /api/plataforma/auth/entrar/
Público.
Corpo: `{ email, senha, codigo }` (6 dígitos do autenticador) **ou** `{ email, senha, codigo_recuperacao }` ("Perdi o acesso ao autenticador"). A tela manda os três campos juntos; o backend faz as duas etapas na mesma chamada.
200 (e o cookie do refresh):
```json
{
  "access": "<jwt>",
  "usuario": { "id": 1, "nome": "Você", "email": "dono@girolocadoras.com.br", "funcao": "dono",
               "pode": { "ver_empresas": true, "entrar_como_suporte": true, "...": true } }
}
```
200 `{ "etapa": "configurar_2fa", "token_pre_2fa": "<jwt, 5 min>" }`: senha certa, mas a pessoa ainda não tem autenticador (ex.: dono criado por comando). O frontend segue para `2fa/configurar/`.
400 `validacao`: `email` ou `senha` faltando.
401 `{ "codigo": "credenciais_invalidas", "mensagem": "E-mail, senha ou código incorretos" }`: a resposta não diz qual dos três errou. Quem tem autenticador e não manda código recebe este 401, com a senha certa ou errada (T-058).
429 `{ "codigo": "PLT-08", "mensagem": "Acesso bloqueado por 15 minutos depois de 3 códigos errados", "detalhes": { "tentar_de_novo_em": "..." } }`: o 3º código errado bloqueia e grava evento de segurança na auditoria do `public`. A 5ª senha errada (ou sem código) também bloqueia, com a mensagem "Acesso bloqueado por 15 minutos depois de 5 senhas erradas". Enquanto o bloqueio vale, nem a senha é conferida.
429 `{ "codigo": "muitas_requisicoes", "mensagem": "Muitas tentativas seguidas. Espere um pouco e tente de novo.", "detalhes": { "tentar_de_novo_em_segundos": 42 } }` e cabeçalho `Retry-After`: limite de requisições, 10 por minuto e 50 por hora por IP e por e-mail. `convites/`, `renovar`, `sair` e `2fa/` têm 30 por minuto por IP. As taxas ficam em `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`; o limite no proxy (S-17) é do devops e soma a este.
403 `{ "codigo": "usuario_inativo" }`: convite pendente ou desativado.
Auditoria: `seguranca`, `usuario.entrar` (sucesso) e `usuario.entrar_falhou` (com IP e aparelho).
Regras: PLT-08.

### POST /api/plataforma/auth/2fa/configurar/
Aceita só `Authorization: Bearer <token_pre_2fa>`.
200: `{ "otpauth_uri": "otpauth://totp/Giro:<email>?secret=<...>&issuer=Giro" }`. O frontend mostra o QR code a partir da URI. Chamar de novo troca o segredo (dispositivo ainda não confirmado).

### POST /api/plataforma/auth/2fa/verificar/
Aceita só `Authorization: Bearer <token_pre_2fa>`. Corpo: `{ codigo }`.
200: igual ao `entrar` (access + cookie), mais `"codigos_recuperacao": ["xxxx-xxxx", "..."]` quando o dispositivo acabou de ser confirmado; os códigos só aparecem esta vez.
401 `credenciais_invalidas`; 429 `PLT-08` (mesma contagem de 3 erros, com a linha do usuário travada: tentativas em paralelo passam uma de cada vez).

### POST /api/plataforma/auth/renovar/
Sem corpo; lê o cookie. 200: `{ access }` e cookie novo (refresh rotativo; o anterior vai para a blacklist). 401 se vencido, na blacklist, de usuário inativo ou de outra empresa (`schema`/`empresa_id`).

### POST /api/plataforma/auth/sair/
Sem corpo; lê o cookie. 204. Põe o refresh na blacklist e apaga o cookie.

### GET /api/plataforma/auth/eu/
Qualquer função. 200: o mesmo `usuario` de `entrar`, mais `{ "dois_fatores_ativo": true, "codigos_recuperacao_restantes": 8 }`.

### Convite da equipe

Fase 1: o primeiro dono e os convites saem pelo comando `python manage.py convidar_equipe_plataforma <email> <funcao>`, que imprime o link. As telas usam os endpoints abaixo desde a fase 1, porque o link do convite abre uma página.

**GET /api/plataforma/convites/{token}/** · público
200: `{ "email": "larissa@girolocadoras.com.br", "nome": "Larissa Melo", "funcao": "suporte", "expira_em": "..." }`
404 `nao_encontrado`; 410 `{ "codigo": "convite_expirado", "mensagem": "Este convite venceu. Peça um novo." }` (7 dias).

**POST /api/plataforma/convites/{token}/aceitar/** · público
Corpo: `{ senha }`. Senha validada pelos validadores do Django.
200: `{ "etapa": "configurar_2fa", "token_pre_2fa": "<jwt, 5 min>" }`. O convite fica usado; a pessoa só vira `ativo` ao confirmar o código em `2fa/verificar/`. Se o token pré-2FA vencer, ela entra por `entrar` com e-mail e senha e recebe outro.

---

## Planos

### GET /api/plataforma/planos/ · fase 1
Funções: todas. Sem paginação (poucos itens).
200:
```json
{ "resultados": [
  { "id": 2, "nome": "Profissional", "ativo": true, "ordem": 2,
    "preco_mensal_centavos": 44900, "meses_cobrados_no_anual": 10, "preco_anual_centavos": 449000,
    "limite_veiculos": 150, "limite_filiais": 3, "limite_usuarios": 10,
    "recursos": ["locacoes_vistoria", "contas_receber", "contrato_digital", "vendas_comissoes", "manutencao_despesas", "relatorios"],
    "empresas_no_plano": 71 }
], "proximo": null, "anterior": null }
```
`limite_*` nulo = ilimitado. `preco_anual_centavos` é calculado pela API.
Valores de `recursos`: `locacoes_vistoria`, `contas_receber`, `contrato_digital`, `vendas_comissoes`, `manutencao_despesas`, `relatorios`, `dominio_proprio`, `api_integracoes`, `suporte_prioritario`.

### POST /api/plataforma/planos/ · PATCH /api/plataforma/planos/{id}/ · POST /api/plataforma/planos/{id}/duplicar/ · fase 2
Função: dono (`planos_e_precos`). Corpo com os campos acima menos os calculados.
Mudar `preco_mensal_centavos` não altera `preco_contratado_centavos` de nenhuma empresa (`PLT-05`); a resposta traz `"empresas_afetadas_por_reajuste": 0`. Reajuste de quem já assina é outra ação (fase 2, com aviso de 30 dias).
Desativar plano (`ativo=false`) tira da página de compra e mantém quem já assina.

### GET /api/plataforma/adicionais/ · fase 2
200: `{ "resultados": [ { "codigo": "filial", "nome": "Filial adicional", "preco_centavos": 7900, "unidade": "mes", "empresas": 14 } ] }`.

---

## Empresas

### GET /api/plataforma/empresas/ · fase 1
Funções: todas (`ver_empresas`).
Query: `?situacao=em_teste|com_problema|saindo|ativa`, `?plano=<id>`, `?status=<enum da empresa>`, `?busca=` (nome, subdomínio, CNPJ), `?ordem=-ultimo_acesso_em|nome|-criado_em`.
200:
```json
{
  "contagens": { "todas": 148, "pagantes": 125, "em_teste": 23, "ativa": 117, "com_problema": 14, "saindo": 2 },
  "resultados": [
    { "id": 12, "nome_exibicao": "Moto Rápida", "subdominio": "motorapida", "cidade": "Fortaleza", "uf": "CE",
      "plano": { "id": 2, "nome": "Profissional" },
      "status": "em_teste",
      "uso": { "veiculos": 86, "limite_veiculos": 150, "filiais": 1, "usuarios": 5 },
      "situacao": { "codigo": "em_teste", "rotulo": "Teste · dia 1", "tom": "info" },
      "ultimo_acesso_em": "2026-10-07T12:12:00Z" }
  ],
  "proximo": "...", "anterior": null
}
```
`situacao` é decidida pela API, na ordem (a primeira que valer):

| `codigo` | Quando | `rotulo` (exemplo) | `tom` | Aba |
| --- | --- | --- | --- | --- |
| `cancelando` | `cancelada` e `acesso_ate` ≥ hoje | "Cancela em 30 out" | `alerta` | saindo |
| `suspensa` | `suspensa` | "Suspensa" | `perigo` | com_problema |
| `fatura_atrasada` | `inadimplente` | "Fatura 12 dias atrasada" | `perigo` | com_problema |
| `implantacao_parada` | em teste e 3 dias ou mais no mesmo passo (`IMP-05`) | "Parada no passo 4" | `alerta` | com_problema |
| `perto_do_limite` | algum uso ≥ 90% do limite (`PLT-03`) | "Perto do limite" | `alerta` | com_problema |
| `em_teste` | `em_teste` | "Teste · dia 1" | `info` | em_teste |
| `pausada` | `pausada` | "Pausada até 07 jan" | `neutro` | — |
| `ativa` | `ativa` | "Ativa" | `sucesso` | ativa |
| `cancelada` | `cancelada` e `acesso_ate` < hoje | "Cancelada" | `neutro` | — |

`uso` e `ultimo_acesso_em` vêm de `UsoEmpresa` (resumo no `public`, ver modelo), sem entrar no schema de cada empresa a cada lista.

### GET /api/plataforma/empresas/{id}/ · fase 1
Funções: todas.
200:
```json
{
  "id": 12, "razao_social": "Moto Rápida Locações Ltda", "nome_exibicao": "Moto Rápida", "cnpj": "12345678000195",
  "subdominio": "motorapida", "endereco_acesso": "motorapida.girolocadoras.com.br", "cidade": "Fortaleza", "uf": "CE",
  "responsavel": { "nome": "Mariana Costa", "email": "mariana@motorapida.com.br", "telefone": "85998124410" },
  "cliente_desde": "2026-10-07",
  "plano": { "id": 2, "nome": "Profissional" }, "ciclo": "mensal", "preco_contratado_centavos": 44900,
  "status": "em_teste", "situacao": { "codigo": "em_teste", "rotulo": "Teste · dia 1", "tom": "info" },
  "teste": { "inicio": "2026-10-07", "fim": "2026-10-21", "dias_restantes": 14 },
  "uso": {
    "veiculos": { "usado": 86, "limite": 150, "aviso": false },
    "filiais":  { "usado": 1,  "limite": 3,   "aviso": false },
    "usuarios": { "usado": 5,  "limite": 10,  "aviso": false }
  },
  "implantacao": {
    "etapa_funil": "precos", "concluidos": 6, "total": 10,
    "passos": [ { "passo": "conta", "rotulo": "Conta e acesso", "concluido_em": "2026-10-07" },
                { "passo": "contrato", "rotulo": "Contrato", "concluido_em": null, "observacao": null },
                { "passo": "equipe", "rotulo": "Equipe", "concluido_em": "2026-10-07", "observacao": "4 convites" } ]
  },
  "locacoes_total": 0,
  "chamados_abertos": 1,
  "suporte_bloqueado": false,
  "faturas_recentes": [ { "codigo": "FAT-0001", "vencimento": "2026-10-22", "valor_centavos": 44900, "status": "aberta", "observacao": "1ª cobrança após o teste" } ],
  "acoes": { "entrar_como_suporte": true, "estender_teste": true, "mudar_plano": true, "suspender": true }
}
```
- `contagens` (conferido na T-055 com a T-010): `em_teste` e `ativa` contam o **status** da empresa; `com_problema` e `saindo` contam a **aba da situação** da tabela acima. Por isso uma empresa em teste com implantação parada conta em `em_teste` e em `com_problema`. `pagantes` = todas menos as `em_teste` (148 = 125 + 23). O filtro `?situacao=` segue a mesma regra de cada chave.
- Na fase 1, `fatura_atrasada` sai com o rótulo "Fatura atrasada", sem os dias, que dependem das faturas (fase 2).
- `implantacao_parada` conta os 3 dias desde que a empresa chegou à etapa atual do funil (`IMP-05`); o rótulo "Parada no passo N" usa o primeiro dos 10 passos ainda aberto.
- `teste.fim` e o vencimento da 1ª fatura seguem `PLT-01`: teste de 07 a 21 out, 1ª fatura vence em 22 out (dia seguinte ao fim). `dias_restantes` = `teste.fim` − hoje (em 07 out: 14).
- `acoes` já combina a função de quem pede com o estado da empresa; o frontend mostra só o que vier `true`.
- Passos da implantação, nesta ordem: `conta`, `marca`, `filial`, `ramo`, `precos`, `contrato`, `recebimentos`, `importar`, `equipe`, `primeira_locacao`. `etapa_funil` é a etapa do funil de `IMP-05` (`conta`, `marca`, `filial`, `precos`, `dados`, `primeira_locacao`, `concluida`): a primeira etapa do funil cujo passo ainda não foi concluído, com `dados` = passo `importar`. Os passos `ramo`, `contrato`, `recebimentos` e `equipe` contam em `concluidos`, mas não movem o funil.
- `faturas_recentes` fica vazio na fase 1 (sem cobrança).
- Na fase 1, `acoes` vem com tudo `false` (as ações são da fase 2) e `chamados_abertos` vem 0 (suporte é da fase 2). O exemplo acima mostra a fase 2.

### GET /api/plataforma/empresas/{id}/atividades/ · fase 2
Últimas atividades da empresa (Plat-Empresa-Detalhe). Lê um resumo dos eventos de auditoria do schema da empresa, só das categorias `configuracoes` e `seguranca` e sem dados pessoais. Pendente de revisão da segurança (T-032) antes de implementar.

### POST /api/plataforma/empresas/ · fase 2 (o serviço é fase 1)
Função: dono. Na fase 1 o Django Admin chama o mesmo serviço, `plataforma.services.criar_empresa`.
Corpo:
```json
{ "razao_social": "...", "nome_exibicao": "...", "cnpj": "...", "subdominio": "motorapida", "cidade": "Fortaleza", "uf": "CE",
  "plano_id": 2, "ciclo": "mensal",
  "administrador": { "nome": "Mariana Costa", "email": "mariana@motorapida.com.br", "celular": "85998124410" } }
```
O serviço, numa transação: cria `Empresa` (`em_teste`, `teste_inicio` = hoje, `teste_fim` = hoje + 14, `preco_contratado_centavos` = preço do plano), `Dominio`, o schema (`migrate_schemas` daquela empresa), `UsoEmpresa`, `ConfiguracaoEmpresa` padrão e o administrador como `Usuario` `convite_pendente` com convite por e-mail (`USR-01`). O e-mail sai depois do commit.
201: o mesmo corpo de `GET /empresas/{id}/`.
409 `{ "codigo": "subdominio_em_uso" }`, `{ "codigo": "cnpj_em_uso" }`.
400 `validacao`: subdomínio só aceita `a-z`, `0-9` e `-`, de 3 a 30 caracteres, e não pode ser reservado (`admin`, `www`, `api`, `app`, `suporte`, `status`).
Regras: PLT-01.

### Ações sobre a empresa · fase 2
Todas `POST /api/plataforma/empresas/{id}/<acao>/`, com `motivo` obrigatório, e respondem 200 com o corpo de `GET /empresas/{id}/`. Transição fora da tabela de estados → 409 `{ "codigo": "transicao_empresa" }`.

| Ação | Função | Corpo | Regra |
| --- | --- | --- | --- |
| `estender-teste` | dono, sucesso | `{ dias, motivo }` | PLT-01 |
| `mudar-plano` | dono, sucesso | `{ plano_id, ciclo, motivo }`. Upgrade vale na hora; downgrade grava `plano_proximo` e vale na próxima fatura. Se o uso não cabe no plano menor: 422 `{ "codigo": "PLT-04", "detalhes": { "veiculos": { "usado": 86, "limite": 30 } } }` | PLT-04 |
| `suspender` | dono, financeiro | `{ motivo }` | tabela de estados |
| `reativar` | dono, financeiro | `{ motivo }` | tabela de estados |

### POST /api/plataforma/empresas/{id}/acessos-suporte/ · fase 2
Função com `entrar_como_suporte`. Corpo: `{ motivo, chamado_id?, duracao_minutos: 15|30|60, permissao: "ver"|"ver_editar" }`.
201: `{ "acesso_suporte_id": 31, "fim": "...", "url_entrada": "https://motorapida.girolocadoras.com.br/suporte/entrar#<token>" }`. O token é do tipo `suporte` (ADR 0013): sem refresh, sem usuário da empresa, vence no `fim` e é conferido no `public` a cada requisição. Vai no fragmento da URL, não na query, para não ficar em log; a página de entrada o guarda em memória e limpa o fragmento. Com permissão `ver`, só as rotas marcadas como "só ver" respondem (sem exportação, URL assinada nem dado pessoal completo).
422 `{ "codigo": "PLT-07", "mensagem": "O administrador da empresa bloqueou o acesso do suporte" }`.
Efeitos: e-mail ao administrador da empresa na hora; evento nas duas auditorias.

---

## Equipe interna · fase 2

`GET /api/plataforma/equipe/` (dono): `{ "resultados": [ { "id", "nome", "email", "funcao", "status", "dois_fatores_ativo", "ultimo_acesso_em", "convite_enviado_em" } ] }`.
`POST /api/plataforma/equipe/convites/` `{ nome, email, funcao }` → 201. `POST /api/plataforma/equipe/{id}/reenviar-convite/`. `PATCH /api/plataforma/equipe/{id}/` `{ funcao }`. `POST /api/plataforma/equipe/{id}/desativar/` (encerra a sessão na hora, ADR 0008). Não é possível desativar ou rebaixar o último dono: 422 `{ "codigo": "ultimo_dono" }`.

---

## Do lado da empresa: assinatura e uso do plano · fase 1

Servido em `<subdominio>.<dominio>/api/` (schema da empresa), implementado em `plataforma/api/` e lido do `public`.

### GET /api/assinatura/
Perfis: todos (cada tela mostra o que precisa; o administrador vê tudo).
200:
```json
{
  "plano": { "nome": "Profissional", "preco_contratado_centavos": 44900, "ciclo": "mensal" },
  "status": "em_teste",
  "teste": { "fim": "2026-10-21", "dias_restantes": 14 },
  "faixa_aviso": null,
  "uso": {
    "veiculos": { "usado": 86, "limite": 150, "aviso": false, "bloqueado": false },
    "filiais":  { "usado": 1,  "limite": 3,   "aviso": false, "bloqueado": false },
    "usuarios": { "usado": 5,  "limite": 10,  "aviso": false, "bloqueado": false }
  },
  "somente_leitura": false
}
```
- `aviso` = uso ≥ 90%; `bloqueado` = uso ≥ 100% (só novos cadastros daquele item, `PLT-03`).
- `faixa_aviso`: texto pronto da faixa do topo quando a empresa está `inadimplente`, `suspensa` ou `pausada`; `null` se não houver.
- `somente_leitura` = empresa `suspensa`, `pausada` ou `cancelada`; todo endpoint de escrita responde 403 `{ "codigo": "empresa_sem_operacao" }` nesse caso.
- Contagem: veículos que não estão `vendido` nem `baixado`; filiais ativas; usuários `ativo` e `convite_pendente` (`USR-01`, `USR-04`).

Caso do seed: Moto Rápida → 86 de 150, 1 de 3, 5 de 10, nenhum `aviso` (`PLT-03`).

---

## Interface interna para os outros apps (não é HTTP)

Os apps da empresa usam só estas funções do `plataforma` (ADR 0011):

| Função | Uso |
| --- | --- |
| `plataforma.selectors.empresa_atual()` | `Empresa` do schema corrente (via `connection.tenant`). |
| `plataforma.selectors.uso_do_plano()` | O mesmo dicionário `uso` de `GET /api/assinatura/`. |
| `plataforma.services.exigir_limite(item)` | `item` ∈ `veiculos`, `filiais`, `usuarios`. Levanta `LimiteDoPlano` → 422 `{ "codigo": "PLT-03", "mensagem": "Seu plano permite até 3 filiais. Para abrir outra, mude de plano.", "detalhes": { "item": "filiais", "usado": 3, "limite": 3 } }`. Chamada pelo serviço de criação de filial, veículo (inclusive importação, `IMP-03`) e convite de usuário, dentro da transação, com `SELECT ... FOR UPDATE` no `UsoEmpresa` para duas criações simultâneas não passarem do limite. |
| `plataforma.services.atualizar_uso(item, delta)` | Mantém `UsoEmpresa` em dia; chamada pelos mesmos serviços ao criar, desativar ou reativar. A tarefa noturna `plataforma.recalcular_uso` corrige qualquer diferença contando de verdade em cada schema. |
| `plataforma.services.registrar_passo_implantacao(passo)` | Marca o passo da implantação e move o funil (`IMP-05`). |
| `plataforma.services.registrar_acesso()` | Atualiza `ultimo_acesso_em` (no máximo 1 escrita a cada 5 min por empresa). |

Ao chegar a 90% de um item, `exigir_limite`/`atualizar_uso` agendam a notificação "limite do plano em 90%" para os administradores (uma vez por item e por mês).
