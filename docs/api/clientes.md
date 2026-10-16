# Clientes

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-247, leitura da CNH-e; T-249, filtro de filial na lista); 07 out 2026 (T-036), emendas de 09 out 2026 (T-088) · **App:** `clientes` (schema da empresa) · **Regras:** CLI-01 a CLI-08, CLI-10, CLI-11, USR-07, AUD-04, AUD-05, AUD-06, APR-05, LOC-07 · **ADRs:** 0014 (documento cifrado), 0015 (blocos de outros apps), 0026 (leitura da CNH-e) · **Telas:** Clientes, Cliente · **Critérios:** `docs/qa/criterios/T-248.md` (CA-248-01 a 07), CA-247-08 a 12

Convenções gerais em `docs/api/README.md`. Modelo: item 11 e `DocumentoCliente` em `docs/decisoes/modelo-de-dados.md`.

O cliente é da empresa, compartilhado entre filiais: a lista não é filtrada pelo `X-Filial` (`USR-07`, `CLI-10`). Ela tem um filtro de filial próprio, o `?filial=` (abaixo), que começa vazio ("Todas as filiais").

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver lista (CPF mascarado) e ficha | sim | sim | sim | — (403, `USR-09`) | sim |
| Ver dados pessoais completos e documentos (`AUD-04`) | sim | sim | sim | — | — |
| Cadastrar e editar | sim | sim | sim | — | — |
| Bloquear manualmente | sim | sim | — | — | — |
| Desbloquear manualmente | sim (direto) | sim (direto) | pede (`APR-05`) | — | — |
| Inativar e reativar | sim | sim | — | — | — |
| Exportar dados do titular e anonimizar (`AUD-06`, fase 2) | sim | — | — | — | — |

Quem não pode ver os dados completos recebe só a representação resumida, com CPF mascarado, sem endereço, CNH e documentos; o financeiro recebe a ficha do financeiro (abaixo, `USR-09`). O vistoriador não abre a lista nem a ficha: 403 `{ "codigo": "permissao", "mensagem": "Seu perfil não tem acesso a esta ação." }`; ele vê do cliente só o que vem com a vistoria (`vistorias.md`, `USR-09`). O token de suporte (`PLT-07`) **sempre** recebe a resumida, mesmo com permissão `ver_editar` (`AUD-09`): ele pode editar campos do cadastro, mas a resposta não traz documento, CNH nem URLs de documento.

## Representação

### Resumida (listas e quem não tem permissão de cadastro)

```json
{
  "id": 1201, "tipo": "pf", "nome": "Juliana Rocha",
  "documento_mascarado": "***.218.330-**",
  "celular": "85981142290",
  "status": "ativo",
  "situacao": { "codigo": "em_dia", "rotulo": "Em dia", "tom": "sucesso" },
  "cliente_desde": "2026-03-04",
  "locacao_atual": { "id": 2836, "codigo": "LOC-2836", "veiculo": "Factor 150", "detalhe": "semanal", "alerta": null },
  "ultima_locacao": null,
  "financeiro": { "total_pago_centavos": 267400, "em_aberto_centavos": 0, "a_devolver_centavos": 0 },
  "venda_aberta": null,
  "acao_principal": { "codigo": "ver_locacao", "rotulo": "Ver locação", "alvo": { "tipo": "locacao", "id": 2836 } }
}
```

- CNPJ não é dado pessoal e sai inteiro em `documento_mascarado` para PJ.
- `situacao` e `acao_principal` são decididas pela API (ver abaixo).

### Ficha do financeiro (detalhe, perfil `financeiro`, `USR-09`, T-136)

A resumida mais `email` e `bloqueio` (o mesmo bloco da completa, com o motivo do bloqueio). `acao_principal` só vem quando é `cobrar` (`CLI-07`); nos demais casos vem `null`. Sem `documento`, CNH, endereço, referência, documentos, pendências nem `analise` (`AUD-04`, `CLI-04`). As locações do cliente vêm de `GET /api/locacoes/?cliente=<id>`, e as parcelas atrasadas e os pagamentos, de `GET /api/financeiro/contas-receber/?cliente=<id>`, que o financeiro já pode ler. A lista continua com a resumida.

### Completa (detalhe, para quem pode cadastrar)

