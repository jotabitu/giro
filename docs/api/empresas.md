# Empresas: marca e ramo da locadora

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-224, ramo; antes T-153, T-130, T-132 e T-128) · **App:** `empresas` (schema da empresa) · **Regras:** IMP (passo 5 · Marca; passo 7 · Ramo), USR-02 (nome no autenticador), PLT-12 (ramo e módulos) · **ADRs:** 0004 (white label por tokens), 0002 (empresa pelo subdomínio), 0005 (simulação), 0022 (sanitização do logo), 0024 (módulos por plano) · **Segurança:** S-12 (logo SVG) · **Telas:** Login, Convite, Acesso-Senha, Admin-Marca (prévia), Onboarding-Marca, Onboarding-Ramo, e a casca (`Main`, `Menu`)

Convenções gerais em `docs/api/README.md`. Este contrato traz a **leitura** da marca (T-128) e a **escrita** (T-130: tela `Admin-Marca` e passo `Onboarding-Marca`, com logo, cor e nome, a sanitização da S-12 e a prévia das cores pela API) e o **ramo** (T-224: passo `Onboarding-Ramo` e a troca em Configurações, `PLT-12`, ADR 0024).

## Regras gerais

- **Uma rota só para a marca, com ou sem sessão.** O login, o convite, o primeiro acesso, o "esqueci a senha" e a entrada do suporte leem a marca antes de haver sessão; a casca do app lê a mesma rota depois do login. Não há marca dentro do `GET /api/auth/eu/`: ali continua só `empresa.nome_exibicao`, que é o mesmo nome desta rota.
- **A empresa é a do subdomínio** (ADR 0002). Não há parâmetro de empresa: `motorapida.<dominio>/api/marca/` responde a marca da Moto Rápida. No host da plataforma (`admin.<dominio>`) e em host desconhecido a rota não existe (404, urlconf do `public`); ali vale a marca Giro, fixa no frontend.
- **A API decide, a tela mostra (ADR 0004).** A cor do texto sobre a marca e a cor suave vêm calculadas; as iniciais do lugar do logo vêm prontas. O frontend só aplica os valores em `--brand`, `--on-brand` e `--brand-soft`.
- **Só o que é público.** A rota devolve o que já aparece na tela de login: nome, logo e cores. Nada de razão social, CNPJ, endereço, contato nem número da operação. O painel ilustrativo ao lado do login (`Login-Desktop`: "Alugados agora 42 de 86", "Ocupação 71%") é desenho fixo do frontend, **não** dado da empresa, e nenhuma rota pública o preenche.

---

## GET /api/marca/

Público (sem `Authorization`; com token também responde igual). Também para o token de suporte (`suporte_somente_leitura = True`).

200:
```json
{
  "nome_exibicao": "Moto Rápida",
  "iniciais": "MR",
  "logo": { "url": "/api/marca/logo/?v=5c1e9a2b", "largura": 120, "altura": 36 },
  "cor": "#C8F04A",
  "cor_sobre": "#111114",
  "cor_suave": "#EEF9CC",
  "cor_suave_escuro": "#2B3510",
  "personalizada": true,
  "versao": "5c1e9a2b"
}
```

