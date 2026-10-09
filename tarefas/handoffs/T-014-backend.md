# T-014 · Clientes, documentos, bloqueio e LGPD · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca, devops

**O que foi feito:**
- **App `clientes`** (`docs/api/clientes.md`), em um PR só:
  - `GET` e `POST /api/clientes/`, com `?situacao=`, `?tipo=`, `?busca=`, `?ordem=`, as `contagens` e os `indicadores`;
  - `GET` e `PATCH /api/clientes/{id}/`;
  - `POST /api/clientes/{id}/documentos/` (multipart);
  - `GET /api/clientes/{id}/analise/` e `POST /api/clientes/analisar/`;
  - `bloquear`, `desbloquear`, `inativar` e `reativar`.
- **Cadastro (`CLI-01`, `CLI-03`, `CLI-08`):**
  - CPF e CNPJ conferidos pelo dígito verificador (`comum.documentos.cpf_valido`) e únicos pelo hash (409 `CLI-01` com `cliente_id` e `nome`, também na corrida entre dois cadastros);
  - salva só com tipo, nome, documento e celular, como `incompleto`. Completar a última pendência leva a `ativo`, e tirar um dado volta a `incompleto`. Bloqueado e inativo não mudam por aí;
  - `consentimento: true` grava o momento do servidor uma vez; `false` não apaga.
- **Dados pessoais:**
  - CPF, CNPJ, CNH e CPF do responsável ficam cifrados, com hash de busca (ADR 0014, S-07);
  - a lista sai mascarada para todos (`AUD-04`); o detalhe completo é só para administrador, gerente e vendedor;
  - o suporte Giro recebe sempre a resumida, em "só ver" e em "ver e editar", inclusive na busca e na resposta do `PATCH` (`AUD-09`);
  - a auditoria do cliente guarda o nome em iniciais, nascimento só com o ano, contatos, endereço e referência mascarados, e omite os cifrados.
- **Documentos (`AUD-05`, S-12):**
  - o arquivo é conferido pelo conteúdo e pelo tamanho (`arquivos.validar`);
  - a foto JPG ou PNG é reprocessada com a Pillow: só os pixels, sem EXIF, GPS nem marca do aparelho. A orientação do EXIF entra nos pixels antes. Imagem que não abre responde 400. O PDF fica como veio;
  - reenviar deixa o anterior `ativo=False`, guardado;
  - cada URL assinada de 15 minutos gera um evento `documento_cliente.ver` com quem viu. A resposta do envio também traz as URLs, e por isso também grava o evento.
- **Análise (`CLI-02`, `CLI-04`):** os itens `cpf`, `cnh`, `lista_bloqueio`, `historico` ("Sem histórico" até o financeiro) e `documentos`. `credito` não aparece. `cnh.situacao` pode ser `valida`, `vencida` (até 30 dias) ou `vencida_impede`.
- **Interface para os outros apps** (`selectors`): `impedimentos_para_retirada(cliente, tipo_veiculo, data)`, `impedimentos_para_nova_locacao(cliente)` e `impedimentos_para_venda(cliente)`.
- **Bloqueio (`CLI-05`, `APR-05`, `APR-09`, `LOC-07`):**
  - gerente e administrador bloqueiam e desbloqueiam na hora, com motivo e auditoria. Bloquear de novo responde 409 `transicao_cliente`;
  - a vendedora pede: 202 com o pedido `APR-05` aberto por `comum.aprovacoes.pedir`, com a filial do `X-Filial` (ou a única filial dela). Pedido repetido responde 409 `pedido_pendente`;
  - o assinante em `clientes/eventos.py` desbloqueia quando o pedido é aprovado. Se gerente ou administrador desbloqueia direto, o pedido pendente é cancelado;
  - assinante de `financeiro.parcela_atrasou`: bloqueia com 15 dias, `motivo: "atraso"`;
  - assinante de `financeiro.parcela_paga`: desbloqueia o bloqueio por atraso quando o contador `contas_atrasadas_15_dias` (do financeiro) chega a 0. O bloqueio manual não sai sozinho.
