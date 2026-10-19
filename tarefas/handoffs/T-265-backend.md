# T-265 · Leitura do CRLV-e (backend) · backend → frontend, qa, seguranca, devops, orquestrador

**Branch:** `t-265-leitura-crlv`, empilhada sobre a `t-257-catalogo-modelos` (PR #351): o catálogo é usado pela leitura. Abrir o PR depois do #351, ou com a base nele.

**O que foi feito** (ADR 0026, `docs/api/veiculos.md`):
- `backend/integracoes/leitura_documentos/`:
  - `__init__.py` (pai): `ler(tipo, conteudo)` roda `[sys.executable, "-I", <caminho absoluto de trabalhador.py>, tipo]` com `env` só `PATH` e `LANG` (M-01), `close_fds`, `stderr=DEVNULL`, `start_new_session`, sem `preexec_fn` (M-02); escreve o PDF e lê no máximo 64 KB em threads, com 8 s de relógio; passou, `os.killpg`. Confere de novo os campos (só as chaves do tipo, tipo e tamanho, B-02/B-03). `vaga()`: semáforo de 2 leituras por processo, cheio dá `LeituraOcupada`. Falha sempre por código fechado (`MOTIVOS`).
  - `trabalhador.py` (filho): aplica `RLIMIT_CPU` 5 s, `AS` 512 MB, `FSIZE` 0, `NOFILE` 16 e `CORE` 0 antes de importar o `pypdf`; recusa senha, mais de 3 páginas, sem texto e mais de 200 mil caracteres; só `extract_text(extraction_mode="layout")`. O tipo `_diagnostico` existe para os testes da ADR (devolve nomes do ambiente, limites e módulos, nunca valores).
  - `crlv.py`: funções puras, só biblioteca padrão. Campo por rótulo, valor na mesma linha (até 2 espaços) ou abaixo na mesma coluna; validadores de placa (antiga e Mercosul), chassi (17, sem I, O e Q), Renavam (dígito verificador), anos, cor, combustível (enum; `ALCOOL/GASOLINA` → `flex`) e o texto de marca/modelo. O proprietário nunca é procurado.
- `comum/comprovante_leitura.py`: o `leitura` assinado (`django.core.signing`, sal por tipo, 30 min) com tipo, SHA-256, schema, quem leu e o resumo `HMAC(HMAC(pepper, "leitura-documento"), sha256 || campo || valor)` por campo (B-04).
- `apps/veiculos/leitura.py` e `LeituraCrlvView`: `POST /api/veiculos/leitura-crlv/` (administrador e gerente; suporte só em "ver e editar"), 30/h por usuário e 200/h por empresa contando as recusas (`comum.limites`, escopos `leitura_documento_*`, para a CNH-e somar), 503 `leitura_ocupada` com `Retry-After`, `Cache-Control: no-store`. Marca e modelo por `catalogo.achar_modelo`; sem modelo único, `dicas.marca_modelo`. Nenhum dos 9 lido: 422.
- `POST /api/veiculos/` aceita multipart com `crlv_arquivo`, `crlv_validade`, `crlv_exercicio` e `leitura` (`services.cadastrar_com_crlv`): uma transação, os bytes e os 2 MB conferidos de novo, arquivo gravado como `CRLV-e.pdf` (nome do armazenamento gerado; `.pdf` dá o `Content-Type`), apagado se a transação falhar. Comprovante válido: `veiculo.cadastrar` leva `preenchido_pelo_documento {tipo, campos, corrigidos}`.
- Migração `0006_combustivel_e_exercicio`: `Veiculo.combustivel` (enum, nulo) e `DocumentoVeiculo.exercicio`. `combustivel` no cadastro, na edição e na representação; `exercicio` no envio de documento.
- **Dependência nova `pypdf>=6.21.1,<7`** (motivo no `requirements.txt` e aqui): a ADR 0026, item 3, já a prevê. 6.21.1 é a mais nova e o `pip-audit` não acusa nada em 19 out 2026. Python puro, usado só no filho.

**Contrato:** `veiculos.md` acertado: o evento é `veiculo.cadastrar` (o texto dizia `veiculo.criar`), `campos` são todos os lidos e `corrigidos` os mudados, e saiu o "até o catálogo existir". OpenAPI regenerado (`CombustivelVeiculoEnum`; o nível do tanque da vistoria ganhou o nome fixo `NivelDoTanqueEnum`, antes `CombustivelEnum`, que o frontend não usa pelo nome); `api:gerar` e `tsc` do frontend passam.
**Regras cobertas:** VEI-08, VEI-01, VEI-03. `tests/aceitacao/test_t265_leitura_crlv.py`: 27 passam (`test_vei_08_le_os_9_campos` CA-01/02, `test_vei_08_salva_com_o_documento` CA-03, `test_vei_08_validacoes_de_sempre` CA-04, `test_vei_08_modelo_fora_da_lista` CA-05, `test_vei_08_nao_da_para_ler` CA-06, `test_vei_08_quem_pode` CA-07, os do filho: ambiente, limites, módulos, sem `preexec_fn`, travado, saída grande, senha, sem texto, páginas, JavaScript e anexo; comprovante de outra pessoa, outro arquivo e adulterado; B-04; 503; 429). Também passam t013, t016, t027, t257, rotas, permissões das rotas e limites entre apps. ruff, `ruff format --check` e mypy do backend inteiro limpos.
**O que ficou de fora:**
- Calibração com CRLV-e reais: não tive documento real. Os PDFs de teste são gerados em `tests/aceitacao/documentos_pdf.py` no leiaute descrito na ADR. Alguém da equipe precisa rodar `crlv.extrair` no texto de 2 ou 3 CRLV-e reais, fora do repositório, e mandar só os ajustes de rótulo.
- Os arquivos do qa (`crlv-tbc5h21.pdf` etc.) ainda não existem; os testes usam os gerados, com os mesmos dados.
- A tela (frontend) e a CNH-e (fase 2).

**Próximo passo para quem recebe:**
- Devops: reconstruir a imagem do backend (dependência nova); o `timeout` do Gunicorn tem que ficar acima de 8 s.
- Frontend: "Preencher pelo CRLV-e" em `Veiculo-Novo` com `POST /api/veiculos/leitura-crlv/`, e o salvar em multipart com o arquivo e o `leitura`.
- Seguranca: revisão do código do filho contra a ADR 0026.
- Orquestrador: abrir o PR depois do #351.
