# Galeria de fotos do veículo · 10 nov 2026

**Tarefa:** T-414 · **Autor:** seguranca · **Base:** PR #499 do backend (`origin/t-414-backend-fotos`, sobre a `develop` de 10 nov), ADR 0036, `docs/api/veiculos.md` ("Fotos do veículo").
**Escopo:** upload (formato, tamanho, reprocessamento, imagem gigante em pixels, nome), limite de 20, permissões e suporte (`PLT-07`), 409 em vendido e baixado, escopo de filial, isolamento entre empresas, links de 15 minutos com `Content-Disposition`, log e Sentry, seed.

## Resumo

O desenho está certo: arquivo privado com caminho aleatório por schema, reprocessado sem EXIF nem GPS, link novo de 15 minutos, nome de download com lista fechada de caracteres e dentro da assinatura, permissão e status antes de decodificar, limite com o veículo travado.

**Dois achados médios para corrigir antes do merge:**

- **M-01:** o suporte em "só ver" recebe links assinados das fotos. A ADR 0013 proíbe isso.
- **M-02:** uma imagem gigante em pixels passa pelo reprocessamento e leva o processo a cerca de 2 GB.

Há também dois achados baixos, que não bloqueiam.

| Ponto | Como está | Onde conferi |
| --- | --- | --- |
| Formato | JPG ou PNG pelo conteúdo (`validar`: assinatura dos primeiros bytes e extensão aceita); PDF recusado no serviço; a imagem é decodificada e gravada de novo, então nada do arquivo original (polyglot, texto embutido) chega ao bucket | `services._foto_limpa`; `test_vei_10_ca_414_02_*` (grande, HEIC, PDF, vazio, JPG quebrado) |
| Tamanho | 10 MB no `validar`; o proxy corta em 12 MB (413) antes do Django; o upload acima de 3 MB vai para disco temporário, não para a memória | `comum/arquivos.py:72`; `infra/proxy/snippets/giro-locais.conf.template:12`; `FILE_UPLOAD_MAX_MEMORY_SIZE` |
| EXIF e GPS | imagem nova (`Image.new` + `paste`), orientação aplicada antes; sem EXIF, GPS, ICC nem texto | `test_vei_10_ca_414_04_sem_localizacao` (JPG com GPS de entrada) |
| Nome do arquivo | `<schema>/veiculos/fotoveiculo/<id>/<uuid>.<ext>`; o nome enviado não vai para o caminho nem para a resposta | `caminho_privado` |
| Ordem das conferências | perfil e suporte (403) antes de ler o corpo; escopo de filial (404) e status (409 `VEI-10`) antes de decodificar; a foto de outro veículo dá 404 antes do arquivo na troca | `FotosView`, `_AcaoNaFotoView`, `enviar_foto`, `trocar_foto` |
| Limite de 20 | contado com o veículo travado (`select_for_update`), na transação que grava; a decodificação fica fora da trava; únicos parciais de capa e de ordem no banco | `enviar_foto`; `test_vei_10_ca_414_03_limite_de_20` |
| Permissões | envio, troca, capa e apagar só administrador e gerente (`GESTAO`); suporte 403 `PLT-07` nos dois modos (`suporte_proibido`) | `test_vei_10_ca_414_08_quem_mexe` |
| Vendido e baixado | 409 `VEI-10` antes e depois da trava | `test_vei_10_ca_414_09_*` |
| Escopo de filial | `_veiculo` filtra por `selectors.no_escopo` (404 fora dele); a foto é sempre buscada dentro do veículo | `test_vei_10_escopo_de_filial_e_foto_de_outro_veiculo` |
| Isolamento | dado no schema da empresa; o caminho começa pelo schema; o token de uma empresa é recusado no host de outra (ADR 0013) | `test_vei_10_isolamento_entre_empresas` (só no banco; ver B-02) |
| Links | dois por foto, novos a cada leitura, 15 minutos (`VALIDADE_DA_URL`); `url` abre e `url_download` baixa | `test_vei_10_ca_414_12_*` |
| `Content-Disposition` | nome montado pela API a partir da placa normalizada e do número; `fullmatch` em `[A-Za-z0-9][A-Za-z0-9.-]{0,149}` (sem aspas, `;`, CR nem LF) antes de assinar; no S3, `ResponseContentDisposition` entra na assinatura; no provedor falso, `baixar` entra no HMAC e é conferido de novo ao servir. A mensagem sem `baixar` é a de antes, e um link antigo não ganha `baixar` sem a chave, porque o caminho não tem `\|` | `disposicao_de_download`, `arquivos_dev.servir`; `test_vei_10_nome_de_download_so_com_caracteres_seguros`, `test_vei_10_link_s3_leva_o_content_disposition` |
| Conteúdo servido | só imagem regravada pelo Pillow, com o tipo do formato; nada que o navegador execute | `sem_metadados` |
| Auditoria | `veiculo.foto_enviar`, `foto_trocar`, `foto_capa`, `foto_apagar`, com ids e sem a imagem; quem apagou fica na foto | `services._evento_da_galeria` |
| Log e Sentry | nenhum `logger` novo; a recusa sai `from None` (sem a exceção do Pillow); o Sentry vai sem corpo de requisição, sem variáveis locais e sem `request.data` (`comum/sentry.py`) | leitura do diff |
| Seed | imagens fictícias geradas na hora com o Pillow (nada binário no git), enviadas pelo serviço como a Mariana (passam pela mesma validação e geram a auditoria), idempotente; o comando recusa produção | `seed/fotos.py`; `seed_moto_rapida.py:24` |

