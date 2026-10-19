# T-328 · Leitura do CRLV-e (código da T-265)

**Data:** 19 out 2026 · **Agente:** segurança · **Regras:** VEI-08, VEI-01, PLT-07, AUD-05, AUD-06, AUD-09 · **ADR:** 0026, 0009, 0014
**Base:** branch `t-265-leitura-crlv` (PR #352, commit `efa659d`), handoff `tarefas/handoffs/T-265-backend.md`, e a revisão da ADR (`docs/seguranca/2026-10-16-t247-leitura-pdf.md`, achados M-01 a M-04 e B-01 a B-06).
**Método:** leitura de `integracoes/leitura_documentos/` (`__init__.py`, `trabalhador.py`, `crlv.py`), `comum/comprovante_leitura.py`, `comum/limites.py`, `apps/veiculos/leitura.py`, a view, o serializer e `services.cadastrar_com_crlv`. Execução num contêiner descartável (`giro-backend:latest` com `pypdf` 6.21.1 instalado na hora, banco `giro_seg`): `test_t265_leitura_crlv` e `test_t257_catalogo_modelos`, 34 passam; `pip-audit -r requirements.txt`; sondas do parser e do `pypdf` com `python -I`. Testes novos em `backend/tests/aceitacao/test_t328_seguranca_crlv.py` (3 `xfail` estritos, um por achado com código).

## Resumo

A implementação segue a ADR e os pedidos da T-247. Não há achado alto. O que a ADR pede para o filho, o upload, o comprovante, o 429, o `no-store` e o log está no código e tem teste.

| Código | Achado | Severidade | Quem |
| --- | --- | --- | --- |
| M-01 | A cor aceita qualquer palavra: o nome do proprietário pode sair como cor | média | backend |
| B-01 | O pai não confere a faixa dos anos nem o limite de 60 da dica | baixa | backend |
| B-02 | Falha depois de gravar o PDF vira 500 e deixa o arquivo órfão | baixa | backend |
| B-03 | Upload acima de 2,5 MB passa por disco antes da recusa | baixa | backend |
| B-04 | O `pypdf` tenta a senha vazia no construtor | baixa | arquiteto (texto da ADR) |

Fora do escopo, mas visto no `pip-audit`: o `weasyprint` 69.0 tem dois avisos (`PYSEC-2026-3940` e `PYSEC-2026-4311`), corrigidos na 70.0. Não é da T-265; vai para o orquestrador.

## O que está conforme

**Processo filho (ADR item 4; M-01, M-02, B-01, B-02 da T-247).**
- Chamada `[sys.executable, "-I", <caminho absoluto>, tipo]`, caminho calculado do `__file__`, sem `-m`. O trabalhador põe no `sys.path` só o diretório dele, que tem só `crlv.py` e `trabalhador.py` (o `__init__.py` do pai não é importado).
- `env` só `PATH` e `LANG`, `close_fds`, `stderr=DEVNULL`, `start_new_session`, sem `preexec_fn`. Testes de ambiente e de `preexec_fn` passam.
- `RLIMIT_CPU` 5 s, `AS` 512 MB, `FSIZE` 0, `NOFILE` 16 e `CORE` 0 aplicados pelo próprio filho, como primeira coisa, antes do `pypdf`, com `soft = hard` (não sobem de novo). Um `setrlimit` que falhe sai com exceção antes de ler a entrada.
- Pai: 8 s de relógio, `os.killpg` no grupo, leitura de no máximo 64 KB + 1 da saída, mensagem e motivo sempre do conjunto fechado `MOTIVOS`. A saída do filho nunca entra em exceção nem em log.
- No fim do filho, `django`, `comum`, `apps` e `config` fora de `sys.modules` (teste do diagnóstico). O `_diagnostico` devolve só nomes das variáveis e números dos limites.
- Semáforo de 2 por processo, sem espera, 503 `leitura_ocupada` com `Retry-After` e `no-store`.

**Upload (item 6; B-06).**
- 2 MB lidos no máximo (`read(2 MB + 1)`), na view e de novo no filho; tipo pelos primeiros bytes `%PDF-`, nunca pelo `Content-Type`. A extensão só escolhe entre o 400 e o 422, e não abre caminho.
- PDF com senha, mais de 3 páginas, sem texto, acima de 200 mil caracteres, travado, com saída grande, JavaScript e anexo: todos com teste. Só `extract_text(extraction_mode="layout")`; nada de formulário, anexo, XMP ou metadado.
- Ao salvar: primeiros bytes e 2 MB conferidos de novo, nome do armazenamento `<schema>/.../<uuid>.pdf`, `arquivo_nome` fixo `CRLV-e.pdf` (o nome enviado não fica), tipo do objeto pelo conteúdo (`_formato_do_conteudo`), nunca o enviado.
- `pypdf>=6.21.1,<7`; o `pip-audit` não acusa nada no `pypdf` hoje (M-04 da T-247).

**Dados pessoais (`AUD-09`, item 4 da ADR).** O parser não tem rótulo do proprietário. A resposta só traz as 9 chaves, e o pai descarta qualquer chave fora da lista (`conferir`). O suporte: 403 `PLT-07` em "só ver", leitura em "ver e editar" (o CRLV-e não tem CPF na resposta). A exceção é o M-01: a cor.

**Comprovante (item 8; B-04).** `django.core.signing` com sal por tipo e 30 min; leva tipo, SHA-256 do arquivo, schema, usuário (ou `suporte-<acesso>`) e um resumo por campo `HMAC(HMAC(pepper, "leitura-documento"), sha256 ‖ 0x00 ‖ campo ‖ 0x00 ‖ valor)`, sem valor. O salvar confere assinatura, validade, tipo, schema, usuário e o SHA-256 com `compare_digest`; qualquer divergência trata o comprovante como ausente e o cadastro segue sem a marca. Testes de outra pessoa, outro arquivo, adulterado e do resumo diferente do `CampoHashBusca` passam. O comprovante assinado não é cifrado (base64 legível), mas não leva nada que a pessoa já não tenha.

**429 (item 6).** `LeituraDocumentoPorUsuario` 30/h (suporte contado pelo acesso) e `LeituraDocumentoPorEmpresa` 200/h, com a chave por schema do `make_key` do django-tenants. O DRF confere permissão e limite antes do handler, então a recusa (400 e 422) conta e o filho não roda depois do limite. Escopos `leitura_documento_*` prontos para a CNH-e somar.

**`no-store`, log e auditoria (item 9).** `Cache-Control: no-store` no 200 e no 503 (o 400, o 403, o 422 e o 429 não levam dado lido). Uma linha `INFO` com tipo, resultado, motivo, quantidade, milissegundos, schema e usuário; nem nome do arquivo, nem valor, nem comprovante. O 422 é igual para toda falha, e o motivo fica só no log. O evento `veiculo.cadastrar` leva só `preenchido_pelo_documento {tipo, campos, corrigidos}`. O Sentry do projeto já está sem variáveis locais e sem corpo (`comum/sentry.py`, M-03 da T-247).

## Achados

### M-01 · A cor aceita qualquer palavra · média

**Onde:** `integracoes/leitura_documentos/crlv.py`, `cor()` e `_candidatos()`.
**Problema:** o valor de um rótulo é o texto na mesma linha ou o primeiro texto não vazio até 3 linhas abaixo, na coluna dele. O validador da cor aceita qualquer sequência de letras e espaços até 30 caracteres. Se a cor não estiver logo abaixo do rótulo (leiaute diferente, campo vazio, o texto do `pypdf` em outra ordem), o primeiro texto que cair na coluna vira a cor: um rótulo ("nome") ou o próprio nome do proprietário. Sonda: `crlv.extrair("COR PREDOMINANTE\n\nMARIA DA SILVA\n")` devolve `{"cor": "maria da silva"}`. A ADR garante que o proprietário "nunca é lido". Para os outros campos, a garantia vem do validador (placa, chassi e Renavam com formato e dígito, anos, enum de combustível). Só a cor e a marca/modelo são texto livre. O leiaute ainda não foi calibrado com CRLV-e reais (handoff da T-265), então hoje não dá para dizer o que fica abaixo da cor no documento de verdade. A pessoa confere antes de salvar, mas, se não perceber, o nome vai para `Veiculo.cor` e para a auditoria.
**Sugestão:** cor por lista fechada, a da tabela de cores do Denatran (amarela, azul, bege, branca, cinza, dourada, grená, laranja, marrom, prata, preta, rosa, roxa, verde, vermelha, fantasia), comparada sem acento. Fora da lista: o campo não é preenchido, como os outros. Teste: tirar o `xfail` de `test_aud_09_cor_nao_aceita_o_nome_do_proprietario`. A marca/modelo já exige uma `/` e passa pelo catálogo; quando não acha, o texto vai como dica e não é gravado. Aceito como está, com o limite do B-01.

### B-01 · O pai confere menos do que o B-03 da T-247 pediu · baixa

**Onde:** `integracoes/leitura_documentos/__init__.py`, `conferir()`.
**Problema:** o pai confere a chave, o tipo e o tamanho do texto, mas não a faixa dos inteiros (`ano_fabricacao`, `ano_modelo`, `exercicio`) nem caractere de controle; e o limite da `marca_modelo` é 80, não os 60 pedidos para a dica. Hoje o validador do filho cobre tudo isso. A conferência do pai é a segunda barreira para um filho que devolva outra coisa (falha explorável no parser). O `type(...) is int` já recusa `bool`, e o `json.loads` recusa inteiro com mais de 4300 dígitos.
**Sugestão:** no `conferir`, anos entre 1900 e o ano de hoje + 1, texto só com caracteres imprimíveis (sem `\x00`-`\x1f` nem `\x7f`), `combustivel` dentro do enum e `marca_modelo` com até 60. Teste: tirar o `xfail` de `test_vei_08_pai_confere_a_faixa_dos_anos`.

### B-02 · Falha depois de gravar o PDF vira 500 e deixa o arquivo órfão · baixa

**Onde:** `apps/veiculos/services.py`, `cadastrar_com_crlv`, bloco `except`; `comum/arquivos.py`, `ArmazenamentoPrivado.delete`.
**Problema:** o `except` chama `storage.delete(nome)`, mas o armazenamento privado sempre levanta `NotImplementedError` ("Arquivo de negócio não é apagado", ADR 0009). Qualquer erro depois do `arquivo.save` (o `registrar_evento` do documento ou o `commit`) vira 500 com `NotImplementedError` no lugar do erro original, e o PDF fica no armazenamento sem registro que aponte para ele. Esse PDF tem o nome e o CPF ou CNPJ do proprietário. Sem registro, ele não entra na exportação nem na anonimização do titular (`AUD-06`) e não tem dono para a retenção. Reproduzido no teste com o evento do documento falhando: 500 com `NotImplementedError`.
**Sugestão:** apagar pelo provedor (`arquivos.provedor().apagar(nome)`, que já trata o versionamento do bucket, como na importação de clientes) dentro de um `try` próprio, que nunca troca a exceção original; ou gravar o arquivo com `transaction.on_commit`. Teste: tirar o `xfail` de `test_vei_08_falha_depois_de_gravar_o_arquivo_devolve_o_erro_certo` (espera o 422 da falha simulada).

### B-03 · Upload acima de 2,5 MB passa por disco · baixa

**Onde:** `config/settings/base.py` (sem `FILE_UPLOAD_MAX_MEMORY_SIZE`); ADR 0026, item 8 ("nem em disco temporário").
**Problema:** o Django guarda em memória o arquivo de até 2,5 MB (padrão) e grava em `/tmp` o maior. A borda deixa passar até 3 MB (T-258). Um PDF entre 2,5 e 3 MB vai para o disco do contêiner antes de a view recusar por tamanho. O arquivo é apagado no fim da requisição, mas, se o processo morrer no meio, fica. Só acontece com arquivo recusado. Isso vale também para o `crlv_arquivo` do salvar.
**Sugestão:** `FILE_UPLOAD_HANDLERS = ["django.core.files.uploadhandler.MemoryFileUploadHandler"]` só nas duas views (via `request.upload_handlers` antes de ler o corpo), ou `FILE_UPLOAD_MAX_MEMORY_SIZE` acima do teto da borda (3 MB) no projeto. A segunda é mais simples, e o teto de memória fica em workers × threads × 3 MB.

### B-04 · O `pypdf` tenta a senha vazia · baixa

**Onde:** ADR 0026, item 6 ("falha, sem tentar senha vazia"); `pypdf.PdfReader._handle_encryption`.
**Problema:** sem senha, o construtor do `PdfReader` 6.21.1 chama `Encryption.verify(b"")`. Com documento cifrado só com a senha do dono (sem senha de abertura), ele decifra. O trabalhador recusa com `senha` logo depois (`is_encrypted`), e nada decifrado é lido. O custo é a derivação da chave, dentro do limite de CPU. Não é falha, mas o texto da ADR não descreve o que acontece.
**Sugestão:** a ADR troca por "falha (`is_encrypted`); o `pypdf` tenta a senha vazia ao abrir, e o trabalhador recusa antes de ler o texto". Para o produto: se os CRLV-e reais vierem cifrados só com a senha do dono (restrição de impressão ou de cópia, comum em PDF oficial), a leitura vai falhar sempre. A calibração com documentos reais precisa conferir isso antes de a tela ir para homologação. Se acontecer, ler o PDF cifrado só com a senha do dono é decisão de ADR, não de código.

## O que fica para quem

- **Backend:** M-01, B-01, B-02 e B-03, tarefa no handoff `tarefas/handoffs/T-328-seguranca.md`, com os três `xfail`.
- **Arquiteto:** o texto do item 6 da ADR 0026 (B-04).
- **Orquestrador:** a calibração com CRLV-e reais confere a cor (M-01) e a cifra só com a senha do dono (B-04); o `weasyprint` 69.0 com dois avisos no `pip-audit` (corrigido na 70.0).
