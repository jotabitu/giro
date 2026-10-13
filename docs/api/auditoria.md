# Auditoria e exportação

**Dono:** arquiteto · **Versão:** 13 out 2026 (T-177, despesas em CSV; antes 12 out 2026, T-151, e 07 out 2026, T-043) · **App:** `auditoria` (schema da empresa **e** `public`) · **Regras:** AUD-01 a AUD-03, AUD-07, FIN-16, AUD-09, PLT-07, PLT-08, PLT-09, AUT-11 · **ADRs:** 0010, 0014, 0016 · **Segurança:** S-06, S-10, S-15 · **Critérios:** `docs/qa/criterios/T-018.md`, `docs/qa/criterios/despesas.md` (CA-DES-06 a 09) · **Telas:** Admin-Auditoria, Plat-Auditoria, Admin-Exportar, Despesas (botão Exportar)

Convenções gerais em `docs/api/README.md`. Modelo: item 25 e `Exportacao` em `docs/decisoes/modelo-de-dados.md`. A gravação dos eventos é de `comum.auditoria` (ADR 0010); este contrato é a consulta e a exportação.

## Quem pode

| Ação | Empresa | Plataforma |
| --- | --- | --- |
| Consultar a auditoria | administrador (os demais perfis: 403) | dono (as demais funções: 403, CA-018-15) |
| Exportar | administrador; as despesas, também o financeiro (T-177) | dono |
| Escrever, editar ou apagar evento | ninguém: não existe endpoint (`POST`, `PUT`, `PATCH`, `DELETE` → 405) | ninguém |

O token de suporte não consulta a auditoria da empresa (403 `PLT-07`): o suporte não lê o rastro de quem audita o próprio suporte.

---

## Evento na API

```json
{
  "id": 50211,
  "ocorrido_em": "2026-10-07T13:30:00Z",
  "ator": { "tipo": "usuario", "id": 3, "nome": "Bruna Alves", "iniciais": "BA" },
  "suporte": null,
  "categoria": "financeiro",
  "acao": "movimento_caixa.sangria",
  "resumo": "Fez sangria de R$ 500,00",
  "detalhe": "Caixa da Filial Centro",
  "objeto": { "tipo": "movimentocaixa", "id": 412, "codigo": null, "filial": "Filial Centro" },
  "regra": null
}
```

- `ator.tipo`: `usuario`, `sistema` ("Sistema"), `suporte` ("Suporte Giro"). `ator.nome` é o nome copiado na hora do evento (CA-018-04).
- `suporte` (`AUD-03`): `{ "atendente": "Diego Santos", "motivo": "Chamado #1042", "permissao": "ver", "acesso_suporte_id": 31 }` em todo evento ligado a um acesso de suporte; a tela destaca a linha.
- `resumo` e `detalhe` são textos prontos montados pela API a partir da `acao` e dos dados do evento (cada app registra o formatador das suas ações em `comum.auditoria`). O frontend não monta frase.
- `categoria` (`AUD-02`): `financeiro`, `operacao`, `configuracoes`, `seguranca`, `suporte`.
- `objeto.tipo` é o nome do model do objeto do evento; a `acao` segue `<objeto>.<verbo>`.
- Movimentos de caixa (`movimento_caixa.entrada`, `.saida`, `.sangria`, `.estornar`, `.estorno_motivo`, `FIN-07`): o objeto é o `MovimentoCaixa` e o evento leva a filial do caixa (`objeto.filial` e o filtro `?filial=`), porque o movimento não tem filial própria (T-150). O `detalhe` da sangria é "Caixa da <filial>"; a descrição digitada vai no `depois` do detalhe do evento.

### GET /api/auditoria/eventos/{id}/
Detalhe, com `antes` e `depois` (só os campos mudados) já tratados pela classificação da ADR 0014 (item 3 e nota de 12 out 2026): campos omitidos vêm como `{ "alterado": true }`, mascarados vêm mascarados, `ip` e `aparelho` do ator.

