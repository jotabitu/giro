# Clientes

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-036) · **App:** `clientes` (schema da empresa) · **Regras:** CLI-01 a CLI-08, AUD-04, AUD-05, AUD-06, APR-05, LOC-07 · **ADRs:** 0014 (documento cifrado), 0015 (blocos de outros apps) · **Telas:** Clientes, Cliente

Convenções gerais em `docs/api/README.md`. Modelo: item 11 e `DocumentoCliente` em `docs/decisoes/modelo-de-dados.md`.

O cliente é da empresa, compartilhado entre filiais: a lista não é filtrada pelo `X-Filial`.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver lista (CPF mascarado) | sim | sim | sim | sim | sim |
| Ver dados pessoais completos e documentos (`AUD-04`) | sim | sim | sim | — | — |
| Cadastrar e editar | sim | sim | sim | — | — |
| Bloquear manualmente | sim | sim | — | — | — |
| Desbloquear manualmente | sim (direto) | sim (direto) | pede (`APR-05`) | — | — |
| Inativar e reativar | sim | sim | — | — | — |
| Exportar dados do titular e anonimizar (`AUD-06`, fase 2) | sim | — | — | — | — |

Quem não pode ver os dados completos recebe só a representação resumida, com CPF mascarado, sem endereço, CNH e documentos. O token de suporte (`PLT-07`) **sempre** recebe a resumida, mesmo com permissão `ver_editar` (`AUD-09`): ele pode editar campos do cadastro, mas a resposta não traz documento, CNH nem URLs de documento.

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
  "locacao_atual": { "id": 2836, "codigo": "LOC-2836", "veiculo": "Factor 150", "detalhe": "devolve hoje", "alerta": null },
  "ultima_locacao": null,
  "financeiro": { "total_pago_centavos": 267400, "em_aberto_centavos": 0, "a_devolver_centavos": 0 },
  "venda_aberta": null,
  "acao_principal": { "codigo": "ver_locacao", "rotulo": "Ver locação", "alvo": { "tipo": "locacao", "id": 2836 } }
}
```

- CNPJ não é dado pessoal e sai inteiro em `documento_mascarado` para PJ.
- `situacao` e `acao_principal` são decididas pela API (ver abaixo).

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
- `bloqueio`: `{ "motivo": "atraso" | "manual", "desde": "...", "descricao": "...", "desbloqueia_sozinho": true }`.
- URLs dos documentos assinadas, 15 minutos (`AUD-05`); cada `GET` gera outras. Cada geração grava evento de auditoria de acesso a documento.
- `pendencias`: o que falta para sair de `incompleto` (`CLI-03`). Valores: os 4 tipos de documento, `consentimento`, `cnh`, `endereco`, `referencia`, `nascimento` (PF), `responsavel` (PJ).

### Blocos de outros apps (ADR 0015)

| Bloco | Fornecedor | Conteúdo |
| --- | --- | --- |
| `locacao_atual` | `locacoes` | locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada`: `id`, `codigo`, `veiculo` (modelo curto), `detalhe` (texto pronto: "devolve hoje", "25 dias de atraso", "mensal"), `valor_a_devolver_centavos` (encerramento antecipado, `LOC-13`), `alerta` ("Cancelando", "Parcela atrasada" etc.) |
| `ultima_locacao` | `locacoes` | sem locação atual: `{ "codigo": "LOC-2702", "encerrada_em": "2026-09-29" }` |
| `financeiro` | `financeiro` | `total_pago_centavos` (soma das contas pagas, sem caução), `em_aberto_centavos` (contas vencidas e não pagas), `a_devolver_centavos` |
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
Perfis: todos.
Query: `?situacao=com_locacao|em_aberto|bloqueados|incompletos|inativos` (`CLI-06`). Sem `situacao`, a lista padrão não traz clientes `inativo`; eles só aparecem com `?situacao=inativos`. Também: `?tipo=pf|pj`, `?busca=`, `?ordem=-criado_em|nome|-total_pago`.
- `busca` com só dígitos (11 ou 14) procura CPF/CNPJ exato pelo hash (ADR 0014); com texto, procura no nome (trigram) e no celular.
200:
```json
{
  "contagens": { "todos": 612, "com_locacao": 42, "em_aberto": 2, "bloqueados": 1, "incompletos": 3 },
  "indicadores": { "novos_no_mes_anterior": 38, "com_locacao_pct": "7.00", "em_aberto_total_centavos": 164640 },
  "resultados": [ { ...resumida... } ],
  "proximo": "...", "anterior": null
}
```
- Filtros `com_locacao` e `em_aberto` são registrados por `locacoes` e `financeiro` (ADR 0015); até eles existirem, as contagens vêm `null`.
- Caso do seed (`FIN-01`): em aberto = Carlos R$ 299,40 + Rafael R$ 1.347,00 = `em_aberto_total_centavos: 164640`, `em_aberto: 2`.
- Exportar: `POST /api/clientes/exportar/`, só administrador, 202 (`AUD-07`).

## GET /api/clientes/{id}/
Perfis: todos. Completa para quem pode cadastrar; resumida para os demais.

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
Perfis: administrador, gerente, vendedor. `multipart/form-data`: `tipo` (`cnh_frente`, `cnh_verso`, `selfie_documento`, `comprovante_residencia`), `arquivo` (JPG, PNG ou PDF, até 10 MB; a imagem é reprocessada e perde os metadados).
201: a completa. Substitui o documento ativo do mesmo tipo (o anterior fica guardado, inativo). Pode levar o cliente a `ativo`.

## Análise do cadastro (CLI-04)

### GET /api/clientes/{id}/analise/
Perfis: quem pode cadastrar. Também vem dentro do detalhe. Para cadastro ainda não salvo, `POST /api/clientes/analisar/` com o mesmo corpo do `POST`, sem gravar nada.
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
- `historico`: atrasos anteriores na empresa (fornecido por `financeiro`, ADR 0015; `pendente` com rótulo "Sem histórico" enquanto não existir).
- `credito`: não aparece no MVP (fase 2, parceiro pago por consulta).

## Bloqueio (CLI-05, APR-05)

### POST /api/clientes/{id}/bloquear/
Perfis: administrador, gerente. Corpo: `{ motivo }`. 200: completa com `bloqueio.motivo = "manual"`, `desbloqueia_sozinho: false`. 409 `transicao_cliente` se já bloqueado.

### POST /api/clientes/{id}/desbloquear/
Corpo: `{ motivo }`.
- Administrador e gerente: desbloqueiam na hora, com motivo e evento de auditoria (`CLI-05`). 200; o cliente volta a `ativo` (ou `incompleto`, se tiver pendências).
- Vendedor: cria o pedido `APR-05`. 202 `{ "pedido_aprovacao": { "id", "tipo": "APR-05", "status": "pendente" } }`. Aprovado por gerente ou administrador (nunca quem pediu, `APR-09`), o cliente volta como acima.
- Padrão A recomendado pelo produto (T-037) enquanto o dono do produto não decide. Se a decisão mudar, muda só quem pode chamar direto.
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
| assinante de `financeiro.parcela_paga` | desbloqueio automático quando não resta conta com mais de 15 dias de atraso. |
| `CAMPOS_AUDITORIA` | cifrados omitidos; nome (PF), nascimento, contatos, endereço e referência mascarados (ADR 0014). |
