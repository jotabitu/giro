# T-329 · Leitura do CRLV-e: cor por lista, conferência do pai e arquivo órfão · backend → seguranca, qa, orquestrador

**O que foi feito** (achados M-01, B-01, B-02 e B-03 de `docs/seguranca/2026-10-19-t328-leitura-crlv.md`):
- **M-01:** `crlv.cor` só aceita a tabela de cores do Denatran (`CORES_DO_DENATRAN`: amarela, azul, bege, branca, cinza, dourada, grená, laranja, marrom, prata, preta, rosa, roxa, verde, vermelha, fantasia). A comparação ignora acento e o valor sai com a grafia da lista ("GRENA" vira "grená"). Fora da lista, o campo fica vazio, então o nome do proprietário não vira cor.
- **B-01:** `leitura_documentos.conferir` (o pai) recusa ano fora de 1900 até o ano que vem, texto com caractere de controle (`\x00`-`\x1f` e `\x7f`), `combustivel` fora do enum e `marca_modelo` acima de 60 (era 80).
- **B-02:** em `cadastrar_com_crlv`, uma falha depois de gravar o PDF devolve o erro original e apaga o arquivo pelo provedor (`arquivos.provedor().apagar`, que trata o versionamento do bucket), num `try` próprio que nunca troca a exceção. Antes, o `storage.delete` levantava `NotImplementedError` (ADR 0009) e virava 500.
- **B-03:** `FILE_UPLOAD_MAX_MEMORY_SIZE = 3 MB` em `config/settings/base.py`, o teto da borda (T-258). Até esse tamanho, o upload fica na memória e nunca vai para o disco do contêiner. O teto de memória por processo fica em workers × threads × 3 MB.

**Onde:** `backend/integracoes/leitura_documentos/crlv.py`, `__init__.py`; `backend/apps/veiculos/services.py`; `backend/config/settings/base.py`; `backend/tests/aceitacao/test_t328_seguranca_crlv.py`.

**Regras cobertas:** VEI-08, AUD-09, AUD-06. Os 3 `xfail` estritos de `test_t328_seguranca_crlv.py` viraram testes comuns e passam. Também entraram `test_vei_08_cor_da_lista_do_denatran`, `test_vei_08_pai_confere_texto_combustivel_e_dica` e `test_vei_08_upload_ate_3_mb_fica_na_memoria`. Com a cor por lista, `test_t265_leitura_crlv.py` e `test_t331_calibracao_crlv.py` (as cores dos reais e dos fictícios) seguem passando, assim como o catálogo e os veículos (T-257, T-013). ruff, ruff format --check e mypy estão limpos no backend inteiro.

**O que ficou de fora:** o B-04 (a senha vazia do `pypdf`) é texto da ADR, com o arquiteto.

**Próximo passo para quem recebe:**
- **seguranca:** conferir as correções contra o relatório.
- **devops:** ficar de olho no teto de memória (workers × threads × 3 MB) ao dimensionar homologação.