## Achados

### M-01 · média · O suporte em "só ver" recebe os links assinados das fotos

**Onde:**

- `FotosView` tem `suporte_somente_leitura = True` (`apps/veiculos/api/views.py:494`).
- A ficha (`VeiculoView`, `:285`) também tem. Ela monta `galeria` e `vistoria_recente` sem olhar o modo do suporte (`selectors.representacao`, `bloco_galeria`; `vistorias/leituras.montar_ficha`).
- O `AtorSuporte` tem `perfil = "administrador"` e passa por todos os filtros de perfil.

**Problema:** a ADR 0013, item 2, diz que no "só ver" fica de fora, mesmo sendo GET, a "geração de URL assinada de documento e foto (`AUD-05`)". A T-315 seguiu essa regra: o suporte em "só ver" não recebe `fotos_chegada`.

Com este PR, o suporte em "só ver" recebe `url` e `url_download` de:

- toda a galeria, em `GET .../fotos/` e na ficha;
- **todas** as fotos da última vistoria, agora também as de avaria.

As fotos da vistoria mostram o veículo de um cliente, às vezes com a pessoa ou o local. O bloco `vistoria_recente` já trazia as 5 fotos fixas desde a T-275, mas este PR aumenta o que sai e cria a rota da galeria.

O contrato (`docs/api/veiculos.md`, "Quem pode") marca "sim" para o suporte, sem separar os modos. O contrato diverge da ADR, e o backend seguiu o contrato.

**Reprodução:** entrar como suporte com "só ver" na Moto Rápida e chamar `GET /api/veiculos/<QXA-4B21>/fotos/`: 200 com 3 `url_download`. Na ficha do mesmo veículo, `vistoria_recente.fotos` vem com 12 links. O teste do PR só cobre o suporte em "ver e editar".

**Correção antes do merge:**

- No "só ver", `GET .../fotos/` volta 403 `PLT-07`: tirar `suporte_somente_leitura` da `FotosView`. A tela do editar não abre para o suporte de qualquer jeito, porque `editar_fotos` é `false`.
- Na ficha, `galeria` e `vistoria_recente` continuam com `total`, `numero`, `rotulo` e datas, mas cada foto vem com `url`, `url_download` e `url_expira_em` nulos. A condição é `getattr(usuario, "e_suporte", False) and usuario.permissao == SUPORTE_SO_VER`. Um helper em `comum` serve para os dois apps.
- Teste novo: `test_plt_07_suporte_so_ver_nao_recebe_link_de_foto` (ficha e `GET .../fotos/`).
- O **arquiteto** ajusta a tabela "Quem pode" do contrato: suporte "só ver" vê a galeria e a vistoria sem links; "ver e editar" vê com links. Se o produto quiser o suporte vendo as fotos no "só ver", isso pede ADR nova revendo o item 2 da 0013.

