# Painel: início por perfil e contadores do menu

**Dono:** arquiteto · **Versão:** 10 out 2026 (T-128; criado na T-047) · **App:** `relatorios` (schema da empresa; só leitura, nível 13 da ADR 0011) · **Regras:** USR-05, USR-07, USR-08, IMP-01, VEI-06, LOC-07, LOC-10, FIN-01, FIN-07, APR-09, VIS-05 · **Telas:** Main, Pos-Dashboard, Gerente, Vendedor, Vistoriador, Financeiro, Menu

Convenções gerais em `docs/api/README.md`. A estrutura do menu e a variante do início vêm em `GET /api/auth/eu/` (`contas.md`, "Menu e início"). Este contrato traz os números.

## Regras gerais

- **A API decide, a tela mostra.** Contagens, somas, percentuais, tendências e textos de contexto vêm prontos. O frontend só formata dinheiro e percentual no padrão da tela (inclusive a forma curta "R$ 18,4 mil").
- **Valor tipado.** Todo número de KPI vem como `{ "tipo": "numero" | "centavos" | "pct", "valor": ... }`: dinheiro em centavos, percentual como texto com 2 casas.
- **Escopo (`USR-07`).** Administrador e financeiro: filial do `X-Filial` ou `todas`. Gerente: a filial escolhida, entre as dele. Vendedor: só os números dele (`painel: proprios`).
- **Módulo que ainda não existe (`USR-08`).** O bloco vem `null`, nunca com número de exemplo. Ex.: `em_manutencao` do gerente fica `null` até o app `manutencao` existir; os blocos de vendas, comissões e conciliação, até a fase 2. O frontend não mostra bloco `null`.
- **Fuso.** "Hoje", "esta semana" e a saudação usam `America/Sao_Paulo`, no fuso da filial.
- **Atualização.** Cada resposta traz `atualizado_em`; a tela mostra "atualizado há 6 min" a partir dele. O início pode vir de cache de até 5 minutos por empresa, filial, pessoa e período; os contadores, de até 60 segundos (o mesmo intervalo da consulta do frontend), para o número de aprovações não ficar parado depois de uma decisão.


## Rotas, perfis e o que entra no MVP (T-128)

- **App dono:** `relatorios` (`relatorios/api/` com as duas views, `relatorios/selectors.py` com `contadores` e `inicio`). As rotas entram em `config/urls.py` (schema da empresa) e respondem **sempre**, sem depender de `relatorios` em `GIRO_MODULOS_ATIVOS`: aquela chave liga o item "Relatórios" do menu, não o início.
- **Perfis:** qualquer usuário ativo da empresa com sessão completa (com o 2º fator quando `exige_2fa`). A variante é a de `eu.navegacao.inicio.variante`, calculada pela mesma função (`contas.navegacao.variante`); o painel não aceita variante na query. Token de suporte: as duas rotas são "só ver" (`suporte_somente_leitura = True`), com a variante e o escopo do administrador.
- **Filial:** pelo `X-Filial`, só por `filiais.selectors.filtrar_por_filial` (`filiais.md`): sem cabeçalho, a matriz ou a primeira filial; `todas` para administrador, financeiro e quem tem `relatorios_todas_filiais`; fora do escopo, 403 `USR-07`. O vendedor vê os números dele dentro da filial da requisição.
- **Erros:** 400 `validacao` para `periodo` fora de `hoje`, `7d`, `30d`; 401 e 403 `USR-07` como acima. Nenhum 404: módulo que falta vira `null`, nunca erro.
- **Contadores e menu andam juntos.** `contadores` devolve exatamente as chaves `contador` dos itens que o `eu` montou para a pessoa (a mesma função de navegação), então um item escondido por `GIRO_MODULOS_ATIVOS` ou pelo plano (`PLT-12`) não tem contador, e um contador cuja fonte ainda não existe vem `null`. No início, bloco ou KPI de módulo desligado na empresa (ADR 0024: despesas, manutenção, vendas, comissões e conciliação no Essencial) vem `null`, como o de fonte que não existe.

**Regra do MVP:** um número sai quando a fonte dele já existe no backend (model e selector do app dono), mesmo que a tela do módulo ainda não esteja no menu; senão, `null` (o bloco ou o KPI inteiro). Nenhum número é estimado ou fixo. Com o backend de hoje (veículos, clientes, locações, contratos, vistorias, aprovações, contas, filiais; `financeiro` só com `ContaReceber`, `Reembolso` e `Comissao`, sem caixa nem despesa):