A resumida mais:

```json
{
  "documento": "05221833018",
  "nascimento": "1998-02-14", "idade": 28,
  "email": "juliana@email.com", "profissao": "Entregadora",
  "cnh": { "numero": "04512345678", "categoria": "A", "validade": "2029-05-10", "primeira_habilitacao": "2017-06-01", "situacao": "valida" },
  "responsavel": null,
  "endereco": { "cep": "60325000", "logradouro": "...", "numero": "...", "complemento": null, "bairro": "...", "cidade": "Fortaleza", "uf": "CE" },
  "referencia": { "nome": "Maria Rocha", "parentesco": "mãe", "telefone": "85999990000" },
  "consentimento_em": "2026-03-04T13:00:00Z",
  "bloqueio": null,
  "documentos": [
    { "tipo": "cnh_frente", "enviado_em": "...", "url": "https://...assinada...", "url_expira_em": "..." },
    { "tipo": "cnh_verso", "enviado_em": "...", "url": "...", "url_expira_em": "..." },
    { "tipo": "selfie_documento", "enviado_em": null, "url": null, "url_expira_em": null },
    { "tipo": "comprovante_residencia", "enviado_em": null, "url": null, "url_expira_em": null }
  ],
  "pendencias": ["selfie_documento", "comprovante_residencia"],
  "analise": { ...ver Análise do cadastro... }
}
```

- `documento` e `cnh.numero` são decifrados só nesta resposta (ADR 0014). `cnh.situacao`: `valida`, `vencida` (até 30 dias), `vencida_impede` (mais de 30 dias, `CLI-02`).
- PJ: `responsavel` = `{ "nome", "cpf", "celular" }` do condutor; `cnh` é a do condutor.
- `bloqueio`: `{ "motivo": "atraso" | "manual", "desde": "...", "descricao": "...", "desbloqueia_sozinho": true }`. `descricao` é o motivo de quem bloqueou, ou "Conta com N dias de atraso desde dd/mm/aaaa" no bloqueio automático. No automático, a descrição é montada na leitura com os dias de atraso de hoje da conta vencida mais antiga (sem a caução, dia corrido em `America/Sao_Paulo`); o número do dia do bloqueio fica no `motivo` do evento `cliente.bloquear` (`CLI-05`, T-140).
- URLs dos documentos assinadas, 15 minutos (`AUD-05`); cada `GET` gera outras. Cada geração grava evento de auditoria de acesso a documento.
- `pendencias`: o que falta para sair de `incompleto` (`CLI-03`). Valores: os 4 tipos de documento, `consentimento`, `cnh`, `endereco`, `referencia`, `nascimento` (PF), `responsavel` (PJ).

### Blocos de outros apps (ADR 0015)

