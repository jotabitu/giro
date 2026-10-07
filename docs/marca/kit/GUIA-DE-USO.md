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