| Bloco | Sai no MVP? | Fonte |
| --- | --- | --- |
| **Contadores** `veiculos`, `locacoes`, `aprovacoes`, `usuarios`, `agenda`, `avarias` | sim | `veiculos`, `locacoes`, `aprovacoes` (sem os da própria pessoa, `APR-09`), `contas` (convites pendentes), `vistorias` |
| `receber` | sim, quando o item `receber` aparecer (com `financeiro` em `GIRO_MODULOS_ATIVOS`, T-017) | `financeiro.selectors`: contas com status exibido `atrasada` (`FIN-01`) |
| `despesas`, `contas_a_pagar` | `null` até existir a despesa (`FIN-05`) | — |
| `manutencoes`, `conciliacao`, `propostas` | `null` (fase 2) | — |
| **`geral`** `atencao`, `pendencias.titulo` | sim | aba `precisam_acao` de `locacoes.selectors` |
| `frota_ativa`, `alugados_agora`, `frota.segmentos`, `ocupacao_pct` | sim | `veiculos.selectors` (`contagens`, `ocupacao_da_frota`, `VEI-06`); a tendência "6 a mais esta semana" sai do histórico de status do veículo |
| `meta_ocupacao_pct` | sim | `empresas.selectors.meta_ocupacao_pct()` (campo novo, padrão 80,00; `empresas.md`) |
| `receita_locacao`, `em_atraso` | sim | `financeiro.selectors` sobre `ContaReceber` (pagas no período sem caução, `FIN-13`; atrasadas, `FIN-01`) |
| `devolucoes_semana` | sim | `locacoes.selectors` (`situacao` como na lista) |
| `pendencias.itens` | devoluções atrasadas e parcelas que vencem até amanhã; preventivas, só com `manutencao` | `locacoes`, `financeiro` |
| `caixa_hoje` | sim (T-017) | `financeiro.selectors.caixa_hoje_do_painel` |
| **`implantacao`** inteira | sim | `plataforma` (teste e `UsoEmpresa.passos_implantacao`, lidos do `public` pela interface de `plataforma.md`), `contas` (convites), `veiculos`, `clientes`, `locacoes`; `a_receber_centavos` de `financeiro` |
| **`gerente`** `aprovacoes`, `ocupacao`, `receita_semana`, `devolucoes_atrasadas`, `equipe_hoje`, `frota_filial` | sim | como acima; `equipe_hoje` com `contas.Sessao.ultimo_uso` e o resumo do dia de `vistorias` e `locacoes` |
| `em_manutencao` | `valor: null` (fase 2) | — |
| **`vendedor`** `kpis`, `parcelas_atrasadas`, `precisam_acao` | sim | `locacoes` (`Locacao.vendedor`), `financeiro` |
| `meta`, `funil`, `comissao_prevista`, `propostas` | `null` (fase 2) | — |
| **`vistoriador`** inteira | sim | `vistorias.selectors` (o mesmo corpo da agenda) |
| **`financeiro`** `entra_hoje`, `em_atraso` | sim | `financeiro.selectors` (`FIN-15`, `FIN-01`) |
| `sai_hoje` | sim (T-017) | `financeiro.selectors` (despesas `a_pagar` com vencimento hoje) |
| `caixas_do_dia` | sim (T-017): lista, `[]` sem caixa hoje (o frontend esconde o bloco vazio) | `financeiro.selectors.caixas_de_hoje` |
| `para_hoje` | sim, só com os reembolsos `a_fazer` (`Reembolso`, T-091); as despesas entram com elas | `financeiro` |
| `saldo_em_contas`, `fluxo_previsto`, `conciliacao` | `null` (fase 2) | — |

Quando a T-017 (caixa) e a tarefa da despesa entrarem, cada uma liga o seu bloco no selector de `relatorios` e acrescenta o teste do número do seed; o contrato acima não muda.

**Cache no backend:** Redis, chave `painel:<schema>:<usuario_id>:<filial ou todas>:<rota>[:<periodo>]`, prazo de 5 minutos (início) e 60 segundos (contadores). Sem invalidação no MVP: o prazo curto basta. O cache nunca é compartilhado entre pessoas, porque escopo e `APR-09` dependem de quem pede.

---

## GET /api/painel/contadores/

