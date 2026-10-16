# Configurações: o resumo da Administração

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-259, cartão do ramo; T-201; T-173) · **App:** `relatorios` (schema da empresa; só leitura, nível 13 da ADR 0011) · **Regras:** FIL-01, USR-05, USR-08, PLT-03, PLT-07, PLT-12, IMP-01, IMP-04, IMP-05 · **ADRs:** 0005 (a API decide), 0011 (limites entre apps) · **Telas:** Config e Admin-Ramo (desktop e celular)

Convenções gerais em `docs/api/README.md`. A tela `Configurações` (`/admin/configuracoes`, chave `config` do menu) é uma lista de cartões, cada um com um título, uma linha de resumo e o link para a tela da área, mais a faixa da implantação no desktop. Ela **não edita nada**: cada área tem a sua tela e o seu contrato. Este contrato traz só a leitura que monta os cartões.

## O que já tem contrato e o que este traz

| Cartão da tela | Tela de destino | Contrato da área | O resumo vem de |
| --- | --- | --- | --- |
| Empresa e marca | `Admin-Marca` | `empresas.md` (T-153, T-154) | texto fixo |
| O que a empresa faz | `Admin-Ramo` (T-253) | `empresas.md` (`GET` e `PUT /api/ramo/`, T-224) | `empresas` (o ramo guardado) |
| Filiais | `Filiais` | `filiais.md` (T-168) | `filiais` |
| Usuários e perfis | `Admin-Usuarios` | `contas.md` (T-169) | `plataforma` (uso do plano) e `contas` (convites) |
| Tabelas de preço | `Precos` | `veiculos.md` (categorias e preços), `locacoes.md` (planos especiais) | `veiculos` e `locacoes` |
| Modelos de contrato | `Contratos-Modelos` | `contratos.md` | `contratos` |
| Integrações | `Integracoes` | **nenhum** (fase 2, menos os pagamentos da T-029) | não vem no MVP |
| Notificações | **sem tela** (lista de "telas que faltam desenhar" das regras) | **nenhum** | não vem no MVP |
| Assinatura | `Admin-Assinatura` | `plataforma.md` (`GET /api/assinatura/`, T-170) | `plataforma` |
| Auditoria | `Admin-Auditoria` | `auditoria.md` (T-171) | texto fixo |
| Exportar dados | `Admin-Exportar` | `auditoria.md` (T-171; no MVP, só a auditoria em CSV) | texto fixo |
| Faixa "Implantação concluída em 6 de 10 passos" | assistente de implantação | **nenhum** (o assistente ainda não tem contrato) | `plataforma` (passos da implantação) |

Não existia rota de configurações: o novo aqui é só `GET /api/configuracoes/`.

## Regras gerais

- **A API decide, a tela mostra.** Os cartões vêm na ordem da tela, com título e resumo prontos (plural, separador "·", data curta). O frontend não conta nada nem monta texto; só liga a `chave` à rota (tabela "Rotas dos cartões") e escolhe o ícone.
- **Cartão sem tela não vem (`USR-05`).** Como o menu (`contas.md`, "Menu e início"), um cartão só vem quando o app da tela de destino está em `GIRO_MODULOS_ATIVOS`, pela mesma tabela de item e app do menu. Nenhum cartão depende de recurso do plano (todos são do núcleo, `PLT-12`); só o resumo de `precos` conta planos especiais quando `locacoes_vistoria` está ligado na empresa (ADR 0024). `integracoes` e `notificacoes` não vêm no MVP: não têm tela nem contrato. Nunca vem cartão desabilitado nem com número de exemplo.
- **Por que `relatorios`.** O resumo lê de oito apps (`empresas`, `filiais`, `contas`, `plataforma`, `veiculos`, `locacoes`, `contratos`, `auditoria`). Pela ADR 0011 só os apps do nível 13 leem de todos; `empresas` (nível 4) não pode importar `filiais` nem `locacoes`. O painel (`painel.md`) já mora em `relatorios` pelo mesmo motivo. `relatorios` chama só os selectors listados em "Fontes", nunca os models dos outros apps.
- **Empresa inteira.** O resumo é da empresa, não da filial: ignora o `X-Filial` (o administrador vê todas as filiais de qualquer jeito). Conta categorias da empresa e das filiais.

---

## GET /api/configuracoes/

Perfis: quem tem `pode.administracao` (administrador). Os outros perfis: 403 `{ "codigo": "permissao", "mensagem": "Seu perfil não tem acesso a esta página" }`. Token de suporte (`suporte_somente_leitura = True`): responde, sem os cartões `auditoria` e `exportar` (o suporte não lê a auditoria da empresa, `PLT-07`, `auditoria.md`). Empresa sem operação (`suspensa`, `pausada`, `cancelada`): responde (é leitura).