CA-018-06, edição do cadastro da Juliana:
- CPF e CNH (`documento`, `cnh_numero`, `responsavel_cpf`) são `CampoCifrado` e vêm sempre omitidos, em `antes` e `depois`: `"documento": { "alterado": true }`. Nenhum dígito vai para o evento; a máscara `***.218.330-**` (`AUD-04`, `AUD-09`) é só das telas, listas e exportações de cadastro.
- Endereço: só a cidade e a UF vêm inteiras; CEP, logradouro, número, complemento e bairro vêm como `"***"`. Ex.: mudança de rua em Fortaleza dá `"antes": { "logradouro": "***", "numero": "***" }`, `"depois": { "logradouro": "***", "numero": "***" }`; mudança de cidade dá também `"cidade": "Fortaleza"` → `"Caucaia"`.

---

## Auditoria da empresa (Admin-Auditoria)

### GET /api/auditoria/eventos/
Perfil: administrador. Do mais novo para o mais velho.
Query (combinam entre si, CA-018-10):
- `?categoria=financeiro|operacao|configuracoes|seguranca|suporte`
- `?ator=<usuario_id>` ou `?ator_tipo=sistema|suporte`
- `?periodo=7d|30d|90d` (padrão `7d`) ou `?de=2026-10-01&ate=2026-10-07` (datas no fuso da empresa)
- `?objeto_tipo=locacao&objeto_id=2856` ou `?objeto_codigo=LOC-2856` (todos os eventos daquela locação)
- `?filial=<id>`
200: `{ "resultados": [ ...eventos... ], "proximo": "...", "anterior": null }`, paginação por cursor (25 por página).
Escopo (CA-018-12): só os eventos do schema da empresa, que já incluem a entrada e a saída do suporte nela (o serviço do suporte grava um evento em cada schema, ADR 0010). Nunca eventos de outra empresa nem da plataforma.

Caso do seed (CA-018-09), "Últimos 7 dias" em 07 out: 9 eventos, do suporte de Diego (13:52 e 13:40) até o convite de João por Mariana (06 out, 18:10); `?categoria=financeiro` traz 4; `?ator=<Bruna>` traz 4; `?categoria=suporte` traz 2.

### GET /api/auditoria/pessoas/
Para o filtro "Pessoa": usuários que aparecem como ator no período, mais "Sistema" e "Suporte Giro". `{ "resultados": [ { "tipo": "usuario", "id": 3, "nome": "Bruna Alves" } ] }`.

---

## Auditoria da plataforma (Plat-Auditoria)

### GET /api/plataforma/auditoria/eventos/
Função: dono. Eventos do schema `public` (equipe interna, acessos de suporte, cobrança da assinatura, planos, segurança do login da plataforma). Mesma representação, mais `"empresa": { "id", "nome_exibicao" }` (onde a ação aconteceu, ou `null`).
Query: as mesmas da empresa, mais `?empresa=<id>`. A aba "Acessos de suporte" é `?categoria=suporte`; "Cobrança" é `?categoria=financeiro`.
200 com `indicadores`: `{ "acessos_suporte_30d": 14, "acessos_suporte_com_edicao_30d": 3, "logins_bloqueados_hoje": 1, "mudancas_de_preco_7d": 1 }`.
- Não lê os schemas das empresas (CA-018-16): ações de dentro da empresa, como "Bruna fez sangria", não aparecem.
- Login bloqueado por códigos errados (`PLT-08`) aparece com ator "Desconhecido" quando o e-mail não existe, e com o IP mascarado (`177.84.x.x`).

---

## Exportação (AUD-07, S-15)

Vale para a empresa (`/api/exportacoes/`: administrador; o item `despesas`, também o financeiro). A exportação da plataforma (`/api/plataforma/exportacoes/`, dono, só auditoria em CSV) é da fase 2.

