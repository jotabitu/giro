# T-079 · Documentos de veículos, arquivo privado e AUT-06 · backend → orquestrador, frontend, qa, arquiteto, devops, produto

**O que foi feito:**
- **`comum/arquivos.py` (ADR 0009, `AUD-05`):**
  - um `Storage` do Django para usar em `FileField(storage=arquivos.armazenamento_privado, upload_to=arquivos.caminho_privado)`;
  - caminho `<schema>/<app>/<model>/<id>/<uuid>.<ext>`. O nome original não entra no caminho, e o objeto precisa estar gravado antes do arquivo;
  - `validar(arquivo)`: PDF, JPG ou PNG pelo conteúdo (assinatura dos bytes) e pela extensão, até 10 MB. Fora disso, 400 `validacao` no campo `arquivo`;
  - `url_assinada(caminho)`: vale 15 minutos, e cada leitura gera outra URL;
  - `GIRO_ARMAZENAMENTO=falso` (memória, padrão em desenvolvimento e testes) ou `s3` (`boto3`, com `S3_BUCKET`, `S3_ENDPOINT_URL`, `S3_REGIAO`, `S3_CHAVE_DE_ACESSO` e `S3_CHAVE_SECRETA`). O `boto3` só é importado com `s3`;
  - nada é apagado: `delete` falha de propósito;
  - pronto para a T-014 (documentos de clientes) e para as fotos de vistoria.
- **`comum/auditoria.retrato`:** um arquivo entra na auditoria pelo caminho, nunca pelo conteúdo. Antes, quebrava ao serializar um `FieldFile`.
- **`veiculos.DocumentoVeiculo` (`VEI-03`):**
  - um ativo por tipo (`crlv`, `ipva`, `seguro`, `rastreador`). Renovar deixa o anterior `ativo=False`, com auditoria;
  - `situacao`: `em_dia`, `vence_em_breve` (30 dias ou menos) ou `vencido`. No dia da validade, o documento já conta como vencido, porque é o dia em que o veículo sai da frota;
  - `documentos_resumo: { pior_situacao }` na ficha e na lista da frota. Vem `null` quando o veículo não tem documento.
- **Rotas:**
  - `GET /api/veiculos/{id}/documentos/`: os ativos, para todos os perfis no escopo de filiais;
  - `POST /api/veiculos/{id}/documentos/` (multipart: `tipo`, `validade`, `arquivo?`): administrador e gerente. O vendedor recebe 403;
  - `GET /api/veiculos/{id}/documentos/historico/`: todos, inclusive os renovados.
- **`desbloquear`:** com CRLV ou seguro ativo vencido, responde 422 `{ codigo: "VEI-03", mensagem: "Renove o CRLV vencido antes de desbloquear o veículo.", detalhes: { documentos: ["crlv"] } }`.
- **`AUT-06`:** `aut_06_vencimento_de_documentos(schema)`, com uma por empresa pelo Beat às 07:00. Rodar duas vezes no mesmo dia não repete nada.
  - 30 dias antes: alerta no sino dos gerentes da filial (`FIL-02`), uma vez por documento, e o evento `veiculos.documento_vencendo`.
  - No dia, com CRLV ou seguro: o veículo `disponivel` vai para `indisponivel`, motivo "Seguro vencido" e origem `documento`. O `alugado` não muda, e os gerentes recebem uma tarefa urgente.
  - IPVA e rastreador só têm o alerta.
- **`notificacoes` (mínimo):** o model `Notificacao` (`urgente` e `chave` de idempotência) e `services.avisar(...)`. Ainda não tem API.

