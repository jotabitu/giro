# Sessões revogáveis e dados sensíveis (cifra, HMAC, auditoria)

**Status:** aceita · 07 out 2026 · complementa a 0010 e a 0013 (revisão de segurança T-032: S-05, S-06, S-07, S-13)

## Contexto

O relatório `docs/seguranca/2026-10-07-fundacao.md` apontou:

- **S-13:** com refresh rotativo não existe "sessão" para listar ou revogar (o plano pede sessões visíveis e revogáveis; `USR-04` pede encerramento na hora), e revogar só o refresh deixa o access valer por até 5 minutos.
- **S-07:** CPF, CNPJ, CNH e CPF do responsável estavam em texto puro no modelo; o plano exige cifra em repouso, e a unicidade (`CLI-01`) e a busca exata precisam de um valor comparável.
- **S-05:** a chave da subconta Asaas só dizia "cifrada".
- **S-06:** a auditoria imutável (0010) mascarava só documentos; na criação de um cliente o evento guardaria nome, contato, endereço e dados da referência por 5 anos, e troca de senha poria o hash no evento.

## Decisão

### 1. Sessões (`contas.Sessao`)

- Model `contas.Sessao` (nos dois schemas, como o `Usuario`): `usuario` FK, `tipo` enum `desktop`, `celular`, `aparelho` (user agent resumido), `ip`, `criada_em`, `ultimo_uso`, `expira_em`, `revogada_em` nulo, `revogada_por` FK nulo, `motivo_revogacao` enum `saiu`, `revogada_pelo_usuario`, `revogada_pelo_administrador`, `usuario_desativado`, `expirou`.
- O login completo (depois das 2 etapas, quando exigidas) cria a `Sessao`. Access e refresh levam a claim `sid`. Tokens `pre_2fa` e `suporte` não têm sessão.
- `USR-06`: a sessão expira com 12 h sem uso no desktop e 30 dias no celular, contados de `ultimo_uso` (atualizado no `renovar` e, no máximo a cada 5 min, nas requisições).
- A autenticação recusa `sid` revogado ou expirado com 401 `{ "codigo": "sessao_encerrada" }`. A verificação usa cache de no máximo 30 s por `sid`, invalidado na revogação; revogar derruba o access na requisição seguinte.
- Revogar põe na blacklist o refresh vigente da sessão. Desativar usuário (`USR-04`) revoga todas as sessões dele na mesma transação.
- Endpoints (contrato de contas, T-011): a pessoa lista e encerra as próprias sessões; o administrador lista e encerra as de qualquer usuário da empresa. Toda revogação gera evento de auditoria (`seguranca`).

### 2. Cifra (`comum/cripto.py`) e campo cifrado

