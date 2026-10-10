# T-090 · Contratos: modelos, PDF, assinatura e aditivo · backend → orquestrador, frontend, qa, arquiteto, seguranca, devops

**O que foi feito** (`docs/api/contratos.md`; CA-015-11 a 13):

- **Modelos (tela Contratos-Modelos, S-09):**
  - rotas `GET`/`POST /api/contratos/modelos/`, `GET`/`PATCH .../{id}/`, `POST .../previa/`, `.../publicar/` e `.../arquivar/`, além de `GET /api/contratos/marcadores/` e `GET /api/contratos/modelos-prontos/`. Só o administrador usa.
  - **Marcadores:** a lista fechada do contrato. Cada `{{grupo.campo}}` é trocado por expressão regular, com o valor escapado; não há motor de template. Um marcador fora da lista dá 400 `marcador_invalido`, ao salvar e ao publicar.
  - **HTML:** limpo ao salvar com `nh3`, pela lista branca. `script`, `style` e `iframe` saem com o conteúdo. `img`, `a`, `style`, `on*` e os outros atributos saem; só ficam `colspan` e `rowspan` com número.
  - **Versões (`LOC-15`):** editar um modelo publicado cria o rascunho da versão seguinte, e publicar tira a anterior de uso. O contrato guarda `versao_modelo` e o texto final (`versao_texto_html`), que não muda depois.
  - **`IMP-04`:** arquivar o último modelo de locação publicado responde 422. Publicar o primeiro marca o passo `contrato` da implantação.
  - **Modelos prontos:** são 6, de locação diária, semanal e mensal, para moto e para carro. Todos já trazem a cláusula de multa e juros.
  - **Prévia:** com `locacao_id`, usa os dados reais. `contratos` lê esses dados pelo registro `contratos/origens.py`, onde `locacoes` registra no `ready()` a função que os monta.
- **Contrato da locação:**
  - `POST /api/locacoes/{id}/contrato/` responde 202 `gerado`. Ele recusa:
    - locação fora de `aguardando_retirada`: 409 `contrato_fora_de_hora`;
    - desconto pendente: 409 `desconto_pendente`;
    - sem modelo publicado: 422 `IMP-04`;
    - contrato que já existe: 409 `contrato_existente`, também garantido por uma restrição no banco.
  - Depois do commit, a tarefa `contratos_preparar_e_enviar` (tempo limite de 60 s):
    1. faz o PDF;
    2. grava o `hash_pdf`;
    3. cria o token;
    4. manda o link por WhatsApp e e-mail, com a marca da locadora;
    5. leva o contrato a `enviado`.
  - `GET .../contrato/pdf/` devolve uma URL de 15 minutos (AUD-05). Não vale para o vistoriador.
  - `POST .../contrato/reenviar/` cria um link novo e invalida o anterior na hora.
  - No detalhe da locação, o bloco `contrato` vem preenchido e as ações `imprimir_contrato` e `reenviar_contrato` passaram a valer.
- **Link de assinatura (S-15):**
  - O token tem 32 bytes, e o banco guarda só o hash. Ele vale 7 dias e vai no fragmento (`/assinar#token`).
  - Rotas públicas: `POST /api/publico/assinaturas/consultar/` e `.../assinar/`. Têm limite de 10 por minuto por IP e de 20 por minuto por token.
  - O nome é conferido sem diferenciar maiúsculas e acentos.
  - Erros: 410 `link_expirado` e `contrato_ja_assinado`, 400 `nome_nao_confere` e 404 para token desconhecido ou trocado.
  - A assinatura grava o momento, o IP e o aparelho, e publica `contratos.contrato_assinado`. A tarefa `contratos_registrar_assinatura` gera o PDF assinado, com a página de registro: data e hora no fuso da filial, IP /24, aparelho e o hash do PDF assinado.
- **PDF (S-09):** sai com o WeasyPrint. O `url_fetcher` só entrega o logo da empresa (`giro-logo:empresa`) e recusa `http`, `https`, `file`, `data` e qualquer outro endereço. O CSS é só o do cabeçalho.
- **Aditivo (`LOC-08`):** `locacoes.contrato.gerar_aditivo(locacao)` é para a renovação da T-091. Usa o texto padrão do sistema. A tarefa diária `contratos_avisar_aditivos_sem_assinatura`, às 08:00, avisa os gerentes da filial quando o aditivo foi enviado há 7 dias e não foi assinado, uma vez por aditivo. O aditivo assinado não conta para a ativação.
- **`FIN-03`:**
  - o contrato grava `clausula_juros`;
  - `contratos.selectors.permite_juros(origem_tipo, origem_id)` é a porta para o financeiro;
  - `ConfiguracaoEmpresa` ganhou `multa_atraso_pct` (2,00) e `juros_mes_pct` (1,00), com os tetos como `CHECK`.
- `contratos` entrou no padrão de `GIRO_MODULOS_ATIVOS`.