| Campo | O que é |
| --- | --- |
| `nome_exibicao` | `ConfiguracaoEmpresa.nome_exibicao`; vazio, cai no `plataforma.Empresa.nome_exibicao` (o nome da compra). Nunca vem vazio. |
| `iniciais` | As duas primeiras iniciais das palavras do nome, ignorando "de", "da", "do", "das", "dos" e "e", em maiúsculas ("Moto Rápida" → "MR"; nome de uma palavra só → as duas primeiras letras). É o que a tela mostra no lugar do logo ("Sem logo, usamos as iniciais", `Onboarding-Marca`). |
| `logo` | `null` sem logo. Com logo: `url` relativa ao host (mesma origem), com a versão na query, e as dimensões do `viewBox` (ou da imagem) para reservar espaço. O frontend mostra **sempre** por `<img src>`, nunca inline (S-12). |
| `cor` | `ConfiguracaoEmpresa.cor_marca` em `#RRGGBB` maiúsculo; com `cor_marca` vazio (sem cor configurada), a padrão do design system, `#C8F04A`. |
| `cor_sobre` | Cor do texto sobre `cor`: `#111114` ou `#FFFFFF`, a de maior razão de contraste WCAG com `cor`. Razão = `(Y_claro + 0,05) / (Y_escuro + 0,05)`, com `Y = 0,2126 R + 0,7152 G + 0,0722 B` em sRGB linear; empate fica com `#111114`. A razão nunca fica abaixo de 4,69:1. |
| `cor_suave` | Fundo suave no tema claro (`--brand-soft`): a `cor` em OKLCH (OKLab de Björn Ottosson, a partir do sRGB linear), trocada para `L = 0,96`, `C = 0,31 × C_cor`, mesmo `H`; volta para sRGB com clamp de cada canal em [0, 1] e `round()`. Para a cor padrão `#C8F04A` vale o valor fixo do `wl-theme.css`, `#EEF9CC` (a fórmula daria `#EBF9CD`). |
| `cor_suave_escuro` | Fundo suave no tema escuro: a mesma conta com `L = 0,31`. Para `#C8F04A` vale o valor fixo do `wl-theme.css`, `#2B3510` (igual ao da fórmula). |
| `personalizada` | `false` enquanto a empresa não salvou marca (nem logo nem cor); o frontend pode usar isso só para a prévia do assistente. |
| `versao` | Resumo curto (8 caracteres hexadecimais) do nome, da cor e do conteúdo do logo. Muda quando qualquer um muda. |

**Sem marca configurada** (empresa recém-criada, passo "Marca" pulado: "não (usa padrão)" na tabela da implantação): 200 com o nome da compra, as iniciais dele, `logo: null`, as cores padrão (`#C8F04A`, `#111114`, `#EEF9CC`, `#2B3510`) e `personalizada: false`. Nunca 404 e nunca "Sua locadora" numa empresa que existe.

**Status da empresa:** a marca responde em qualquer status em que o schema exista (`em_teste`, `ativa`, `inadimplente`, `suspensa`, `pausada`, `cancelada` até o expurgo). O bloqueio de acesso é do login (`contas.md`, `PLT`), não da marca: a pessoa vê a tela da locadora e a mensagem do login.

**Cache:**
- Resposta com `Cache-Control: public, max-age=300` e `ETag: "<versao>"`; `If-None-Match` com a versão atual → 304 sem corpo.
- No backend, o resultado fica em cache por schema (`marca:<schema>`) até a marca mudar: o serviço de escrita (`PATCH /api/marca/`) apaga a chave no `on_commit`. O prazo de 1 hora continua, para não depender só da invalidação.
- O frontend lê a marca uma vez por carga (pode ser no servidor do Next.js, pelo mesmo host) e guarda no TanStack Query com `staleTime` de 5 minutos; depois de salvar a marca, a tela `Admin-Marca` invalida a consulta.

**Limite:** `comum.limites` por IP, 120 por minuto (é chamada em toda abertura do login); acima, 429 `muitas_requisicoes`.

**Erros:** só 429. Host sem empresa → 404 do urlconf, que o frontend trata como "sem marca": nome "Sua locadora", sem logo, cores padrão (o que a T-126 já faz).

---

## GET /api/marca/logo/

Público. O arquivo do logo, servido pela própria API (o storage continua privado; a URL assinada de 15 minutos do `AUD-05` não serve aqui, porque o logo aparece antes do login, em e-mail e precisa de cache longo).

- `?v=<versao>` igual à atual: 200 com o arquivo, `Cache-Control: public, max-age=31536000, immutable`.
- `?v=` ausente ou antiga: 200 com o arquivo atual e `Cache-Control: public, max-age=300` (e-mail antigo continua mostrando o logo).
- Sem logo: 404 `nao_encontrado`.
- Cabeçalhos sempre: `Content-Type` do formato guardado (`image/svg+xml` ou `image/png`), `X-Content-Type-Options: nosniff`, `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox` e `Content-Disposition: inline; filename="logo.svg"` (ou `.png`). Assim, mesmo aberto direto na barra de endereço, um SVG não roda script (S-12; a sanitização no upload é a primeira barreira, estes cabeçalhos a segunda).
- Mesmo limite por IP da rota de marca.

