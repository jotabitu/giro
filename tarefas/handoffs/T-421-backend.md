# T-421 · Campos do CRLV-e no cadastro e na ficha do veículo · backend → frontend, qa

**O que foi feito:** a parte do backend da `VEI-09`. O veículo ganhou as 12 colunas do contrato (potência, cilindrada, espécie, tipo, carroceria, lotação, peso bruto, número do motor, observações do CRLV-e, rastreador e anotações), todas opcionais. A ficha e as respostas do `POST` e do `PATCH` trazem os blocos `documento`, `rastreador` e `anotacoes`. O número do motor e as observações vêm só para administrador e gerente; para vendedor, vistoriador e financeiro as duas chaves ficam ausentes. A leitura do CRLV-e lê os 9 campos novos (até 18). A rota nova `POST /api/veiculos/{id}/leitura-crlv/` faz a leitura no editar (padrão A).

**Onde:**
- `backend/apps/veiculos/models.py`: `Especie`, `CAMPOS_DA_VEI_09` (chave da API → campo), colunas, `CHECK` de faixa e `CAMPOS_AUDITORIA` (`inteiro`); migração `0007_campos_do_crlv`.
- `backend/apps/veiculos/services.py`: `_validar_vei_09` (formatos e mensagens do contrato, chave pontuada), `dados_da_vei_09`, `valores_pontuados`; `editar` aceita os blocos por chave e grava o `veiculo.editar` com as chaves pontuadas e, com o comprovante da leitura no editar, o `preenchido_pelo_documento`; `cadastrar_com_crlv` compara também os campos novos.
- `backend/apps/veiculos/selectors.py`: `dados_do_documento` e `representacao(..., com_dados_do_documento=True)`.
- `backend/apps/veiculos/api/`: `DocumentoDoVeiculoEntradaSerializer`, `RastreadorEntradaSerializer` (erros achatados na chave pontuada; em multipart o DRF monta `documento.potencia_cv`), `VeiculoComDadosDoDocumentoSerializer`, `CamposDoCrlv` com as 9 chaves pontuadas, `LeituraCrlvNoEditar`; view `LeituraCrlvDoVeiculoView` e a rota.
- `backend/apps/veiculos/leitura.py`: `DO_DOCUMENTO`, conferência de placa e chassi no editar (422 `crlv_outro_veiculo`; sem os dois lidos, 422 `VEI-08`).
- `backend/integracoes/leitura_documentos/crlv.py`: validadores novos (`potencia_cilindrada`, `especie_tipo` com os tipos do CTB acentuados, `carroceria`, `lotacao`, `peso_bruto_kg`, `numero_motor`), o bloco das observações em várias linhas e `VAZIO` para o campo que o documento traz vazio ("NÃO APLICAVEL", asteriscos, potência 0). `__init__.py`: segunda barreira com faixas, espécie, motor e a quebra de linha só nas observações.
- `backend/comum/comprovante_leitura.py`: o comprovante leva `veiculo` (o do editar); `conferir_do_veiculo` e `campos_pelo_hash`. O comprovante do editar não vale no cadastro, e o do cadastro não vale no editar.
- `backend/seed/frota.py` e `seed/moto_rapida.py`: QXA-4B21 com a linha "Dados do CRLV-e do QXA-4B21" (flex, 15 cv, 162 cc, passageiro, Motocicleta, 2, 290 kg, motor, alienação, rastreador e anotação). Os outros 85 ficam sem.
- `backend/config/settings/base.py`: `EspecieVeiculoEnum` no OpenAPI.

**Contrato:** `docs/api/veiculos.md` ("Dados do documento, rastreador e anotações", "Preencher pelo CRLV-e" e "POST /api/veiculos/{id}/leitura-crlv/"); `docs/api/openapi.yaml` regenerado. Bate com o contrato; nenhuma divergência.

**Regras cobertas:** `VEI-09`, `VEI-08`, `VEI-01` (testes em `backend/tests/aceitacao/test_t421_campos_crlv.py`):
- `test_vei_08_le_os_campos_da_vei_09` (CA-421-01 a 03, com os 3 PDFs da lista e os 2 no leiaute do Detran da T-331/T-406), `test_vei_08_le_16_campos_com_alienacao`, `test_vei_08_nao_le_o_que_nao_e_da_lista` (CA-421-04), `test_vei_08_corrigidos_com_campos_novos` (CA-421-05, multipart achatado);
- `test_vei_09_campos_opcionais` (CA-421-06), `test_vei_09_cadastro_com_os_blocos`, `test_vei_09_formatos` (CA-421-07, os 15 casos no cadastro e no editar), `test_vei_09_formatos_no_servico`, `test_vei_09_editar_por_chave`, `test_vei_09_combustivel_e_auditoria` (CA-421-08), `test_vei_09_quem_edita` (CA-421-09);
- `test_vei_08_leitura_no_editar`, `test_vei_08_leitura_no_editar_outro_veiculo`, `test_vei_08_leitura_no_editar_quem_pode`, `test_vei_08_editar_com_comprovante`, `test_vei_08_comprovante_do_editar_nao_vale_no_cadastro` (CA-421-10);
- `test_vei_09_motor_e_observacoes_por_perfil` (CA-421-11 e 12), `test_vei_09_alienacao_nao_bloqueia` (CA-421-13), `test_vei_09_veiculo_antigo` (CA-421-14), `test_vei_09_isolamento_entre_empresas`;
- parser: `test_vei_09_parser_converte_o_texto_do_documento`, `test_vei_09_parser_observacoes_em_varias_linhas`, `test_vei_09_processo_filho_confere_os_campos_novos`; e `test_vei_09_detran_campo_do_documento` em `test_t331_calibracao_crlv.py`.

