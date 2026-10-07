# GIRO Motos — Guia de uso do logo

## 1. O logo
**Ideia:** a chave é a roda traseira da moto. Alugou, girou a chave, saiu rodando.
A cabeça da chave é o anel partido do GIRO (o giro da roda e do motor).

| Versão | Arquivo | Quando usar |
|---|---|---|
| Horizontal (principal) | `giro-motos-horizontal.svg` / `-fundo.svg` | site, fachada, materiais em geral |
| Empilhado | `giro-motos-empilhado.svg` / `-fundo.svg` | camiseta, adesivo, posts quadrados |
| Símbolo | `giro-motos-simbolo.svg` | quando o nome já aparece por perto |
| Ícone de app / avatar | `giro-motos-app-icon.svg`, `giro-motos-avatar.svg` | app, redes sociais, WhatsApp |
| Versão pequena (só a chave) | `giro-motos-small.svg`, `web/favicon.*` | abaixo de 32 px: favicon, ícones minúsculos |
| Uma cor | `mono/` (preto, branco, limão) | carimbo, gravação, bordado, impressão em 1 cor |

## 2. Área de proteção
Mantenha livre, em volta do logo, uma margem igual a **1× o diâmetro externo da cabeça da chave**.
A margem cresce e diminui junto com o logo. Nada de texto, foto ou borda dentro dela.

## 3. Tamanho mínimo
| Versão | Tela | Impressão |
|---|---|---|
| Horizontal | 120 px de largura | 30 mm |
| Empilhado | 80 px de largura | 20 mm |
| Símbolo completo | 32 px | 10 mm |
| Abaixo disso | usar a **versão pequena** (só a chave) | — |

## 4. Cores
| Nome | HEX | RGB | CMYK (aprox.) |
|---|---|---|---|
| Grafite | `#111114` | 17 17 20 | C0 M0 Y0 K95 (ou preto rico C60 M40 Y40 K100) |
| Verde-limão | `#C8F04A` | 200 240 74 | C17 M0 Y69 K6 |
| Cinza-claro | `#ECEBF0` | 236 235 240 | C2 M2 Y0 K6 |

O CMYK é uma conversão aproximada. Peça prova de cor à gráfica (e um Pantone equivalente) antes de imprimir em volume.

**Combinações aprovadas**
- **Principal:** chave limão + moto e nome cinza-claro sobre **grafite**.
- **Fundos claros (branco, cinza-claro):** tudo em **grafite**. Não use limão sobre branco, porque o contraste é baixo.
- **Fundo limão:** tudo em **grafite**.
- **Fotos:** versão branca ou grafite sobre uma área calma da imagem, ou o logo dentro de um retângulo grafite.

## 5. Tipografia
- O "GIRO" foi desenhado em vetor e não depende de fonte. Use sempre o arquivo, nunca digite o nome.
- Para textos de apoio (site, panfletos), sugestão gratuita e com o mesmo espírito geométrico: **Outfit** ou **Urbanist** (Google Fonts, licença OFL).

## 6. Não faça
- Não distorça, estique, gire ou incline o logo.
- Não troque as cores fora da paleta nem aplique degradê, sombra ou contorno.
- Não mude a posição da chave em relação à moto nem o tamanho do símbolo em relação ao nome.
- Não use o limão sobre fundo branco.
- Não aplique sobre fundos com muita informação sem um retângulo de apoio.

## 7. Arquivos
- `*.svg`: mestres vetoriais (site, gráfica, plotagem). Para AI/EPS/PDF, abra o SVG no Illustrator ou Inkscape e salve.
- `png/`: imagens prontas (logo com fundo, ícone de app 1024 px).
- `web/`: favicon.ico, ícones PNG, `site.webmanifest` e `head-snippet.html` (colar no `<head>` do site).
- `apresentacao.html` / `slides/`: apresentação com aplicações (fachada, camiseta, app, adesivo, site, cartão).
- `gerar_kit.py`: script que gera todos os SVGs. Para ajustes, altere-o e rode `python gerar_kit.py`.

## 8. Antes de registrar
Faça uma busca de marca no **INPI** (classes 39 — locação de veículos e 12 — veículos) e uma busca reversa de imagem
antes de registrar ou investir em fachada.

## 9. Uso no sistema Giro
- O produto se chama **Giro**. A marca aparece no painel da plataforma, nas telas de compra, no assistente de implantação e no rodapé "Tecnologia Giro" das telas das locadoras.
- Dentro do sistema de cada locadora vale a marca da locadora (white label); o Giro não aparece.
- Sobre fundo branco (menus do painel): símbolo dentro de um quadrado grafite + "GIRO" em grafite.
- Sobre fundo grafite (login do painel): logo horizontal principal (chave limão, moto e nome cinza-claro).

## 10. SVGs principais

