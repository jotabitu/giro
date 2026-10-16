# T-247 · Leitura do CRLV-e e da CNH-e por PDF (ADR e contratos) · arquiteto → orquestrador, segurança, backend, frontend, design-system, qa

**O que foi feito:** a ADR 0026 (proposta) e os contratos da leitura, respondendo às 7 perguntas do handoff do produto. Branch `t-247-adr-leitura-pdf`, **empilhada sobre a `origin/t-247-regras-leitura-pdf`** (PR #243, ainda não mesclado), porque cita a `VEI-08`, a `CLI-11` e os CA-247. Mesclar o #243 antes. Só documentos, sem teste para rodar.

**Onde:**
- `docs/decisoes/0026-leitura-de-documentos-em-pdf.md` (nova, proposta) e a linha dela em `docs/decisoes/README.md`.
- `docs/api/veiculos.md`:
  - `POST /api/veiculos/leitura-crlv/`;
  - o salvar em multipart (`crlv_arquivo`, `crlv_validade`, `crlv_exercicio`, `leitura`);
  - `combustivel` no veículo e `exercicio` no documento;
  - o catálogo `GET /api/veiculos/modelos/`, ainda sem tarefa.
- `docs/api/clientes.md`: `POST /api/clientes/leitura-cnh/`, o salvar em multipart e o tipo `cnh_digital`, na fase que o dono decidir.
- `docs/decisoes/modelo-de-dados.md`: `Veiculo.combustivel`, `DocumentoVeiculo.exercicio` e `cnh_digital`.
- `tarefas/backlog.md` (estado da ADR) e `tarefas/feito.md` (PR a abrir).

**Respostas às 7 perguntas do produto:**
1. **Como ler:** pela camada de texto do PDF, por rótulo, com um validador por campo. O QR code não é lido. Sem OCR: PDF sem texto falha. A leitura parcial preenche o que passou no validador. Marca e modelo dependem do catálogo (item 7 da ADR).
2. **Assinatura:** não é conferida. Conferir pede a cadeia da ICP-Brasil e a consulta de revogação na internet (proibida pelo item 5). A leitura nunca diz "válido", e a conferência da pessoa continua. O caso "assinatura inválida" da `VEI-08` não acontece.
3. **Biblioteca:** `pypdf` (BSD, Python puro). PyMuPDF (AGPL, nativo), Poppler e pdfminer foram descartados. Roda na requisição, num processo filho novo, sem Django, com `RLIMIT` e tempo máximo.
4. **Limites:** 2 MB, 3 páginas, 5 s de CPU e 8 s de relógio, 512 MB, 200 mil caracteres de texto, sem PDF com senha. Requisições: 30 por hora por usuário e 200 por hora por empresa.
5. **Nenhuma consulta externa:** o catálogo é local, o QR não é seguido e o filho não precisa de rede.
6. **Arquivo entre ler e salvar:** não fica no servidor. A tela guarda o arquivo e o manda de novo no salvar, junto com um comprovante assinado (SHA-256 do arquivo e resumos HMAC dos valores, sem os valores) que deixa o evento dizer o que veio do documento. Se a pessoa desiste, nada sobra.
7. **Contrato:** a resposta traz `campos`, `lidos`, `quantidade` e `rotulo` prontos (a tela não conta), e o `exercicio` vai para o documento CRLV.

**Perguntas para a segurança (revisão da ADR 0026):**
1. **Processo filho:** os `RLIMIT` (CPU 5 s, memória 512 MB, sem escrita em arquivo) e os 8 s de relógio bastam contra PDF que trava, bomba de descompressão e laço no `pypdf`? O filho precisa de rede fechada no contêiner (namespace ou política de rede, com o devops), ou basta o código não abrir conexão?
2. **Dados que não podem sair:** o desenho garante que o texto bruto (proprietário no CRLV-e; filiação, RG, naturalidade e observações na CNH-e) não sai do filho, porque só os campos permitidos voltam pela saída padrão e a saída de erro é descartada. Isso basta, ou o teste "o nome do proprietário e a filiação não aparecem na resposta nem no log" (ADR, Consequências) deve rodar também contra o Sentry?
3. **Comprovante `leitura`:** é assinado com `django.core.signing` (sal por tipo, 30 min) e leva o SHA-256 do arquivo e resumos HMAC dos valores. O resumo HMAC de um CPF lido, com a chave do servidor, é aceitável no comprovante que vai ao navegador? Ou o da CNH-e deve levar só a lista de campos lidos, sem resumo?
4. **Suporte Giro (`PLT-07`, `AUD-09`):** o padrão do contrato é 403 `PLT-07` na leitura da CNH-e (mostraria o CPF completo) e permissão de escrita do acesso na do CRLV-e. Confirma ou troca?
5. **Limite de requisições:** 30 por hora por usuário e 200 por hora por empresa, somando CRLV-e e CNH-e. Está bom para a abertura de um processo filho por chamada?
6. **Arquivo anexado:** o PDF lido é anexado como veio (sem reprocessar, diferente das imagens dos documentos do cliente, que perdem os metadados). Ele guarda os metadados e a assinatura do Detran, e isso é desejado para o registro. Precisa de alguma limpeza, ou de um `Content-Disposition: attachment` no link assinado?
7. **Não conferir a assinatura digital:** de acordo com o motivo (sem consulta de revogação, sem prova de autenticidade)? Algum caso exige a conferência antes do MVP?

**O que ficou de fora:**
- **Catálogo de marcas e modelos** (`GET /api/veiculos/modelos/`): a tela diz "Da lista FIPE", mas o backend não tem a lista. Sem ela, a leitura não preenche marca e modelo, e o CA-247-01 dá 7 campos em vez de 9. Proposta para o orquestrador numerar: arquiteto e backend definem o arquivo do catálogo (fonte, atualização por comando, sem consulta em tempo real). Pode ser que o produto precise dizer a fonte.
- As duas perguntas em aberto para o dono (fase e o PDF no lugar das fotos): o contrato da CNH-e está escrito para as duas respostas.
- A calibragem do parser com documentos reais (que nunca entram no repositório) fica com o backend, no início da tarefa. Se a camada de texto do CRLV-e ou da CNH-e real não servir, a ADR volta para revisão.
- `timeout` do Gunicorn acima de 8 s: o devops confere.
- O `clientes.md` e o `modelo-de-dados.md` também mudaram na T-249 (PR #245). Ao mesclar as duas, há um conflito simples no cabeçalho de versão do `clientes.md`.

**Próximo passo para quem recebe:**
- **Segurança:** as 7 perguntas acima. Depois da revisão, a ADR passa de "proposta" para "aceita".
- **Orquestrador:** numerar o backend do CRLV-e (MVP pelo padrão), o frontend da `Veiculo-Novo`, a fase 2 da CNH-e e o catálogo.
- **Design-system:** a `[divergência]` da `Veiculo-Novo-Mobile` (fotografar) continua com o produto; a tela pede só PDF.
- **Qa:** os arquivos fictícios de `docs/qa/criterios/T-247.md`, no formato com camada de texto.