- **Inativar (`CLI-09`):** só administrador e gerente, com motivo. O inativo sai da lista padrão e aparece em `?situacao=inativos`. Com locação, venda ou valor em aberto, responde 422 `cliente_com_pendencia` (contadores de `locacoes`, `vendas` e `financeiro`, que ainda não existem).
- **Lista (`CLI-06`, `CLI-07`):** a `situacao` e a `acao_principal` são calculadas na ordem do contrato. Os blocos `locacao_atual`, `ultima_locacao`, `financeiro` e `venda_aberta` vêm `null` até os fornecedores existirem. Os filtros `com_locacao` e `em_aberto` também dependem deles, e enquanto isso a contagem vem `null` e a aba vem vazia.
- **Segurança da T-050:**
  - R-02: `nome` e `pagador` entraram nos segmentos sensíveis. Os `nome` de coisas (plano, filial, feriado, categoria, extra, usuário, empresa, `ator_nome`, `arquivo_nome`) foram declarados como `inteiro`, e o `Cliente.nome` como mascarado;
  - R-05: `decifrar` de valor truncado ou com base64 inválido levanta `ErroDeCifra`, e `definir_<campo>` com o mesmo valor não recifra, para não gerar "alterado" falso.
- **`comum`:**
  - `documentos.cpf_valido`;
  - `arquivos.sem_metadados`, para ser reaproveitada nas fotos de vistoria;
  - `leituras.registrar_filtro` e `filtro`, para os filtros de outros apps (ADR 0015).
- **`GIRO_MODULOS_ATIVOS`:** `clientes` entrou no padrão.

**Onde:**
- `backend/apps/clientes/`: `models.py`, `services.py`, `selectors.py`, `eventos.py`, `apps.py`, `api/`, a migração `0001` e o `README.md`. A tabela "O que os outros apps registram aqui" do README é o roteiro para locações, financeiro e vendas.
- `backend/comum/`: `documentos.py`, `cripto.py`, `campos.py`, `classificacao.py`, `arquivos.py` e `leituras.py`.
- `CAMPOS_AUDITORIA` em `plataforma`, `auditoria`, `contas`, `filiais` e `veiculos` (só declaração, sem migração).
- `config/urls.py`, `config/settings/base.py` (o módulo e os enums), `requirements.txt`, `backend/README.md` e `docs/api/openapi.yaml`.

**Testes:**
- `tests/aceitacao/test_t014_clientes.py`, com 27 testes e sem xfail. Cobrem do CA-014-01 ao CA-014-22, mais:
  - `test_aud_06_auditoria_de_cliente_nao_guarda_nome_nem_documento_completos`, o teste obrigatório da ADR 0014;
  - o PDF aceito como veio;
  - o isolamento entre empresas.
- Os critérios [integração] (CA-014-15, 16, 18 com pendência, 19, 20 e 21) rodam com fornecedores falsos, registrados pela mesma porta que os apps de verdade vão usar. Os números do seed completo (612 clientes, 164640 em aberto) ficam para a T-019.
- Unitários:
  - `test_cli_01_cpf_valido` e `test_cli_01_cpf_invalido`;
  - `test_r05_*` em `test_cripto.py`;
  - `test_r02_nome_e_pagador_obrigam_a_classificar`;
  - o filtro de `leituras`.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `442 passed`, sem xfail. Antes eram 399 passed e 17 xfailed: os 17 eram os esqueletos da T-014.