### Horizontal (fundo grafite)
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 690 256" width="690" height="256" role="img" aria-labelledby="t"><title id="t">GIRO Motos</title>
<g transform="translate(16 48) scale(1.088) translate(-6 -74)"><g id="symbol"><path fill="#ECEBF0" fill-rule="evenodd" d="M168 168 A36 36 0 1 1 240 168 A36 36 0 1 1 168 168 Z M184 168 A20 20 0 1 0 224 168 A20 20 0 1 0 184 168 Z"/><path fill="#ECEBF0" d="M186 92 H198 L217.83 166 L206.63 169 Z M168 82 H196 Q202 82 202 88 Q202 94 196 94 H174 Z M206 100 H213 Q221 100 221 108 V110 Q221 118 213 118 H206 Z M100 124 Q110 104 142 102 H180 L188 118 L164 138 H112 Q100 138 100 128 Z M116 138 H158 V151 H116 Z"/><path fill="#C8F04A" d="M14 165 A42 42 0 0 1 98 165 H77 A21 21 0 0 0 35 165 Z M110 171 A42 42 0 0 1 26 171 H47 A21 21 0 0 0 89 171 Z M98 159 H150 L159 168 L150 177 H98 Z M120 177 H132 V193 H120 Z M140 177 H150 V189 H140 Z"/></g></g><g id="wordmark" transform="translate(323.4013605442177 80.0) scale(0.8)" fill="#ECEBF0"><path fill-rule="evenodd" d="M123.0 60.0 A61.5 61.5 0 1 1 104.99 16.51 L88.02 33.48 A37.5 37.5 0 1 0 99.0 60.0 Z M146 0 H170 V120 H146 Z M196 0 H252 A36 36 0 0 1 252 84 H220 V120 H196 Z M220 24 V60 H252 A12 12 0 0 0 252 24 Z M226 84 H260 L296 120 H262 Z M316.0 60 A61.5 61.5 0 1 1 439.0 60 A61.5 61.5 0 1 1 316.0 60 Z M340.0 60 A37.5 37.5 0 1 0 415.0 60 A37.5 37.5 0 1 0 340.0 60 Z"/><path d="M65.5 59 H123.0 V81 H65.5 Z"/></g>
</svg>

```

### Horizontal (fundo claro)
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 690 256" width="690" height="256" role="img" aria-labelledby="t"><title id="t">GIRO Motos</title>
<g transform="translate(16 48) scale(1.088) translate(-6 -74)"><g id="symbol"><path fill="#111114" fill-rule="evenodd" d="M168 168 A36 36 0 1 1 240 168 A36 36 0 1 1 168 168 Z M184 168 A20 20 0 1 0 224 168 A20 20 0 1 0 184 168 Z"/><path fill="#111114" d="M186 92 H198 L217.83 166 L206.63 169 Z M168 82 H196 Q202 82 202 88 Q202 94 196 94 H174 Z M206 100 H213 Q221 100 221 108 V110 Q221 118 213 118 H206 Z M100 124 Q110 104 142 102 H180 L188 118 L164 138 H112 Q100 138 100 128 Z M116 138 H158 V151 H116 Z"/><path fill="#111114" d="M14 165 A42 42 0 0 1 98 165 H77 A21 21 0 0 0 35 165 Z M110 171 A42 42 0 0 1 26 171 H47 A21 21 0 0 0 89 171 Z M98 159 H150 L159 168 L150 177 H98 Z M120 177 H132 V193 H120 Z M140 177 H150 V189 H140 Z"/></g></g><g id="wordmark" transform="translate(323.4013605442177 80.0) scale(0.8)" fill="#111114"><path fill-rule="evenodd" d="M123.0 60.0 A61.5 61.5 0 1 1 104.99 16.51 L88.02 33.48 A37.5 37.5 0 1 0 99.0 60.0 Z M146 0 H170 V120 H146 Z M196 0 H252 A36 36 0 0 1 252 84 H220 V120 H196 Z M220 24 V60 H252 A12 12 0 0 0 252 24 Z M226 84 H260 L296 120 H262 Z M316.0 60 A61.5 61.5 0 1 1 439.0 60 A61.5 61.5 0 1 1 316.0 60 Z M340.0 60 A37.5 37.5 0 1 0 415.0 60 A37.5 37.5 0 1 0 340.0 60 Z"/><path d="M65.5 59 H123.0 V81 H65.5 Z"/></g>
</svg>

```

### Ícone de app
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="t"><title id="t">GIRO Motos</title>
<rect width="256" height="256" rx="56" fill="#111114"/><g transform="translate(34 70.900826446281) scale(0.777) translate(-6 -74)"><g id="symbol"><path fill="#ECEBF0" fill-rule="evenodd" d="M168 168 A36 36 0 1 1 240 168 A36 36 0 1 1 168 168 Z M184 168 A20 20 0 1 0 224 168 A20 20 0 1 0 184 168 Z"/><path fill="#ECEBF0" d="M186 92 H198 L217.83 166 L206.63 169 Z M168 82 H196 Q202 82 202 88 Q202 94 196 94 H174 Z M206 100 H213 Q221 100 221 108 V110 Q221 118 213 118 H206 Z M100 124 Q110 104 142 102 H180 L188 118 L164 138 H112 Q100 138 100 128 Z M116 138 H158 V151 H116 Z"/><path fill="#C8F04A" d="M14 165 A42 42 0 0 1 98 165 H77 A21 21 0 0 0 35 165 Z M110 171 A42 42 0 0 1 26 171 H47 A21 21 0 0 0 89 171 Z M98 159 H150 L159 168 L150 177 H98 Z M120 177 H132 V193 H120 Z M140 177 H150 V189 H140 Z"/></g></g>
</svg>

```

### Versão pequena (favicon)
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256" role="img" aria-labelledby="t"><title id="t">GIRO Motos ícone</title>
<path fill="#111114" d="M10 123 A76 76 0 0 1 162 123 H124 A38 38 0 0 0 48 123 Z M182 133 A76 76 0 0 1 30 133 H68 A38 38 0 0 0 144 133 Z M174 112 H232 L244 128 L232 144 H174 Z M200 144 H218 V166 H200 Z"/>
</svg>

```


## Arquivos

O kit completo está em `kit/` (SVG, PNG, favicons, versões monocromáticas e o guia original em `kit/GUIA-DE-USO.md`). Cinco arquivos vieram vazios no pacote original e precisam ser exportados de novo: `giro-motos-empilhado.svg`, `web/favicon.svg`, `web/giro-motos-simbolo-favicon.svg`, `web/giro-motos-simbolo-square.svg` e `mono/giro-motos-empilhado-escuro-white-800.png`.