200 (Moto Rápida em 07 out, com todos os apps ativos, depois da 1ª locação):
```json
{
  "cartoes": [
    { "chave": "marca", "titulo": "Empresa e marca", "resumo": "Logo, cor, nome e endereço do sistema" },
    { "chave": "ramo", "titulo": "O que a empresa faz", "resumo": "Locação e venda · motos" },
    { "chave": "filiais", "titulo": "Filiais", "resumo": "1 filial · Centro, Fortaleza" },
    { "chave": "usuarios", "titulo": "Usuários e perfis", "resumo": "5 de 10 usuários" },
    { "chave": "precos", "titulo": "Tabelas de preço", "resumo": "4 categorias" },
    { "chave": "modelos_contrato", "titulo": "Modelos de contrato", "resumo": "1 modelo" },
    { "chave": "assinatura", "titulo": "Assinatura", "resumo": "Profissional · teste até 21 out" },
    { "chave": "auditoria", "titulo": "Auditoria", "resumo": "Quem fez o quê no sistema" },
    { "chave": "exportar", "titulo": "Exportar dados", "resumo": "Baixe a auditoria em CSV" }
  ],
  "implantacao": null
}
```

Uma empresa ainda implantando (como na tela de referência):
```json
{
  "cartoes": [ "..." ],
  "implantacao": {
    "concluidos": 6, "total": 10,
    "titulo": "Implantação concluída em 6 de 10 passos",
    "faltam": "Faltam contrato, recebimentos, importar dados e a 1ª locação.",
    "acao": null
  }
}
```

### Cartões

Ordem fixa: `marca`, `ramo`, `filiais`, `usuarios`, `precos`, `modelos_contrato`, `integracoes`, `notificacoes`, `assinatura`, `auditoria`, `exportar` (a da tela). Um cartão que não vem não deixa buraco.

| `chave` | `titulo` | Vem quando o app está ativo | `resumo` |
| --- | --- | --- | --- |
| `marca` | Empresa e marca | `empresas` (fora do padrão até a T-153 e a T-154; o item `config` do menu tem chave própria, `configuracoes`) | "Logo, cor, nome e endereço do sistema" (fixo) |
| `ramo` | O que a empresa faz | `empresas` (como o `marca`); não vem para o token de suporte, porque a tela só serve para trocar o ramo, e escrita com token de suporte é 403 `PLT-07` (T-259) | O ramo guardado (`PLT-12`): "{atividades} · {tipos}". Atividades: `aluga` "Locação", `vende` "Venda", `ambos` "Locação e venda". Tipos: `motos` "motos", `carros` "carros", `ambos` "motos e carros". Seed Moto Rápida: "Locação e venda · motos". Empresa que ainda não passou pelo passo 7 tem o padrão do modelo (`ambos` e `motos`, ADR 0024), e o texto é o mesmo. A referência da T-253 mostra o texto fixo "Locação, venda e tipos de veículo"; vale o da API. |
| `filiais` | Filiais | `filiais` | Filiais ativas. Uma: "1 filial · {nome a mostrar}, {cidade}", com o nome curto da filial, ou o nome quando ela não tem (`FIL-01`, T-201; Moto Rápida: "1 filial · Centro, Fortaleza", CA-FIL-01). Mais de uma, em até 3 cidades: "{n} filiais · {cidades}" ("2 filiais · Fortaleza e Caucaia"); em 4 cidades ou mais: "{n} filiais em {c} cidades". |
| `usuarios` | Usuários e perfis | `contas` | Uso do plano (`usuarios` de `GET /api/assinatura/`: `ativo` e `convite_pendente`, `PLT-03`): "{usado} de {limite} usuários"; plano sem limite: "{usado} usuários". Com convites pendentes, acrescenta " · 1 convite" ou " · {n} convites". |
| `precos` | Tabelas de preço | `veiculos` | Categorias ativas: "{n} categorias" ("1 categoria"); com planos especiais ativos, acrescenta " · 1 plano especial" ou " · {n} planos especiais" (o plano especial é do app `locacoes`; com `locacoes` fora de `GIRO_MODULOS_ATIVOS` ou `locacoes_vistoria` desligado na empresa, não entra no texto). Nenhuma categoria: "Nenhuma categoria cadastrada". |
| `modelos_contrato` | Modelos de contrato | `contratos` | Modelos não arquivados: "{n} modelos" ("1 modelo"); com rascunho em aberto (modelo `rascunho` ou publicado com `tem_rascunho`, `contratos.md`), acrescenta " · 1 rascunho" ou " · {n} rascunhos". Sem modelo de locação publicado: "Nenhum modelo publicado" (é o que trava a 1ª locação, `IMP-04`). |
| `integracoes` | Integrações | não vem no MVP | — |
| `notificacoes` | Notificações | não vem no MVP | — |
| `assinatura` | Assinatura | `plataforma` | "{plano} · {situação}", com a situação pelo status da empresa: `em_teste` "teste até {21 out}"; `ativa` "mensal" ou "anual" (o `ciclo`); `inadimplente` "fatura em atraso"; `suspensa` "suspensa"; `pausada` "pausada até {30 nov}" (sem data, "pausada"); `cancelada` "cancelada". Data curta como em `plataforma.selectors._dia_mes`. |
| `auditoria` | Auditoria | `auditoria`; não vem para o token de suporte | "Quem fez o quê no sistema" (fixo) |
| `exportar` | Exportar dados | `auditoria`; não vem para o token de suporte | "Baixe a auditoria em CSV" (fixo; ver "Pendências") |

