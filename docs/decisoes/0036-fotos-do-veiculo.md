# Fotos do veículo: galeria própria, reprocessamento e link para baixar com nome

**Status:** aceita · 03 nov 2026 · T-414 (regras: `VEI-10`, `VIS-01`, `AUD-01`, `AUD-05`, `PLT-07`; critérios CA-414-01 a 14; decisão do dono de 29 out 2026) · detalha a 0009 (arquivos privados), a 0011 (limites entre apps) e a 0015 (blocos de outros apps)

## Contexto

Até aqui o veículo não tinha foto própria: as únicas fotos eram as da vistoria (`vistorias.FotoVistoria`). A `VEI-10` cria a **galeria do veículo** (até 20 fotos de cadastro, com capa, para a ficha e depois para o catálogo da T-418) e pede que a ficha mostre, à parte, **todas** as fotos da última vistoria concluída. As duas origens se veem ampliadas e se baixam com um nome que leva a placa ("QXA-4B21-galeria-1.jpg"), sempre pelo link temporário de 15 minutos.

Quatro pontos são caros de desfazer:

1. **Onde a galeria mora.** A galeria é a base do catálogo e, mais tarde, da vitrine pública (T-419). Se ela nascer num armazenamento público "porque um dia vai para a internet", o veículo da locadora fica exposto antes de a locadora decidir vender.
2. **O reprocessamento.** A `AUD-05` e a `VEI-10` pedem a foto sem localização. Redimensionar ou gerar miniatura no envio muda o que "Baixar" entrega, e a regra diz que o baixado é a foto "como foi guardada".
3. **O envio de várias fotos.** O proxy aceita corpo de até 12 MB (`infra/README.md`, `client_max_body_size 12m`). Um envio com 20 fotos de 10 MB não passa por ele, e um 413 no meio derruba as fotos boas junto.
4. **O nome do arquivo baixado.** O link assinado aponta para o S3, em outra origem. O navegador ignora o atributo `download` do `<a>` entre origens, então o nome tem que vir do servidor, no cabeçalho `Content-Disposition`.

## Decisão

### 1. `veiculos.FotoVeiculo`, no schema da empresa, no armazenamento privado

Model novo no app `veiculos` (dono da galeria; modelo de dados, item 9a). O arquivo usa o `FileField` privado de sempre (`comum.arquivos.armazenamento_privado`, caminho `<schema>/veiculos/fotoveiculo/<id>/<uuid>.<ext>`), no mesmo bucket das fotos de documento e de vistoria. Isso garante, sem nada novo:

- leitura só por URL assinada de 15 minutos, gerada a cada `GET` (`AUD-05`);
- apagamento junto com a empresa no 90º dia, pelo prefixo do schema (`AUD-08`, ADR 0025);
- nenhum arquivo de negócio apagado: a foto apagada pela tela fica `ativo = False`, com o arquivo guardado (`VEI-10`, convenções).

O catálogo interno (T-418) lê a galeria pelo mesmo link assinado. A vitrine pública (T-419) **não** abre este bucket: se ela precisar de link sem validade, a ADR dela decide uma cópia derivada, publicada só para o veículo `a_venda` e retirada quando ele sai da venda.

### 2. Reprocessar no envio, sem redimensionar

O envio passa por `comum.arquivos.validar` e `comum.arquivos.sem_metadados`, os mesmos da foto da vistoria (`vistorias.services.enviar_foto`): só JPG ou PNG pelo conteúdo, até 10 MB; a orientação do EXIF vai para os pixels; a imagem é refeita do zero, sem EXIF, GPS, ICC nem texto embutido (JPG em qualidade 90, PNG sem perdas). É síncrono, na requisição do envio: uma foto de até 10 MB leva menos de um segundo, e a resposta já devolve a galeria certa.