**Onde:**
- `backend/comum/arquivos.py`, `comum/auditoria.py`, `comum/tests/test_arquivos.py` e `backend/README.md`.
- `backend/apps/veiculos/`: `models.py`, `services.py`, `selectors.py`, `tasks.py`, `api/`, a migração `0002` e o `README.md`.
- `backend/apps/notificacoes/`: `models.py`, `services.py`, a migração `0001` e o `README.md`.
- `config/settings/base.py`: `GIRO_ARMAZENAMENTO` e `S3_*`, o Beat da `AUT-06` e `TipoDocumentoEnum`.
- `requirements.txt`: `boto3`.

**Testes:**
- Sem xfail: `test_vei_03_ca_013_17_situacao_do_documento`, `test_vei_03_aut_06_ca_013_18_vencimento_tira_da_frota_disponivel`, `test_vei_03_ca_013_19_renovar_nao_libera_sozinho` e `test_aud_05_ca_013_20_arquivo_privado`.
- O CA-013-20 também cobre o prefixo do caminho e o PDF disfarçado (`.pdf` com conteúdo de `.exe`).
- `comum/tests/test_arquivos.py` (`test_aud_05_*`): formatos aceitos e recusados, URL de 15 minutos nova a cada leitura, caminho sem id e armazenamento desconhecido.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `399 passed, 17 xfailed`. Antes eram 385 e 21.
- O OpenAPI foi regerado com `--validate`, sem aviso. O `TipoDocumentoEnum` entrou em `ENUM_NAME_OVERRIDES`.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Ajustes em testes de outras tarefas:**
- `test_t011_contas.py`: a lista de rotas que o suporte lê ganhou as 2 rotas de leitura de documentos.
- `Notificacao.chave` foi classificada como `inteiro` em `CAMPOS_AUDITORIA`, porque é a chave de idempotência e não um segredo (`tests/test_campos_sensiveis.py`).

**Dependência nova (registrar no PR):**
- `boto3>=1.35,<2`. É o cliente do S3 para o bucket privado e as URLs assinadas (ADR 0009); não usei o `django-storages`.
- Só é importado com `GIRO_ARMAZENAMENTO=s3`. Os testes e o desenvolvimento usam o falso, então a imagem atual roda sem ele.
- **DevOps:** reconstruir a imagem do backend. Em homologação e produção, configurar `GIRO_ARMAZENAMENTO=s3` e as variáveis `S3_*`, com o bucket privado (sem leitura pública).
- **Pendente na CSP:** `img-src` e `frame-src` precisam aceitar o host do bucket (`infra/README.md`, avaliação da T-052).

**Diferenças em relação ao contrato** (para o arquiteto conferir):
1. Cada documento traz também `ativo`, para o histórico mostrar os renovados.
2. O model guarda `arquivo_nome` (o nome original, mostrado em `arquivo.nome`) e `por` (quem enviou), que não estavam no modelo de dados.
3. `documentos_resumo` é `null` sem documentos e não vem mais dos blocos de leitura (ADR 0015): `veiculos` calcula direto, uma consulta por página.
4. No dia da validade, a `situacao` já é `vencido`, com `dias_para_vencer: null`.

**Dúvida para o produto:** está em `tarefas/backlog.md` com a etiqueta `[decisão]`. É sobre o veículo `reservado` ou em `manutencao` no dia em que vence o CRLV ou o seguro. Também marquei como decidido o `km_mudou` da T-081.

**Falta (fora desta tarefa):**
- O e-mail ao gerente da `AUT-06` e a API do sino. Isso entra com o contrato `docs/api/notificacoes.md`.

**Próximo passo para quem recebe:**
- **Frontend:** a aba de documentos da ficha usa as 3 rotas. Envie com `multipart/form-data`. A URL do arquivo vence em 15 minutos: busque de novo a lista para abrir o arquivo.
- **QA:** a `AUT-06` roda nos testes com `aut_06_vencimento_de_documentos("empresa_a")` e o relógio em `relogio.em(...)`.
- **Backend (T-014):** `DocumentoCliente.arquivo` usa os mesmos `armazenamento_privado` e `caminho_privado`, e chama `arquivos.validar` antes de gravar.
