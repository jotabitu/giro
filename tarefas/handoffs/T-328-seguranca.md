# T-328 · Revisão de segurança da leitura do CRLV-e · segurança → orquestrador, backend, arquiteto

**O que foi feito:** revisão do código da T-265 (PR #352) contra a ADR 0026 e a revisão da T-247: processo filho e limites, upload do PDF, dados pessoais (`AUD-09`), comprovante com HMAC, 429, `no-store`, log e auditoria. Relatório: `docs/seguranca/2026-10-19-t328-leitura-crlv.md`.
**Onde:** `backend/tests/aceitacao/test_t328_seguranca_crlv.py` (3 `xfail` estritos, um por achado com código). Nenhum código de produção mudou.
**Regras cobertas:** VEI-08, AUD-09, AUD-06 (testes `test_aud_09_*`, `test_vei_08_*`).
**Testes rodados** (contêiner descartável com `pypdf` 6.21.1, banco `giro_seg`): `test_t265_leitura_crlv` e `test_t257_catalogo_modelos`, 34 passed; `test_t328_seguranca_crlv`, 3 xfailed, e com `--runxfail` cada um falha pelo motivo do achado. ruff, ruff format e mypy no arquivo novo. `pip-audit`: nada no `pypdf`.

**Achados:** M-01 (média), B-01 a B-04 (baixas). Sem achado alto. O resto está conforme a ADR e os pedidos da T-247 (M-01, M-02, M-04, B-01 a B-04 e B-06).

**Ordem de merge:** a branch `t-328-revisao-crlv` sai da `t-265-leitura-crlv`, e o teste usa o código dela. Entra depois do PR #352.

**Tarefa de backend para numerar:**

```
### T-??? · Leitura do CRLV-e: cor por lista, conferência do pai e arquivo órfão
- **Agente:** backend · **Depende de:** T-265 (PR #352) · **Regras:** VEI-08, AUD-09, AUD-06 · **Severidade:** média · **Origem:** T-328 (segurança), M-01, B-01, B-02 e B-03 de `docs/seguranca/2026-10-19-t328-leitura-crlv.md`
- **Pronto quando:**
  - `crlv.cor` aceita só a lista de cores do Denatran (amarela, azul, bege, branca, cinza, dourada, grená, laranja, marrom, prata, preta, rosa, roxa, verde, vermelha, fantasia), sem acento na comparação; fora dela, o campo não é preenchido. Tirar o `xfail` de `test_aud_09_cor_nao_aceita_o_nome_do_proprietario` (M-01);
  - `leitura_documentos.conferir` recusa ano fora de 1900 até o ano de hoje + 1, texto com caractere de controle, `combustivel` fora do enum e `marca_modelo` acima de 60. Tirar o `xfail` de `test_vei_08_pai_confere_a_faixa_dos_anos` (B-01);
  - em `cadastrar_com_crlv`, uma falha depois de gravar o PDF devolve o erro original e apaga o arquivo pelo provedor (`arquivos.provedor().apagar`), num `try` que nunca troca a exceção; ou o arquivo é gravado no `on_commit`. Tirar o `xfail` de `test_vei_08_falha_depois_de_gravar_o_arquivo_devolve_o_erro_certo` (B-02);
  - `FILE_UPLOAD_MAX_MEMORY_SIZE` acima do teto da borda (3 MB), para o PDF recusado não passar por disco (B-03).
```

**Para o arquiteto:** no item 6 da ADR 0026, trocar "falha, sem tentar senha vazia" por "falha (`is_encrypted`); o `pypdf` tenta a senha vazia ao abrir, e o trabalhador recusa antes de ler o texto" (B-04).

**Sugestões sem tarefa própria (para o orquestrador decidir):**
- A calibração com CRLV-e reais (pendente no handoff da T-265) confere duas coisas: o que fica abaixo de "COR PREDOMINANTE" (M-01) e se o PDF vem cifrado só com a senha do dono (B-04). Nesse caso a leitura falharia sempre, e aceitar esse PDF pede decisão na ADR.
- `pip-audit` acusa `weasyprint` 69.0 (`PYSEC-2026-3940` e `PYSEC-2026-4311`, corrigidos na 70.0). Não é da T-265; sugiro tarefa de backend ou devops para subir o limite em `requirements.txt`.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar a tarefa de backend, levar o B-04 ao arquiteto e decidir sobre o `weasyprint`.
- **Backend:** ao corrigir, tirar os três `xfail` deste arquivo.
