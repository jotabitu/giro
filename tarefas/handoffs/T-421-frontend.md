# T-421 · Campos do CRLV-e no cadastro, no editar e na ficha do veículo · frontend → qa, orquestrador

**O que foi feito:** a parte do frontend da `VEI-09`, na mesma branch e no mesmo PR (#488) do backend. Cadastro, editar e ficha mostram combustível, dados do documento, rastreador e anotações; o cadastro lê os 16 campos do CRLV-e; o editar lê o CRLV-e pelo veículo (padrão A) e manda o comprovante no `PATCH`.

**Onde (tudo em `frontend/src`):**
- `lib/veiculos.ts`: `CAMPOS_VEI_09` (campo da tela ↔ chave pontuada da API), `NOME_DO_CAMPO_DA_API` (erro 400 `documento.potencia_cv` cai no campo), `paraCorpoVeiculo` e `paraCorpoEdicao` com os blocos `documento`, `rastreador` e `anotacoes`, `valoresDaLeitura` lendo as chaves pontuadas, `temMotorEObservacoes`, rótulos de combustível e espécie.
- `lib/api/tipos-frota.ts`: `VeiculoDetalhe` ganha `combustivel`, `documento`, `rastreador` e `anotacoes` (tipos do OpenAPI gerado); `NovoVeiculo` e `EdicaoVeiculo` ganham os blocos e `leitura`.
- `lib/api/veiculos.ts`: multipart do cadastro com chaves achatadas (`documento.lotacao`, `rastreador.numero`, `anotacoes`); `lerCrlvDoVeiculo` (`veiculos_leitura_crlv_do_veiculo_create`).
- `components/frota/CamposDoDocumento.tsx` (novo): painéis "Dados do documento" e "Rastreador e anotações", usados pelo cadastro e pelo editar. Número do motor e observações só aparecem quando a API os mandou.
- `components/frota/NovoVeiculoForm.tsx`, `EditarVeiculo.tsx`, `PreencherPeloCrlv.tsx`: campos novos, marca "Lido do documento", leitura no editar com `veiculoId`, 422 `crlv_outro_veiculo` mostrada como vem, comprovante no `PATCH`.
- `components/frota/FichaVeiculo.tsx`: bloco "Dados do documento" na coluna lateral (desktop) e no celular; vazio é "—"; motor e observações sem linha quando ausentes.
- `testes/falsos/falso-frota.ts`: os falsos acertados (leitura com as 9 chaves pontuadas e 16 campos, `lerCrlvDoVeiculo`, blocos e formatos do contrato, QXA-4B21 com a linha das regras).

**Regras cobertas:** `VEI-09`, `VEI-08`, `VEI-01`. Testes com o código no nome em `lib/veiculos.test.ts`, `lib/api/veiculos.test.ts`, `components/frota/EditarVeiculo.test.tsx`, `FichaVeiculo.test.tsx` e `NovoVeiculo.test.tsx` (`test_vei_09_...`, `test_vei_08_...`): CA-421-01 (16 campos), 04 (rastreador e anotações fora da leitura), 05 (multipart achatado), 06, 07 (chave pontuada), 08, 09, 10, 11, 12 e 14.

**Checks:** `npm run lint`, `tsc --noEmit` e a suíte inteira do Vitest (98 arquivos, 883 testes) passam.

**Decisões minhas:**
- Texto que não é inteiro em potência, cilindrada, lotação e peso vai como veio no corpo, para a API recusar no campo com a mensagem dela (a tela não decide o formato).
- No editar, a tela manda todas as chaves do bloco (campo vazio vai `null`, que apaga); número do motor e observações só vão quando a ficha as trouxe, para nunca apagar o que a pessoa não via.
- A leitura não toca no rastreador nem nas anotações, nem apaga o que a pessoa digitou neles.
- O combustível virou campo da tela (antes ia escondido no corpo). Escolhida a lista fechada da API, com "Não informado" como vazio.

**O que ficou de fora / aviso ao QA:**
- **Não conferi a 1440 e a 390 px no navegador.** O compose de desenvolvimento roda a `develop`, sem a migração 0007 deste PR, então não havia como abrir a ficha e os formulários com a API real. A marcação reusa as classes dos painéis existentes (`md:grid-cols-2`, `CartaoDoCelular`); falta o olho no CA-421-11 nas duas larguras e o E2E dos CA-421-05 e 10 com os PDFs de `documentos_pdf.py`.
- A tela de referência (`docs/telas`) não tem os campos novos; a ordem e os rótulos seguem a tabela da `VEI-09`. Se o design-system quiser outro arranjo, é ajuste de posição.

**Próximo passo:** qa (E2E com os PDFs fictícios e conferência visual a 1440 e 390 px), depois o aval do dono para o merge do #488.