Números ao lado dos itens do menu. Perfis: todos. Sem paginação. O frontend consulta ao abrir a casca e a cada 60 segundos.
200:
```json
{ "atualizado_em": "...",
  "contadores": { "veiculos": 86, "locacoes": 42, "aprovacoes": 3, "receber": 7, "despesas": 1, "usuarios": 2,
                  "agenda": 6, "avarias": 2, "contas_a_pagar": 4, "manutencoes": null, "conciliacao": null, "propostas": null } }
```
Só vêm as chaves dos itens que a pessoa vê; `null` = módulo ainda não existe (o item não mostra número). O que cada um conta:

| Chave | Conta | Escopo |
| --- | --- | --- |
| `veiculos` | veículos fora de `vendido` e `baixado` | filial |
| `locacoes` | locações abertas (`aguardando_retirada`, `ativa`, `devolucao_atrasada`) | filial; vendedor: as dele |
| `aprovacoes` | pedidos `pendente` que a pessoa pode decidir, **sem os que ela mesma fez** (`APR-09`) | filial |
| `receber` | contas `atrasada` (`FIN-01`) | filial |
| `despesas` | despesas `aguardando_aprovacao` que a pessoa pode aprovar; para quem não aprova, sem contador | filial |
| `contas_a_pagar` | despesas `a_pagar` com vencimento até hoje | filial ou todas |
| `usuarios` | convites pendentes | empresa |
| `agenda` | vistorias do dia não concluídas (`VIS-05`) | filial |
| `avarias` | avarias abertas | filial |
| `reembolsos` | reembolsos `a_fazer` (T-358) | filial de origem; administrador e financeiro, todas |
| `pendencias_pagamento` | pendências do pagamento abertas (T-358) | empresa |
| `manutencoes`, `conciliacao`, `propostas` | fase 2 | — |

---

## GET /api/painel/inicio/

Perfis: todos. Query: `?periodo=hoje|7d|30d` (padrão `7d`; só muda os números que dependem de período, indicados abaixo).
A resposta tem sempre `variante` (a mesma de `eu.navegacao.inicio.variante`), `saudacao` e `atualizado_em`, e os blocos da variante.

```json
{ "variante": "geral", "saudacao": "Bom dia, Mariana", "atualizado_em": "...", "...": "blocos" }
```

### Variante `geral` (administrador, tela `Main`)

