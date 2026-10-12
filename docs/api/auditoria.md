# Auditoria e exportação

**Dono:** arquiteto · **Versão:** 12 out 2026 (T-151; antes 07 out 2026, T-043) · **App:** `auditoria` (schema da empresa **e** `public`) · **Regras:** AUD-01 a AUD-03, AUD-07, AUD-09, PLT-07, PLT-08, PLT-09, AUT-11 · **ADRs:** 0010, 0014, 0016 · **Segurança:** S-06, S-10, S-15 · **Critérios:** `docs/qa/criterios/T-018.md` · **Telas:** Admin-Auditoria, Plat-Auditoria, Admin-Exportar

Convenções gerais em `docs/api/README.md`. Modelo: item 25 e `Exportacao` em `docs/decisoes/modelo-de-dados.md`. A gravação dos eventos é de `comum.auditoria` (ADR 0010); este contrato é a consulta e a exportação.

## Quem pode

| Ação | Empresa | Plataforma |
| --- | --- | --- |
| Consultar a auditoria | administrador (os demais perfis: 403) | dono (as demais funções: 403, CA-018-15) |
| Exportar | administrador | dono |
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

Vale para a empresa (`/api/exportacoes/`, administrador) e para a plataforma (`/api/plataforma/exportacoes/`, dono, só auditoria em CSV).

### POST /api/exportacoes/
Corpo: `{ "itens": ["clientes", "veiculos", "locacoes_contratos", "financeiro", "vistorias_fotos", "auditoria"], "formato": "planilha" | "csv" | "zip", "periodo": { "de": "2026-01-01", "ate": "2026-10-07" } | null }`.
- `zip` é o backup completo (todos os itens, com fotos): exige token com 2 etapas confirmadas há no máximo 15 minutos (`amr` com `otp` e `auth_time` recente); senão 403 `{ "codigo": "2fa_recente", "mensagem": "Confirme o código do autenticador para gerar o backup completo" }`. Gera evento `seguranca`.
- Células de texto que começam com `=`, `+`, `-`, `@`, tabulação ou retorno de carro saem com apóstrofo na frente (injeção de fórmula, `docs/api/README.md`).
- Dados pessoais saem como a pessoa veria na tela: o administrador vê completos; a auditoria sai sempre com a classificação da ADR 0014 (CA-018-13).
202: `{ "id": 17, "status": "na_fila" }`. Uma task gera o arquivo no storage privado e avisa por e-mail com o link.

### GET /api/exportacoes/
"Exportações recentes": `{ "resultados": [ { "id", "solicitada_em", "solicitada_por": "Mariana Costa" | "Automático", "conteudo": "Financeiro · setembro", "formato", "tamanho_bytes", "status": "na_fila" | "pronta" | "expirada" | "falhou", "expira_em" } ] }`.

### GET /api/exportacoes/{id}/baixar/
O "link de 7 dias" do e-mail é esta rota do sistema, não uma URL do storage (S-15):
- Exige login de administrador (e 2 etapas recentes para `zip`), dentro dos 7 dias da `expira_em`.
- Responde **302** para uma URL assinada do storage válida por 15 minutos (`AUD-05`).
- Cada download grava `exportacao.baixar` (categoria `seguranca`).
- Depois de 7 dias: 410 `{ "codigo": "exportacao_expirada" }`; o arquivo é apagado do storage.

### Backup automático (AUT-11)
`GET /api/exportacoes/backup-automatico/` → `{ "ativo": true, "frequencia": "mensal", "dia": 1, "hora": "09:00", "inclui_fotos": true, "envia_para": ["mariana@motorapida.com.br"] }`.
`PATCH` · administrador · `{ ativo?, inclui_fotos? }`. Os destinatários são sempre os administradores da empresa (não se digita e-mail). A tarefa `aut_11_backup_mensal` gera uma `Exportacao` `zip` com `solicitada_por = null` ("Automático").

---

## Garantias (testes da T-001 e da T-018)

- Imutável: `save()` de existente, `delete()`, `UPDATE`, `DELETE` e `TRUNCATE` falham (ADR 0010 e ADR 0016), nos schemas `public` e da empresa.
- Expurgo de 5 anos (`AUD-02`): só pela função de expurgo, só eventos com `ocorrido_em` anterior a 5 anos (em 07 out 2026, o de 06 out 2021 sai e o de 08 out 2021 fica).
- Uma transição, um evento, na mesma transação (CA-018-07).
- Nenhum CPF, CNH, senha, código de 2 etapas ou token completo em evento (ADR 0014; CA-018-06 busca os 11 dígitos do CPF na tabela e não acha).