Ajustados para os 16 campos: `test_t265_leitura_crlv.py` (o `test_vei_08_le_os_9_campos` virou `test_vei_08_le_os_16_campos`; "CRLV-e lido · 16 campos preenchidos"; CA-247-05 passa de 7 a 14 campos), `test_t331_calibracao_crlv.py` (o `..._traz_os_nove_campos` virou `..._traz_os_campos`) e `test_t415_versoes_crlv.py` (o Cruze passa de 8 a 15). Os PDFs fictícios de `documentos_pdf.py` ganharam os campos novos: o `Crlv` simples tem os rótulos da `VEI-09`, e o `CrlvDetran` usa os campos do dataclass no lugar dos valores fixos. Novos: `CRLV_ALIENADO`, `CRLV_PNB7C04`, `CRLV_CARRO`, e o `CRLV_QXA4B21` com os dados do seed.

**Checks:** ruff, ruff format e mypy limpos; OpenAPI com `--validate` sem erro. Os 126 testes do CRLV-e e do catálogo e os 321 de veículos, seed, ficha, movimentações, reserva e arquitetura passam. A suíte completa está registrada na mensagem ao orquestrador.

**Decisões técnicas minhas:**
- `CrlvDetran` sem os valores fixos de antes ("110CC/0110", "HA12E1234567", "ALIENADO FIDUCIARIAMENTE"): agora vêm dos campos, com os padrões do `crlv-tbc5h21.pdf`.
- A potência aceita "CV" ou "CC" antes da barra, porque o leiaute calibrado na T-331 trazia "110CC/0110".
- Espécie fora do CTB não para a busca nas outras colunas, e os dois campos ficam vazios. Tipo fora da tabela do CTB vem com só a 1ª maiúscula ("Triciclo eletrico").
- As observações vão até "MENSAGENS SENATRAN", até 3 linhas em branco seguidas ou até 12 linhas abaixo do rótulo, só na coluna do rótulo (o bloco do seguro DPVAT, na mesma linha, fica de fora).

**Seed:** num banco novo, o QXA-4B21 nasce com os dados. Num banco que já tinha a frota, o próximo `make seed` preenche o QXA-4B21 pelo editar, como a Mariana, uma vez só (`frota.garantir_dados_do_crlv`; a saída diz "dados do CRLV-e do QXA-4B21"). Testes `test_vei_09_seed_dados_do_crlv_do_qxa4b21` e `test_vei_09_seed_preenche_o_qxa4b21_do_banco_antigo` em `test_t127_seed.py`.

**O que ficou de fora:** as telas (frontend).

**Próximo passo para quem recebe:**
- **frontend (mesma branch `t-421-backend-campos-crlv`, mesmo PR):** rode `npm run api:gerar`. O que muda no cliente:
  - `GET /api/veiculos/{id}/` (`VeiculoDetalhe`) e as respostas do `POST /api/veiculos/` e do `PATCH /api/veiculos/{id}/` (agora `VeiculoComDadosDoDocumento`) trazem `documento` (`DocumentoDoVeiculo`), `rastreador` (`Rastreador`) e `anotacoes`, obrigatórios. `documento.numero_motor` e `documento.observacoes` são opcionais no tipo: ausentes para vendedor, vistoriador e financeiro. A lista da Frota (`Veiculo`) não muda.
  - `LeituraCrlv.campos` (`CamposDoCrlv`) ganha 9 chaves pontuadas obrigatórias (`"documento.potencia_cv"` etc.). Acerte os falsos (`src/testes/falsos/falso-frota.ts` e o que mais montar a ficha ou a leitura), ou o typecheck quebra.
  - Corpo do `POST` em JSON e do `PATCH`: `documento` e `rastreador` como objetos, `anotacoes` como texto. No `POST` em multipart (com o CRLV lido), as chaves achatadas, como vêm da leitura: `documento.lotacao`, `rastreador.numero`, `anotacoes`. Erro 400 com a chave pontuada em `campos` (`"documento.potencia_cv"`), para mostrar no campo.
  - Editar: "Preencher pelo documento" chama `POST /api/veiculos/{id}/leitura-crlv/` (`veiculos_leitura_crlv_do_veiculo_create`), que não traz placa nem chassi. A 422 `crlv_outro_veiculo` traz a `mensagem` para mostrar como vem. Mande o `leitura` da resposta no corpo do `PATCH`, junto com o que foi lido.
  - Combustível visível e editável no cadastro, no editar e na ficha; rótulos de `especie` e as unidades na tela (contrato).
- **qa:** os PDFs fictícios da lista dos critérios existem em `backend/tests/aceitacao/documentos_pdf.py` (`CRLV_TBC5H21`, `CRLV_ALIENADO`, `CRLV_QXA4B21`, `CRLV_PNB7C04`, `CRLV_CARRO`). Use `.pdf()` para gerar os arquivos do E2E. O CA-247-01 passa a "16 campos preenchidos".