```json
{
  "atencao": { "quantidade": 7, "texto": "7 contratos pedem atenção" },
  "kpis": [
    { "chave": "frota_ativa", "rotulo": "Frota ativa", "valor": { "tipo": "numero", "valor": 86 }, "contexto": "52 motos · 34 carros", "destaque": true },
    { "chave": "alugados_agora", "rotulo": "Alugados agora", "valor": { "tipo": "numero", "valor": 42 }, "contexto": "6 a mais esta semana", "tendencia": "sobe" },
    { "chave": "receita_locacao", "rotulo": "Receita de locação", "valor": { "tipo": "centavos", "valor": 1840000 }, "contexto": "últimos 7 dias" },
    { "chave": "em_atraso", "rotulo": "Em atraso", "valor": { "tipo": "numero", "valor": 2 }, "contexto": "R$ 1.646,40 a receber" }
  ],
  "frota": {
    "ocupacao_pct": "71.00", "meta_ocupacao_pct": "80.00", "nota": "ocupação de 71% · meta de 80%",
    "segmentos": [ { "status": "disponivel", "rotulo": "Disponível", "quantidade": 16 },
                   { "status": "alugado", "rotulo": "Alugado", "quantidade": 42 },
                   { "status": "reservado", "rotulo": "Reservado", "quantidade": 9 },
                   { "status": "em_manutencao", "rotulo": "Manutenção", "quantidade": 7 },
                   { "status": "a_venda", "rotulo": "À venda", "quantidade": 12 } ]
  },
  "devolucoes_semana": {
    "subtitulo": "6 contratos",
    "linhas": [ { "locacao_id": 2841, "codigo": "LOC-2841", "placa": "QXA4B21", "veiculo": "Honda CG 160 Fan", "cliente": "Carlos Menezes",
                  "data": "2026-10-06", "situacao": { "rotulo": "Atrasado", "tom": "perigo" } } ]
  },
  "pendencias": {
    "titulo": "7 contratos precisam de ação hoje",
    "itens": [ { "texto": "3 devoluções estão atrasadas", "gravidade": "critica", "destino": { "chave": "locacoes", "filtro": "aba=precisam_acao" } },
               { "texto": "2 parcelas vencem até amanhã", "gravidade": "info", "destino": { "chave": "receber", "filtro": "situacao=vencem_hoje" } } ]
  },
  "caixa_hoje": { "filial": "Filial Centro", "data": "2026-10-07", "status": "aberto",
                  "recebido_centavos": 111190, "a_receber_hoje_centavos": 262580, "despesas_centavos": 4800, "saldo_dia_centavos": 106390 }
}
```
- `atencao` e `pendencias.titulo` contam as locações da aba `precisam_acao` (`locacoes.md`). Com zero: `atencao.texto` "Nenhum contrato pede atenção" e `pendencias.titulo` "Nenhum contrato precisa de ação hoje"; com 1, "1 contrato pede atenção" e "1 contrato precisa de ação hoje".
- `frota_ativa`: veículos fora de `vendido` e `baixado`. `ocupacao_pct` (`VEI-06`) no período escolhido. `meta_ocupacao_pct` vem de `ConfiguracaoEmpresa` (padrão 80,00; telas `Login` e `Main`).
- `receita_locacao` (depende do período): valor das contas de locação pagas no período (parcelas e cobranças do acerto), sem caução e **sem multa e juros por atraso** (`FIN-15`; multa e juros ficam na DRE, `FIN-13`).
- Tendência de `alugados_agora`: diferença para a mesma hora de 7 dias atrás. Sobe: "6 a mais esta semana", `tendencia: "sobe"`; cai: "3 a menos esta semana", `tendencia: "desce"`; igual: `contexto` e `tendencia` `null`.
- `em_atraso`: clientes com conta `atrasada`, e o total em atraso no contexto (seed: 2 clientes, R$ 1.646,40).
- `devolucoes_semana`: locações com fim previsto de hoje até 6 dias à frente, mais as `devolucao_atrasada`, em ordem de data; `situacao` como na lista de locações.
- `pendencias.itens`: devoluções atrasadas, parcelas que vencem até amanhã e, quando o app `manutencao` existir, preventivas vencidas. Cada item leva `destino` (chave do menu e filtro) para "Ver pendências".
- `caixa_hoje` (revisto na T-144): o caixa de hoje da filial **em qualquer status** (`aberto`, `aguardando_aprovacao`, `fechado`, `fechado_sem_conferencia`, como em `financeiro.md`), com o `status` para a tela mostrar a situação; `null` só com `X-Filial: todas` ou quando a filial não abriu caixa hoje. `recebido_centavos` é o `resumo.entrou_hoje_centavos` do caixa; `despesas_centavos` são as saídas de despesa pagas no caixa, sem sangria; `saldo_dia_centavos` = recebido − despesas pagas no caixa. `a_receber_hoje_centavos` é o "vence hoje" da `FIN-15` (contas não pagas com vencimento hoje), o mesmo `vence_hoje_centavos` de `financeiro.md`. Seed em 07 out (`FIN-15`, carteira de outubro): R$ 2.625,80 em 6 parcelas. Caixa da Filial Centro: recebido 111190 (`FIN-07`), saldo 111190 − 4800 = 106390.

### Variante `implantacao` (administrador antes da 1ª locação ou venda, tela `Pos-Dashboard`)

```json
{
  "teste": { "fim": "2026-10-21", "dias_restantes": 14, "texto": "Seu teste grátis termina em 14 dias (21 out)." },
  "primeiros_passos": { "concluidos": 2, "total": 3, "pct": "66.67",
    "itens": [ { "chave": "configuracao_inicial", "rotulo": "Configuração inicial", "detalhe": "Marca, filial, preços, contrato e 83 veículos importados", "concluido": true },
               { "chave": "convidar_equipe", "rotulo": "Convidar a equipe", "detalhe": "3 convites enviados", "concluido": true },
               { "chave": "primeira_locacao", "rotulo": "Fazer uma locação de teste", "detalhe": "Contrato, vistoria e assinatura com um cliente seu ou de teste", "concluido": false, "acao": { "rotulo": "Começar", "destino": "nova_locacao" } } ] },
  "convites": [ { "nome": "Rodrigo Pinheiro", "contato": "rodrigo@motorapida.com.br", "perfil": "gerente", "status": "aceito" } ],
  "indicadores": { "frota_cadastrada": 83, "alugados_agora": 0, "clientes": 0, "a_receber_centavos": 0 }
}
```
- `teste` vem `null` quando a empresa não está `em_teste`.
- `convidar_equipe.detalhe`: "1 convite enviado", "3 convites enviados"; sem convite, "Chame quem vai usar o sistema com você".
- `primeiros_passos` vem dos passos da implantação (`IMP-05`, `plataforma.UsoEmpresa.passos_implantacao`). Os itens "Instalar o app no celular do vistoriador" e "Conectar o WhatsApp da loja" da tela só entram quando esses recursos existirem; até lá, não vêm.
- Ao existir a 1ª locação ou venda (`IMP-01`), a variante passa a `geral`.