- O OpenAPI foi regerado com `--validate`, sem aviso, e só com acréscimos. Prefixei os componentes de clientes (`...ClienteSerializer`) e fixei `MotivoEnum` e `SituacaoEnum` de veículos em `ENUM_NAME_OVERRIDES`, para os nomes que o frontend já usa não mudarem.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`, numa imagem reconstruída com a Pillow.

**Ajustes em testes de outras tarefas:**
- `test_t011_contas.py`: a lista de rotas que o suporte lê ganhou `api/clientes/` e `api/clientes/<int:pk>/`.
- `test_classificacao.py`: o campo de exemplo `nome_contato` virou `status_atual`, porque `nome` agora é sensível (R-02).

**Dependência nova (registrar no PR):**
- `Pillow>=11.1,<13` (a 12.3 foi instalada). Ela reprocessa as fotos de documento sem metadados (`AUD-05`), e a WeasyPrint dos contratos também vai usá-la.
- **DevOps:** reconstruir a imagem do backend. Não precisa de pacote de sistema: a imagem já tem `libjpeg-dev`, e a Pillow vem em wheel.

**Diferenças em relação ao contrato** (para o arquiteto conferir):
1. `contagens` traz também `inativos`, para a aba de inativos.
2. Os momentos (`consentimento_em`, `bloqueio.desde`, `enviado_em`, `url_expira_em`) saem em UTC com `Z`, como pede `docs/api/README.md`. O `DateTimeField` do DRF devolve no fuso do servidor (`-03:00`), e por isso os serializers de clientes usam `default_timezone=UTC`. **Ponto geral:** `aprovacoes` (`pedido_em`, `decidido_em`) e `contas` (`fim`, `criada_em`, `ultimo_uso`, `expira_em`) usam o `DateTimeField` puro e, pelo mesmo motivo, saem com `-03:00`. Vale uma tarefa pequena para alinhar tudo, talvez com um campo único em `comum`.
3. O bloco `financeiro` precisa trazer também `conta_mais_antiga_id`, que é o alvo do `cobrar`.
4. Os eventos do financeiro precisam levar `cliente_id`: `parcela_atrasou(cliente_id, dias_atraso, vencimento?)` e `parcela_paga(cliente_id, ...)`. O exemplo da ADR 0011 só tem `parcela_id`, `origem_tipo` e `origem_id`.
5. O desbloqueio automático depende do contador `contas_atrasadas_15_dias` que o financeiro registra. A inativação depende dos contadores `locacao_aberta`, `em_aberto_centavos` e `venda_aberta`.
6. `bloqueio.descricao` é o motivo de quem bloqueou, ou "Conta com N dias de atraso desde dd/mm/aaaa" no automático. O model ganhou `bloqueio_desde`, `bloqueio_descricao` e `responsavel_celular`, que não estavam no modelo de dados.
7. Sem índice trigram no nome: a busca usa `icontains`, com índice em `Lower(nome)`. O `pg_trgm` precisa ser instalado uma vez no banco, fora dos schemas das empresas, e isso pede uma decisão de infraestrutura (arquiteto e devops). Até 612 clientes por empresa, não faz diferença.
8. `POST /analisar/` não tem documentos, então o item `documentos` vem sempre "Faltam 4 documentos".
9. `desbloquear` de cliente que não está bloqueado responde 409 `transicao_cliente`.
10. Exportação (`POST /api/clientes/exportar/`), exportar dados do titular e anonimizar ficaram de fora (`AUD-06` e `AUD-07`, fase 2).

**Dúvida para o produto:** está em `tarefas/backlog.md` com a etiqueta `[decisão]`. São duas leituras que fiz no código:
- CNH C, D ou E aluga carro, porque pela lei elas incluem a B;
- cliente bloqueado não pode ser inativado.

**Para a Seguranca revisar:**
- `arquivos.sem_metadados`: a imagem é aberta e copiada pixel a pixel para uma nova. Uma bomba de descompressão vira 400, e o limite de 10 MB vale antes.
- `pode_ver_completo` nega o completo a qualquer ator com `e_suporte`, antes de olhar o perfil.
- Nenhuma URL de documento é gerada na representação resumida, e o teste confere que não há evento `documento_cliente.ver` do suporte.

**Próximo passo para quem recebe:**
- **Frontend:** trocar o `falso-clientes.ts` pela API. Os nomes seguem `tipos-clientes.ts`, mais `inativos` nas contagens e os blocos `null`. O envio de documento é `multipart/form-data`, e a resposta é o cliente completo. A URL do documento vence em 15 minutos: busque o cliente de novo para abrir.
- **QA:** a T-019 pode partir dos dados de `test_t014_clientes.py` (CPFs válidos com o miolo do seed: Rafael `32137710587`, Ana `74155201658`, Carlos `25890144227`, Patrícia `36912987451`, Diego `14778912349`).
- **Backend (T-015 e T-017):**
  - locações registram `locacao_atual`, `ultima_locacao`, o filtro `com_locacao` e o contador `locacao_aberta`, e chamam `impedimentos_para_retirada` antes da vistoria de saída;
  - o financeiro registra `financeiro`, `historico`, o filtro `em_aberto` e os contadores, e publica os dois eventos com `cliente_id`.