### O que existe no MVP (opção A do dono, 12 out 2026, T-151)
A **auditoria em CSV**, por período (`AUD-07`, nota de 12 out nas regras), e, desde a decisão do dono de 13 out 2026 (T-176, nota de 13 out na `AUD-07`), as **despesas em CSV**, por mês e filial, pedidas pelo botão "Exportar" da tela `Despesas` (seção "Despesas em CSV", abaixo). Os outros itens (`clientes`, `veiculos`, `locacoes_contratos`, `financeiro`, `vistorias_fotos`), o formato `planilha`, o backup completo `zip`, o backup automático (`AUT-11`) e a exportação da plataforma vão para a fase 2. O contrato abaixo descreve o corpo completo para a fase 2 não mudar o formato; no MVP:

- **A tela `Admin-Exportar` continua só com a auditoria, fixa e sem consultar disponibilidade:** mostra só o período e o botão de exportar a auditoria em CSV, e manda sempre `{ "itens": ["auditoria"], "formato": "csv", "periodo": { "de", "ate" } | null }`. Os outros itens, os outros formatos e o cartão do backup automático não aparecem, nem desabilitados. Não há endpoint de opções no MVP; se a fase 2 precisar que a tela descubra o que está liberado, ele entra com a fase 2.
- **As despesas saem só da tela `Despesas`,** com `{ "itens": ["despesas"], "formato": "csv", "mes", "filial_id" }` (abaixo). A `Admin-Exportar` não as oferece.
- **Qualquer outro item ou formato responde 422** `{ "codigo": "exportacao_indisponivel", "mensagem": "Por enquanto, só a auditoria e as despesas podem ser exportadas, em CSV." }`, e nada é criado. Vale para um item fora da lista disponível, mesmo junto de um disponível (`["auditoria", "clientes"]`), para `despesas` junto de outro item (`["auditoria", "despesas"]`: período e filial são diferentes), para `planilha` e para `zip`. A mensagem muda com a T-177; o código não.
- `zip` sem 2 etapas recentes responde antes o 403 `2fa_recente` (a checagem das 2 etapas vem primeiro); com elas, o 422 `exportacao_indisponivel`.
- `GET /api/exportacoes/backup-automatico/` (e o `PATCH`) não existem no MVP.

