# Plataforma

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-236, empresa apagada e compra de quem já foi cliente; T-201, andamento do assistente; T-193; T-183; T-055; T-030) · **App:** `plataforma` (+ `contas` no schema `public`, ADR 0008) · **Regras:** PLT-01, PLT-03, PLT-04, PLT-06, PLT-07, PLT-08, PLT-09, PLT-14, PLT-16, AUD-08, IMP-01, IMP-05 · **Telas:** Plat-Login, Plat-Empresas, Plat-Empresa-Detalhe, Plat-Planos, Plat-Equipe, Admin-Assinatura, a moldura do assistente (`Onboarding-*`)

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (itens 1 a 5 e apoio do public).

## Fases

| Fase | O que entra | Tarefa |
| --- | --- | --- |
| 1 (MVP) | login da equipe com 2 etapas, `eu`, convite da equipe por comando, leitura de planos e empresas, serviço `criar_empresa` (chamado pelo Django Admin), uso do plano visto pela empresa e a checagem de limite usada pelos outros apps | T-010 |
| 1 (MVP, decisões de 14 out 2026) | assinatura e cobrança do lado da empresa (`assinatura.md`); faturas de todas as empresas, mudança de ciclo e reativação da `cancelada` pelo Django Admin (seção "Faturas de todas as empresas") | T-184 a T-187 |
| 2 | criar empresa pela tela, estender teste, mudar plano, suspender, editar planos, equipe interna pela tela, entrar como suporte, a tela `Plat-Cobranca` | a definir |

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

Fase 1: o primeiro dono e os convites saem pelo comando `python manage.py convidar_equipe_plataforma <email> <funcao>`, que imprime o link `https://admin.<dominio>/convite#<token>`. As telas usam os endpoints abaixo desde a fase 1, porque o link do convite abre uma página. A página lê o fragmento, apaga-o da barra de endereço (`history.replaceState`) e guarda o token só em memória, como em `/suporte/entrar#<token>`. O fragmento não vai ao servidor nem ao proxy, então o token não cai em log de acesso nem no Sentry (P-09 da T-057, T-072). A API recebe o token sempre no corpo.