E-mails, WhatsApp e PDF que levam o logo usam a URL absoluta `https://<subdominio>.<dominio>/api/marca/logo/?v=<versao>`; o PDF do WeasyPrint lê o arquivo direto do storage do schema atual (`modelo-de-dados.md`, contratos).

---

## Escrita da marca (T-130)

Telas `Admin-Marca` (bloco "Marca" e "Prévia") e `Onboarding-Marca` (passo 1 do assistente: "Logo" e "Cor de destaque"). Os blocos "Dados da empresa" (razão social, CNPJ, endereço) e "Endereço do sistema" (domínio próprio) da `Admin-Marca`, e CNPJ, razão social e nome fantasia do `Onboarding-Marca`, **não** fazem parte deste contrato.

- **Perfis:** administrador (`pode.administracao`, tabela de perfis: "Administração (marca, ...)"). Outro perfil: 403 `permissao`. Token de suporte: 403 (as rotas de escrita não têm `suporte_somente_leitura`). Empresa `suspensa`, `pausada` ou `cancelada`: 403 `empresa_sem_operacao`, como toda escrita.
- **A API decide, a tela mostra.** A prévia nunca calcula cor: as telas de referência trazem um script que mistura 82% de branco para a cor suave e usa outra fórmula de contraste; ele é só desenho. O frontend chama `POST /api/marca/simular/` e aplica o que voltar.
- Nenhuma rota de escrita aceita URL de logo: o logo só entra como arquivo enviado.

### POST /api/marca/simular/

Calcula a prévia sem gravar nada (ADR 0005). A tela chama ao escolher uma das seis cores do `Onboarding-Marca`, ao digitar uma cor válida em "Cor principal" (com espera de 300 ms depois da última tecla) e ao mudar o nome.

Corpo (JSON), campos opcionais; o que não vem usa o valor salvo:
```json
{ "cor": "#ff7a45", "nome_exibicao": "Moto Rápida" }
```

200:
```json
{
  "nome_exibicao": "Moto Rápida",
  "iniciais": "MR",
  "cor": "#FF7A45",
  "cor_sobre": "#111114",
  "cor_suave": "#FFE7D6",
  "cor_suave_escuro": "#47261A"
}
```

Mesmas contas e mesmos campos de `GET /api/marca/` (função pura de `empresas/marca.py`); `cor: ""` simula a volta para a cor padrão, e `nome_exibicao: ""` a volta para o nome da compra. As seis cores do `Onboarding-Marca` estão na tabela de exemplos em "Dados". 400 `validacao` com as mesmas mensagens do `PATCH`. Limite: `comum.limites` por usuário, 120 por minuto; acima, 429 `muitas_requisicoes`.

### PATCH /api/marca/

Salva a marca. `multipart/form-data` quando há logo novo; JSON também é aceito quando não há arquivo. Todos os campos são opcionais e só o que vem muda:

| Campo | Regra |
| --- | --- |
| `nome_exibicao` | Texto; espaços nas pontas removidos; até 80 caracteres; sem caracteres de controle. Vazio volta para o nome da compra. |
| `cor` | `#RRGGBB`, maiúsculas ou minúsculas (grava em maiúsculas). Vazio volta para a cor padrão. Qualquer cor vale: o texto em cima dela é sempre o de maior contraste (`cor_sobre`, nunca abaixo de 4,69:1). |
| `logo` | Arquivo até **2 MB**. O formato vem do conteúdo, nunca da extensão nem do `Content-Type`: SVG (texto que começa, depois de BOM e espaços, por `<?xml` ou `<svg`) ou PNG (assinatura completa `\x89PNG\r\n\x1a\n`). Passa pelo tratamento da ADR 0022 (PNG: item 6 e a nota de 13 out 2026, aceito pela Segurança) e é gravado já limpo. |
| `remover_logo` | `true` apaga o logo; a marca volta às iniciais. Junto com `logo` → 400. |

200: o mesmo corpo de `GET /api/marca/`, já com a `versao` nova, e `ETag` com ela. O frontend grava esse corpo na consulta `marca` do TanStack Query e a invalida; a casca troca as cores na hora.

Corpo sem nenhum campo, ou com os mesmos valores salvos e sem logo: 200 com a marca atual, sem evento de auditoria e sem mudar a `versao`.

400 `validacao`, mensagens em `campos`:

| Campo | Mensagem |
| --- | --- |
| `cor` | "Use uma cor no formato #RRGGBB." |
| `nome_exibicao` | "Use até 80 caracteres." |
| `logo` | "Envie o logo em SVG ou PNG." (formato desconhecido) |
| `logo` | "O logo passa de 2 MB." (o enviado, ou o PNG depois de codificado de novo) |
| `logo` | "Não conseguimos ler este SVG. Exporte o logo de novo pelo seu programa de desenho." (XML inválido, DTD, entidade, raiz que não é `svg`) |
| `logo` | "Não conseguimos ler este PNG. Exporte o logo de novo pelo seu programa de desenho." (PNG que não abre, truncado, com assinatura forjada ou de outro formato depois de aberto) |
| `logo` | "O SVG tem conteúdo que não aceitamos, como script ou link externo. Exporte o logo de novo, só com o desenho." (conteúdo ativo, ADR 0022, item 3) |
| `logo` | "O SVG precisa de tamanho definido (viewBox)." |
| `logo` | "Não encontramos desenho neste SVG." (nada desenhável depois da limpeza) |
| `logo` | "O logo é grande demais. Use até 4.096 pixels de lado." (PNG, ou SVG com mais de 5.000 elementos ou 32 níveis) |
| `remover_logo` | "Envie um logo novo ou remova o atual, não os dois." |

Limite: `comum.limites` por usuário, 30 por hora (upload); acima, 429 `muitas_requisicoes`.

**O que o serviço faz** (`empresas.services.salvar_marca(nome_exibicao=..., cor=..., logo=..., remover_logo=...)`, numa transação, com `select_for_update` na linha única):

1. Valida e limpa o logo antes de abrir a transação (ADR 0022). O arquivo limpo é gravado no storage privado do schema com o resumo do conteúdo no nome (`marca/logo-<sha256 de 16 caracteres>.svg` ou `.png`), e `logo_largura` e `logo_altura` vêm do `viewBox` (SVG, arredondados, no mínimo 1) ou dos pixels (PNG).
2. Grava `nome_exibicao`, `cor_marca` e o logo com evento `empresa.alterar_marca`, categoria `configuracoes` (ADR 0010). `CAMPOS_AUDITORIA` de `ConfiguracaoEmpresa` passa a ter `nome_exibicao`, `cor_marca` e `logo` inteiros: o logo aparece no evento pelo nome do arquivo, que é o resumo do conteúdo, nunca pelo conteúdo. A tela da auditoria mostra "Marca alterada".
3. No `on_commit`: apaga `selectors.chave_da_marca()` e apaga do storage o arquivo antigo do logo (trocado ou removido). Se a transação falhar, apaga o arquivo novo. Logo não é registro de negócio: o arquivo antigo não fica guardado, e e-mail antigo com `?v=` velho mostra o logo atual (como já diz `GET /api/marca/logo/`).
4. Chama `plataforma.services.registrar_passo_implantacao("marca")` (`IMP-05`; idempotente). Vale para o `Onboarding-Marca` ("Continuar") e para a `Admin-Marca`. "Pular por agora" não chama esta rota; como fica o passo pulado é do contrato do assistente de implantação, que ainda não existe.

Nada no modelo muda além de `CAMPOS_AUDITORIA`: os campos da T-129 bastam.

**Frontend:**
- "Trocar logo" e "Enviar logo" abrem o seletor com `accept` do formato aceito; a tela confere extensão e os 2 MB antes de enviar, só para avisar mais cedo (a API confere de novo). A prévia do arquivo ainda não salvo usa `URL.createObjectURL` em `<img>`, nunca o SVG inline (S-12). Depois de salvar, usa a `url` da API.
- O texto da ajuda é "PNG ou SVG, fundo transparente, até 2 MB", e o seletor usa `accept="image/png,image/svg+xml,.png,.svg"`.
- "Remover" manda `remover_logo: true` no "Salvar"; até lá, a prévia já mostra as iniciais.
- Erro 400 aparece no campo, com a `mensagem` da API.

---

## Ramo da empresa (T-224)

Passo 7 do assistente (`Onboarding-Ramo`, "O que a empresa faz") e a troca depois da implantação, em Configurações. As duas telas usam as mesmas rotas e o mesmo serviço, `empresas.services.mudar_ramo` (ADR 0024, itens 9 e 10). O ramo liga e desliga módulos junto com o plano (`PLT-12`): `aluga` pede `locacoes_vistoria`, `vende` pede `vendas_comissoes`.

