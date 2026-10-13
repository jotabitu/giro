# Sanitização do logo da empresa

**Status:** aceita · 12 out 2026 · detalha a S-12 para a escrita da marca (T-130); PNG aceito pela Segurança em 13 out 2026 (nota no item 6)

## Contexto

O administrador da locadora envia o logo em `PATCH /api/marca/` (`docs/api/empresas.md`). Esse arquivo aparece na tela de login de todos os usuários, na casca do app, no painel da plataforma (`admin.`), em e-mails, no WhatsApp e no PDF do contrato (WeasyPrint). Um SVG pode carregar `<script>`, eventos `on*`, `<foreignObject>` com HTML, links `javascript:`, recursos externos e entidades XML (S-12).

A leitura (T-128, T-129) já pôs a segunda barreira: o logo sai por `GET /api/marca/logo/` com `nosniff`, `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; sandbox` e `Content-Disposition: inline`, e o frontend só o mostra por `<img>`. Falta a primeira barreira: o que entra no storage.

O `nh3`, já no projeto, sanitiza HTML e não serve para SVG (o parser de HTML5 perde os namespaces e os atributos com maiúscula, como `viewBox`). O `xml.etree` da biblioteca padrão não recusa DTD nem entidades.

## Decisão

### 1. O arquivo gravado é sempre um arquivo novo, montado pelo backend

Nada do que foi enviado vai para o storage como veio. O SVG é lido, limpo e serializado de novo; o PNG (item 6) é decodificado e codificado de novo. O código fica em `empresas/logo.py`, função pura `limpar_logo(conteudo: bytes) -> LogoLimpo(conteudo, extensao, largura, altura)`, que levanta `LogoInvalido(mensagem)` com as mensagens do contrato.

### 2. Leitura do SVG

- Até 2 MB, conferidos antes de ler.
- O formato vem dos primeiros bytes, não da extensão nem do `Content-Type`.
- Parser `defusedxml.ElementTree.fromstring(conteudo, forbid_dtd=True, forbid_entities=True, forbid_external=True)`. Dependência nova, `defusedxml` (Python puro, sem dependência própria); o motivo vai no PR. DTD, entidade ou XML quebrado → "Não conseguimos ler este SVG...".
- A raiz tem que ser `{http://www.w3.org/2000/svg}svg`.
- Até 5.000 elementos e 32 níveis de profundidade; acima → "O logo é grande demais...".

### 3. Conteúdo ativo: recusa, não limpeza silenciosa

O arquivo é recusado ("O SVG tem conteúdo que não aceitamos...") quando tem qualquer um destes:

- elementos `script`, `foreignObject`, `iframe`, `object`, `embed`, `a`, `image`, `feImage`, `animate`, `animateMotion`, `animateTransform`, `set`, `handler`, `listener`;
- atributo que começa com `on` (qualquer caixa);
- `href` ou `xlink:href` que não seja uma referência interna `#id`;
- valor de atributo com `javascript:`, `data:` ou `url(` que não seja `url(#id)`.

Recusar, em vez de tirar e seguir, deixa claro ao administrador que o arquivo não é o que ele pensa, e não grava um logo diferente do que ele viu. A recusa gera um `WARNING` no log com o schema e o id do usuário, sem o conteúdo.

`<image>` fica de fora mesmo com `data:`: é o "SVG" que só embrulha uma imagem, e esconderia um PNG ou JPEG sem passar pelo tratamento do item 6.

### 4. O resto: lista fechada, o que estiver fora sai em silêncio

Programas de desenho (Illustrator, Inkscape, Figma, Corel) põem no arquivo metadados, comentários e atributos próprios. Isso sai sem erro:

- comentários, instruções de processamento, `<metadata>`, `<sodipodi:*>`, `<inkscape:*>` e todo elemento ou atributo de namespace que não seja SVG ou `xlink`;
- elementos e atributos fora das listas abaixo.