### Variante `gerente` (tela `Gerente`)

```json
{
  "aprovacoes": { "total": 3, "mais_antigo": "há 2 h",
    "itens": [ { "id": 88, "tipo": "APR-01", "titulo": "Desconto de 8% para Diego Martins", "detalhe": "Bruna · ... (limite dela: 5%)", "acoes": ["recusar", "aprovar"] } ] },
  "kpis": [
    { "chave": "ocupacao", "rotulo": "Ocupação", "valor": { "tipo": "pct", "valor": "71.00" }, "contexto": "meta de 80%" },
    { "chave": "receita_semana", "rotulo": "Receita da semana", "valor": { "tipo": "centavos", "valor": 1840000 }, "contexto": "6% a mais que a anterior", "tendencia": "sobe" },
    { "chave": "devolucoes_atrasadas", "rotulo": "Devoluções atrasadas", "valor": { "tipo": "numero", "valor": 3 }, "contexto": "1 há mais de 2 dias" },
    { "chave": "em_manutencao", "rotulo": "Em manutenção", "valor": null, "contexto": null }
  ],
  "equipe_hoje": [ { "usuario_id": 4, "nome": "João Silva", "perfil": "vistoriador", "resumo": "2 de 6 vistorias feitas", "online": true } ],
  "frota_filial": { "total": 83, "segmentos": [ { "rotulo": "Livres", "quantidade": 16 }, { "rotulo": "Alugados", "quantidade": 42 }, { "rotulo": "Reserv.", "quantidade": 9 }, { "rotulo": "Oficina e venda", "quantidade": 16 } ] }
}
```
- `aprovacoes`: pedidos `pendente` da filial que ele pode decidir, **sem os que ele mesmo fez** (`APR-09`), do mais antigo para o mais novo, até 5 itens. As ações usam `aprovacoes.md`.
- `equipe_hoje`: só pessoas ativas ligadas à filial (`USR-08`). `online` = sessão usada nos últimos 5 minutos (`contas.Sessao.ultimo_uso`). `resumo` é texto pronto do dia: vistoriador "2 de 6 vistorias feitas"; vendedor "3 locações hoje" (metas e propostas na fase 2); quem não fez nada hoje, o último acesso: "último acesso hoje", "último acesso ontem", "último acesso em 03 out" (dia com 2 dígitos e mês abreviado, no fuso da filial) ou, quem nunca entrou, "ainda não acessou".
- `receita_semana`: os últimos 7 dias contra os 7 anteriores, na base da `receita_locacao`. Sobe: "6% a mais que a anterior", `tendencia: "sobe"`; cai: "6% a menos que a anterior", `tendencia: "desce"` (percentual inteiro, arredondado meio para cima); igual ou semana anterior sem receita: `contexto` e `tendencia` `null`.
- `em_manutencao` vem com `valor: null` até o app `manutencao` existir (o frontend esconde o cartão).

### Variante `vendedor` (fase 1: locação; tela `Vendedor` completa na fase 2)

```json
{
  "kpis": [
    { "chave": "minhas_locacoes_ativas", "rotulo": "Minhas locações ativas", "valor": { "tipo": "numero", "valor": 12 }, "contexto": null },
    { "chave": "devolvem_hoje", "rotulo": "Devolvem hoje", "valor": { "tipo": "numero", "valor": 2 }, "contexto": null },
    { "chave": "parcelas_atrasadas", "rotulo": "Parcelas atrasadas", "valor": { "tipo": "numero", "valor": 1 }, "contexto": "R$ 299,40 de 1 cliente" }
  ],
  "parcelas_atrasadas": [ { "conta_id": 9010, "cliente": "Carlos Menezes", "locacao": "LOC-2841", "vencimento": "2026-09-30", "valor_centavos": 29940, "dias": 7, "acao": "cobrar" } ],
  "precisam_acao": [ { "locacao_id": 2856, "codigo": "LOC-2856", "cliente": "Lucas Ferreira", "situacao": { "rotulo": "Aguardando assinatura", "tom": "alerta" } } ],
  "meta": null, "funil": null, "comissao_prevista": null, "propostas": null
}
```
- "Meus" (`USR-08`): as locações que o vendedor criou (`Locacao.vendedor`). `parcelas_atrasadas`: contas atrasadas dessas locações.
- `meta`, `funil`, `comissao_prevista` e `propostas` vêm `null` até vendas e comissões existirem (fase 2, `FIN-09`).