### M-02 · média · Imagem gigante em pixels passa pelo reprocessamento (cerca de 2 GB por envio)

**Onde:** `comum/arquivos.sem_metadados` (`comum/arquivos.py:95-106`) chama `original.load()` sem conferir o tamanho em pixels.

**Problema:** o Pillow só **recusa** (`DecompressionBombError`) acima de 2 × `MAX_IMAGE_PIXELS`, cerca de 179 MP. Entre 89,5 MP e 179 MP ele só emite `DecompressionBombWarning`, e o `except` não pega aviso. Os 10 MB não ajudam: uma imagem de cor lisa comprime quase tudo.

`load()`, `exif_transpose` (cópia) e `Image.new` + `paste` deixam três cópias da imagem na memória ao mesmo tempo.

**Reprodução:** feita num contêiner `giro-backend:latest` (Pillow 13.0.0), com os passos de `sem_metadados` copiados, fora do repositório:

| Imagem | Arquivo | Resultado | Pico de memória |
| --- | --- | --- | --- |
| PNG RGB 13000 × 13000 (169 MP) | 518 KB | só o aviso | **1.957 MB** |
| PNG em tons de cinza do mesmo tamanho | 194 KB | só o aviso | 506 MB |

Um administrador ou gerente de qualquer empresa derruba o worker com poucos envios em sequência. A máquina de produção é pequena e divide o processo entre as empresas.

A mesma porta serve as fotos de vistoria (vistoriador), da chegada da movimentação, os documentos do cliente e as notas. O defeito já existia, mas este PR abre mais uma entrada, e a ADR 0036 (item 2) conta com `sem_metadados` para barrar "bomba de descompressão". Como está, ela só barra as maiores.

**Correção antes do merge** (cerca de 5 linhas em `comum`, valendo para todas as entradas):

- Depois de `Image.open` e **antes** de `load()`, recusar `largura × altura` acima de um teto, com a mesma `ErroDeValidacao`, como o logo já faz (`empresas/logo.py`, `_conferir_pixels`).
- Teto sugerido: 50 MP. O comentário do logo diz que as fotos da vistoria chegam a 48 MP. Uma foto de celular de 200 MP passaria a ser recusada, o que é aceitável para a galeria e a vistoria. Se o produto discordar, o teto sobe, mas fica abaixo de 89 MP.
- Envolver a decodificação em `warnings.catch_warnings()` com `simplefilter("error", Image.DecompressionBombWarning)` e incluir o aviso no `except`, sem mexer no `Image.MAX_IMAGE_PIXELS` global.
- Teste novo: `test_aud_05_foto_gigante_em_pixels_recusada`, com um PNG liso de 10000 × 6000 (60 MP, poucos KB): 400 com a mensagem da galeria e nada gravado.

### B-01 · baixa · `SyntaxError` do Pillow escapa e vira 500

**Onde:** o `except` de `sem_metadados` pega `UnidentifiedImageError`, `OSError`, `ValueError` e `DecompressionBombError`.

**Problema:** um fuzz de 8.000 arquivos corrompidos (JPG e PNG com bytes trocados e cortes) deu 4 `SyntaxError: broken PNG file (chunk ...)` fora do `except`. Cada um volta 500, em vez de 400 com "Envie uma foto JPG ou PNG de até 10 MB.", e vai para o Sentry. O Sentry não leva o arquivo nem as variáveis locais, então nada vaza. É só barulho e uma resposta errada.

**Correção:** incluir `SyntaxError` e `EOFError` no `except`, como `empresas/logo.py` faz. Pode ir junto com a M-02.

### B-02 · baixa · O teste de isolamento só olha o banco

**Onde:** `test_vei_10_isolamento_entre_empresas` troca o schema e confere que a empresa B não tem `FotoVeiculo`.

**Problema:** o teste não cobre o caminho pela API. O isolamento está garantido pela infraestrutura (schema por empresa, token preso ao host, ADR 0013), então não há falha hoje. O que falta é a prova pela rota, que o checklist pede ("teste com duas empresas").

**Correção (não bloqueia):**

- No host da empresa B, `GET`, `POST .../trocar/` e `POST .../apagar/` com o id do veículo e da foto da empresa A voltam 404, e a foto da A continua ativa.
- `foto.arquivo.name` começa por `empresa_a/veiculos/fotoveiculo/`.