Quando a fase 2 entregar as integrações e as notificações, cada uma acrescenta o resumo dela nesta tabela (a tela pede "Pagamentos, WhatsApp e rastreador ligados" e "Lembretes de pagamento e devolução"); o corpo da resposta não muda.

### Implantação

- `implantacao` vem `null` quando a implantação está concluída (`IMP-01`: passo `primeira_locacao` marcado, por `plataforma.services.concluir_implantacao`). Depois disso a faixa some de vez.
- Antes disso: `concluidos` e `total` são os de `plataforma.selectors.implantacao` (os 10 passos de `plataforma.md`, `IMP-05`; 9 sem `recebimento_parceiro`, como no Essencial, em que `recebimentos` não entra em `total` nem em `faltam`, `PLT-12`). `titulo` é "Implantação concluída em {concluidos} de {total} passos".
- `faltam` lista os passos ainda abertos, na ordem dos passos, com estes nomes: `conta` "conta e acesso", `marca` "empresa e marca", `filial` "primeira filial", `ramo` "o que a empresa faz", `precos` "tabela de preços", `contrato` "contrato", `recebimentos` "recebimentos", `importar` "importar dados", `equipe` "equipe", `primeira_locacao` "a 1ª locação". Juntados com ", " e " e " antes do último, com "Faltam " no começo e ponto final ("Falta a 1ª locação." quando é um só).
- `acao`: o botão "Continuar implantação" leva ao passo aberto do assistente, que ainda não tem contrato nem tela. Até ele existir, `acao` vem `null` e a faixa aparece sem botão, **exceto** quando o único passo aberto é `primeira_locacao`: aí `acao` é `{ "rotulo": "Fazer uma locação de teste", "destino": "nova_locacao" }`, o mesmo destino do início de implantação (`painel.md`). Quando o assistente for contratado, `acao` passa a `{ "rotulo": "Continuar implantação", "destino": "implantacao", "passo": "<primeiro passo aberto>" }`; o contrato do assistente acrescenta isso aqui.
- Os passos são lidos do `public` pela interface de `plataforma` (`plataforma.selectors.passos_implantacao`), como no painel; nada de consulta direta ao `public` em `relatorios`.

### Erros

401 e 403 como acima. Nenhum 404 nem 422: área que falta vira cartão ausente, nunca erro.

### Cache

Nenhum. São contagens pequenas, e a tela é aberta pouco e logo depois de mudar alguma coisa (voltar de Filiais ou de Usuários tem que mostrar o número novo). Teste de quantidade de queries: no máximo 10 com todos os cartões (`django_assert_num_queries`), sem N+1 por filial ou por modelo.

---

## Fontes (interface interna)

`relatorios/selectors.py` ganha `configuracoes(usuario, suporte)` e chama só:

| Cartão | Função | Existe? |
| --- | --- | --- |
| `ramo` | `empresas.selectors.configuracao()` (`atividade` e `trabalha_com`) | existe |
| `filiais` | `filiais.selectors.resumo_das_filiais_ativas()` → `{ "ativas": int, "cidades": [str], "unica": { "nome", "cidade" } \| None }` | nova (`resumo_das_filiais(usuario)` já existia, para o `eu`) |
| `usuarios` | `plataforma.selectors.uso_do_plano()["usuarios"]` e `contas.selectors.convites_pendentes()` → int | a primeira existe; a segunda é nova (o contador `usuarios` do painel já conta o mesmo: reaproveitar) |
| `precos` | `veiculos.selectors.categorias_ativas()` → int e `locacoes.selectors.planos_especiais_ativos()` → int | novas |
| `modelos_contrato` | `contratos.selectors.resumo_dos_modelos()` → `{ "modelos": int, "rascunhos": int, "tem_publicado_de_locacao": bool }` | nova (`modelo_publicado` já existe para o `IMP-04`) |
| `assinatura` | `plataforma.selectors.assinatura()` (o corpo de `GET /api/assinatura/`) | existe |
| `implantacao` | `plataforma.selectors.implantacao(empresa_atual())` | existe |
| todos | `contas.navegacao` para a tabela de item e app de `GIRO_MODULOS_ATIVOS` (a mesma do menu) | existe |

