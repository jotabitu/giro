# T-414 (parte do arquiteto) · Modelo e contrato das fotos do veículo · arquiteto → backend, frontend, qa

**O que foi feito:** modelo, rotas e ADR da galeria do veículo e das fotos da última vistoria na ficha (`VEI-10`, CA-414-01 a 14), e o seed das fotos do QXA-4B21 descrito para o backend.

**Onde:**
- `docs/decisoes/0036-fotos-do-veiculo.md` (nova) e o índice em `docs/decisoes/README.md`.
- `docs/decisoes/modelo-de-dados.md`, item 9a: `veiculos.FotoVeiculo`.
- `docs/api/veiculos.md`, seção "Fotos do veículo" (nova), e o bullet `vistoria_recente.fotos` em "Blocos da ficha".

**Decisões (ADR 0036):**
1. `veiculos.FotoVeiculo` no schema da empresa, no armazenamento privado de sempre (`comum.arquivos`). A vitrine pública (T-419) não abre o bucket; se precisar, decide uma cópia derivada na ADR dela.
2. Reprocessar no envio com `comum.arquivos.validar` e `sem_metadados` (os da vistoria), síncrono, **sem redimensionar e sem miniatura**: o baixado é a foto guardada.
3. **Uma foto por requisição**, enviadas em sequência pela tela: o proxy corta em 12 MB e a recusa de uma não derruba as outras.
4. Dois links por foto: `url` (ver) e `url_download` (baixar com `Content-Disposition`, o nome com a placa). `comum.arquivos.url_assinada(caminho, baixar_como=None)`.
5. Capa como bool com único parcial; trocar herda `ordem` e `capa`.
6. `vistoria_recente.fotos` passa a trazer as 12 (fixas e de avaria), ainda fornecido por `vistorias`.

**Contrato (resumo):**
- `GET /api/veiculos/{id}/`: blocos `galeria` (todos os perfis) e `vistoria_recente.fotos` com todas as fotos (sem o financeiro), `acoes.editar_fotos`.
- `GET /api/veiculos/{id}/fotos/` · `POST /api/veiculos/{id}/fotos/` (um `arquivo`) · `POST .../fotos/{foto_id}/trocar/` · `POST .../fotos/{foto_id}/capa/` · `POST .../fotos/{foto_id}/apagar/`. As de escrita devolvem a galeria inteira.
- Erros: 400 `validacao` em `campos.arquivo` com as duas mensagens da `VEI-10`; 403 para vendedor, vistoriador e financeiro; 403 `PLT-07` para o suporte, mesmo em "ver e editar"; 409 `VEI-10` em `vendido` e `baixado`; 404 em foto inativa ou de outro veículo.
- Nome baixado: `QXA-4B21-galeria-<numero>.<ext>` (numero = posição na exibição, capa = 1) e `QXA-4B21-vistoria-<saida|chegada>-<posição>.<ext>` (`lado-esquerdo`, `avaria-1`).

**Regras cobertas:** `VEI-10`, `VIS-01`, `AUD-01`, `AUD-05`, `PLT-07` (no contrato; os testes são do backend).

## Próximo passo para o Backend