**Elementos aceitos:** `svg`, `g`, `defs`, `symbol`, `use`, `title`, `desc`, `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `text`, `tspan`, `linearGradient`, `radialGradient`, `stop`, `clipPath`, `mask`, `pattern`, `style`, `filter`, `feGaussianBlur`, `feOffset`, `feFlood`, `feComposite`, `feBlend`, `feColorMatrix`, `feMerge`, `feMergeNode`.

**Atributos aceitos:** `id`, `class`, `style`, `viewBox`, `preserveAspectRatio`, `width`, `height`, `x`, `y`, `x1`, `y1`, `x2`, `y2`, `cx`, `cy`, `r`, `rx`, `ry`, `fx`, `fy`, `fr`, `d`, `points`, `transform`, `fill`, `fill-opacity`, `fill-rule`, `stroke`, `stroke-width`, `stroke-linecap`, `stroke-linejoin`, `stroke-miterlimit`, `stroke-dasharray`, `stroke-dashoffset`, `stroke-opacity`, `opacity`, `color`, `display`, `visibility`, `clip-path`, `clip-rule`, `clipPathUnits`, `mask`, `maskUnits`, `maskContentUnits`, `filter`, `filterUnits`, `primitiveUnits`, `offset`, `stop-color`, `stop-opacity`, `gradientUnits`, `gradientTransform`, `spreadMethod`, `patternUnits`, `patternContentUnits`, `patternTransform`, `font-family`, `font-size`, `font-weight`, `font-style`, `text-anchor`, `dominant-baseline`, `letter-spacing`, `xml:space`, `href` e `xlink:href` (só `#id`), `stdDeviation`, `in`, `in2`, `result`, `dx`, `dy`, `mode`, `operator`, `k1`, `k2`, `k3`, `k4`, `type` e `values` (só em `feColorMatrix`), `flood-color`, `flood-opacity`, `version`.

