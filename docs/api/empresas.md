# Empresas: marca da locadora

**Dono:** arquiteto · **Versão:** 12 out 2026 (T-132; antes T-128) · **App:** `empresas` (schema da empresa) · **Regras:** IMP (passo 5 · Marca), USR-02 (nome no autenticador) · **ADRs:** 0004 (white label por tokens), 0002 (empresa pelo subdomínio) · **Segurança:** S-12 (logo SVG) · **Telas:** Login, Convite, Acesso-Senha, Admin-Marca (prévia), Onboarding-Marca, e a casca (`Main`, `Menu`)

Convenções gerais em `docs/api/README.md`. Este contrato traz só a **leitura** da marca. A edição (tela `Admin-Marca` e passo `Onboarding-Marca`: trocar logo, cor e nome, com a sanitização da S-12) fica para a tarefa da marca da empresa e acrescenta a rota de escrita aqui.

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
- No backend, o resultado fica em cache por schema (`marca:<schema>`) até a marca mudar: o serviço de escrita da marca (tarefa da `Admin-Marca`) apaga a chave na mesma transação (`on_commit`). Sem escrita ainda, o cache não precisa de prazo, mas use 1 hora para não depender da invalidação.
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

Texto sobre as suaves: `#111114` sobre `cor_suave` e `#F4F4F6` sobre `cor_suave_escuro`, os dois acima de 11:1 nesses exemplos.

O seed (`seed_moto_rapida`) grava a marca da Moto Rápida pelo serviço de escrita quando ele existir; até lá, a Moto Rápida responde com o padrão (nome "Moto Rápida", `MR`, `#C8F04A`), que é o mesmo das telas.

## Interface interna

| Função | Uso |
| --- | --- |
| `empresas.selectors.marca()` | Dicionário desta rota, lido do cache por schema. Registrada em `comum.empresa` no `ready()`, como `exige_2fa_todos`: `contas` (e-mail de convite e de senha, `issuer` do autenticador), `notificacoes` e `contratos` (PDF) leem a marca por ela, sem importar `empresas`. Hoje esses lugares leem `request.tenant.nome_exibicao`; passam a usar `marca()["nome_exibicao"]` na mesma tarefa. |
| `empresas.selectors.meta_ocupacao_pct()` | Para o painel (`relatorios`). Sem a linha, `Decimal("80.00")`. |