## Observação, sem achado

- **Nome de download inválido derruba a ficha.** `disposicao_de_download` levanta `ValueError` se o nome sair fora do formato. Na leitura da ficha, isso viraria 500 da ficha inteira, com o nome na mensagem do Sentry. Hoje não acontece: a placa é normalizada para `[A-Z0-9]` e nunca fica vazia. Se um dia o nome vier de texto livre (a T-416 vai reusar o `baixar_como` para o comprovante), monte o nome com uma troca segura, por exemplo `foto-<id>.<ext>`, em vez de levantar erro na leitura.

## O que o backend corrige antes do merge

1. **M-01:** sem links de foto para o suporte em "só ver" (`GET .../fotos/` 403 `PLT-07`; ficha com `url`, `url_download` e `url_expira_em` nulos), com teste. Avisar o **arquiteto** para alinhar o contrato.
2. **M-02:** teto em pixels antes do `load()` e aviso de bomba virando erro em `comum/arquivos.sem_metadados`, com teste.
3. **B-01:** `SyntaxError` e `EOFError` no mesmo `except` (junto com o item 2).

B-02 pode entrar neste PR ou depois.

## Conferência das correções · 10 nov 2026

Conferi o commit `779170b7` do PR #499, com o CI verde. **Os quatro achados estão fechados.**

| Achado | Correção | Teste |
| --- | --- | --- |
| M-01 | `FotosView` sem `suporte_somente_leitura`: no "só ver", `GET .../fotos/` volta 403 `PLT-07` sem link no corpo. Na ficha, `galeria` não gera links (`com_links=False`), e `vistoria_recente` passa por `arquivos.sem_links`; os três campos de link vêm nulos. `comum.autenticacao.suporte_so_ver` decide pelo `e_suporte` e pelo `permissao == "ver"`. A tabela "Quem pode" de `docs/api/veiculos.md` separa os dois modos | `test_plt_07_suporte_so_ver_nao_recebe_link_de_foto` (só ver: 3 + 12 fotos sem link e 403; ver e editar: links presentes e 200) |
| M-02 | `PIXELS_MAXIMOS = 50_000_000`, conferido pelo cabeçalho (`original.size`) antes do `load()`, com lado zero também recusado. `DecompressionBombWarning` vira erro dentro de `warnings.catch_warnings()`, sem mexer no limite global | `test_aud_05_foto_gigante_em_pixels_recusada` (60 MP e 120 MP, a faixa em que o Pillow só avisava); `test_aud_05_teto_em_pixels_vale_para_toda_foto` (acima de 50 MP nada é decodificado) |
| B-01 | `SyntaxError` e `EOFError` no `except`, com a recusa de formato (400) | `test_aud_05_png_quebrado_volta_400_e_nao_500` |
| B-02 | teste pela rota: a administradora da empresa B, no host dela, recebe 404 em ler, trocar, usar como capa e apagar com os ids da A; nada é gravado na B, e a foto da A continua ativa e capa; o arquivo da A fica em `empresa_a/veiculos/fotoveiculo/` | `test_vei_10_isolamento_entre_empresas_pela_rota` |

**Observação, sem achado:** no "só ver", o bloco `vistoria_recente` ainda assina os links dentro de `vistorias.leituras`, e a ficha os descarta antes de responder. Nenhum link chega ao suporte, e assinar um link no S3 é só uma conta local, sem chamada externa. Se um dia esse bloco servir outra rota, vale passar o `com_links` também para `montar_ficha`, como na galeria.

## Como conferi

- Leitura do diff completo do PR #499 contra a `develop`: `veiculos` (models, migração, services, selectors, api), `vistorias/leituras.py`, `comum/arquivos.py`, `comum/arquivos_dev.py`, `seed/fotos.py` e os testes da T-414.
- Também li `comum/autenticacao.py` (guarda do suporte), `comum/sentry.py`, a ADR 0013 (item 2), a ADR 0036 e o contrato.
- Memória e fuzz em contêiner avulso `giro-backend:latest` com `--memory` limitado, sem banco e sem tocar na cópia principal. Os scripts ficaram fora do repositório. Nenhum contêiner de teste ficou de pé.