### POST /api/exportacoes/
No MVP só `["auditoria"]` e `["despesas"]`, cada um sozinho, com `csv` passam; o resto é 422 `exportacao_indisponivel` (acima). Perfis **por item**: `auditoria`, só o administrador; `despesas`, o administrador e o financeiro (decisão do dono, 13 out 2026, PR #187). Fora disso, 403 `{ "codigo": "permissao" }` (o financeiro pedindo a auditoria; o gerente e o vendedor pedindo as despesas, CA-DES-08); token de suporte: 403 (é escrita). Corpo da auditoria: `{ "itens": ["clientes", "veiculos", "locacoes_contratos", "financeiro", "vistorias_fotos", "auditoria"], "formato": "planilha" | "csv" | "zip", "periodo": { "de": "2026-01-01", "ate": "2026-10-07" } | null }`.
- *(fase 2)* `zip` é o backup completo (todos os itens, com fotos): exige token com 2 etapas confirmadas há no máximo 15 minutos (`amr` com `otp` e `auth_time` recente); senão 403 `{ "codigo": "2fa_recente", "mensagem": "Confirme o código do autenticador para gerar o backup completo" }`. Gera evento `seguranca`.
- Células de texto que começam com `=`, `+`, `-`, `@`, tabulação ou retorno de carro saem com apóstrofo na frente (injeção de fórmula, `docs/api/README.md`).
- Dados pessoais saem como a pessoa veria na tela: o administrador vê completos; a auditoria sai sempre com a classificação da ADR 0014 (CA-018-13).
202: `{ "id": 17, "status": "na_fila" }`. 422 `exportacao_indisponivel` para item ou formato fora do MVP. Uma task gera o arquivo no storage privado e avisa por e-mail com o link.

### Despesas em CSV (`FIN-16`, `AUD-07`, T-177)

Pedido pelo botão "Exportar" da tela `Despesas` (não pela `Admin-Exportar`), pelo administrador ou pelo financeiro. Mesmo fluxo da auditoria: `POST /api/exportacoes/`, `na_fila` → `pronta` na task, arquivo no storage privado, e-mail com o link, 7 dias, `GET /api/exportacoes/{id}/baixar/` com o evento `exportacao.baixar` a cada download, e a linha em "Exportações recentes".

Corpo: `{ "itens": ["despesas"], "formato": "csv", "mes": "2026-10", "filial_id": 1 | null }`.
- `mes` obrigatório, `AAAA-MM` (400 `{ "mes": ["Escolha o mês no formato 2026-10."] }`); `periodo` não vale com `despesas` (400 `{ "periodo": ["Para as despesas, use o mês."] }`). O serviço grava `periodo_inicio` e `periodo_fim` com o primeiro e o último dia do mês.
- `filial_id`: a filial escolhida na tela (a mesma do `X-Filial`); `null` = todas as filiais. Filial que não existe na empresa: 400 `{ "filial_id": ["Filial não encontrada."] }`. Desativada vale (tem despesas antigas, `FIL-06`). O administrador e o financeiro veem todas as filiais (`USR-07`), então não há outra checagem de escopo.
- Fica em `Exportacao.parametros` (JSON novo, padrão `{}`): `{ "mes": "2026-10", "filial_id": 1, "filial_nome": "Filial Centro" }`, com o nome copiado no pedido (como `solicitada_por_nome`), e entra no evento `exportacao.pedir`.
- A busca e a aba da tela não vão no pedido: o arquivo é sempre o mês e a filial inteiros (CA-DES-07).

Arquivo `despesas.csv`, como o da auditoria: UTF-8 com BOM, separador `;`, uma linha de cabeçalho, proteção contra fórmula em toda célula de texto (`celula`).
- **Linhas:** uma por despesa da filial (ou de todas) com `data` no mês, **em qualquer status**, as `recusada` também (CA-DES-09). Diferente do gasto do mês, que não soma as recusadas. Ordem: `data`, depois `id`.
- **Colunas**, nesta ordem: `data`, `descricao`, `categoria`, `veiculo`, `filial`, `valor`, `vencimento`, `situacao`, `pago_em`, `forma`, `lancada_por`.

| Coluna | Valor | Ex. (pneus) |
| --- | --- | --- |
| `data`, `vencimento` | `DD/MM/AAAA` | `07/10/2026` |
| `descricao` | como lançada | `Pneus (2 unidades)` |
| `categoria` | rótulo | `Manutenção` |
| `veiculo` | placa **com hífen** depois do 3º caractere, como nas telas (decisão do dono, 13 out 2026, PR #187): `PMZ3E17` → `PMZ-3E17`, `ROE2A88` → `ROE-2A88`; placa guardada fora de 7 caracteres sai como está; vazio sem veículo | `PMZ-3E17` |
| `filial` | nome da filial da despesa | `Filial Centro` |
| `valor` | reais com vírgula, sem separador de milhar nem "R$" (a planilha lê como número) | `1200,00` |
| `situacao` | rótulo do status: "Aguardando aprovação", "A pagar", "Paga", "Recusada" | `Aguardando aprovação` |
| `pago_em` | `DD/MM/AAAA` em `America/Sao_Paulo`; vazio se não paga | |
| `forma` | rótulo da forma ("Dinheiro", "Pix", "Boleto", "Cartão", "Transferência"); vazio se não paga | |
| `lancada_por` | nome de quem lançou | `João Silva` |

- **Caso do seed (CA-DES-06):** outubro na Filial Centro, 6 linhas, a soma de `valor` dá 7.066,70; `conteudo` "Despesas · Filial Centro · 01/10/2026 a 31/10/2026". Com os pneus recusados, continuam 6 linhas, e a dos pneus traz "Recusada".
- **Quem monta as linhas:** `financeiro`, não `auditoria`. `auditoria` (nível 2 da ADR 0011) não importa `financeiro` (nível 8) nem `filiais`. Por isso `auditoria/exportacao.py` ganha um registro de itens, `registrar_item(item, *, rotulo, colunas, validar, linhas, conteudo)`, e `financeiro` registra o item `despesas` no `AppConfig.ready()` (`financeiro/exportacao.py`): `validar(dados) -> parametros` confere `mes` e `filial_id` e copia o nome da filial; `linhas(exportacao) -> list[list]` lê as despesas; `conteudo(exportacao) -> str` monta o texto de "Exportações recentes". A auditoria continua com o código dela; `solicitar`, `gerar` e `conteudo_rotulo` passam a consultar o registro para os outros itens. É o mesmo desenho da ADR 0015 (o de baixo registra, o de cima chama), sem ADR nova.
- `ItemExportacao` ganha `despesas` ("Despesas"), separado de `financeiro`, que continua sendo o item da fase 2 (todo o financeiro). `DISPONIVEIS` ganha `("despesas", "csv")`.

### GET /api/exportacoes/
"Exportações recentes": `{ "resultados": [ { "id", "solicitada_em", "solicitada_por": "Mariana Costa" | "Automático", "conteudo": "Auditoria · 01/10/2026 a 07/10/2026" | "Despesas · Filial Centro · 01/10/2026 a 31/10/2026", "formato", "tamanho_bytes", "status": "na_fila" | "pronta" | "expirada" | "falhou", "expira_em" } ] }`. As despesas aparecem aqui como as da auditoria, com a filial no `conteudo` ("Todas as filiais" quando `filial_id` é `null`). "Automático" (backup mensal) e "Backup completo" no `conteudo` só aparecem na fase 2. Perfis: o administrador vê todas; o financeiro vê só as de `despesas`, de qualquer pessoa (na tela `Despesas`); os outros perfis, 403.

### GET /api/exportacoes/{id}/baixar/
O "link de 7 dias" do e-mail é esta rota do sistema, não uma URL do storage (S-15):
- Exige login de quem pode exportar o item (administrador; nas despesas, também o financeiro), e 2 etapas recentes para `zip`, dentro dos 7 dias da `expira_em`. Outro perfil: 403 `permissao`.
- Responde **302** para uma URL assinada do storage válida por 15 minutos (`AUD-05`).
- Cada download grava `exportacao.baixar` (categoria `seguranca`).
- Depois de 7 dias: 410 `{ "codigo": "exportacao_expirada" }`; o arquivo é apagado do storage.

### Backup automático (AUT-11) · fase 2
`GET /api/exportacoes/backup-automatico/` → `{ "ativo": true, "frequencia": "mensal", "dia": 1, "hora": "09:00", "inclui_fotos": true, "envia_para": ["mariana@motorapida.com.br"] }`.
`PATCH` · administrador · `{ ativo?, inclui_fotos? }`. Os destinatários são sempre os administradores da empresa (não se digita e-mail). A tarefa `aut_11_backup_mensal` gera uma `Exportacao` `zip` com `solicitada_por = null` ("Automático").

---

## Garantias (testes da T-001 e da T-018)

- Imutável: `save()` de existente, `delete()`, `UPDATE`, `DELETE` e `TRUNCATE` falham (ADR 0010 e ADR 0016), nos schemas `public` e da empresa.
- Expurgo de 5 anos (`AUD-02`): só pela função de expurgo, só eventos com `ocorrido_em` anterior a 5 anos (em 07 out 2026, o de 06 out 2021 sai e o de 08 out 2021 fica).
- Uma transição, um evento, na mesma transação (CA-018-07).
- Nenhum CPF, CNH, senha, código de 2 etapas ou token completo em evento (ADR 0014; CA-018-06 busca os 11 dígitos do CPF na tabela e não acha).