**POST /api/plataforma/convites/consultar/** · público
Corpo: `{ token }`. Só lê o convite para a tela.
200: `{ "email": "larissa@girolocadoras.com.br", "nome": "Larissa Melo", "funcao": "suporte", "expira_em": "..." }`
404 `nao_encontrado`; 410 `{ "codigo": "convite_expirado", "mensagem": "Este convite venceu. Peça um novo." }` (7 dias).

**POST /api/plataforma/convites/aceitar/** · público
Corpo: `{ token, senha }`. Senha validada pelos validadores do Django.
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
    "recursos": ["locacoes_vistoria", "contas_receber", "contrato_digital", "vendas_comissoes", "manutencao_despesas", "conciliacao", "relatorios", "recebimento_parceiro", "cobranca_whatsapp"],
    "empresas_no_plano": 71 }
], "proximo": null, "anterior": null }
```
`limite_*` nulo = ilimitado. `preco_anual_centavos` é calculado pela API.
Valores de `recursos` (ADR 0024, `PLT-12`): `locacoes_vistoria`, `contas_receber`, `contrato_digital`, `vendas_comissoes`, `manutencao_despesas`, `conciliacao`, `relatorios`, `recebimento_parceiro`, `cobranca_whatsapp`, `suporte_prioritario`. Saíram `dominio_proprio` e `api_integracoes` (`PLT-11`: não existem; voltam com uma ADR quando existirem). Os três planos (migração de dados da T-196):

| Plano | `recursos` |
| --- | --- |
| Essencial | `locacoes_vistoria`, `contas_receber`, `contrato_digital` |
| Profissional | os do Essencial, mais `vendas_comissoes`, `manutencao_despesas`, `conciliacao`, `relatorios`, `recebimento_parceiro`, `cobranca_whatsapp` |
| Completo | os do Profissional, mais `suporte_prioritario` |

`recursos` é o que o código liga; os textos de "O que inclui" são o catálogo (`PLT-11`, `itens` em `assinatura.md`). No `PATCH` (fase 2), valor fora da lista: 400 `validacao`.

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
    { "id": 12, "nome_exibicao": "Moto Rápida", "cnpj": "12345678000195", "subdominio": "motorapida", "cidade": "Fortaleza", "uf": "CE",
      "apagada": false, "ja_foi_cliente": false,
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
| `cancelando` | cancelamento marcado: `acesso_ate` preenchido e `status` diferente de `cancelada` (`cancelamento.md`) | "Cancela em 30 out" (dia seguinte a `acesso_ate`) | `alerta` | saindo |
| `suspensa` | `suspensa` | "Suspensa" | `perigo` | com_problema |
| `fatura_atrasada` | `inadimplente` | "Fatura 12 dias atrasada" | `perigo` | com_problema |
| `implantacao_parada` | em teste e 3 dias ou mais no mesmo passo (`IMP-05`) | "Parada no passo 4" | `alerta` | com_problema |
| `perto_do_limite` | algum uso ≥ 90% do limite (`PLT-03`) | "Perto do limite" | `alerta` | com_problema |
| `em_teste` | `em_teste` | "Teste · dia 1" | `info` | em_teste |
| `pausada` | `pausada` | "Pausada até 07 jan" (`pausada_ate`) | `neutro` | — |
| `ativa` | `ativa` | "Ativa" | `sucesso` | ativa |
| `cancelada` | `cancelada` | "Cancelada" ("Dados apagados" com `apagada_em`) | `neutro` | — |

**Empresa apagada** (`AUD-08`, `cancelamento.md`, T-236): `apagada: true`, `nome_exibicao` `null`, `situacao` `cancelada` com o rótulo "Dados apagados", `uso` `null` e `ultimo_acesso_em` `null` (a `UsoEmpresa` saiu). A tela mostra o CNPJ no lugar do nome. `cidade`, `uf` e `subdominio` continuam (o subdomínio fica reservado). `?busca=` acha a apagada pelo CNPJ, enquanto ele existir na linha. `ja_foi_cliente` (`PLT-16`): `true` na empresa criada pela compra de um CNPJ já apagado.

`uso` e `ultimo_acesso_em` vêm de `UsoEmpresa` (resumo no `public`, ver modelo), sem entrar no schema de cada empresa a cada lista.

### GET /api/plataforma/empresas/{id}/ · fase 1
Funções: todas.
200:
```json
{
  "id": 12, "razao_social": "Moto Rápida Locações Ltda", "nome_exibicao": "Moto Rápida", "cnpj": "12345678000195",
  "subdominio": "motorapida", "endereco_acesso": "motorapida.girolocadoras.com.br", "cidade": "Fortaleza", "uf": "CE",
  "responsavel": { "nome": "Mariana Costa", "email": "mariana@motorapida.com.br", "telefone": "85998124410" },
  "cliente_desde": "2026-10-07", "apagada": false, "ja_foi_cliente": null,
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
- `fatura_atrasada` sai com os dias da fatura atrasada mais antiga ("Fatura 12 dias atrasada") quando as faturas existirem (T-184); antes, "Fatura atrasada", sem os dias.
- `implantacao_parada` conta os 3 dias desde que a empresa chegou à etapa atual do funil (`IMP-05`); o rótulo "Parada no passo N" usa o primeiro dos 10 passos ainda aberto.
- `teste.fim` e o vencimento da 1ª fatura seguem `PLT-01`: teste de 07 a 21 out, 1ª fatura vence em 22 out (dia seguinte ao fim). `dias_restantes` = `teste.fim` − hoje (em 07 out: 14).
- **Empresa apagada** (T-236): `razao_social`, `nome_exibicao`, `responsavel` e `implantacao` vêm `null`; `uso` `null`; `cnpj`, plano, ciclo, preço, datas, `cidade` e `uf` continuam; `faturas_recentes` continua (as faturas ficam, com o tomador). `acoes` com tudo `false`.
- `ja_foi_cliente` (`PLT-16`): `null`, ou `{ "empresa_id": 12, "apagada_em": "2027-01-20" }` quando a empresa nasceu da compra de um CNPJ já apagado (`Empresa.empresa_anterior`, a apagada mais recente com o mesmo CNPJ). A tela diz "Já foi cliente" com a data.
- `acoes` já combina a função de quem pede com o estado da empresa; o frontend mostra só o que vier `true`.
- Passos da implantação, nesta ordem: `conta`, `marca`, `filial`, `ramo`, `precos`, `contrato`, `recebimentos`, `importar`, `equipe`, `primeira_locacao`. `etapa_funil` é a etapa do funil de `IMP-05` (`conta`, `marca`, `filial`, `precos`, `dados`, `primeira_locacao`, `concluida`): a primeira etapa do funil cujo passo ainda não foi concluído, com `dados` = passo `importar`. Os passos `ramo`, `contrato`, `recebimentos` e `equipe` contam em `concluidos`, mas não movem o funil.
- `faturas_recentes`: as 5 faturas mais novas da empresa (`FaturaAssinatura`, T-184), da mais nova para a mais antiga; vazio até a T-184.
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
409 `{ "codigo": "subdominio_em_uso" }`; 409 `{ "codigo": "cnpj_em_uso", "mensagem": "Este CNPJ já tem uma assinatura no Giro. Para voltar, fale com a equipe Giro." }`; 409 `{ "codigo": "fatura_anterior_em_atraso", "mensagem": "Há uma fatura em aberto da assinatura anterior. Fale com a equipe Giro para pagar antes de assinar de novo." }` (`PLT-16`, abaixo).

**CNPJ único só entre empresas não apagadas** (achado B-02 da T-230, T-236): a restrição de `Empresa.cnpj` é parcial, `UniqueConstraint(fields=["cnpj"], condition=Q(apagada_em__isnull=True))`, com um índice comum em `cnpj` para achar as apagadas. Uma empresa apagada e uma nova podem ter o mesmo CNPJ; duas não apagadas, não.

**Compra de quem já foi cliente** (`PLT-16`, decisão do dono de 15 out 2026, T-235; CA-ASS-61 e 62). `criar_empresa`, antes de criar, chama `plataforma.selectors.situacao_do_cnpj(cnpj)`, que devolve uma de quatro situações, nesta ordem:

| Situação | Quando | O que a criação faz |
| --- | --- | --- |
| `em_uso` | há `Empresa` com o CNPJ e `apagada_em` nulo, em qualquer estado (inclusive a `cancelada` nos 90 dias) | recusa com 409 `cnpj_em_uso`; a volta da `cancelada` é pela reativação (`assinatura.md`) |
| `fatura_em_atraso` | há empresa apagada com o CNPJ e alguma `FaturaAssinatura` dela `atrasada` | recusa com 409 `fatura_anterior_em_atraso`; paga a fatura pela 2ª via (baixa pelo webhook, `cancelamento.md`), a compra segue |
| `ja_foi_cliente` | há empresa apagada com o CNPJ, sem fatura atrasada | cria a empresa **sem teste** (abaixo) |
| `nova` | nenhuma linha com o CNPJ (ou o CNPJ já saiu da linha apagada, fim do prazo de guarda) | criação de sempre, com teste |

Sem teste (`ja_foi_cliente`):
- `Empresa` nasce `ativa`, com `teste_inicio` e `teste_fim` nulos, `empresa_anterior` = a apagada mais recente com o CNPJ, `dia_vencimento` = dia de hoje, e subdomínio novo (o antigo continua reservado na linha apagada; pedir o mesmo dá 409 `subdominio_em_uso`).
- A 1ª fatura (`mensalidade`, `aberta`, valor do plano) vence hoje e cobre de hoje até a véspera do mesmo dia no mês seguinte (`proximo_periodo`; no anual, 12 meses). CA-ASS-61: compra em 01 mar 2027 → R$ 449,00 vencendo em 01 mar, "Plano Profissional · 01 mar a 31 mar", e as seguintes todo dia 1.
- A empresa nasce sem forma de pagamento (a compra não pede cartão, ADR 0023). Na `Admin-Assinatura`, `acoes.pagar` vem `true` nessa fatura (vence hoje) e o administrador paga com o `meio`, ou escolhe a forma, que vale para a fatura em aberto (`PLT-13`). Sem pagamento, a régua é a da `ativa`: `inadimplente` em D+1 (`assinatura.md`).
- Sem a linha do teste em `faturas/` (empresa que não passou por teste), com `teste` `null` no detalhe da plataforma e no `GET /api/assinatura/`, e sem os avisos da `IMP-06`, que só olham a `em_teste`. O assistente de implantação é o de sempre.
- Auditoria `empresa.criar` com `ja_foi_cliente` e o `empresa_anterior` (só ids; os dados da empresa vão como "alterado" no `public`, `auditoria.md`).

A tela de compra (`Compra-Checkout`, fase 2, sem rota pública ainda) usa o mesmo `situacao_do_cnpj` para avisar ao reconhecer o CNPJ: `ja_foi_cliente` → "Este CNPJ já usou o teste grátis. A 1ª fatura vence hoje."; as duas recusas com as mensagens acima. No MVP, a equipe cria pelo Django Admin, que mostra o mesmo aviso no formulário e as recusas como erro. Testes `test_plt_16_compra_de_novo_sem_teste` (CA-ASS-61) e `test_plt_16_compra_de_novo_recusada` (CA-ASS-62, os dois casos).
400 `validacao`: subdomínio só aceita `a-z`, `0-9` e `-`, de 3 a 30 caracteres, e não pode ser reservado (`admin`, `www`, `api`, `app`, `suporte`, `status`).
Regras: PLT-01.

### Ações sobre a empresa · fase 2
Todas `POST /api/plataforma/empresas/{id}/<acao>/`, com `motivo` obrigatório, e respondem 200 com o corpo de `GET /empresas/{id}/`. Transição fora da tabela de estados → 409 `{ "codigo": "transicao_empresa" }`.

| Ação | Função | Corpo | Regra |
| --- | --- | --- | --- |
| `estender-teste` | dono, sucesso | `{ dias, motivo }` | PLT-01 |
| `mudar-plano` | dono, sucesso | `{ plano_id, ciclo, motivo }`. Upgrade vale na hora; downgrade e mudança de ciclo gravam `plano_proximo` (e `ciclo_proximo`) e valem na próxima fatura (`PLT-04`). Se o uso não cabe no plano menor: 422 `{ "codigo": "PLT-04", "detalhes": { "veiculos": { "usado": 86, "limite": 30 } } }` | PLT-04 |
| `suspender` | dono, financeiro | `{ motivo }` | tabela de estados |
| `reativar` | dono, financeiro | `{ motivo }`. Da `suspensa` → `ativa`; da `cancelada` dentro dos 90 dias, sem fatura atrasada (409 `fatura_em_atraso`), → `ativa` com fatura nova no dia seguinte ao fim do período pago, se ele ainda corre, ou no dia da volta (`plataforma.services.reativar_empresa`, `assinatura.md`, "Mudança de ciclo e reativação pela equipe") | tabela de estados, PLT-06 |

### POST /api/plataforma/empresas/{id}/acessos-suporte/ · fase 2
Função com `entrar_como_suporte`. Corpo: `{ motivo, chamado_id?, duracao_minutos: 15|30|60, permissao: "ver"|"ver_editar" }`.
201: `{ "acesso_suporte_id": 31, "fim": "...", "url_entrada": "https://motorapida.girolocadoras.com.br/suporte/entrar#<token>" }`. O token é do tipo `suporte` (ADR 0013): sem refresh, sem usuário da empresa, vence no `fim` e é conferido no `public` a cada requisição. Vai no fragmento da URL, não na query, para não ficar em log; a página de entrada o guarda em memória e limpa o fragmento. Com permissão `ver`, só as rotas marcadas como "só ver" respondem (sem exportação, URL assinada nem dado pessoal completo).
422 `{ "codigo": "PLT-07", "mensagem": "O administrador da empresa bloqueou o acesso do suporte" }`.
Efeitos: e-mail ao administrador da empresa na hora; evento nas duas auditorias.

### Abrir o acesso de suporte pelo Django Admin · fase 1 (`PLT-07`, T-358)

No MVP, a equipe abre o acesso pelo Django Admin, sem a tela `Plat-Suporte-Acesso` (decisão do dono de 25 out 2026).

- **Onde:** na lista de `Empresa` do Admin, a ação "Entrar como suporte" abre um formulário com:
  - motivo, obrigatório, de preferência o número do chamado;
  - duração: 15, 30 ou 60 minutos;
  - permissão: "Só ver" ou "Ver e editar".
- **O que chama:** `plataforma.services.abrir_acesso_suporte`, o mesmo serviço da rota acima. O operador é o usuário do Admin (`nome` do `AcessoSuporte`). Valem os mesmos efeitos: e-mail ao administrador, evento nas duas auditorias e a recusa `PLT-07` quando a empresa bloqueou o suporte. A recusa aparece como erro no formulário e não cria acesso.
- **O link de entrada** (`url_de_entrada_do_suporte`, com o token no fragmento) aparece **uma vez**, na página de resposta da ação, com `Cache-Control: no-store`. Ali estão o botão "Abrir" (nova aba) e o fim do acesso.
  - O link **não** vai para o framework de mensagens do Django, que pode guardar o texto em cookie ou na sessão.
  - O link não vai para log nem para o histórico do Admin (`LogEntry` só com "Abriu acesso de suporte" e o id).
  - Para ter outro link, abre-se outro acesso.
- **Quem:** só o dono, que é quem entra no Admin (ADR 0029, lista de IPs e 2 etapas).
- Teste: `test_plt_07_admin_abre_suporte_pelo_servico`. O teste confere que o acesso foi criado, que saiu o e-mail, que o link não está na sessão nem em `LogEntry` e que a recusa com a empresa bloqueada não cria acesso.

### Faturas de todas as empresas · Django Admin (fase 1)

Até a `Plat-Cobranca` (fase 2), a equipe Giro vê as faturas de todas as empresas pelo Django Admin (`PLT-14`, U13 das decisões de 14 out 2026). Só leitura, no `public`:

- `FaturaAssinatura`: lista com código, empresa (razão social e CNPJ; na fatura com tomador gravado, o tomador dela, `assinatura.md`, "Tomador da fatura"; da empresa apagada sem tomador, "Dados apagados" e o CNPJ), tipo, período, valor, vencimento, status, forma, pago em, tentativas do cartão e situação da nota; filtros por status, tipo, vencimento, forma e "nota pendente"; busca por código, razão social e CNPJ (também os do tomador); filtro "empresa apagada". Na fatura `atrasada` de empresa apagada, o detalhe mostra o `email_cobranca` da fatura e o link da 2ª via da cobrança, para a equipe cobrar à mão (`AUD-08`, `cancelamento.md`). Sem incluir, editar nem apagar: a baixa vem só do webhook, e fatura paga não se edita (`PLT-14`). Ação "Pedir a nota de novo" nas faturas pagas com a nota em `erro` ou pendente (`PLT-15`, `assinatura.md`).
- `Empresa`: ações "Mudar plano ou ciclo" e "Reativar", com motivo obrigatório, que chamam `mudar_plano` e `reativar_empresa` (os mesmos serviços das ações acima) e gravam a auditoria nos dois lugares com o usuário da equipe.
- Quem entra no Django Admin é só o dono (`is_superuser` no `public`); as funções da `PLT-09` valem nas ações pela tela, na fase 2.

---

## Equipe interna · fase 2

`GET /api/plataforma/equipe/` (dono): `{ "resultados": [ { "id", "nome", "email", "funcao", "status", "dois_fatores_ativo", "ultimo_acesso_em", "convite_enviado_em" } ] }`.
`POST /api/plataforma/equipe/convites/` `{ nome, email, funcao }` → 201. `POST /api/plataforma/equipe/{id}/reenviar-convite/`. `PATCH /api/plataforma/equipe/{id}/` `{ funcao }`. `POST /api/plataforma/equipe/{id}/desativar/` (encerra a sessão na hora, ADR 0008). Não é possível desativar ou rebaixar o último dono: 422 `{ "codigo": "ultimo_dono" }`.

---

## Do lado da empresa: assinatura e uso do plano · fase 1

Servido em `<subdominio>.<dominio>/api/` (schema da empresa), implementado em `plataforma/api/` e lido do `public`.

O resto da tela `Admin-Assinatura` (mudar e comparar planos, forma de pagamento, faturas, dados da nota fiscal, cartão do plano Completo e os campos novos deste `GET`: `teste.inicio`, `proxima_fatura`, `plano_proximo` e os blocos do administrador) está em `docs/api/assinatura.md` (T-183). A ação `mudar-plano` abaixo e a da empresa usam o mesmo serviço `plataforma.services.mudar_plano`.

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
- `somente_leitura` = empresa `suspensa`, `pausada` ou `cancelada`; todo endpoint de escrita responde 403 `{ "codigo": "empresa_sem_operacao" }` nesse caso, fora a lista explícita de exceções (pagar e forma de pagamento na `suspensa`, `assinatura.md`; cancelar na `suspensa` e na `pausada` e voltar da pausa, `cancelamento.md`). A `cancelada` não chega aqui: todo pedido dela recebe 403 `empresa_cancelada` (`cancelamento.md`, `AUD-08`).
- Contagem: veículos que não estão `vendido` nem `baixado`; filiais ativas; usuários `ativo` e `convite_pendente` (`USR-01`, `USR-04`).

Caso do seed: Moto Rápida → 86 de 150, 1 de 3, 5 de 10, nenhum `aviso` (`PLT-03`).

### GET /api/implantacao/ · andamento do assistente (T-201)
Perfis: administrador e token de suporte (só leitura); os demais, 403 `{ "codigo": "permissao" }`. As rotas `/implantacao/*` do frontend são só do administrador. Lido do `public` (`UsoEmpresa.passos_implantacao`) por `plataforma.selectors.andamento_do_assistente(empresa)`, como o `GET /api/assinatura/`. Decisão da T-190 (proposta 9, T-172): a moldura do assistente marca os passos feitos pelo que a API manda, e não por conta própria.

200 (empresa no Profissional com 6 dos 10 passos da implantação, o exemplo da faixa de `Configurações`):
```json
{
  "concluida": false,
  "total": 8,
  "feitos": 5,
  "proximo": "contrato",
  "passos": [
    { "passo": "marca",        "numero": 1, "rotulo": "Empresa e marca",     "feito": true,  "feito_em": "2026-10-07" },
    { "passo": "filial",       "numero": 2, "rotulo": "Primeira filial",     "feito": true,  "feito_em": "2026-10-07" },
    { "passo": "ramo",         "numero": 3, "rotulo": "O que a empresa faz", "feito": true,  "feito_em": "2026-10-07" },
    { "passo": "precos",       "numero": 4, "rotulo": "Tabela de preços",    "feito": true,  "feito_em": "2026-10-07" },
    { "passo": "contrato",     "numero": 5, "rotulo": "Modelo de contrato",  "feito": false, "feito_em": null },
    { "passo": "recebimentos", "numero": 6, "rotulo": "Recebimentos",        "feito": false, "feito_em": null },
    { "passo": "importar",     "numero": 7, "rotulo": "Importar dados",      "feito": false, "feito_em": null },
    { "passo": "equipe",       "numero": 8, "rotulo": "Convidar equipe",     "feito": true,  "feito_em": "2026-10-07" }
  ]
}
```
- **Os passos do assistente** são os 10 passos da implantação (acima, "Passos da implantação") menos `conta` (feito na compra, antes do assistente) e `primeira_locacao` (feita fora dele, na nova locação): 8 passos, nesta ordem, com os rótulos da tela (diferentes dos rótulos do painel da plataforma em `contrato` e `equipe`). No Essencial (sem `recebimento_parceiro`, `PLT-12`), `recebimentos` sai: 7 passos, e `importar` é o 6 ("Passo 6 de 7"). Passo `recebimentos` guardado continua guardado e volta ao subir de plano.
- `numero` e `total` são o "Passo N de M" da tela; a tela acha o próprio passo pela chave e não conta nada. `feito_em` é a data, em `America/Sao_Paulo`, em que o passo foi marcado.
- `feito` vem de `registrar_passo_implantacao` (cada contrato diz qual ação marca o seu passo: `empresas.md` a marca, `filiais.md` a filial, `importacao.md` o importar, e assim por diante). Pular ("Pular por agora", "Cadastrar um por um depois") e "Salvar e sair" **não** marcam passo: o passo continua `feito: false` e o assistente só navega. Não há rota de pular. Isso fecha o ponto que `empresas.md` deixava para "o contrato do assistente".
- `proximo`: o primeiro passo do assistente ainda não feito, na ordem; `null` quando todos estão feitos.
- `concluida` = `IMP-01` (passo `primeira_locacao` marcado). Com `true`, a tela inicial deixa de ser a de implantação (`contas.md`, `inicio.variante`); o assistente continua abrindo para quem quiser terminar um passo.
- Contagens diferentes de propósito: aqui conta o assistente (5 de 8); a faixa de `Configurações` e o painel da plataforma contam os 10 passos da implantação (6 de 10). A tela não mostra os dois lado a lado (T-200).
- O botão "Continuar implantação" da `Configurações` (`configuracoes.md`, `acao`) leva ao `proximo` daqui desde a casca do assistente (T-335): `acao.passo` é o `proximo`, inclusive para passo ainda sem tela (T-340).
- Teste (T-202): `test_imp_05_andamento_do_assistente` (o exemplo acima dá 5 de 8 com `proximo: "contrato"`; no Essencial, 7 passos sem `recebimentos`; pular não marca; vendedor 403; token de suporte 200).

### Quando cada passo conta como feito (`IMP-07`, T-358)

`registrar_passo_implantacao` é idempotente, e o passo feito continua feito: desfazer depois não desmarca. Por exemplo, inativar a categoria ou cancelar o convite (`IMP-07`). Vale tanto no assistente quanto na tela de Configurações que faz a mesma coisa.

| Passo | O que marca | Onde marca | Situação no código |
| --- | --- | --- | --- |
| `marca` | "Continuar" do passo, que grava a marca | `PATCH /api/marca/` (`empresas.md`) | já existe |
| `filial` | a criação da filial matriz | `POST /api/filiais/` (`filiais.md`). A primeira filial nasce sempre matriz | já marca na criação de qualquer filial. Ajustar para marcar só quando a filial nasce matriz. Na prática, dá no mesmo |
| `ramo` | gravar o ramo | `PUT /api/ramo/` (`empresas.md`) | já existe |
| `precos` | a primeira categoria ativa com preço vigente (diária, semanal ou mensal maior que zero), da empresa ou de uma filial (`LOC-01`, `FIL-04`) | `POST /api/categorias/` com `preco`, `POST /api/categorias/{id}/precos/` e `PUT .../precos/{vigente_desde}/` (`veiculos.md`): marca quando o preço gravado já vale hoje (`vigente_desde` ≤ hoje) | **novo**. Se a categoria só tem preço agendado para o futuro, o passo fica aberto até a data. Na data, a primeira leitura de `GET /api/implantacao/` ou de `GET /api/configuracoes/` confere (`veiculos.selectors.tem_preco_vigente()`) e marca. Não há tarefa agendada para isso |
| `contrato` | o primeiro modelo de contrato de locação publicado (`IMP-04`) | `POST /api/contratos/modelos/{id}/publicar/` (`contratos.md`) | já existe |
| `recebimentos` | a subconta **aprovada** pelo parceiro (`FIN-04`), só com `recebimento_parceiro` (`PLT-12`) | transição `pendente → aprovada` da `ContaPagamento` (abaixo, "Recebimentos da empresa") | **muda**: hoje `conectar_recebimentos` marca ao criar a subconta `pendente`. Passa a marcar na transição para `aprovada`, em `atualizar_recebimentos` |
| `importar` | concluir uma importação | `importacao.md` | já existe. "Cadastrar um por um depois" é pular |
| `equipe` | o primeiro convite enviado, mesmo sem aceite (`USR-01`) | `POST /api/usuarios/convites/` (`contas.md`) | **novo**. O convite do administrador da compra (`criar_empresa`) não conta: ele é o passo `conta` |

Testes: `test_imp_07_precos_marca_com_preco_vigente`, `test_imp_07_precos_agendado_marca_na_data`, `test_imp_07_equipe_marca_no_primeiro_convite`, `test_imp_07_recebimentos_so_com_a_subconta_aprovada`, `test_imp_07_filial_marca_na_matriz` e `test_imp_07_desfazer_nao_desmarca`.

### Rotas de cada passo do assistente (T-358)

O assistente (`/implantacao/[passo]`) não tem rotas próprias além do `GET /api/implantacao/`. Cada passo usa as rotas de Configurações, e a tela acha o passo pela chave. Os botões são sempre os mesmos:
- "Pular por agora" só navega para o `proximo`;
- "Continuar" grava pela rota do passo e depois relê `GET /api/implantacao/`;
- "Salvar e sair" grava, se houver o que gravar, e volta ao início.

| Passo (tela) | Lê | Grava | Observação |
| --- | --- | --- | --- |
| Primeira filial (`Onboarding-Filial`) | `GET /api/filiais/` (se já há matriz, o passo já está feito e mostra a matriz) | `POST /api/filiais/` com `matriz: true` (campos da Nova filial, `filiais.md`) | O aviso do endereço da nota (`PLT-15`) já está em `filiais.md`. Limite do plano: 422 `PLT-03` |
| Tabela de preços (`Onboarding-Precos`) | `GET /api/categorias/` | `POST /api/categorias/` com o primeiro `preco`; para mudar o preço, `POST /api/categorias/{id}/precos/` | São as mesmas rotas da tela `Precos` (`/admin/precos`). O passo mostra só categorias e preço; extras e planos especiais ficam na tela `Precos` |
| Modelo de contrato (`Onboarding-Contrato`) | `GET /api/contratos/modelos-prontos/` e `GET /api/contratos/modelos/` | `POST /api/contratos/modelos/` `{ nome, a_partir_de }`, depois `POST /api/contratos/modelos/{id}/publicar/` | A prévia usa `POST .../previa/`. Editar o texto é na tela `Modelos de contrato` |
| Recebimentos (`Onboarding-Recebimentos`) | `GET /api/recebimentos/` | `POST /api/recebimentos/` | Abaixo. Não aparece no Essencial |
| Convidar equipe (`Onboarding-Equipe`) | `GET /api/usuarios/?situacao=convites` e `GET /api/filiais/` | `POST /api/usuarios/convites/`, um por pessoa | Limite do plano: 422 `PLT-03`; e-mail em uso: 409 |

## Recebimentos da empresa (`FIN-04`, passo 10) · fase 1 (T-358)

Servido no host da empresa e implementado em `plataforma/api/`. Usa `conectar_recebimentos` e `atualizar_recebimentos`, que já existem (T-029), e a `ContaPagamento` no `public` (ADR 0007). Liga o Pix e o boleto pelo parceiro: `POST .../cobranca/` de `financeiro.md` deixa de responder `recebimentos_desligados` quando a subconta fica `aprovada`.

**Quem:**
- Administrador. Outro perfil: 403 `permissao`.
- Token de suporte: 403 `PLT-07` nos dois modos, porque os dados são cadastrais e financeiros da empresa no parceiro.
- Plano sem `recebimento_parceiro` (Essencial): 403 `PLT-12` nas duas rotas, com a mensagem de `financeiro.md` ("Seu plano não inclui Pix e boleto automáticos. Para usar, mude de plano.").

### GET /api/recebimentos/

200:
```json
{ "situacao": "pendente",
  "rotulo": "Em análise pelo parceiro",
  "mensagem": "O parceiro está conferindo o cadastro. Enquanto isso, registre os pagamentos à mão em Contas a receber.",
  "conectado_em": "2026-10-07T13:20:00Z",
  "sugestao": null,
  "acoes": { "conectar": false } }
```

**`situacao`, `rotulo` e `mensagem` (textos prontos):**

| `situacao` | `rotulo` | `mensagem` |
| --- | --- | --- |
| `desconectado` | "Não conectado" | "Conecte para gerar Pix e boleto e dar baixa sozinho." |
| `pendente` | "Em análise pelo parceiro" | o texto do exemplo acima |
| `aprovada` | "Recebimentos ligados" | "Pix e boleto saem pelo parceiro, e a baixa é feita sozinha." |
| `recusada` | "Cadastro recusado" | "O parceiro recusou o cadastro. Fale com a equipe Giro." |

- **`acoes.conectar`:** `true` só em `desconectado`. Um novo pedido depois da recusa fica com a equipe Giro no MVP, e o produto decide se a tela ganha isso.
- **`sugestao`:** só em `desconectado`, com os campos pré-preenchidos para o formulário: `{ nome, documento, email, celular, cep, logradouro, numero, complemento, bairro }`. Vêm da razão social e do CNPJ da empresa, do e-mail e do celular do administrador e do endereço da matriz. O administrador confere e corrige.
- **Consulta ao parceiro:** em `pendente`, o `GET` chama `atualizar_recebimentos` no máximo uma vez por minuto por empresa, com cache no Redis. Se o parceiro está fora do ar, responde a situação gravada, sem erro. Na transição para `aprovada`, marca o passo `recebimentos` (`IMP-07`, acima) e grava `conta_pagamento.aprovada` na auditoria `configuracoes`, regra `FIN-04`. Na transição para `recusada`, grava `conta_pagamento.recusada`.

### POST /api/recebimentos/

Corpo:
```json
{ "nome": "Moto Rápida Locadora LTDA", "documento": "12345678000195", "email": "financeiro@motorapida.com.br",
  "celular": "85998124410", "cep": "60110000", "logradouro": "Av. Santos Dumont", "numero": "1500",
  "complemento": "", "bairro": "Aldeota", "faturamento_mensal_centavos": 5000000, "tipo_empresa": "LIMITED" }
```

`tipo_empresa` vem da lista do parceiro: `MEI`, `LIMITED`, `INDIVIDUAL`, `ASSOCIATION`.

- **201:** o corpo do `GET`, com `situacao: "pendente"`. Chama `conectar_recebimentos` e grava `conta_pagamento.criar` (já existe). **Não marca o passo:** o passo só conta na aprovação.
- **400 `validacao`:** CNPJ ou CPF com dígito errado, CEP fora de 8 dígitos, celular fora de 10 ou 11 dígitos, faturamento menor ou igual a zero.
- **409 `recebimentos_conectados`:** já existe subconta, em qualquer situação.
- **422 `parceiro_recusou`:** com a mensagem do parceiro. Nada é gravado (CA-029-02).
- **503 `parceiro_indisponivel`:** nada é gravado.
- **A chave da subconta e o token do webhook nunca saem na resposta** (S-05, S-14).

**A tela de referência pede mais do que a API faz** (`Onboarding-Recebimentos`; o design-system ajusta a tela):
- **Banco, agência, conta e chave Pix:** a transferência automática para a conta da locadora fica para depois (S-05, `financeiro.md`, "Devoluções ao cliente").
- **Interruptores de Pix automático, boleto e cartão recorrente:** as formas vêm do plano e da cobrança, sem escolha por empresa no MVP. O boleto já vem com o Pix (T-305).
- **"Lembretes no WhatsApp":** é a régua da `AUT-03`, fixa, sem configuração.
- **O que o formulário tem:** os campos do corpo acima.

Testes: `test_fin_04_conectar_recebimentos`, `test_fin_04_recebimentos_aprovada_liga_a_cobranca`, `test_plt_12_recebimentos_essencial_403`, `test_plt_07_recebimentos_recusa_suporte` e `test_imp_07_recebimentos_so_com_a_subconta_aprovada`.

---

## Módulos por plano (`PLT-12`, ADR 0024)

O conjunto da empresa é `recursos_da_empresa()`: os `recursos` do plano atual, menos `locacoes_vistoria` quando o ramo (`ConfiguracaoEmpresa.atividade`, passo 7) não aluga e menos `vendas_comissoes` quando não vende. `GIRO_MODULOS_ATIVOS` continua global e só esconde do menu o app ainda não entregue.

**Recusa.** Rota de módulo desligado, em leitura e escrita, para qualquer perfil e para o token de suporte, antes da conferência de perfil e filial:

| HTTP | Corpo |
| --- | --- |
| 403 | `{ "codigo": "PLT-12", "mensagem": "Seu plano não inclui {módulo}. Para usar, mude de plano.", "detalhes": { "recurso": "<recurso>", "motivo": "plano" } }` |
| 403 | `{ "codigo": "PLT-12", "mensagem": "Sua empresa não está configurada para {alugar\|vender}. Mude em Configurações.", "detalhes": { "recurso": "<recurso>", "motivo": "ramo" } }` |

`{módulo}` é o nome do recurso: Locação e vistoria, Contas a receber, Contrato digital, Vendas e comissões, Manutenção e despesas, Conciliação, Relatórios, Pix e boleto automáticos, Cobrança pelo WhatsApp.

**Rotas por recurso.** As views declaram `recurso_do_plano` (ou `recurso_por_acao`); o teste das rotas confere esta tabela.

| Recurso | Rotas |
| --- | --- |
| `locacoes_vistoria` | `/api/locacoes/...`, `/api/planos-especiais/...`, `/api/vistorias/...` (inclusive agenda e avarias), `/api/devolucoes/...`. Ficam abertas (núcleo, `veiculos`): `/api/categorias/...`, `/api/extras/...`, preços |
| `contas_receber` | nenhuma rota fecha no MVP (todos os planos têm): `/api/financeiro/contas-receber/...`, `/api/financeiro/caixas/...`, devoluções ao cliente |
| `contrato_digital` | nenhuma rota fecha (todos os planos têm) |
| `vendas_comissoes` | `/api/vendas/...` (fase 2), `/api/financeiro/comissoes/...` (fase 2) |
| `manutencao_despesas` | `/api/manutencao/...` (fase 2), `/api/financeiro/despesas/...` (inclusive exportar) |
| `conciliacao` | `/api/financeiro/conciliacao/...` (fase 2) |
| `relatorios` | `/api/relatorios/...` (fase 2). **Não** fecham: `/api/painel/...` e `/api/configuracoes/` |
| `recebimento_parceiro` | `POST /api/financeiro/contas-receber/{id}/cobranca/` (Pix e boleto pela subconta), cobrança recorrente (`AUT-04`), passo `recebimentos` e as rotas da subconta da empresa (`ContaPagamento`). O webhook do parceiro não fecha: pagamento de cobrança gerada antes do downgrade ainda baixa a conta |
| `cobranca_whatsapp` | nenhuma rota fecha: `cobrar/` e `cobrar-em-lote/` continuam, só sem o canal WhatsApp (`financeiro.md`) |

Rotas que ainda não existem entram na tabela com o contrato do módulo delas; quem escreve o contrato diz o recurso.

**Implantação.** Sem `recebimento_parceiro`, o passo `recebimentos` sai da lista de `PASSOS_IMPLANTACAO` da empresa: no Essencial são 9 passos, e `concluidos`, `total` e `faltam` (`configuracoes.md`, `GET /api/plataforma/empresas/{id}/`) contam 9. Passo `recebimentos` já marcado continua guardado e volta a contar ao subir de plano.

**Downgrade.** O que está aberto nos módulos que saem recusa o downgrade (`assinatura.md`, 422 `PLT-04` com `detalhes.abertos`; grupos na ADR 0024, item 7), e também a atividade que o plano novo não aceita (`detalhes.atividade`: quem só vende não vai para o Essencial, ADR 0024, item 10). O painel da plataforma (`mudar-plano`, fase 2) usa o mesmo serviço e a mesma recusa.

**Ramo.** Trocar o ramo (passo 7 e Configurações, `PUT /api/ramo/` em `empresas.md`) passa pela mesma conta: as atividades aceitas no plano atual (Essencial: `aluga` e `ambos`) e o que está aberto nos módulos que saem, com o grupo `locacoes` a mais (422 `PLT-12`, ADR 0024, item 9).

## Interface interna para os outros apps (não é HTTP)

Os apps da empresa usam só estas funções do `plataforma` (ADR 0011):

| Função | Uso |
| --- | --- |
| `plataforma.selectors.empresa_atual()` | `Empresa` do schema corrente (via `connection.tenant`). |
| `plataforma.selectors.uso_do_plano()` | O mesmo dicionário `uso` de `GET /api/assinatura/`. |
| `plataforma.services.exigir_limite(item)` | `item` ∈ `veiculos`, `filiais`, `usuarios`. Levanta `LimiteDoPlano` → 422 `{ "codigo": "PLT-03", "mensagem": "Seu plano permite até 3 filiais. Para abrir outra, mude de plano.", "detalhes": { "item": "filiais", "usado": 3, "limite": 3 } }`. Chamada pelo serviço de criação de filial, veículo (inclusive importação, `IMP-03`) e convite de usuário, dentro da transação, com `SELECT ... FOR UPDATE` no `UsoEmpresa` para duas criações simultâneas não passarem do limite. |
| `plataforma.services.atualizar_uso(item, delta)` | Mantém `UsoEmpresa` em dia; chamada pelos mesmos serviços ao criar, desativar ou reativar. A tarefa noturna `plataforma.recalcular_uso` corrige qualquer diferença contando de verdade em cada schema. |
| `plataforma.services.registrar_passo_implantacao(passo)` | Marca o passo da implantação e move o funil (`IMP-05`). |
| `plataforma.services.copiar_endereco_da_matriz(endereco)` | Chamada por `filiais.services.criar_filial` quando a filial nasce matriz; grava o endereço da nota da assinatura só se a empresa ainda não tem (`PLT-15`, `assinatura.md`). |
| `plataforma.services.concluir_implantacao(objeto)` | Na confirmação da 1ª locação (ou venda), marca o passo `primeira_locacao` uma vez só, com o evento `implantacao.concluir` na auditoria da empresa (`IMP-01`). |
| `plataforma.services.registrar_acesso()` | Atualiza `ultimo_acesso_em` (no máximo 1 escrita a cada 5 min por empresa). |
| `plataforma.selectors.recursos_para(plano, atividade)` | Função pura: `plano.recursos` menos `locacoes_vistoria` quando `atividade` não aluga e menos `vendas_comissoes` quando não vende. Base de `recursos_da_empresa`, do downgrade e da troca de ramo (ADR 0024, itens 2, 7 e 9). |
| `plataforma.selectors.atividades_aceitas(plano)` | Atividades com pelo menos um módulo de operação (`locacoes_vistoria` ou `vendas_comissoes`) em `recursos_para(plano, atividade)`, na ordem `aluga`, `vende`, `ambos`. Essencial: `("aluga", "ambos")` (ADR 0024, item 10). |
| `plataforma.selectors.recursos_da_empresa(empresa=None)` | `frozenset` dos recursos ligados (plano e ramo, ADR 0024). Os apps de cima usam `comum.empresa.tem_recurso(recurso)`, que `plataforma` registra no `ready()`; no `public`, `True`. Lido uma vez por pedido. |
| `plataforma.services.pendencias_dos_modulos(empresa, recursos_que_saem)` | Entra no schema da empresa e soma os grupos registrados em `comum.modulos.registrar_pendencia` para os recursos que saem; devolve a lista `abertos` de `assinatura.md` (só grupos com quantidade > 0). Com `empresa=None`, conta no schema corrente. Usada por `mudar_plano` (pedido, simulação e `excede`), por `gerar_faturas` e por `empresas.services.mudar_ramo` (ADR 0024, item 9). |

Ao chegar a 90% de um item, `exigir_limite`/`atualizar_uso` agendam a notificação "limite do plano em 90%" para os administradores (uma vez por item e por mês).
