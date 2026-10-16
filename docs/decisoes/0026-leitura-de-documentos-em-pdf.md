# Leitura do CRLV-e e da CNH-e por PDF

**Status:** aceita · 16 out 2026 (proposta em 15 out 2026) · T-247 (regras `VEI-08` e `CLI-11` no PR #243) · revisada pela segurança em 16 out 2026 (`docs/seguranca/2026-10-16-t247-leitura-pdf.md`, PR #265, sem achado alto); achados M-01, M-02, M-04, B-01 e B-04 incorporados na T-273

## Contexto

A `VEI-08` pede o botão "Preencher pelo documento" da tela `Veiculo-Novo`: a pessoa envia o PDF do CRLV-e e a tela preenche 9 campos (placa, chassi, Renavam, marca, modelo, ano de fabricação, ano do modelo, cor e combustível), sem gravar nada até "Salvar veículo". A `CLI-11` pede o mesmo com a CNH-e e 7 campos (nome, CPF, nascimento, registro, categoria, validade e 1ª habilitação). Pelo padrão em "Pontos em aberto", o CRLV-e entra no MVP e a CNH-e fica para a fase 2; esta ADR vale para os dois.

Quatro fatos pesam na decisão:

- Os dois documentos são PDF gerados pelo sistema do Detran e da Senatran (Carteira Digital de Trânsito), com a camada de texto, um QR code e uma assinatura digital. Não são foto.
- O PDF vem de fora e é o tipo de arquivo com mais casos de parser que trava, estoura memória ou esconde conteúdo (script, anexo, fluxo comprimido gigante).
- A CNH-e tem dado pessoal que a regra manda descartar: filiação, RG, naturalidade, foto e assinatura. O CRLV-e tem o nome e o CPF ou CNPJ do proprietário, que também não podem ser lidos nem guardados.
- A tela espera a resposta com a pessoa no formulário. A regra exige que nada seja gravado como dado do veículo ou do cliente antes de "Salvar".

O projeto não tem leitor de PDF. O WeasyPrint gera PDF, mas não lê.

## Decisão

### 1. Como ler: pela camada de texto do PDF

- O texto é extraído do PDF e os campos saem por rótulo: "PLACA", "CHASSI", "CÓDIGO RENAVAM", "MARCA / MODELO / VERSÃO", "ANO FABRICAÇÃO", "ANO MODELO", "COR PREDOMINANTE", "COMBUSTÍVEL" e "EXERCÍCIO" no CRLV-e; "NOME", "CPF", "DATA NASCIMENTO", "Nº REGISTRO", "CAT. HAB.", "VALIDADE" e "1ª HABILITAÇÃO" na CNH-e. Cada campo tem um validador: placa no formato antigo ou Mercosul, chassi com 17 caracteres, Renavam e CPF com dígito verificador, anos plausíveis, datas válidas, categoria da lista.
- Campo que não passa no validador **não é preenchido**, e a leitura segue com os outros. Isso é a leitura parcial que a `VEI-08` aceita: a resposta diz quais campos saíram e quantos são.
- O que o método garante: com o texto presente, os 9 e os 7 campos estão no documento. A marca e o modelo dependem também da lista do cadastro (item 7). Sem camada de texto (PDF que é só imagem, como a "foto escaneada"), a leitura falha. **Não há OCR**: OCR seria outra dependência, mais pesada e menos certeira, e pediria nova ADR.
- **O QR code não é lido.** No CRLV-e e na CNH-e, ele leva à conferência no serviço da Senatran (consulta externa, item 5) ou guarda dados que só o aplicativo oficial abre. Ler o QR não traria campo que o texto não traz.
- Os rótulos e o leiaute são calibrados com documentos reais da equipe, na tarefa do backend, antes de fechar o parser. Esses documentos nunca entram no repositório; os testes usam os arquivos fictícios do qa (`docs/qa/criterios/T-247.md`).

### 2. Assinatura digital: não é conferida

O Giro não confere a assinatura do Detran nem da Senatran. Conferir de verdade pede uma biblioteca de assinatura (PAdES) e a cadeia de certificados da ICP-Brasil mantida no servidor. Pede também a consulta de revogação (OCSP ou LCR) **na internet**, que o item 5 proíbe sem nova decisão. Conferir sem a revogação daria um "válido" que não garante nada.

A leitura é uma ajuda para preencher, não uma prova: a pessoa confere os campos antes de salvar (`VEI-08`, `CLI-11`), e o PDF fica anexado ao cadastro. A API e a tela nunca dizem "documento válido" ou "autêntico". Por isso, o caso "com a assinatura inválida" da `VEI-08` não acontece. Se um dia o Giro precisar provar a autenticidade (venda, por exemplo), a conferência vem em ADR própria.

### 3. Biblioteca: `pypdf`

Dependência nova, **`pypdf`** (licença BSD; Python puro, sem código nativo nem binário do sistema). O motivo vai no PR do backend.

**Versão mínima pelo `pip-audit` (M-04).** O limite de baixo não é um número fixo desta ADR: é a versão mais nova do `pypdf` sem aviso no `pip-audit` quando o backend começar a tarefa (a 6.0.0 corrige a bomba de descompressão da CVE-2025-55197, e as 6.x seguintes, laços e consumo excessivo em filtros), com o teto na próxima versão maior. A cada aviso novo no `pypdf`, o limite de baixo sobe para a versão corrigida. A verificação de vulnerabilidades do CI falha o PR com aviso no `pypdf`, sem exceção aceita: é a biblioteca que lê arquivo de fora. Usamos dela só a abertura do arquivo e a extração de texto com leiaute (`extract_text(extraction_mode="layout")`). Nada de formulário, anexo, JavaScript, decifração nem renderização.

Descartadas:
- **PyMuPDF:** licença AGPL, que obrigaria a abrir o código do Giro; e é código nativo (C) lendo arquivo de fora.
- **`pdftotext` (Poppler):** binário do sistema em C, mais um pacote na imagem e mais superfície para arquivo hostil.
- **`pdfminer.six` e `pdfplumber`:** Python puro, mas mais lentos e com muito mais código para o mesmo resultado.

### 4. Onde roda: na requisição, num processo filho isolado

- A leitura roda **durante a requisição**, não no Celery: a tela espera a resposta, e um PDF de documento lê em décimos de segundo. Uma fila poria mais espera e mais um caminho para o arquivo, sem ganho.
- A view **não** abre o PDF no processo do servidor web. Ela chama `integracoes.leitura_documentos.ler(tipo, conteudo)`, que roda um processo filho novo. O PDF vai pela entrada padrão, e a resposta volta pela saída padrão, em JSON.
- **Como o filho é chamado (B-01).** Pelo caminho absoluto do arquivo, no modo isolado: `[sys.executable, "-I", <caminho absoluto de trabalhador.py>, <tipo>]`, com o caminho calculado a partir do `__file__` do módulo de `ler`, nunca de variável de ambiente. Não se usa `-m`: no Python 3.12 o `-I` implica `-P`, o diretório atual não entra no `sys.path`, e `python -I -m integracoes...` não acha o pacote (conferido pela segurança na imagem). O `-I` fica, porque é ele que impede o filho de ler `PYTHONPATH`, `PYTHONSTARTUP` e o site do usuário. O `trabalhador.py` põe no `sys.path` só o diretório dele, por caminho fixo, e importa `crlv.py` e `cnh.py` como módulos irmãos; os três importam só a biblioteca padrão e o `pypdf`, nunca `django`, `comum` ou outro app.
- **Ambiente mínimo (M-01).** O filho não herda o ambiente do servidor, onde estão `DJANGO_SECRET_KEY`, `JWT_SIGNING_KEY`, `GIRO_CHAVE_DADOS_PESSOAIS`, `GIRO_CHAVE_SEGREDOS`, `GIRO_PEPPER_HMAC`, a chave do Asaas, `DATABASE_URL` e as chaves do S3. A chamada é `subprocess.run(..., env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LANG": "C.UTF-8"}, close_fds=True, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, start_new_session=True)`, e nada além de `PATH` e `LANG` entra no `env`. Um PDF que explore uma falha do parser não acha chave nenhuma no processo.
- **Limites aplicados pelo próprio filho (M-02).** Nada de `preexec_fn`: a documentação do Python diz que ele não é seguro em processo com threads, e o worker `gthread` do Gunicorn (ADR 0027) tem threads; um filho travado entre o `fork` e o `exec` prenderia a thread até os 8 s. O `trabalhador.py` aplica os limites a si mesmo como primeira coisa, antes de qualquer import que não seja da biblioteca padrão (o `pypdf` vem depois): `RLIMIT_CPU` de 5 s, `RLIMIT_AS` de 512 MB, `RLIMIT_FSIZE` 0 (não escreve arquivo), `RLIMIT_NOFILE` baixo e `RLIMIT_CORE` 0 (sem core dump com o PDF e o texto em disco). Um processo comum pode baixar os próprios limites. Se algum `setrlimit` falhar, o filho sai com erro antes de ler o arquivo.
- **No pai:** tempo máximo de 8 s de relógio; passou disso, o grupo de processos do filho é morto (`os.killpg`, por isso o `start_new_session`) e a leitura falha. O pai lê no máximo 64 KB da saída e confere de novo cada campo (só as chaves do tipo, tipos e tamanhos; B-02 e B-03 da segurança, detalhados na tarefa do backend). Um PDF que trava, estoura memória ou entra em laço derruba só o filho, nunca o worker do Gunicorn.
- O filho **não importa o Django** nem toca no banco, nas chaves ou no armazenamento: recebe bytes e devolve campos. O código dele (`integracoes/leitura_documentos/`, com `crlv.py`, `cnh.py` e `trabalhador.py`) é de funções puras, testáveis sem o filho.
- **Só os campos permitidos saem do filho.** O parser do CRLV-e nunca procura o proprietário; o da CNH-e nunca procura filiação, RG, naturalidade e observações. O texto bruto morre no filho: não volta ao pai, não vai para log, não vai para disco. A foto e a assinatura do titular são imagens, e a extração de texto não as lê.
- Em ambiente sem `resource` (Windows fora do Docker), o filho roda sem os `RLIMIT` e só com o tempo do pai; o desenvolvimento e o CI usam o contêiner Linux.

### 5. Nenhuma consulta externa

Nada sai do servidor na leitura: nem Detran, nem Senatran, nem FIPE online, nem a URL do QR code. A lista de marcas e modelos é a do cadastro, local (item 7). O filho não precisa de rede, e o código não abre conexão em nenhum caminho. **A rede fechada do filho não é condição do MVP** (segurança, resposta 1): o que pesaria numa falha explorável são as chaves, e o filho não as tem (item 4, M-01). As condições são o Postgres e o Redis exigirem senha em homologação e produção (devops, T-274) e nenhuma chave no ambiente do filho. Fechar a rede por namespace pede `unshare`, que o perfil padrão do Docker bloqueia; se a leitura for um dia para um contêiner próprio, ele sobe com `network_mode: none`.

### 6. Limites

| Limite | Valor | Onde |
| --- | --- | --- |
| Tamanho do arquivo | **2 MB** | conferido na view, antes do filho (o `DATA_UPLOAD_MAX_MEMORY_SIZE` não vale para arquivo; a view lê no máximo 2 MB + 1 byte) |
| Tipo | só PDF, pelos primeiros bytes (`%PDF-`), nunca pela extensão nem pelo `Content-Type` | view |
| Páginas | até **3** (o CRLV-e tem 1; a CNH-e, 1 ou 2) | filho |
| PDF com senha (`is_encrypted`) | falha, sem tentar senha vazia | filho |
| Tempo | 5 s de CPU no filho e 8 s de relógio no pai | filho e pai |
| Memória | 512 MB de espaço de endereço no filho | filho |
| Texto extraído | até 200 mil caracteres; acima, falha (documento oficial tem poucos milhares) | filho |
| Requisições | 30 por hora por usuário e 200 por hora por empresa, somando as duas rotas, em `comum.limites`; a recusa (400 e 422) também conta, e a contagem vem antes do filho; acima, 429 `muitas_requisicoes` | view |
| Leituras ao mesmo tempo | 2 por processo (semáforo); cheio, 503 `leitura_ocupada` com `Retry-After` (pedido do devops na T-258, B-02 da segurança) | view |

Os documentos oficiais ficam abaixo de 500 KB. 2 MB deixa folga e mantém o filho pequeno. O anexo ao salvar continua com o limite de 10 MB dos documentos, mas o arquivo anexado pela leitura é o mesmo de até 2 MB.

### 7. Marca e modelo pela lista do cadastro

A `VEI-08` manda escolher a marca e o modelo da lista do cadastro (a tela diz "Da lista FIPE"). Hoje o `Veiculo` guarda `marca` e `modelo` como texto, e não há lista no backend. Esta ADR fixa só como a leitura usa a lista. A lista em si (de onde vem, como se atualiza) fica para uma tarefa à parte, proposta no handoff:

- A lista é local: um catálogo de marcas e modelos com o tipo (moto ou carro), servido por `GET /api/veiculos/modelos/`. Ele é carregado de um arquivo que a equipe atualiza por comando, nunca consultado na internet durante o uso.
- O texto lido ("HONDA/POP 110I ES") é normalizado (sem acento, maiúsculas, sem pontuação) e comparado com o catálogo. Achou um modelo só: `marca` e `modelo` vêm preenchidos com o nome da lista e contam 2 campos. Não achou, ou achou mais de um: os dois ficam vazios, o texto vai em `dicas.marca_modelo`, e a contagem cai para 7 (CA-247-05).
- **Enquanto o catálogo não existir**, a leitura nunca preenche marca e modelo e sempre manda a dica. O CA-247-01 (9 campos) depende do catálogo com o Pop 110i ES.

### 8. O arquivo entre a leitura e o salvar: não fica no servidor

- A leitura **não guarda o PDF** em lugar nenhum: nem no armazenamento, nem em disco temporário, nem em cache. O arquivo vive na memória do pai e do filho durante a requisição.
- A tela guarda o arquivo no navegador e o manda de novo no "Salvar", junto com o cadastro. Se a pessoa desiste, nada ficou no servidor, e não há limpeza a fazer.
- Para o evento de auditoria dizer o que veio do documento sem confiar na tela, a leitura devolve um comprovante `leitura`: um texto assinado com `django.core.signing` (sal próprio por tipo, validade de 30 min) que leva o tipo, o SHA-256 do arquivo, o `schema` da empresa, o id do usuário e, para cada campo lido, um resumo HMAC do valor lido. O comprovante não leva o valor, então não carrega CPF nem número da CNH.
- **Chave própria do resumo (B-04).** O resumo usa uma chave só da leitura, derivada do pepper: `chave_leitura = HMAC(GIRO_PEPPER_HMAC, "leitura-documento")`, e leva o SHA-256 do arquivo junto: `HMAC(chave_leitura, sha256_do_arquivo || campo || valor)`. Assim ele nunca é igual ao `CampoHashBusca` do CPF guardado no banco (ADR 0014), e dois comprovantes do mesmo CPF, de arquivos diferentes, não se ligam. A segurança aceitou o resumo do CPF nessas condições (pergunta 3).
- No "Salvar", o serviço confere a assinatura, se o `schema` e o usuário do comprovante são os da requisição e se o arquivo enviado tem o mesmo SHA-256. Depois compara os resumos com os valores gravados e registra no evento quais campos vieram do documento e quais a pessoa mudou. Sem comprovante, ou com ele vencido, de outra empresa, de outro usuário ou de outro arquivo: o comprovante é tratado como ausente, o cadastro salva normalmente, sem a marca de leitura, e o arquivo, se veio, é anexado como um documento comum. O salvar confere de novo os primeiros bytes e os 2 MB do arquivo e o grava com `Content-Type: application/pdf` fixado pelo backend (B-06).

### 9. O que nunca vai para log, Sentry ou evento

- Nunca: o conteúdo do PDF, o texto extraído, o nome do arquivo (pode trazer o nome da pessoa), os valores lidos (CPF, número da CNH, nome, nascimento; e, no CRLV-e, nem placa, chassi e Renavam, por simplicidade) e o comprovante `leitura`.
- O log da leitura é uma linha `INFO` com o tipo, o resultado (`lido`, `parcial` ou `falhou`), o motivo da falha por código fechado (`nao_pdf`, `grande`, `senha`, `sem_texto`, `paginas`, `tempo`, `memoria`, `nao_reconhecido`), a quantidade de campos, os milissegundos, o schema e o id do usuário.
- A saída de erro do filho é descartada, não registrada. Falha no filho não sobe exceção com o conteúdo, e a mensagem de erro do pai nunca inclui a saída do filho: o pai traduz para o código de motivo. No Sentry, só o código. O `sentry-sdk` não deixa tirar uma função só da captura de variáveis locais, então a captura sai do projeto inteiro: `include_local_variables=False` e `max_request_body_size="never"` no `sentry_sdk.init` (M-03 da segurança, com o devops na T-270), com um teste de transporte de mentira provando que um CPF numa variável local não chega ao evento.
- O evento de auditoria do cadastro leva só a lista de campos vindos do documento e os corrigidos, sem valor. O CPF e a CNH já são omitidos por serem `CampoCifrado` (ADR 0014, nota de 12 out 2026).
- A resposta da leitura sai com `Cache-Control: no-store`.

### 10. Quem pode

A leitura do CRLV-e é de quem cadastra veículo (administrador e gerente); a da CNH-e, de quem cadastra cliente (administrador, gerente e vendedor). Os outros perfis recebem 403 `permissao`. O token de suporte (`PLT-07`), como a segurança confirmou: 403 `PLT-07` na leitura da CNH-e nos dois modos, porque ela mostra o CPF completo (`AUD-09`); na do CRLV-e, só com o acesso "ver e editar", e 403 `PLT-07` em "só ver".

## Consequências

- Uma dependência nova, `pypdf`, em Python puro. Ela entra no `requirements.txt` e na verificação de vulnerabilidades do CI, com a versão mínima revista a cada aviso (item 3).
- Um processo filho por leitura, de 100 a 200 ms de custo fixo. No volume esperado (cadastro de frota e de clientes), cabe. O limite por usuário e por empresa evita abuso. O `timeout` do Gunicorn tem de ficar acima de 8 s (devops confere).
- A leitura falha em PDF sem texto, e a pessoa preenche à mão. Mudar isso pede OCR e nova ADR.
- O parser depende do leiaute do Detran e da Senatran. Se o leiaute mudar, a leitura vira parcial ou falha, sem gravar nada errado, porque cada campo passa pelo validador e pela conferência da pessoa. O log com `nao_reconhecido` mostra quando isso começa.
- O modelo ganha `Veiculo.combustivel`, `DocumentoVeiculo.exercicio` e, na fase da CNH-e, o tipo `cnh_digital` em `DocumentoCliente` (`docs/decisoes/modelo-de-dados.md`).
- Testes:
  - os parsers puros, com os arquivos fictícios do qa;
  - o filho com PDF que trava, PDF com senha, PDF gigante, imagem com extensão `.pdf` e PDF com JavaScript e anexo (nada executa, a leitura só não acha os campos);
  - um teste que confere que o nome do proprietário e a filiação do arquivo de teste não aparecem na resposta nem nos registros de log capturados, nem num evento do Sentry (transporte de mentira);
  - o ambiente do filho: chamado com um tipo de teste, ele devolve `sorted(os.environ)`, e o resultado é só `LANG` e `PATH` (M-01);
  - os limites: o filho lê `resource.getrlimit` depois de subir e confere os cinco valores, e o pai não usa `preexec_fn` (M-02);
  - o isolamento do código: no fim do trabalhador, `django` e `comum` não estão em `sys.modules` (B-01);
  - o comprovante: de outra empresa, de outro usuário ou de outro arquivo, o salvar não marca os campos; e o resumo de um CPF difere do `CampoHashBusca` do mesmo CPF (B-04);
  - os de rota, pelos critérios CA-247-01 a 12.