| Bloco | Fornecedor | Conteúdo |
| --- | --- | --- |
| `locacao_atual` | `locacoes` | locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada`: `id`, `codigo`, `veiculo` (modelo curto), `detalhe` (texto pronto: "devolve hoje", "25 dias de atraso", "mensal"), `valor_a_devolver_centavos` (encerramento antecipado, `LOC-13`), `alerta` ("Cancelando", "Parcela atrasada" etc.) |
| `ultima_locacao` | `locacoes` | sem locação atual: `{ "codigo": "LOC-2702", "encerrada_em": "2026-09-29" }` |
| `financeiro` | `financeiro` | `total_pago_centavos` (soma das contas pagas, sem caução), `em_aberto_centavos` (contas vencidas e não pagas), `a_devolver_centavos`, `conta_mais_antiga_id` (alvo do `cobrar`, `null` sem conta em aberto) |
| `venda_aberta` | `vendas` | `{ "id", "codigo": "VEN-0177", "veiculo" }` |

Enquanto o fornecedor não existe, o bloco vem `null` (em T-014, todos).

### Situação e ação principal

`situacao`, na ordem (a primeira que valer):

| `codigo` | Quando | `rotulo` |
| --- | --- | --- |
| `bloqueado` | `status = bloqueado` | Bloqueado |
| `cancelando` | locação atual com cancelamento pendente (alerta de `locacoes`) | Cancelando |
| `parcela_atrasada` | `em_aberto_centavos > 0` | Parcela atrasada |
| `incompleto` | `status = incompleto` | Cadastro incompleto |
| `inativo` | `status = inativo` | Inativo |
| `em_dia` | tem locação atual | Em dia |
| `sem_locacao` | o resto | Sem locação |

`acao_principal` (`CLI-07`), na ordem: em aberto → `cobrar` (alvo: a conta mais antiga); cadastro incompleto → `completar_cadastro`; com venda aberta → `ver_proposta`; com locação → `ver_locacao`; sem locação e `ativo` → `nova_locacao`. Ordem decidida pelo produto em 07 out 2026 (T-037), igual à tela: Lucas (LOC-2856) recebe `completar_cadastro`; Diego Martins (LOC-2848 e proposta da CB 300F) recebe `ver_proposta`. Cliente bloqueado sem valor em aberto não ganha `nova_locacao`.

---

## GET /api/clientes/
Perfis: todos menos o vistoriador (403, `USR-09`).
Query: `?situacao=com_locacao|em_aberto|bloqueados|incompletos|inativos` (`CLI-06`). Sem `situacao`, a lista padrão não traz clientes `inativo`; eles só aparecem com `?situacao=inativos`. Também: `?tipo=pf|pj`, `?busca=`, `?ordem=-criado_em|nome|-total_pago`, `?filial=<id>` (`CLI-10`, T-249).
- `busca` com só dígitos (11 ou 14) procura CPF/CNPJ exato pelo hash (ADR 0014); com texto, procura no nome (`icontains`, com índice em `Lower(nome)`) e no celular. Trigram (`pg_trgm`) só quando o volume pedir, com ADR de infraestrutura.
200:
```json
{
  "contagens": { "todos": 612, "com_locacao": 42, "em_aberto": 2, "bloqueados": 1, "incompletos": 3, "inativos": 0 },
  "indicadores": { "novos_no_mes_anterior": 38, "com_locacao_pct": "7.00", "em_aberto_total_centavos": 164640 },
  "resultados": [ { ...resumida... } ],
  "proximo": "...", "anterior": null
}
```
- Filtros `com_locacao` e `em_aberto` são registrados por `locacoes` e `financeiro` (ADR 0015); até eles existirem, as contagens vêm `null`.
- Caso do seed (`FIN-01`): em aberto = Carlos R$ 299,40 + Rafael R$ 1.347,00 = `em_aberto_total_centavos: 164640`, `em_aberto: 2`.
- Exportar: `POST /api/clientes/exportar/`, só administrador, 202 (`AUD-07`).

**Filtro de filial (`CLI-10`, decisão do dono de 15 out 2026, T-248; CA-248-01 a 07).**
- **Sem `?filial`** ("Todas as filiais", o padrão para todo perfil): todos os clientes da empresa, como antes. O `X-Filial` do seletor do topo é ignorado nesta rota, e a tela não o usa para preencher o filtro (CA-248-06).
- **Com `?filial=<id>`:** só os clientes com pelo menos uma locação nessa filial, em qualquer estado (inclusive `aguardando_retirada` e `cancelada`, CA-248-02). Cliente sem locação só aparece sem o filtro. Cliente com locação em duas filiais aparece nas duas, uma vez em cada (CA-248-03).
- **Quem pode escolher:** só filial ativa do escopo da pessoa, `filiais.selectors.filiais_do_usuario(usuario)` (`USR-07`; administrador e financeiro, todas as ativas, sem estar ligados a elas). Filial de fora do escopo, desativada (`FIL-06`) ou que não existe: 403 `{ "codigo": "USR-07", "mensagem": "Você não tem acesso a esta filial" }`, a mesma resposta nos três casos (não revela se a filial existe). Valor que não é número: 400 `validacao`. As opções do filtro na tela são as de `GET /api/filiais/minhas/` (`filiais.md`), mais "Todas as filiais"; não há rota nova (CA-248-07).
- **O que vale dentro da filial:** `situacao`, `tipo`, `busca` e `ordem` combinam com ela (CA-248-05); as `contagens` das abas e os `indicadores` contam só os clientes que passam no filtro de filial. Os números de cada cliente (blocos `financeiro`, `locacao_atual`, `ultima_locacao`) e as somas dos `indicadores` que vêm deles (`em_aberto_total_centavos`) continuam os do cliente na empresa inteira: o filtro escolhe **quem** aparece, não recorta os números (CA-248-04; Carlos na Caucaia mostra R$ 299,40 e a LOC-2841, da Centro).
- **Como, sem `clientes` ler o model de `locacoes`** (ADR 0015, item 5): `locacoes` registra o filtro `filial` em `clientes` por `registrar_filtro("clientes", "filial", func)`, e a `func(queryset, filial_id)` devolve `queryset.filter(Exists(Locacao.objects.filter(cliente=OuterRef("pk"), filial_id=filial_id)))`. A conferência do escopo (`USR-07`) é de `clientes`, antes de chamar o filtro, por `comum.permissoes`. Sem o fornecedor registrado (módulo de locações desligado), `?filial` com filial válida devolve a lista vazia e as contagens zeradas. O índice de `Locacao` em `cliente` vira `(cliente, filial)` (`modelo-de-dados.md`).
- O vistoriador continua sem a lista (403 `permissao`); o token de suporte usa o filtro com o mesmo escopo de filial que já tem nas outras listas (`PLT-07`).
- Testes com o código: `test_cli_10_lista_filtra_por_filial` (CA-248-01 a 05; é o `test_cli_lista_filtra_por_filial` do backlog, com o código da regra no nome), `test_cli_10_lista_ignora_o_seletor` (CA-248-06) e `test_cli_10_filial_sem_acesso` (CA-248-07).

## GET /api/clientes/{id}/
Perfis: todos menos o vistoriador (403, `USR-09`). Completa para quem pode cadastrar; a ficha do financeiro para o financeiro; resumida para o suporte (`AUD-09`).

## POST /api/clientes/
Perfis: administrador, gerente, vendedor.
Corpo (PF):
```json
{ "tipo": "pf", "nome": "Lucas Ferreira", "documento": "12345678909", "nascimento": "1998-02-14",
  "celular": "85988771203", "email": "lucas@email.com", "profissao": "Entregador",
  "cnh": { "numero": "...", "categoria": "A", "validade": "2030-01-10", "primeira_habilitacao": "2018-03-01" },
  "endereco": { ... }, "referencia": { "nome": "...", "parentesco": "...", "telefone": "..." },
  "consentimento": true }
