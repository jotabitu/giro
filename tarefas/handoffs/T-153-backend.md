# T-153 · Escrita da marca · backend → frontend, qa, seguranca

**O que foi feito:**
- `empresas/logo.py`: `limpar_logo(conteudo) -> LogoLimpo(conteudo, extensao, largura, altura)`, função pura pela ADR 0022. SVG lido com `defusedxml` (sem DTD, entidade nem recurso externo), conteúdo ativo recusado (item 3), o resto pela lista fechada (item 4, constantes iguais às da ADR), tamanho pelo `viewBox` ou `width`/`height` (item 5), serializado de novo sem declaração XML. PNG pela nota de 13 out 2026: assinatura completa, 2 MB antes de abrir, lado e área conferidos no cabeçalho antes do `load()` (sem mexer em `Image.MAX_IMAGE_PIXELS`), `verify()` e reabertura, `DecompressionBombWarning` vira erro só ali, `convert("RGBA")` e imagem nova sem `info` (não usa `comum.arquivos.sem_metadados`), só o primeiro quadro do APNG, 2 MB de novo depois de codificar.
- `empresas.services.salvar_marca(nome_exibicao=, cor=, logo=, remover_logo=, por=)`: limpa e grava o logo antes da transação (`<schema>/empresas/marca/logo-<sha256 16>.svg|png`, direto no provedor, para o nome ser o resumo); na transação, `select_for_update` na linha única, evento `empresa.alterar_marca` (categoria `configuracoes`) só quando algo muda; apaga `marca:<schema>` já e de novo no `on_commit`, junto com o arquivo antigo; se a transação falhar, apaga o novo; chama `registrar_passo_implantacao("marca")` em toda gravação aceita (inclusive sem mudança). Recusa suspeita (conteúdo ativo ou arquivo que não se lê) vai para o log como `WARNING` com schema, id do usuário e a mensagem, nunca o conteúdo.
- `empresas.services.simular_marca(nome_exibicao=, cor=)`: as contas de `GET /api/marca/` sem gravar.
- `CAMPOS_AUDITORIA` de `ConfiguracaoEmpresa`: `nome_exibicao`, `cor_marca` e `logo` inteiros (sem migração).
- Rotas: `PATCH /api/marca/` (multipart e JSON; o `GET` continua público na mesma view, que troca autenticação, permissão e limite pelo método) e `POST /api/marca/simular/`. Só administrador; suporte 403 `PLT-07` mesmo com "ver e editar" (`suporte_proibido`); empresa sem operação 403 `empresa_sem_operacao`. Limites: `marca_salvar_usuario` 30/hora e `marca_simular_usuario` 120/min.

**Onde:** `backend/apps/empresas/logo.py`, `services.py`, `models.py`, `api/views.py`, `api/serializers.py`, `api/urls.py`; `backend/comum/limites.py`; `backend/config/settings/base.py`; `backend/pyproject.toml` (mypy: `defusedxml.*` sem stubs).

**Dependência:** `defusedxml` já estava no `requirements.txt` (`>=0.7.1,<0.8`, entrou para o `openpyxl` da importação). A T-153 passa a usá-lo direto, pelo motivo da ADR 0022: o `xml.etree` da biblioteca padrão não recusa DTD nem entidades, e o `nh3` não serve para SVG. Nada novo a instalar.

**Contrato:** `docs/api/empresas.md`, "Escrita da marca"; `docs/api/openapi.yaml` regenerado; `npm run api:gerar` e `npm run typecheck` no frontend sem erro.

**Regras cobertas:** S-12 (`apps/empresas/tests/test_logo.py`: um teste por vetor da ADR, os que passam e os oito do PNG; `test_s_12_png_servido_com_nosniff` e `test_s_12_svg_ativo_recusado_com_warning_sem_conteudo` em `tests/aceitacao/test_t153_marca_escrita.py`), IMP-05 (`test_imp_05_salvar_marca_marca_o_passo`), `test_marca_simular_seis_cores`, `test_marca_patch_invalida_cache_e_versao`, `test_marca_patch_so_administrador`, idempotência, mensagens do contrato, troca e remoção apagando o arquivo antigo, falha na transação apagando o novo, limite de 30 por hora.

**Decisões de implementação:**
1. Caracteres de controle no `nome_exibicao` saem em silêncio: o contrato diz "sem caracteres de controle", mas a tabela de mensagens só tem a do tamanho.
2. Texto (não arquivo) em `logo` responde "Envie o logo em SVG ou PNG." (nenhuma rota aceita URL de logo).
3. Erro de leitura do SVG (XML quebrado, DTD, entidade, raiz errada) também gera o `WARNING`, como o do PNG.
4. Os elementos proibidos do item 3 são recusados em qualquer namespace, e os valores perigosos são conferidos em todos os atributos, inclusive nos que sairiam pela lista.

**Testes rodados:** `apps/empresas`, `test_t153_marca_escrita.py`, `test_t129_marca.py`, `test_t262_ramo.py`, `test_t181_configuracoes.py`, `test_t018_auditoria.py`, `test_permissoes_das_rotas.py`, `test_rotas.py`, `test_limites_entre_apps.py`; ruff, ruff format --check e mypy no backend inteiro, limpos.

**O que ficou de fora:** `tests/test_campos_sensiveis.py` falha na main por `movimentacoes.LocalApoio` (`nome`, `nome_busca` sem classificação em `CAMPOS_AUDITORIA`), fora desta tarefa; fica para quem cuida de `movimentacoes`. A T-165 (paleta em `comum.arquivos.sem_metadados`) segue aberta: o logo não usa essa função.

**Próximo passo para quem recebe:**
- **frontend (T-154):** as rotas estão no cliente gerado; o `PATCH` devolve o corpo de `GET /api/marca/` com o `ETag` novo.
- **qa:** marca salva no seed continua fora (o contrato diz que a Moto Rápida responde o padrão).
- **seguranca:** revisar `empresas/logo.py` contra a ADR 0022 e a nota do PNG.