**CSS** (`<style>` e atributo `style`): o bloco inteiro sai se tiver `@` (`@import`, `@font-face`), `\` (escape), `expression`, `javascript:` ou `url(` que não seja `url(#id)`. `<style>` com `type` diferente de `text/css` sai.

As listas ficam em constantes de `empresas/logo.py` iguais às desta ADR. Mudar uma lista é mudar esta decisão: pede ADR nova ou nota datada aqui, com a Segurança.

### 5. Tamanho e resultado

- Tamanho pelo `viewBox` (quatro números, largura e altura maiores que zero). Sem `viewBox`, `width` e `height` numéricos (sem unidade ou em `px`) viram `viewBox="0 0 w h"`. Sem nenhum dos dois → "O SVG precisa de tamanho definido (viewBox)."
- A raiz gravada leva `viewBox`, `width` e `height` iguais ao tamanho do `viewBox`, para o `<img>` não cair no 300×150 do navegador. `logo_largura` e `logo_altura` são esse tamanho arredondado, no mínimo 1.
- Depois da limpeza, tem que sobrar ao menos um `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon` ou `text` com conteúdo → senão "Não encontramos desenho neste SVG.".
- Serializado em UTF-8, sem declaração XML, com o namespace SVG padrão e `xlink` só se usado.

### 6. PNG (aceito em 13 out 2026, ver a nota)

A tela diz "PNG ou SVG, até 2 MB"; o modelo de dados dizia só SVG. Quem decide é a Segurança (`[decisão]` da T-130 no backlog). Até lá, o backend implementava só o SVG (superado pela nota abaixo).

Se o PNG for aceito, o desenho já está definido: assinatura `\x89PNG` nos primeiros bytes; Pillow (já no projeto) com `Image.MAX_IMAGE_PIXELS` em 4096 × 4096; `verify()` e reabertura; até 4.096 pixels de lado; codificado de novo como PNG RGBA (mantém a transparência), sem os blocos de texto e metadados, como as fotos da vistoria. `logo_largura` e `logo_altura` em pixels.

**Nota de 13 out 2026 (T-153): PNG aceito pela Segurança** (`C:/Users/Jota/Documents/giro-produto/decisao-t153-seguranca.md`, fora do git). O backend aceita PNG com estas condições, que substituem o parágrafo acima onde ele diverge:

1. **Formato:** os 8 primeiros bytes são a assinatura completa `\x89PNG\r\n\x1a\n` (a de `comum/arquivos.py`), nunca a extensão nem o `Content-Type`. Os 2 MB são conferidos antes de abrir. Depois de abrir, `imagem.format == "PNG"`; outro formato (assinatura forjada) é erro de leitura.
2. **Pixels antes de decodificar:** lado até 4.096 px e área até 4.096 × 4.096, conferidos em `imagem.size` logo depois do `Image.open` (que só lê o cabeçalho) e antes do `load()`; largura e altura de pelo menos 1. **Não** mudar `Image.MAX_IMAGE_PIXELS`: é global do processo e quebraria as fotos da vistoria de 48 MP, e o Pillow só levanta erro acima do dobro dele. Proteção extra opcional: `warnings.catch_warnings()` com `simplefilter("error", Image.DecompressionBombWarning)` só dentro de `limpar_logo`.
3. **Verificação e reabertura:** `Image.open` → `verify()` → reabrir dos bytes → conferir o tamanho de novo → `load()`. `UnidentifiedImageError`, `OSError`, `ValueError`, `SyntaxError`, `DecompressionBombError` ou `DecompressionBombWarning` viram 400 de leitura, nunca 500 e nunca o texto da exceção na resposta.
4. **Codificação nova, sem metadados:** `convert("RGBA")` antes de copiar os pixels (mantém a transparência de PNG em paleta com `tRNS`, em cinza e de 16 bits); **não** reaproveitar `comum.arquivos.sem_metadados`, que perde a paleta do modo `P`. Grava com `Image.new("RGBA", tamanho)` e `paste` (ou `frombytes`) e `save(format="PNG", optimize=True)` sem `pnginfo`, `exif`, `icc_profile` nem `save_all`: saem `tEXt`, `zTXt`, `iTXt`, `eXIf`, `iCCP`, `tIME`, `pHYs` e os blocos privados. PNG animado grava só o primeiro quadro, sem erro. Os bytes enviados não vão para o storage nem para o log.
5. **Resultado:** `logo_largura` e `logo_altura` são os pixels do PNG gravado; se o PNG novo passar de 2 MB, "O logo passa de 2 MB.". Nome no storage pelo resumo do conteúdo limpo.
6. **Mensagem de leitura:** PNG que não abre, truncado, com assinatura forjada ou de outro formato depois de aberto: "Não conseguimos ler este PNG. Exporte o logo de novo pelo seu programa de desenho.", com `WARNING` no log (schema e id do usuário, sem conteúdo), como no SVG.

Servir e mostrar não muda (item 7). Testes com `s_12` no nome: `test_s_12_png_passa_sem_metadados`, `test_s_12_png_em_paleta_mantem_cores_e_transparencia`, `test_s_12_png_acima_de_4096_recusado_sem_decodificar`, `test_s_12_png_assinatura_forjada`, `test_s_12_png_truncado`, `test_s_12_png_poliglota`, `test_s_12_png_animado_grava_primeiro_quadro` e `test_s_12_png_servido_com_nosniff`.

### 7. Depois de gravar

O logo continua servido só por `GET /api/marca/logo/`, com os cabeçalhos da T-128, e mostrado só por `<img>`. O PDF lê o arquivo limpo do storage do schema atual (S-09). Nenhuma tela ou e-mail põe o SVG inline.

## Consequências

- Um logo com conteúdo ativo é recusado com mensagem clara; um logo comum de programa de desenho passa, mais leve, sem os metadados.
- Efeitos de SVG fora da lista (animação, imagem embutida, fonte externa, `feImage`, `feTurbulence`) não funcionam. Para logo, basta.
- `defusedxml` entra como dependência nova do backend.
- Testes com `s_12` no nome em `empresas/tests/`, um por vetor: `script`, `onload` (e `ONLOAD`), `foreignObject`, `href="javascript:..."`, `xlink:href` externo, `<image href="data:...">`, `<animate>` e `<set>` mudando `href`, DTD com entidade (bilhão de risadas), entidade externa, `<style>@import`, `url(http...)` em `fill` e em `style`; e os que passam: SVG do Inkscape com metadados (sai sem eles), sem `viewBox` mas com `width`/`height`, gradiente com `url(#id)`, `<use href="#id">`.

## Alternativas descartadas

- **Tirar o conteúdo ativo e gravar o resto, sem avisar.** Grava um logo diferente do enviado e esconde uma tentativa de ataque.
- **Converter todo SVG em PNG no upload.** Pede biblioteca de renderização nova (cairosvg e libcairo na imagem), perde a nitidez do vetor na tela, e não tira a necessidade de ler o SVG com segurança.
- **Servir os arquivos de usuário de outro domínio.** É a proteção mais forte para arquivo aberto direto, mas pede domínio, certificado e CDN novos; com a lista fechada e os cabeçalhos da T-128, o ganho é pequeno para um arquivo só. Fica para quando houver mais arquivos públicos de usuário.