```
PJ: `nome` = razão social, `documento` = CNPJ, `responsavel: { nome, cpf, celular }`, `cnh` do condutor; `nascimento` não se aplica.
Obrigatórios para salvar: `tipo`, `nome`, `documento`, `celular`. O resto pode faltar: o cliente fica `incompleto` (`CLI-03`) e pode ter locação criada, mas a retirada só libera com o cadastro completo.
201: completa. O `status` é `ativo` se não houver `pendencias`, senão `incompleto`.
400 `validacao`: CPF ou CNPJ com dígito verificador errado (`CLI-01`), CEP inválido, categoria de CNH fora da lista.
409 `{ "codigo": "CLI-01", "mensagem": "Já existe um cliente com este CPF", "detalhes": { "cliente_id": 1201, "nome": "Juliana Rocha" } }` (busca pelo hash). A tela oferece abrir o cadastro existente.
`consentimento: true` grava `consentimento_em` com data e hora; não pode ser desmarcado depois por aqui (revogar é pedido do titular, `AUD-06`).
"Salvar e iniciar locação" (`CLI-08`) é o mesmo `POST`; o frontend abre a Nova locação com o `id` devolvido.
Regras: CLI-01, CLI-03.

## PATCH /api/clientes/{id}/
Perfis: administrador, gerente, vendedor. Corpo: qualquer campo do `POST` menos `tipo`. Trocar `documento` passa pelas mesmas validações (`CLI-01`).
200: completa. Completar a última pendência leva `incompleto` → `ativo`; tirar um dado obrigatório leva `ativo` → `incompleto`. Cliente `bloqueado` continua bloqueado.

## POST /api/clientes/{id}/documentos/
Perfis: administrador, gerente, vendedor. `multipart/form-data`: `tipo` (`cnh_frente`, `cnh_verso`, `selfie_documento`, `comprovante_residencia`; `cnh_digital` só pelo salvar com a CNH-e lida, abaixo), `arquivo` (JPG, PNG ou PDF, até 10 MB; a imagem é reprocessada e perde os metadados).
201: a completa. Substitui o documento ativo do mesmo tipo (o anterior fica guardado, inativo). Pode levar o cliente a `ativo`.

## Análise do cadastro (CLI-04)

### GET /api/clientes/{id}/analise/
Perfis: quem pode cadastrar. Também vem dentro do detalhe. Para cadastro ainda não salvo, `POST /api/clientes/analisar/` com o mesmo corpo do `POST`, sem gravar nada. Sem documentos enviados, o item `documentos` dele vem sempre `pendente`, "Faltam 4 documentos".
200:
```json
{ "itens": [
    { "codigo": "cpf", "situacao": "ok", "rotulo": "CPF válido" },
    { "codigo": "cnh", "situacao": "ok", "rotulo": "CNH categoria A, válida" },
    { "codigo": "lista_bloqueio", "situacao": "ok", "rotulo": "Fora da lista de bloqueio" },
    { "codigo": "historico", "situacao": "ok", "rotulo": "Sem atraso na empresa" },
    { "codigo": "documentos", "situacao": "pendente", "rotulo": "Faltam 2 documentos" }
  ] }