### Variante `vistoriador` (tela `Vistoriador`)

```json
{ "agenda": { "...": "o mesmo corpo de GET /api/vistorias/agenda/?dia=hoje" }, "avarias_abertas": 2 }
```
Sem valores em dinheiro. As abas Amanhã e Semana chamam `GET /api/vistorias/agenda/` direto (`vistorias.md`).

### Variante `financeiro` (tela `Financeiro`, sem o que é fase 2)

```json
{
  "kpis": [
    { "chave": "entra_hoje", "rotulo": "Entra hoje", "valor": { "tipo": "centavos", "valor": 262580 }, "contexto": "6 parcelas" },
    { "chave": "sai_hoje", "rotulo": "Sai hoje", "valor": { "tipo": "centavos", "valor": 41230 }, "contexto": "1 conta a pagar" },
    { "chave": "em_atraso", "rotulo": "Em atraso", "valor": { "tipo": "centavos", "valor": 164640 }, "contexto": "2 clientes" },
    { "chave": "saldo_em_contas", "rotulo": "Saldo em contas", "valor": null, "contexto": null }
  ],
  "caixas_do_dia": [ { "filial": "Filial Centro", "status": "aberto", "aberto_por": "Bruna Alves", "esperado_gaveta_centavos": 28100 } ],
  "para_hoje": [
    { "texto": "Devolver R$ 183,00 a Juliana Rocha por Pix", "tipo": "reembolso", "destino": { "chave": "reembolsos", "id": 31 } },
    { "texto": "Pagar conta de luz · R$ 412,30", "tipo": "despesa", "destino": { "chave": "contas_a_pagar", "id": 803 } }
  ],
  "fluxo_previsto": null, "conciliacao": null
}
```
- `entra_hoje`: o "vence hoje" da `FIN-15` (contas não pagas com vencimento hoje, sem caução), com a quantidade de parcelas no contexto; mesmo número de `caixa_hoje.a_receber_hoje_centavos` e de `vence_hoje_*` em `financeiro.md` (seed em 07 out: 262580 em 6 parcelas); `sai_hoje`: despesas `a_pagar` com vencimento hoje; `em_atraso`: total `atrasada` e número de clientes.
- `para_hoje` (`USR-08`): só reembolsos `a_fazer` e despesas a pagar vencendo até hoje. Texto do reembolso pela forma (`DEV-02`): "Devolver R$ 183,00 a Juliana Rocha por Pix", "... no cartão" (estorno) e "... em dinheiro". O de dinheiro só aparece até a T-017: com o caixa, o dinheiro sai na hora e o reembolso nasce `feito`. **Sem aprovações**: o financeiro não decide `APR-03` nem `APR-04`.
- `caixas_do_dia`: o caixa de hoje de cada filial do escopo, em qualquer status (os mesmos valores do `caixa_hoje`), matriz primeiro; `[]` quando nenhuma filial abriu caixa hoje.
- `saldo_em_contas`, `fluxo_previsto` e `conciliacao` vêm `null` até a fase 2 (conciliação bancária).

---

## Interface interna

`relatorios.selectors.inicio(usuario, variante, filial, periodo)` e `contadores(usuario, filial)` leem dos outros apps só por `selectors` (ADR 0011, nível 13). Um teste por variante com o seed Moto Rápida em 07 out confere os números citados nos contratos de origem: em atraso R$ 1.646,40 em 2 clientes; caixa da Filial Centro com R$ 1.111,90 recebidos; entra hoje R$ 2.625,80 em 6 parcelas; a despesa de R$ 1.200,00 pedida por João aparece nas aprovações de Rodrigo; um pedido feito pelo próprio Rodrigo não aparece para ele (`APR-09`).