- Cifra autenticada pela biblioteca `cryptography` (Fernet multi-chave ou AES-256-GCM, à escolha do backend, registrada no PR). Formato `v<id_da_chave>:<cifrado>` para trocar de chave sem migração em massa. Dado associado = `empresa_id` + nome da tabela e do campo + `id_cifra` da linha. `id_cifra` é um UUID gerado na criação de cada linha que tem campo cifrado (coluna própria, imutável, porque o `id` ainda não existe quando o valor é cifrado antes do primeiro `save()`). Assim o cifrado copiado para outra linha da mesma tabela, ou para outra empresa, não decifra. *(Corrigido em 07 out 2026, antes de qualquer implementação: a versão anterior não tinha o `id_cifra` e não cumpria a promessa de "outra linha"; apontado pelo backend na T-033.)*
- Duas chaves mestras separadas, fora do banco e do repositório, vindas do cofre de segredos do ambiente (o devops define; KMS pede ADR dele): `GIRO_CHAVE_DADOS_PESSOAIS` e `GIRO_CHAVE_SEGREDOS`. Um terceiro segredo, `GIRO_PEPPER_HMAC`, é usado só para os hashes de busca. Nenhuma delas é a `SECRET_KEY`.
- `comum/campos.py` ganha `CampoCifrado` (texto cifrado, decifrado só sob demanda por `obj.<campo>_claro()`, nunca no `__str__`, no `repr` nem no Admin) e `CampoHashBusca` (HMAC-SHA256 do valor normalizado, hex de 64). A chave do HMAC é derivada por empresa, `HMAC(GIRO_PEPPER_HMAC, empresa_id)`, para que o mesmo CPF tenha hashes diferentes em empresas diferentes.
- Dados pessoais cifrados com `GIRO_CHAVE_DADOS_PESSOAIS`: `Cliente.documento`, `Cliente.cnh_numero`, `Cliente.responsavel_cpf`. Unicidade e busca exata pelo hash: `documento_hash` **único** no schema (`CLI-01`), `cnh_hash` e `responsavel_cpf_hash` com índice. A busca por CPF na lista normaliza o termo, calcula o HMAC e compara.
- Segredos cifrados com `GIRO_CHAVE_SEGREDOS`: `plataforma.ContaPagamento.chave_api_cifrada`. Ela só é decifrada dentro de `backend/integracoes/pagamentos/`, no momento da chamada, e nunca entra em serializer, Admin, log, Sentry nem auditoria.
- `AUD-04`: a máscara (`***.218.330-**`) é montada no serializer a partir do valor decifrado; o valor completo só sai para quem tem permissão de cadastro, e só no detalhe.
- `AUD-06` (anonimização): apaga o cifrado, troca o hash por um valor aleatório e grava `anonimizado_em`.

### 3. Classificação dos campos na auditoria (substitui o item 7 da 0010)

Cada model declara `CAMPOS_AUDITORIA = {"omitir": [...], "mascarar": [...]}`; o resto vai inteiro. `comum.auditoria` aplica:

| Tratamento | O que vai em `antes`/`depois` | Exemplos |
| --- | --- | --- |
| omitir | só `{"alterado": true}` | `password`, todo `*_hash` de token, `chave_api_cifrada`, todo `CampoCifrado`, chaves e tokens do `django_otp` |
| mascarar | máscara fixa | documento (CPF `***.218.330-**`; CNPJ inteiro), CNH (`*******1234`), nome de cliente PF (iniciais), nascimento (só o ano), celular e telefone (`(85) *****-1234`), e-mail (`l***@g***.com`), endereço do cliente (só cidade e UF), nome da referência (iniciais), `Contrato.assinado_ip` (/24), `LancamentoBancario.pagador` (iniciais) |
| inteiro | valor | valores, status, datas de negócio, ids, códigos; nome e e-mail do funcionário (ele é o ator) |

`ip` e `aparelho` do ator ficam inteiros. Um teste de arquitetura falha se algum model tiver campo cujo nome case com `cpf|cnh|documento|senha|password|token|chave|secret|celular|telefone|email|endereco|logradouro|nascimento|ip` sem estar classificado.

## Consequências

- `comum/cripto.py`, `CampoCifrado`, `CampoHashBusca` e a classificação da auditoria entram na T-001 (ou logo depois, antes de T-011 e T-014); `Sessao` entra na T-011.
- Dependência nova: `cryptography` (registrar no PR). Três segredos novos no `.env.example` e nos ambientes (devops).
- Perder uma chave mestra é perder os dados cifrados: o backup das chaves fica fora do backup do banco, sob responsabilidade do devops.
- Testes obrigatórios: `test_cli_01_cpf_unico_pelo_hash`, `test_aud_06_auditoria_de_cliente_nao_guarda_nome_nem_documento_completos`, `test_aud_01_troca_de_senha_nao_grava_hash`, `test_conta_pagamento_chave_nao_aparece_em_serializer_admin_e_auditoria`, `test_usr_04_desativar_derruba_access_na_proxima_requisicao`, cifrado copiado para outra linha da mesma tabela, ou para outra empresa, não decifra.