```
- `situacao`: `ok`, `pendente`, `problema`.
- `cpf`: dígito verificador. "Regular" na Receita depende de integração e fica fora do MVP (decisão de 07 out 2026, consulta de crédito); o rótulo é "CPF válido".
- `lista_bloqueio`: o documento, ou o CPF do responsável na PJ, pertence a cliente `bloqueado` da empresa.
- `historico`: atrasos na empresa (fornecido por `financeiro`, ADR 0015), com as situações e os rótulos da `CLI-04`: `problema` "Conta em atraso na empresa", `pendente` "Já pagou com atraso na empresa", `ok` "Sem atraso na empresa", `ok` "Cliente novo na empresa". Atraso contado pela `FIN-03`. Com o módulo financeiro desligado, `pendente` "Sem histórico".
- `credito`: não aparece no MVP (fase 2, parceiro pago por consulta).

## Bloqueio (CLI-05, APR-05)

### POST /api/clientes/{id}/bloquear/
Perfis: administrador, gerente. Corpo: `{ motivo }`. 200: completa com `bloqueio.motivo = "manual"`, `desbloqueia_sozinho: false`. 409 `transicao_cliente` se já bloqueado.

### POST /api/clientes/{id}/desbloquear/
Corpo: `{ motivo }`.
- Administrador e gerente: desbloqueiam na hora, com motivo e evento de auditoria (`CLI-05`). 200; o cliente volta a `ativo` (ou `incompleto`, se tiver pendências). Um pedido `APR-05` pendente é cancelado (`cancelar_pendentes`).
- Cliente que não está bloqueado: 409 `transicao_cliente`.
- Vendedor: cria o pedido `APR-05` por `comum.aprovacoes.pedir` (ADR 0019), com origem `cliente` e a filial da requisição do vendedor (cliente é da empresa). 202 `{ "pedido_aprovacao": { "id", "tipo": "APR-05", "status": "pendente" } }`; outro pedido igual pendente → 409 `pedido_pendente`. Aprovado por gerente ou administrador (nunca quem pediu, `APR-09`), o cliente volta como acima.
- Decidido pelo dono do produto em 07 out 2026 (item 12, opção A; `CLI-05`, `APR-05`).
- Bloqueio automático por atraso não precisa disso: some sozinho quando o cliente quita (assinante de `financeiro.parcela_paga`, `CLI-05`).

Bloqueio automático: o assinante de `financeiro.parcela_atrasou` bloqueia com `motivo = "atraso"` quando alguma conta do cliente passa de 15 dias de atraso (`CLI-05`, `LOC-07`). Caso do seed: Rafael Sousa, 25 dias → `bloqueado`.

## Inativar

`POST /api/clientes/{id}/inativar/` · administrador, gerente · `{ motivo }` → 200. Inativo some da lista padrão, da escolha na Nova locação e da venda. 422 `{ "codigo": "cliente_com_pendencia", "detalhes": { "locacao_aberta": true, "em_aberto_centavos": 0, "venda_aberta": false } }` com locação aberta, valor em aberto ou venda aberta.
`POST /api/clientes/{id}/reativar/` · administrador, gerente · `{ motivo }` → 200; volta a `ativo` ou `incompleto` conforme as pendências (`CLI-03`).
Decidido pelo produto em 07 out 2026 (T-037).

## LGPD do titular (AUD-06) · fase 2

`POST /api/clientes/{id}/exportar-dados/` (administrador) → 202 `{ "exportacao_id" }`; arquivo com os dados do cliente em segundo plano, link de 7 dias.
`POST /api/clientes/{id}/anonimizar/` (administrador) · `{ motivo, confirmacao: "<nome do cliente>" }` → 200. Apaga os cifrados, troca os hashes por valores aleatórios, troca nome, contato, endereço e referência por marcas fixas e grava `anonimizado_em`; contratos e registros financeiros ficam, anonimizados (ADR 0014). 422 `cliente_com_pendencia` com locação aberta ou valor em aberto.

---

## Interface interna para os outros apps

| Item | Uso |
| --- | --- |
| `clientes.selectors.impedimentos_para_retirada(cliente, tipo_veiculo, data)` | lista de `{ codigo, mensagem }` usada por locações e vistorias antes da retirada: `CLI-03` (cadastro incompleto), `CLI-02` (CNH sem a categoria A para moto ou B para carro, ou vencida há mais de 30 dias), `CLI-05` (bloqueado), `cliente_inativo`. Vazia = pode retirar. |
| `clientes.selectors.impedimentos_para_nova_locacao(cliente)` e `..._para_venda(cliente)` | `CLI-05` (bloqueado não faz nova locação nem compra), `cliente_inativo`. |
| assinante de `financeiro.parcela_atrasou` | bloqueio automático com 15 dias (`CLI-05`). |
| assinante de `financeiro.parcela_paga` | desbloqueio automático quando o contador `contas_atrasadas_15_dias` do cliente (registrado por `financeiro`) chega a 0. |
| contadores pedidos aos outros apps (ADR 0015) | `contas_atrasadas_15_dias` e `em_aberto_centavos` (`financeiro`), `locacao_aberta` (`locacoes`), `venda_aberta` (`vendas`): o `cliente_com_pendencia` do inativar. Sem o fornecedor, contam 0. |
| `CAMPOS_AUDITORIA` | cifrados omitidos; nome (PF), nascimento, contatos, endereço e referência mascarados (ADR 0014). |

## O que muda para as tarefas (T-249)

- **T-250 (backend):** `?filial=` em `GET /api/clientes/`, com o escopo conferido em `clientes` e o filtro registrado por `locacoes` (ADR 0015); contagens e indicadores dentro do filtro; índice `(cliente, filial)` em `Locacao`. Testes `test_cli_10_*` acima.
- **T-251 (frontend):** filtro de filial na lista, com as opções de `GET /api/filiais/minhas/` e "Todas as filiais" como padrão, sem ler o seletor do topo; a 403 `USR-07` mostra a mensagem da API. CA-248-01 a 07.
## Preencher pela CNH-e (`CLI-11`, ADR 0026, T-247)
Na fase que o dono decidir ("Pontos em aberto" das regras; padrão: fase 2). Decisão técnica na ADR 0026, a mesma do CRLV-e (`veiculos.md`). A leitura não grava nada. Critérios CA-247-08 a 12.
### POST /api/clientes/leitura-cnh/
Perfis: administrador, gerente e vendedor (quem cadastra cliente, `pode.clientes_cadastrar`); vistoriador e financeiro, 403 `permissao` (CA-247-12). **Token de suporte: 403 `PLT-07`** nos dois modos, porque a resposta traz o CPF completo, que o suporte nunca vê (`AUD-09`). Confirmado pela segurança na T-247.
`multipart/form-data`: `arquivo` (o PDF da CNH-e, até **2 MB**). Serve ao cliente novo e ao cadastro já aberto; no cadastro aberto, a tela manda `cliente_id` (opcional) só para o aviso abaixo.
200, com `Cache-Control: no-store`:
```json
{ "documento": "cnh",
  "campos": { "nome": "Lucas Ferreira", "cpf": "12345678909", "nascimento": "1998-02-14",
              "cnh_numero": "01234567890", "cnh_categoria": "A", "cnh_validade": "2030-01-10",
              "cnh_primeira_habilitacao": "2018-03-01" },
  "lidos": ["nome", "cpf", "nascimento", "cnh_numero", "cnh_categoria", "cnh_validade", "cnh_primeira_habilitacao"],
  "quantidade": 7,
  "rotulo": "CNH-e lida · 7 campos preenchidos",
  "cliente_existente": { "id": 1201, "nome": "Lucas Ferreira" },
  "leitura": "<comprovante assinado>" }