- O PDF, que o `validar` aceita para documentos, é recusado aqui com a mensagem da galeria.
- As mensagens de `validar` ("O arquivo passa de 10 MB.", "Envie um arquivo PDF, JPG ou PNG.") **não** saem na galeria: o serviço troca todas pela da `VEI-10`, "Envie uma foto JPG ou PNG de até 10 MB.".
- **Sem redimensionar e sem miniatura** nesta tarefa. A ficha mostra a foto guardada com `object-fit` e `loading="lazy"`. Se o catálogo ou a vitrine pedirem miniatura, ela é derivada da foto guardada, num campo à parte, sem mudar o original que "Baixar" entrega.
- A imagem que não abre (corrompida, bomba de descompressão) é recusada como formato errado, como já faz `sem_metadados`.

### 3. Uma foto por requisição; o frontend envia em sequência

`POST /api/veiculos/{id}/fotos/` recebe **um** arquivo. Escolher 18 fotos na tela vira 18 envios, um depois do outro, cada um com a própria resposta. Assim:

- cada envio fica abaixo dos 12 MB do proxy;
- a foto recusada não derruba as outras ("as outras do mesmo envio seguem", `VEI-10`);
- a ordem é a da escolha, e a recusada pelo limite é sempre a que passou de 20 (CA-414-03). Em paralelo, a trava manteria o limite, mas a foto recusada seria qualquer uma.

O limite de 20 é conferido no serviço com `select_for_update` no veículo, na mesma transação que grava a foto. Não há `CHECK` de contagem no banco.

### 4. Dois links por foto: ver e baixar

`comum.arquivos.url_assinada(caminho, baixar_como=None)` ganha o parâmetro opcional. Com ele, o link sai com `Content-Disposition: attachment; filename="<nome>"`:

- **S3:** `generate_presigned_url` com `ResponseContentDisposition`, que entra na assinatura.
- **Falso (desenvolvimento e testes):** a consulta leva `baixar=<nome>`, e a assinatura HMAC passa a cobrir `caminho|expira|nonce|baixar` (sem `baixar`, a mensagem assinada é a de hoje, e os links atuais continuam valendo). `comum/arquivos_dev.servir` põe o cabeçalho.

O nome é montado pela API e só tem `A-Z`, `a-z`, `0-9`, `-` e `.`, para não abrir espaço a injeção de cabeçalho. Cada foto, nas duas origens, sai com `url` (ver, inline), `url_download` (baixar), `url_expira_em` (o mesmo para os dois) e `nome_arquivo`. Os dois links são novos a cada `GET` e valem 15 minutos (`AUD-05`); depois disso o próprio armazenamento recusa, e a tela recarrega a ficha para ter outros.

### 5. A capa é um campo da foto, com índice único

`FotoVeiculo.capa` (bool) com único parcial `(veiculo)` quando `ativo AND capa`. A primeira foto ativa vira capa; "Usar como capa" tira a marca da anterior e põe na escolhida, na mesma transação; apagada a capa, a ativa mais antiga (menor `ordem`) vira capa. A ordem de exibição é capa primeiro, depois as outras por `ordem` (a de envio). Trocar uma foto inativa a antiga e cria a nova com a mesma `ordem` e a mesma `capa`, ligada pela antiga (`substituida_por`).

### 6. As fotos da vistoria na ficha seguem com o app `vistorias`

O bloco `vistoria_recente` da ficha continua fornecido por `vistorias.selectors` (ADR 0015). `fotos` passa a trazer todas as fotos ativas da vistoria (as 5 posições fixas e as de avaria), não só as fixas, com os mesmos campos de link da galeria. `vistorias` não importa `veiculos` para montar o nome: recebe a placa de quem monta a ficha. Nenhuma foto da vistoria vira `FotoVeiculo` e vice-versa (`VEI-10`, `VIS-01`).

## Consequências

- `comum.arquivos` ganha `baixar_como`, que o comprovante da despesa (T-416) e outros downloads podem usar.
- O app `veiculos` passa a ter uma tabela com arquivo; a importação de veículos (ADR 0017) não traz foto.
- Sem miniatura, a ficha de um veículo com 20 fotos grandes pesa mais no celular. Fica registrado como o primeiro ponto a rever quando a T-418 medir o catálogo.
- Reverter o item 4 é barato (é um parâmetro); reverter o item 1 (galeria pública) seria caro, e por isso fica fechado aqui.
