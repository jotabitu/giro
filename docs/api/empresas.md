# Empresas: marca da locadora

**Dono:** arquiteto · **Versão:** 13 out 2026 (T-153, PNG aceito; antes T-130, T-132 e T-128) · **App:** `empresas` (schema da empresa) · **Regras:** IMP (passo 5 · Marca), USR-02 (nome no autenticador) · **ADRs:** 0004 (white label por tokens), 0002 (empresa pelo subdomínio), 0005 (simulação), 0022 (sanitização do logo) · **Segurança:** S-12 (logo SVG) · **Telas:** Login, Convite, Acesso-Senha, Admin-Marca (prévia), Onboarding-Marca, e a casca (`Main`, `Menu`)

Convenções gerais em `docs/api/README.md`. Este contrato traz a **leitura** da marca (T-128) e a **escrita** (T-130: tela `Admin-Marca` e passo `Onboarding-Marca`, com logo, cor e nome, a sanitização da S-12 e a prévia das cores pela API).

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
| `empresas.selectors.meta_ocupacao_pct()` | Para o painel (`relatorios`). Sem a linha, `Decimal("80.00")`. |