**Dependências novas** (o motivo vai no PR):
- `weasyprint>=66,<70` (veio a 69.0): o PDF do contrato, que a stack e a ADR 0011 já preveem. A imagem já tinha pango, harfbuzz e fontes.
- `nh3>=0.2.18,<1` (veio a 0.3.7): a limpeza do HTML do modelo pela lista branca (S-09). Usa o `ammonia`, em Rust, e é mantido. O `bleach` foi descontinuado.
- **Orquestrador:** reconstruir a imagem do compose. Eu testei numa imagem local, `giro-backend:t090`, feita com o Dockerfile do repositório.

**Para o arquiteto (diferenças do contrato e do modelo de dados; nada mudou nos `.md`):**
1. `Contrato` ganhou campos que o modelo de dados não tem:
   - `filial` e `cliente` (FK): o escopo, o nome para conferir e o celular;
   - `titulo`, `enviado_em`, `cancelado_em`, `motivo_cancelamento` e `lembrete_aditivo_em`;
   - `pdf_assinado` e `hash_pdf_assinado`. O `pdf` e o `hash_pdf` do PDF que foi assinado não mudam, e o PDF final, com a página de registro, fica nesses dois campos.
   - `modelo` e `versao_modelo` são nulos no aditivo.
2. Códigos que o contrato não citava: 409 `contrato_fora_de_hora`, `desconto_pendente`, `sem_contrato` (reenviar sem contrato), `contrato_cancelado` e `modelo_arquivado`.
3. O resumo do contrato no detalhe ganhou `enviado_em`. O item do modelo ganhou `arquivado`, e a lista aceita `?arquivados=true`. O `id` de cada item da lista é o da versão mais nova, e as ações aceitam o `id` de qualquer versão do grupo.
4. `logo_url` e `cor_marca` vêm `null` na consulta pública, e o PDF leva o nome da empresa no cabeçalho, até a marca existir na `ConfiguracaoEmpresa`. O `url_fetcher` já aceita o logo.
5. O "20 por token" ficou por minuto.
6. Reenviar um contrato assinado manda pelo WhatsApp a URL do PDF assinado, que vale 15 minutos (AUD-05). Se a ideia for outra (anexo, ou página com login), é uma decisão para o contrato.
7. As rotas públicas mantêm `EmpresaOperando`: com a empresa suspensa, a assinatura é recusada (403). Elas entraram na lista de exceções de `test_permissoes_das_rotas.py`, sem `EscopoDeFilial`, porque ninguém está logado.

**Para devops:** o PDF tem tempo limite na tarefa (60 s soft, 70 s hard). O limite de memória (S-09) precisa ficar no worker: um container ou fila de PDF com memória limitada, ou `worker_max_memory_per_child`. O texto do modelo tem no máximo 200 mil caracteres.

**Para seguranca:** S-09 e S-15 têm testes com o nome da regra:
- `test_s_09_pdf_nao_busca_url_externa`;
- `test_s_09_contrato_marcador_fora_da_lista_recusado`;
- `test_s_09_ca_015_13_modelo_de_contrato`, que também cobre a limpeza do HTML;
- os testes `test_s_15_*`: link, reenvio, limites e isolamento entre empresas.
Na auditoria, o IP vai mascarado (/24), o token não aparece e o `versao_texto_html` (que tem CPF e endereço) fica omitido.

**Para o frontend:**
- telas Contratos-Modelos (lista, editor com "Campos automáticos", prévia, publicar e arquivar) e Onboarding-Contrato (modelos prontos);
- a página pública `/assinar`: lê o fragmento, apaga da barra e chama `consultar` e `assinar` com o token no corpo;
- no detalhe da locação, o bloco `contrato` e os botões "Imprimir" e "Reenviar".

**Para qa:** CA-015-11 a 13 estão em `tests/aceitacao/test_t090_contratos.py`, e os 3 `xfail` da T-090 saíram de `test_t015_locacoes.py`. A renovação real com o aditivo é da T-091.

**Onde:**
- `backend/apps/contratos/`: `models.py`, `marcadores.py`, `sanitizacao.py`, `pdf.py`, `prontos.py`, `origens.py`, `services.py`, `selectors.py`, `tasks.py`, `api/`, a migração `0002` e o `README.md`.
- `backend/apps/locacoes/`: `contrato.py` (novo), `apps.py`, `selectors.py`, `api/` e `README.md`.
- `backend/apps/empresas/models.py` e a migração `0003`.
- `backend/comum/limites.py`.
- `backend/config/settings/base.py`: o módulo, as taxas, o Beat e os nomes de enum.
- `backend/config/urls.py`, `backend/requirements.txt` e `docs/api/openapi.yaml`.

**Check:** (rodei com o `rodar.sh`, com `--rm` e `POSTGRES_HOST`, na imagem `giro-backend:t090`)
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `507 passed, 10 xfailed`. Antes eram 490 passed e 13 xfailed: os 3 `xfail` da T-090 saíram, e os 10 que ficam são da T-091 e da T-092.
- O OpenAPI foi regerado com `--validate`, sem aviso e só com acréscimos. A única linha que saiu é a descrição provisória do bloco `contrato`, que virou o componente `ContratoResumo`.