1. **`comum.arquivos`:** `url_assinada(caminho, baixar_como: str | None = None)`. S3: `Params["ResponseContentDisposition"] = f'attachment; filename="{nome}"'`. Falso: `baixar=<nome>` na consulta e na assinatura (`assinar(caminho, expira, nonce, baixar="")`, com a mensagem de hoje quando `baixar` vem vazio, para os links atuais não quebrarem); `arquivos_dev.servir` põe o `Content-Disposition`. Recuse (`ValueError`) nome fora de `[A-Za-z0-9.-]`. Teste com os dois provedores (S3 com `botocore.stub` ou conferindo os `Params`).
2. **Model e migração** de `FotoVeiculo` como no item 9a, com os dois únicos parciais e o índice.
3. **`veiculos.services`:** `enviar_foto(veiculo, arquivo, usuario)`, `trocar_foto(foto, arquivo, usuario)`, `usar_como_capa(foto, usuario)`, `apagar_foto(foto, usuario)`. Trave o veículo (`select_for_update`), confira `vendido`/`baixado` (409 `VEI-10`) antes do arquivo, valide e limpe antes de abrir a transação (como `vistorias.services.enviar_foto`), e troque as mensagens de `validar` pela da `VEI-10`. Recuse PDF. Evento de auditoria do veículo por ação (`veiculo.foto_enviar`, `foto_trocar`, `foto_capa`, `foto_apagar`), sem a imagem. Apagada a capa, a ativa de menor `ordem` vira capa na mesma transação.
4. **`veiculos.selectors`:** `galeria(veiculo)` e `capa(veiculo)`; representação da foto com `numero`, os dois links, `url_expira_em` e `nome_arquivo` (placa por `comum.documentos.placa_com_hifen`). Bloco `galeria` e `acoes.editar_fotos` só no detalhe; `editar_fotos` é `false` para o token de suporte.
5. **`vistorias.selectors`:** o bloco `vistoria_recente` com todas as fotos ativas (fixas na ordem de `PosicaoFoto`, depois as de avaria por `tirada_em`), `numero`, `rotulo` ("Avaria 1"...), `avaria_id`, `rotulo_tipo` e os links. A placa vem de quem monta a ficha, como parâmetro.
6. **Rotas** em `veiculos/api/` como no contrato; `suporte_proibido = True` nas de escrita (`contas/api/acesso.py`). OpenAPI e `npm run api:gerar` no mesmo PR.
7. **Seed** (`backend/seed/`, linha "Fotos do QXA-4B21" das regras; idempotente):
   - Imagens fictícias geradas na hora com Pillow (nada binário no git): JPG 1600×1200, fundo neutro e o texto "QXA-4B21 · <rótulo> · foto fictícia".
   - Galeria: com o relógio do seed em 12 mar 2025, a Mariana envia, pelo `enviar_foto`, lateral, frente e painel, nesta ordem, e escolhe a frente com `usar_como_capa`. Resultado: 3 ativas, a frente com `numero` 1. Só se o QXA-4B21 não tiver foto.
   - Vistoria: na saída concluída da LOC-2841 (a que `seed/financeiro._saida` cria), 12 `FotoVistoria` ativas, criadas direto como a vistoria do seed já é: as 5 posições fixas e 7 `avaria`, com `tirada_em` em 23 set, pela vistoria já concluída. **Sem** criar `Avaria`: o bloco `avarias` e os números do seed não mudam. Só se a vistoria não tiver foto.
   - Os outros 85 veículos ficam sem galeria; as outras vistorias, sem fotos.
8. **Testes** `test_vei_10_*` cobrindo CA-414-01 a 09 e 11 a 14 pela API (CA-414-04: baixar o arquivo e conferir que não há EXIF nem GPS; CA-414-12: o nome no `Content-Disposition` e o link vencido depois de 15 min pelo relógio).

## Próximo passo para o Frontend

1. Rode `npm run api:gerar` com o OpenAPI do backend; até lá, trabalhe com o contrato.
2. **Editar (`/veiculos/[id]/editar`, telas `Veiculo-Editar-*`):** seção "Galeria de fotos" com `GET .../fotos/`; contador "3 de 20 fotos" com `total` e `limite`. Escolher várias fotos dispara um `POST` por foto, **uma depois da outra**, na ordem da escolha; cada item mostra a recusa de `campos.arquivo` e as outras seguem. 413 do proxy vira "Envie uma foto JPG ou PNG de até 10 MB.". "Usar como capa", "Trocar" e "Apagar" (com confirmação) chamam as rotas e trocam a galeria pela resposta. Sem `editar` (ou com `motivo`), a galeria fica só para ver, com o `motivo` quando vier.
3. **Ficha (`/veiculos/[id]`, telas `Veiculo-*`):** bloco `galeria` (capa primeiro; vazio: "Nenhuma foto do veículo." e "Adicionar fotos" só com `acoes.editar_fotos`) e, à parte, `vistoria_recente` com "Vistoria de saída · LOC-2841 · 23 set" (de `rotulo_tipo`, `locacao_codigo` e `concluida_em`) e todas as fotos. Sem o bloco, a seção não aparece.
4. **Visualizador (telas `Veiculo-Visualizador-*`):** abre na foto tocada e passa só pelas fotos da mesma origem, na ordem do bloco. "Baixar" é um link para `url_download`; não monte nome nem use `download` com outro nome. Antes de abrir ou baixar com `url_expira_em` passado, recarregue a ficha (invalide a consulta).
5. Na galeria, a foto não tem legenda (`rotulo` `null`): mostre "Foto 1 de 3", não "Frente" ou "Traseira" como na tela de referência.

## O que ficou de fora

- Miniatura e capa na lista da Frota e no catálogo: T-418.
- Vitrine pública: T-419, com ADR própria (item 1 da 0036).
- Lista de vistorias anteriores por veículo: continua fora, como na T-275.

## Para o QA

Critérios em `docs/qa/criterios/T-414.md`. No CA-414-12, o nome vem do `Content-Disposition` do `url_download`, não do atributo `download`.