- **Perfis:** administrador, como a marca. Outro perfil: 403 `permissao`. O token de suporte lê o `GET` e recebe 403 no `PUT`. Empresa `suspensa`, `pausada` ou `cancelada`: 403 `empresa_sem_operacao` no `PUT`.
- **Configurações não tem tela de ramo** entre as telas de referência; a rota fica pronta para ela (pendência no fim desta seção).

### GET /api/ramo/

200, a Moto Rápida do seed (Profissional, aluga e vende, motos):

```json
{ "atividade": "ambos",
  "trabalha_com": "motos",
  "atividades": [
    { "valor": "aluga", "titulo": "Locação", "descricao": "Aluguel por dia, semana ou mês", "aviso": null },
    { "valor": "vende", "titulo": "Venda de veículos", "descricao": "Novos, seminovos e consignados", "aviso": null } ],
  "atividades_aceitas": ["aluga", "vende", "ambos"],
  "tipos": [
    { "valor": "motos", "titulo": "Motos" },
    { "valor": "carros", "titulo": "Carros" } ],
  "modulos": {
    "aluga": ["Locação e vistoria", "Contas a receber", "Contrato digital", "Manutenção e despesas", "Conciliação", "Relatórios", "Pix e boleto automáticos", "Cobrança pelo WhatsApp"],
    "vende": ["Contas a receber", "Contrato digital", "Vendas e comissões", "Manutenção e despesas", "Conciliação", "Relatórios", "Pix e boleto automáticos", "Cobrança pelo WhatsApp"],
    "ambos": ["Locação e vistoria", "Contas a receber", "Contrato digital", "Vendas e comissões", "Manutenção e despesas", "Conciliação", "Relatórios", "Pix e boleto automáticos", "Cobrança pelo WhatsApp"] } }
```

No Essencial (CA-ASS-51):

```json
{ "atividade": "aluga", "trabalha_com": "motos",
  "atividades": [
    { "valor": "aluga", "titulo": "Locação", "descricao": "Aluguel por dia, semana ou mês", "aviso": null },
    { "valor": "vende", "titulo": "Venda de veículos", "descricao": "Novos, seminovos e consignados", "aviso": "Vendas faz parte do plano Profissional." } ],
  "atividades_aceitas": ["aluga", "ambos"],
  "tipos": ["..."],
  "modulos": {
    "aluga": ["Locação e vistoria", "Contas a receber", "Contrato digital"],
    "ambos": ["Locação e vistoria", "Contas a receber", "Contrato digital"] } }
```

- `atividade` e `trabalha_com`: o que está guardado em `ConfiguracaoEmpresa`. Empresa que ainda não passou pelo passo 7: `ambos` e `motos`, o padrão do modelo (ADR 0024, item 2).
- `atividades_aceitas`: `plataforma.selectors.atividades_aceitas(plano atual)` (ADR 0024, item 10). A tela mostra "Locação" e "Venda de veículos" como dois botões e só deixa salvar uma combinação que está na lista: no Essencial, "Locação" não desliga, e "Venda de veículos" pode ficar marcada ("aluga e vende"). A tela não decide a lista.
- `aviso` de "vende": "Vendas faz parte do plano Profissional." quando o plano atual não liga `vendas_comissoes`; senão `null`. Aparece junto do botão.
- `modulos`: para cada atividade aceita, os nomes (`Recurso.label`) de `recursos_para(plano atual, atividade)`, na ordem do enum, sem `suporte_prioritario`. É o bloco "Módulos que vamos ligar": a tela mostra a lista da combinação marcada. Os nomes são os do 403 `PLT-12` (`plataforma.md`), não os da tela de referência ("Clientes e documentos", "Avaliação de troca"), que misturam o núcleo com módulos que não existem.
- Sem cache: o plano pode ter mudado no pedido anterior.

### PUT /api/ramo/

Corpo: `{ "atividade": "aluga" | "vende" | "ambos", "trabalha_com": "motos" | "carros" | "ambos" }`. Os dois são obrigatórios.

200: o corpo do `GET` já atualizado. Em ordem, numa transação com `SELECT ... FOR UPDATE` na linha de `ConfiguracaoEmpresa`:

1. `atividade` fora de `atividades_aceitas(plano atual)`: 422 `PLT-12` com `motivo: "plano"` (abaixo). Nada muda.
2. Recursos que saem = `recursos_da_empresa()` menos `recursos_para(plano atual, atividade nova)`. Havendo algum, `plataforma.services.pendencias_dos_modulos(None, recursos_que_saem)` conta no schema corrente; com algum grupo, 422 `PLT-12` com `motivo: "abertos"`. Nada muda.
3. Grava os dois campos, registra `empresa.mudar_ramo` na auditoria (categoria configurações; antes e depois de `atividade` e `trabalha_com`, e os recursos que saíram e entraram) e chama `plataforma.services.registrar_passo_implantacao("ramo")` (idempotente). Mesmo ramo de antes: 200 sem evento de auditoria, e o passo é marcado.
4. O menu e as rotas mudam no pedido seguinte (`recursos_da_empresa()` não é guardado). Nenhum dado muda de status nem é apagado (`PLT-12`, ADR 0024, item 6): a locação encerrada continua no banco e volta com o ramo.

A empresa sempre fica com pelo menos uma atividade, então sai no máximo uma por vez; `aluga` → `vende` tira `locacoes_vistoria` e liga `vendas_comissoes`.

Erros:

- 400 `validacao`: campo fora do enum ou faltando.
- 422 `{ "codigo": "PLT-12", "mensagem": "O plano Essencial não inclui vendas. Escolha locação, ou locação e venda.", "detalhes": { "motivo": "plano", "atividades_aceitas": ["aluga", "ambos"] } }` (CA-ASS-51), com o nome do plano atual. A tela não deixa chegar aqui; a rota recusa mesmo assim.
- 422 com algo aberto no módulo que sai (CA-ASS-50), todos os grupos de uma vez, no formato do downgrade (`assinatura.md`):
  ```json
  { "codigo": "PLT-12",
    "mensagem": "Para deixar de alugar, resolva o que está aberto: 1 locação aberta.",
    "detalhes": { "motivo": "abertos", "recurso": "locacoes_vistoria",
      "abertos": [ { "grupo": "locacoes", "quantidade": 1, "texto": "1 locação aberta" } ],
      "abertos_texto": "1 locação aberta" } }
  ```
  Deixar de vender: "Para deixar de vender, resolva o que está aberto: 1 venda aberta e 1 comissão a pagar.", com `recurso: "vendas_comissoes"` e os grupos `vendas` e `comissoes`. Os grupos, os textos e a ordem são os de `assinatura.md` (422 `PLT-04`), mais `locacoes` ("1 locação aberta", "{n} locações abertas": `aguardando_retirada`, `ativa` e `devolucao_atrasada`), que só aparece aqui.
- 403 `permissao`, `empresa_sem_operacao`; 403 do token de suporte.

Testes com o código: `test_plt_12_troca_de_ramo_com_algo_aberto` (CA-ASS-50) e `test_plt_12_essencial_sem_so_vende` (CA-ASS-51, o `GET` e o `PUT`).

**Pendência.** A troca do ramo em Configurações não tem tela de referência nem cartão em `GET /api/configuracoes/`. Fica no backlog para o design-system: a tela pode reaproveitar o `Onboarding-Ramo` e mostrar a recusa com o `abertos_texto`. Até lá, só o passo 7 usa estas rotas.


## Dados (`ConfiguracaoEmpresa`, `modelo-de-dados.md`)

A tarefa que implementa esta leitura acrescenta à linha única de `ConfiguracaoEmpresa`:

| Campo | Tipo | Padrão |
| --- | --- | --- |
| `nome_exibicao` | texto(80), vazio permitido | vazio (cai no nome da compra) |
| `logo` | arquivo no storage privado do schema, nulo | nulo |
| `logo_largura`, `logo_altura` | inteiro positivo, nulo | nulo |
| `cor_marca` | texto(7) `#RRGGBB`, vazio permitido (nunca nulo), `CHECK` do formato | vazio (padrão do design system) |
| `meta_ocupacao_pct` | percentual, 2 casas | `80.00` (usada pelo painel, `painel.md`) |