Os textos dos cartões ficam em `relatorios/configuracoes.py` (função pura, testada com os casos da tabela "Cartões").

## Rotas dos cartões

O frontend liga `chave` → rota (referência em `docs/telas/README.md`, "Rotas dos cartões de Configurações"):

| `chave` | Rota |
| --- | --- |
| `marca` | `/admin/marca` |
| `ramo` | `/admin/ramo` (T-253, T-259) |
| `filiais` | `/admin/filiais` |
| `usuarios` | `/admin/usuarios` |
| `precos` | `/admin/precos` |
| `modelos_contrato` | `/admin/contratos` |
| `integracoes` | `/admin/integracoes` (fase 2) |
| `notificacoes` | `/admin/notificacoes` (sem tela) |
| `assinatura` | `/admin/assinatura` |
| `auditoria` | `/admin/auditoria` |
| `exportar` | `/admin/exportar` |

`acao.destino`: `nova_locacao` → `/locacoes/nova`; `implantacao` → definido no contrato do assistente.

O item `config` do menu depende de `configuracoes` em `GIRO_MODULOS_ATIVOS` (`contas.md`), uma chave própria que a T-181 acrescentou ao padrão do backend. `empresas` continua fora do padrão até a T-153 e a T-154 entregarem a tela Empresa e marca: ele liga o item `marca` do menu e o cartão `marca`. `GET /api/configuracoes/` responde sempre, como o painel, sem depender de `configuracoes` (decisão do arquiteto na T-181). Pela ADR 0024 (T-192), `configuracoes` é do núcleo: entra em todos os planos, como a administração, sem recurso.

## Casos para teste (seed Moto Rápida)

| Caso | Esperado |
| --- | --- |
| Administradora (Mariana) em 07 out, todos os apps ativos | os 9 cartões do primeiro exemplo (com `ramo` "Locação e venda · motos"), com os resumos dele; `implantacao: null` (a carteira do seed tem locações, `IMP-01`) |
| Mesma empresa com 2 convites pendentes | `usuarios`: "7 de 10 usuários · 2 convites" (convite pendente conta no uso, `PLT-03`) |
| Planos `Entregador` e `Mensal fidelidade` criados | `precos`: "4 categorias · 2 planos especiais" |
| Um rascunho de modelo a mais | `modelos_contrato`: "2 modelos · 1 rascunho" |
| `auditoria` fora de `GIRO_MODULOS_ATIVOS` | sem `auditoria` e sem `exportar` |
| Token de suporte | sem `ramo`, `auditoria` e `exportar`; o resto igual |
| Ramo trocado para só locação de motos e carros (`PUT /api/ramo/`) | `ramo`: "Locação · motos e carros" (sem cache, já no pedido seguinte) |
| Essencial, aluga e vende, motos | `ramo`: "Locação e venda · motos" (o que está guardado; o plano não muda o texto) |
| Gerente, vendedor, vistoriador, financeiro | 403 `permissao` |
| Empresa nova, passos `conta`, `marca`, `filial`, `ramo`, `precos` e `equipe` marcados | `implantacao`: 6 de 10, "Faltam contrato, recebimentos, importar dados e a 1ª locação.", `acao: null` |
| Empresa no Essencial com os mesmos 6 passos | `implantacao`: 6 de 9, "Faltam contrato, importar dados e a 1ª locação." (sem `recebimentos`) |
| Só `primeira_locacao` aberto | "Implantação concluída em 9 de 10 passos", "Falta a 1ª locação.", `acao` com `nova_locacao` |
| Sem modelo de locação publicado | `modelos_contrato`: "Nenhum modelo publicado" |

## Pendências

- **Texto do cartão Exportar (produto).** A tela diz "Baixe tudo quando quiser", mas no MVP só a auditoria se exporta (decisão do dono na T-151, `auditoria.md`). O contrato usa "Baixe a auditoria em CSV" até o produto responder a `[decisão]` no backlog; na fase 2, com o backup completo, volta o texto da tela.
- **"Filial Centro" ou "Centro" (design-system).** A tela mostra "1 filial · Centro, Fortaleza"; a API usa o nome da filial como está cadastrado ("Filial Centro"), sem cortar palavras. Divergência para a T-028.
- **Integrações e Notificações** ficam fora até terem tela e contrato (fase 2).