```
- `campos` traz só os 7 da `CLI-11`. Filiação, RG e órgão emissor, naturalidade, códigos de observação, foto e assinatura não são extraídos nem saem do processo filho (ADR 0026, item 4; CA-247-11). Os nomes dos campos são os do `POST /api/clientes/` (`documento` = `cpf`; `cnh.numero`, `cnh.categoria`, `cnh.validade`, `cnh.primeira_habilitacao`), e a tela faz o mapa.
- `cliente_existente`: o CPF lido procurado pelo hash (`CLI-01`, ADR 0014). Vem `null` quando não há cliente com ele ou quando é o próprio `cliente_id` enviado. Quando vem, a tela avisa e oferece abrir o cadastro dele (CA-247-09); salvar como cliente novo continua recusado com o 409 `CLI-01` de sempre. Ele traz só `id` e `nome`, como o 409.
- 422 `{ "codigo": "CLI-11", "mensagem": "Não conseguimos ler este documento. Preencha os campos à mão." }` e 400 `{ "codigo": "validacao", "campos": { "arquivo": "Envie o PDF da CNH-e." } }`, pelos mesmos motivos da leitura do CRLV-e. 429 `muitas_requisicoes` no mesmo limite, somado ao do CRLV-e (30 por hora por usuário, 200 por empresa; as recusas também contam), e 503 `leitura_ocupada` como no CRLV-e.
### Salvar com a CNH-e lida
`POST /api/clientes/` ou `PATCH /api/clientes/{id}/` em `multipart/form-data`, com os campos de sempre e mais `cnh_arquivo` (o mesmo PDF) e `leitura?`. Numa transação só, salva o cliente (com as validações de sempre: `CLI-01`, `CLI-02`) e grava o `DocumentoCliente` do tipo **`cnh_digital`**, no armazenamento privado (`AUD-05`, link de 15 minutos na leitura do documento). O nome do arquivo é gerado pelo backend. O comprovante `leitura` vencido, de outra empresa, de outro usuário ou de outro arquivo é tratado como ausente, e o `cnh_arquivo` é conferido de novo (primeiros bytes, 2 MB) e gravado com `Content-Type: application/pdf` fixo (ADR 0026, item 8). O `cnh_digital` entra na exportação do titular e é apagado na anonimização, como as fotos (`AUD-06`, B-05 da segurança).
- O evento `cliente.criar` ou `cliente.editar` leva `preenchido_pelo_documento: { "tipo": "cnh", "campos": [...], "corrigidos": [...] }`, só com os nomes dos campos (o CPF e a CNH já são omitidos, ADR 0014; CA-247-11).
- **Cadastro completo (`CLI-03`):** com o padrão A do ponto em aberto, o `cnh_digital` ativo vale pela `cnh_frente` e pela `cnh_verso`; a selfie e o comprovante de residência continuam obrigatórios (CA-247-08 e 10). Com a opção B, o `cnh_digital` é só mais um anexo. A regra de `pendencias` muda conforme a resposta do dono.
### O que muda para as tarefas (T-247, fase da CNH-e)
- **Backend (sem número):** o parser da CNH-e no mesmo `integracoes/leitura_documentos/`; a rota; o multipart do `POST` e do `PATCH`; o tipo `cnh_digital` e as `pendencias` do `CLI-03`. Testes `test_cli_11_le_os_7_campos` (CA-247-08), `test_cli_11_cpf_ja_cadastrado` (CA-247-09), `test_cli_11_cliente_novo` (CA-247-10), `test_cli_11_nao_le_filiacao_nem_rg` (CA-247-11) e `test_cli_11_quem_pode` (CA-247-12, com o suporte).