`cor_sobre`, `cor_suave`, `cor_suave_escuro` e `versao` são calculados na leitura (função pura em `empresas/marca.py`, testada com as seis cores do `Onboarding-Marca`), não guardados. A função é Python puro, sem dependência nova, e os testes cobrem também os exemplos da tabela abaixo. O modelo de dados listava `cor_marca_suave` e `cor_sobre_marca` como campos; passam a ser calculados, para não existirem duas fontes da mesma cor.

`cor_marca` é texto vazio, e não nulo, quando a empresa não escolheu cor (o ruff proíbe `null` em `CharField`, regra DJ001; decisão 1 do handoff da T-129). Vazio e padrão significam a mesma coisa; a API nunca devolve vazio em `cor`.

Exemplos da fórmula das cores (conferidos no backend):

| `cor` | `cor_sobre` | `cor_suave` | `cor_suave_escuro` |
| --- | --- | --- | --- |
| `#C8F04A` (padrão, valores fixos) | `#111114` | `#EEF9CC` | `#2B3510` |
| `#1D4ED8` | `#FFFFFF` | `#DBF2FF` | `#1F2F52` |
| `#C62828` | `#FFFFFF` | `#FFE3DC` | `#4A2320` |

As seis cores do `Onboarding-Marca`, calculadas pela função da T-129 (`empresas/marca.py`), para o teste da simulação e da prévia:

| `cor` (rótulo na tela) | `cor_sobre` | `cor_suave` | `cor_suave_escuro` |
| --- | --- | --- | --- |
| `#C8F04A` (Verde-limão) | `#111114` | `#EEF9CC` | `#2B3510` |
| `#FF7A45` (Laranja) | `#111114` | `#FFE7D6` | `#47261A` |
| `#2F6FED` (Azul) | `#FFFFFF` | `#DBF3FF` | `#1E3050` |
| `#16B8A6` (Verde-água) | `#111114` | `#D7FBF4` | `#183732` |
| `#E11D48` (Vermelho) | `#FFFFFF` | `#FFE0E1` | `#4D2023` |
| `#7A5AF8` (Roxo) | `#FFFFFF` | `#EEECFF` | `#2E2A51` |

Texto sobre as suaves: `#111114` sobre `cor_suave` e `#F4F4F6` sobre `cor_suave_escuro`, os dois acima de 11:1 nesses exemplos.

O seed (`seed_moto_rapida`) não grava marca: a Moto Rápida responde com o padrão (nome "Moto Rápida", `MR`, `#C8F04A`, `personalizada: false`), que é o mesmo das telas. Teste que precisa de marca salva usa `empresas.services.salvar_marca`.

**Cor padrão com valores fixos (saída (b) de `cores-da-marca.md`, T-130).** Para `#C8F04A` a API devolve as suaves do `wl-theme.css` (`#EEF9CC` e `#2B3510`), e a fórmula vale para todas as outras cores. A saída (a), aceitar `#EBF9CD` e mudar o `wl-theme.css`, foi descartada: a diferença é de 3 em um canal, invisível; o `wl-theme.css` é do design-system e é a fonte das telas de referência; e o código e os testes da T-129 já seguem a (b). Quem escolher `#C8F04A` na tela recebe os mesmos valores fixos, porque a conta é sobre a cor, não sobre ter salvado.

## Interface interna

| Função | Uso |
| --- | --- |
| `empresas.selectors.marca()` | Dicionário desta rota, lido do cache por schema. Registrada em `comum.empresa` no `ready()`, como `exige_2fa_todos`: `contas` (e-mail de convite e de senha, `issuer` do autenticador), `notificacoes` e `contratos` (PDF) leem a marca por ela, sem importar `empresas`. Hoje esses lugares leem `request.tenant.nome_exibicao`; passam a usar `marca()["nome_exibicao"]` na mesma tarefa. |
| `empresas.services.mudar_ramo(atividade, trabalha_com, por)` | O único caminho para mudar o ramo (passo 7 e Configurações), descrito em `PUT /api/ramo/`. |
| `comum.empresa.atividade()` | Registrada por `empresas` no `ready()`; `plataforma` lê o ramo por ela (ADR 0024, item 2). |
| `empresas.selectors.meta_ocupacao_pct()` | Para o painel (`relatorios`). Sem a linha, `Decimal("80.00")`. |
