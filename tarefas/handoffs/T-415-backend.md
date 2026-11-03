# T-415 · CRLV-e: escolher a versão quando várias batem · backend → frontend, qa

**O que foi feito:** a leitura do CRLV-e devolve as versões do catálogo que batem com o texto do documento, para a pessoa escolher uma (decisão do dono em 29 out 2026). Palavras do documento que não existem em nenhuma versão (o "NB" de "CHEVROLET/CRUZE LT NB") são ignoradas. Quando todas as versões são da mesma marca, a marca vem preenchida. A lista de modelos aceita os apelidos da marca do Detran ("Chevrolet" acha "GM - Chevrolet").

**Onde:** `backend/apps/veiculos/catalogo.py` (`candidatos(texto)`, `_pelas_versoes`, `listar` com apelidos; `achar_modelo` passa a ser o candidato único), `backend/apps/veiculos/leitura.py` (`_resposta`, `LIMITE_DE_CANDIDATOS = 20`), `backend/apps/veiculos/api/serializers.py` (`DicasDaLeituraSerializer.candidatos`). Não mexe em `integracoes/leitura_documentos/crlv.py`.

**Contrato:** `docs/api/veiculos.md` ("POST /api/veiculos/leitura-crlv/" e "GET /api/veiculos/modelos/"); `docs/api/openapi.yaml` (`DicasDaLeitura.candidatos`, obrigatório, lista de `ModeloDoCatalogo`). Mudança aditiva, mais uma mudança de comportamento: com várias versões da mesma marca, `campos.marca` agora vem preenchida e entra em `lidos` (antes vinha `null`).

**O Cruze (CRLV-e real do Detran-CE, "CHEVROLET/CRUZE LT NB"):** `campos.marca` "GM - Chevrolet", `campos.modelo` `null`, 8 campos, `dicas.marca_modelo` com o texto e `dicas.candidatos` com "CRUZE LT 1.4 16V Turbo Flex 4p Aut.", "CRUZE LT 1.8 16V FlexPower 4p Aut." e "CRUZE LT 1.8 16V FlexPower 4p Mec.".

**Regras cobertas:** `VEI-08` (testes em `backend/tests/aceitacao/test_t415_versoes_crlv.py`: `test_vei_08_candidatos_ignoram_sufixo_que_nao_existe_na_fipe`, `test_vei_08_candidatos_so_a_marca_nao_basta`, `test_vei_08_crlv_do_cruze_preenche_a_marca_e_traz_as_versoes`, `test_vei_08_versoes_demais_ficam_para_a_busca`, `test_vei_08_lista_de_modelos_aceita_o_apelido_da_marca`). Ajustados para o formato novo: `test_t265_leitura_crlv.py`, `test_t374_catalogo_completo.py` (o Mobi Like agora traz a marca Fiat e 2 versões) e `test_t406_marcas_crlv.py`.

**Checks:** ruff, ruff format e mypy do backend inteiro limpos; 49 testes do CRLV-e e do catálogo passando (t415, t406, t374, t257, t265), mais t331 e t328 na primeira rodada.

**O que ficou de fora:** a tela da escolha.

**Próximo passo para quem recebe:**
- frontend (mesma branch `t-415-crlv-versoes`): rode `npm run api:gerar`. Acerte o falso `src/testes/falsos/falso-frota.ts` (`dicas` ganha `candidatos: []`, obrigatório; o typecheck do CI quebra sem isso, como na T-416). Em `PreencherPeloCrlv.tsx`, quando `dicas.candidatos` vier com itens, mostre as versões para a pessoa escolher uma; a escolha preenche marca e modelo como a escolha da lista. Com `campos.marca` preenchida e `candidatos` vazio (mais de 20 versões), deixe a marca escolhida e a busca de modelo aberta. A lista de modelos já aceita "Chevrolet" na marca e na busca, sem mudança no cliente.
- qa: com o PDF do Cruze ("CHEVROLET/CRUZE LT NB"), a tela diz "CRLV-e lido · 8 campos preenchidos" e oferece as 3 versões; com "SUZUKI/YES 125", continua 7 campos e sem versões (CA-247-05).
- arquiteto (T-421): a T-415 acrescenta só `dicas.candidatos`; nenhuma chave nova em `campos` ou `lidos`.
