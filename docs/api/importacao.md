# Importação por planilha

**Dono:** arquiteto · **Versão:** 10 nov 2026 (T-440: planilha de veículos sem filial e categoria, categoria por modelo, `IMP-08`; antes T-164 e T-044) · **App:** `importacao` (schema da empresa, ADR 0017) · **Regras:** IMP-02, IMP-03, IMP-05, IMP-08, PLT-03, VEI-01, VEI-11, FIL-04, CLI-01, CLI-03, AUD-04, AUD-09 · **ADRs:** 0012, 0014, 0017 · **Telas:** Onboarding-Importar (passo 11 da implantação)

Convenções gerais em `docs/api/README.md`. Base: `/api/importacoes/`.

## Quem pode

Administrador (é parte da Administração e do assistente de implantação). Os demais perfis: 403.
O suporte com permissão `ver_editar` pode importar ("nossa equipe faz a importação por você"). Para ele, as linhas de clientes seguem a representação resumida de `clientes.md` (`AUD-09`): só `nome`, `tipo`, documento mascarado e `celular`; sem endereço, nascimento, CNH e referência. Ele pode corrigir pelo `PATCH`, e a resposta volta resumida.

## Fluxo

```
enviar planilha ──► validando ──► validada (prontas + com erro) ──importar──► concluida
                                      ▲   │                                    │
                         corrigir linha┘   └── importar de novo as corrigidas ◄─┘
```

1. O administrador envia o arquivo; a API responde na hora e uma task valida linha por linha (`IMP-02`), sem gravar nada nos cadastros.
2. A tela mostra "83 prontos · 3 com erro", com o erro de cada linha. As linhas com erro podem ser corrigidas ali mesmo ("Corrigir aqui").
3. Em veículos, a pessoa escolhe a categoria de cada modelo ("Categoria de cada modelo", `IMP-08`). Com uma categoria só, nada é perguntado.
4. "Importar os 83" grava as prontas, até o limite do plano (`IMP-03`).
5. Corrigidas as 3, "Importar" de novo grava só as que faltam, cada uma na categoria do modelo dela. Caso do seed: 83 + 3 = **86 veículos**.

Uma importação em andamento por tipo de cada vez: enviar outra planilha do mesmo tipo com uma importação `validando` ou `importando` → 409 `{ "codigo": "importacao_em_andamento" }`.

## Planilha

- `.xlsx` ou `.csv` (UTF-8, separador `;` ou `,`), até 5 MB e 5.000 linhas, primeira linha com os nomes das colunas.
- Colunas reconhecidas pelo nome, sem diferenciar maiúsculas e acentos; colunas não reconhecidas são descartadas antes de gravar a linha.
- Célula com mais de 1.000 caracteres numa coluna reconhecida: a linha fica com erro (`validacao`, "Célula com mais de 1.000 caracteres" no campo da coluna), no `.xlsx` e no `.csv`. A célula é guardada com os primeiros 1.000 caracteres, para a correção em "Corrigir aqui". Em coluna não reconhecida não há erro: a coluna é descartada.
- No `.csv`, célula com mais de 1.000 caracteres **e** quebra de linha dentro é aspas sem fechar (o resto do arquivo viraria uma célula só, e as linhas seguintes sumiriam sem aviso): o arquivo é recusado com "A linha N tem aspas sem fechar. Confira o arquivo e envie de novo.", com N a linha do arquivo onde a célula começa. Quebra de linha em célula de até 1.000 caracteres é aceita.

### GET /api/importacoes/modelo/?tipo=veiculos|clientes
200: arquivo `.xlsx` com as colunas abaixo, uma linha de exemplo e uma aba "Instruções".

**Veículos** (obrigatórias em negrito): **placa**, **chassi**, renavam, **marca**, **modelo**, **ano_fabricacao**, **ano_modelo**, **cor**, **km**, capacidade_tanque_litros, valor_compra, data_compra. **Sem filial e sem categoria** (`IMP-08`, T-440): a filial é a do envio e a categoria é escolhida por modelo, na tela. A planilha antiga que ainda traz as colunas `categoria` e `filial` é aceita, e as duas são descartadas como qualquer coluna fora do modelo (nenhuma linha fica com erro por elas).
**Clientes**: **tipo** (`pf`/`pj`; vazio = deduzido pelo documento), **nome**, **documento** (CPF ou CNPJ), **celular**, email, nascimento, profissao, cnh_numero, cnh_categoria, cnh_validade, cnh_primeira_habilitacao, cep, logradouro, numero, complemento, bairro, cidade, uf, referencia_nome, referencia_parentesco, referencia_telefone, responsavel_nome, responsavel_cpf.

Valores em reais aceitam `13900`, `13.900,00` ou `13900.00`; datas, `dd/mm/aaaa` ou `aaaa-mm-dd`.

## Representação

```json
{
  "id": 12, "tipo": "veiculos", "arquivo": "frota-moto-rapida.xlsx",
  "status": "validada",
  "filial_padrao": { "id": 1, "nome": "Filial Centro" },
  "contagens": { "linhas": 86, "prontas": 83, "com_erro": 3, "importadas": 0, "acima_do_limite": 0 },
  "plano": { "usado": 0, "limite": 150, "cabem": 150 },
  "categorias": {
    "pergunta": true,
    "opcoes": [ { "id": 4, "nome": "Carro compacto", "tipo_veiculo": "carro" },
                { "id": 2, "nome": "Street 150–160", "tipo_veiculo": "moto" }, "..." ],
    "modelos": [ { "marca": "Honda", "modelo": "Pop 110i", "veiculos": 20, "categoria_id": null },
                 { "marca": "Honda", "modelo": "CG 160 Fan", "veiculos": 15, "categoria_id": 2 }, "..." ],
    "falta_escolher": true
  },
  "aviso": null,
  "enviada_por": "Mariana Costa", "enviada_em": "...", "concluida_em": null,
  "apagar_em": "2026-11-06"
}
```

`status`: `validando`, `validada`, `importando`, `concluida` (importou tudo o que estava pronto; pode haver linhas com erro esperando correção), `falhou` (arquivo ilegível), `cancelada`.

**`categorias`** (`IMP-08`; `null` em clientes):
- `opcoes`: as categorias ativas da empresa ou da filial da importação (`FIL-04`), moto e carro (`VEI-11`), por tipo e nome. Categoria só de outra filial não aparece.
- `pergunta`: `true` com mais de uma opção. Com uma só, todas as linhas ficam nela, sem pergunta, e a tela não mostra o bloco.
- `modelos`: "Categoria de cada modelo". Cada marca e modelo das linhas a gravar (`pronta` ou `acima_do_limite`) aparece uma vez, na ordem da planilha, com quantos veículos e a categoria escolhida (`null` se ainda não tem). Marca e modelo se comparam sem diferenciar maiúsculas, acentos e espaços. A linha que é exceção (abaixo) não entra na conta do modelo. Fora de `validada` e `concluida`, a lista vem vazia.
- `falta_escolher`: alguma linha a gravar ainda sem categoria. Enquanto `true`, "Importar" fica travado e a tela diz "Escolha a categoria de cada modelo.".

### Linha
```json
{ "numero": 14, "status": "com_erro",
  "dados": { "placa": "QXA4B2", "chassi": "9C2KC2210PR004417", "modelo": "CG 160 Fan", "...": "..." },
  "erros": [ { "campo": "placa", "codigo": "VEI-01", "mensagem": "Placa QXA4B2 está incompleta" } ],
  "objeto": null }
```
`status` da linha: `pronta`, `com_erro`, `importada` (com `objeto: { "tipo": "veiculo", "id": 501 }`), `acima_do_limite`, `ignorada`.

Em veículos, a linha traz também `categoria_id` (a categoria da linha, `null` sem escolha) e `categoria_propria` (`true` quando a linha é exceção do modelo, escolhida em "Corrigir aqui"). Em clientes, as duas chaves vêm ausentes.

---

### GET /api/importacoes/preparo/?filial_id=
Antes do envio de veículos (`IMP-08`). 200:
```json
{ "filiais": [ { "id": 1, "nome": "Filial Centro" } ], "pede_filial": false,
  "filial": { "id": 1, "nome": "Filial Centro" }, "pode_importar": true, "motivo": null }
```
- `filiais`: as ativas. `pede_filial`: mais de uma; a tela mostra "Filial dos veículos", sem nenhuma marcada. Com uma só, `filial` é ela, e a tela diz "Os veículos entram na Filial Centro.". Com `?filial_id=` de uma ativa, `filial` é a escolhida.
- `pode_importar`: `false` sem categoria ativa (da filial, ou de nenhuma, enquanto a filial não foi escolhida), com `motivo` "Cadastre os preços antes de importar veículos."; a tela mostra o atalho para o passo 8 (`/implantacao/precos`) e não a área de envio. A importação de clientes não depende disso.
- Mesmos perfis da leitura da importação (o suporte lê nos dois modos).

## POST /api/importacoes/
`multipart/form-data`: `tipo` (`veiculos` | `clientes`), `arquivo`, `filial_id?` (a filial de todos os veículos da planilha, `IMP-08`; obrigatório com mais de uma filial ativa, e com uma só é ela).
- Veículos com mais de uma filial e sem `filial_id`: 400 `{ "campos": { "filial_id": ["Escolha a filial dos veículos."] } }`. Sem filial ativa: "Cadastre a filial antes de importar veículos.".
- Veículos sem categoria ativa para a filial: 422 `{ "codigo": "sem_categoria", "mensagem": "Cadastre os preços antes de importar veículos." }`. Nada é gravado.
202: a importação em `validando`. A task `importacao_validar(schema, id, ator)` lê o arquivo e valida cada linha.
- **Arquivo de clientes:** apagado do storage (todas as versões, se o bucket tiver versionamento) assim que a validação grava as linhas cifradas; daí em diante só as linhas existem. O de veículos fica até `apagar_em`.
400 `validacao`: extensão, tamanho, arquivo vazio, coluna obrigatória faltando no cabeçalho (`detalhes.colunas_faltando`), aspas sem fechar no `.csv`.

### Validação de cada linha (IMP-02)

Cada linha passa pelas mesmas validações do cadastro pela tela, sem gravar:

| Tipo | Validações |
| --- | --- |
| Veículos | placa no formato antigo ou Mercosul e **única** na empresa e na planilha (`VEI-01`); chassi com 17 caracteres e **único** na empresa, em qualquer estado, e na planilha (`VEI-01`); campos obrigatórios; ano e km numéricos. Filial e categoria não são conferidas na linha (`IMP-08`): a filial é a do envio, e a categoria é escolhida depois, por modelo |
| Clientes | documento com dígito verificador válido e **único** na empresa (pelo hash, ADR 0014) e na planilha (`CLI-01`); nome e celular; formatos de e-mail, CEP, UF, datas e categoria de CNH |

- Repetição dentro da planilha: a primeira ocorrência fica pronta e as seguintes ficam com erro ("Chassi repetido na linha 12").
- Mensagens prontas, uma por problema, com o código da regra quando existe (`VEI-01`, `CLI-01`) ou `validacao`.
- Em **clientes**, a mensagem nunca repete o valor da célula: "CPF inválido", "CPF já cadastrado (linha 12)", nunca "CPF 123.456.789-00 inválido". Os `erros` não são cifrados, então não podem carregar dado pessoal. Em veículos, a mensagem pode citar placa e chassi.
- A linha já existente na empresa (placa, chassi ou documento) é erro, não atualização: importar não altera cadastros existentes.

### GET /api/importacoes/
`{ "resultados": [ ...importações recentes... ] }` (últimos 30 dias).

### GET /api/importacoes/{id}/
200: representação.

### GET /api/importacoes/{id}/linhas/
Query: `?status=com_erro|pronta|importada|acima_do_limite`. Paginação por cursor. 200: `{ "resultados": [ ...linhas... ] }`.

### PATCH /api/importacoes/{id}/linhas/{numero}/
"Corrigir aqui". Corpo: `{ "dados": { "placa": "QXA4B21" }, "categoria_id"?: 3 }` (só os campos corrigidos; ao menos um dos dois). Só linhas `com_erro` ou `pronta`, em importação `validada` ou `concluida`.
200: a linha revalidada na hora (`pronta` ou ainda `com_erro`); as contagens da importação são atualizadas.
- **Categoria desta linha** (veículos, `IMP-08`): `categoria_id` põe a linha numa categoria só dela, exceção do modelo ("Escolha outra só se este veículo for uma exceção do modelo dele."); `"categoria_id": null` faz a linha voltar a seguir o modelo; sem a chave, nada muda. A categoria tem que estar em `categorias.opcoes` (400 `{ "campos": { "categoria_id": ["Escolha uma categoria da lista."] } }`).
- A linha que segue o modelo fica com a categoria que o modelo já tem, também quando a correção muda a marca ou o modelo para um que está na planilha (ex.: "cg  160 FAN" segue a CG 160 Fan). Um modelo que só aparece na correção ("Honda Elite 125") fica sem categoria e entra em `categorias.modelos`, esperando a escolha.

### POST /api/importacoes/{id}/categorias/
"Categoria de cada modelo" (veículos, `IMP-08`). Corpo: `{ "modelos": [ { "marca": "Honda", "modelo": "Pop 110i", "categoria_id": 1 } ] }` (um ou mais). Em importação `validada` ou `concluida`.
200: a importação, com `categorias` atualizado. A categoria vale para todas as linhas do modelo (`pronta`, `acima_do_limite` e `com_erro`) que seguem o modelo; as exceções ficam como estão, e as linhas corrigidas depois seguem a escolha.
- Categoria fora de `categorias.opcoes` (inativa ou de outra filial): 400 `{ "campos": { "categoria_id": ["Escolha uma categoria da lista."] } }`.
- Importação de clientes: 422 `so_veiculos`. Fora de `validada` e `concluida`: 409 `importacao_fechada`.
- A escolha fica guardada nas próprias linhas (`LinhaImportacao.dados`, chaves internas que não voltam em `dados`), e sai com elas em `apagar_em`; não há tabela nova.

### POST /api/importacoes/{id}/linhas/{numero}/ignorar/
Tira a linha da importação (`ignorada`). 200.

### POST /api/importacoes/{id}/importar/
Corpo vazio. Importação `validada` ou `concluida` com linhas `pronta`.
202: `importando`; a task `importacao_importar(schema, id, ator)` grava as linhas prontas, na ordem da planilha:
- **Ator:** as duas tasks recebem o ator de quem pediu (`tipo`, `id`, `acesso_suporte_id`; nenhum dado pessoal) e entram com `na_empresa(schema, ator=...)`. Cada cadastro e o `importacao.concluir` ficam na auditoria em nome do administrador ou do "Suporte Giro" com o destaque do `AUD-03`, nunca como "Sistema".
- Cada linha pelo serviço do app dono (`veiculos.services.criar`, `clientes.services.criar`), cada uma no próprio savepoint: uma linha que falhe na hora de gravar (ex.: alguém cadastrou a mesma placa pela tela no meio do caminho) volta a `com_erro` e as outras seguem.
- Veículos entram `disponivel`; clientes entram `incompleto`, porque a planilha não traz fotos de documento nem o consentimento (`CLI-03`).
- **Limite do plano (`IMP-03`, `PLT-03`):** antes de começar, a task trava o `UsoEmpresa` (`SELECT ... FOR UPDATE`) e calcula quantos cabem. Importa até o limite; as linhas prontas que sobram vão para `acima_do_limite`, e a importação termina com `aviso`: `{ "codigo": "IMP-03", "mensagem": "Importamos 30 veículos, o limite do plano Essencial. 12 ficaram de fora: mude de plano para importar o resto." }`. Mudando de plano, `importar` de novo pega as `acima_do_limite` como prontas.
- Clientes não têm limite de plano.
Ao terminar: `concluida`, `concluida_em`, evento de auditoria `importacao.concluir` (categoria `configuracoes`, com as contagens) além do evento de cada cadastro criado; marca o passo `importar` da implantação e a etapa `dados` do funil (`IMP-05`); aviso no sino do administrador.
422 `{ "codigo": "nada_para_importar" }` sem linha pronta.
422 `{ "codigo": "categoria_do_modelo", "mensagem": "Escolha a categoria de cada modelo." }` com alguma linha a gravar sem categoria (`categorias.falta_escolher`, `IMP-08`). Se a categoria escolhida for desativada antes de importar, a linha deixa de contar como escolhida e o `importar` volta a responder isso; se ela for desativada no meio da gravação, a linha volta `com_erro` ("A categoria escolhida está inativa. Escolha outra").

### POST /api/importacoes/{id}/cancelar/
Só `validada`. 200 `cancelada`; nada é gravado nos cadastros.

---

## Dados temporários e segurança

- O arquivo enviado fica no storage privado, sob o prefixo do schema, com **nome aleatório** (`AUD-05`); o nome original só aparece na tela, escapado. O de clientes é apagado logo depois da validação; o de veículos e todas as linhas, 30 dias depois do envio (`apagar_em`), pela tarefa diária de limpeza. Arquivo e linhas não são registro de negócio; o que importa fica nos cadastros criados e na auditoria.
- `LinhaImportacao.dados` de **clientes** é gravado cifrado (`CampoCifrado`, chave de dados pessoais, ADR 0014). Nas respostas, CPF e CNH saem mascarados para o suporte (`AUD-09`) e completos só para o administrador.
- O tipo é conferido pelo **conteúdo**, não pela extensão: `.xlsx` precisa ser um zip com `[Content_Types].xml`; `.csv` precisa decodificar como UTF-8 (com ou sem BOM, que é removido).
- `.xlsx`, antes de abrir: soma de `ZipInfo.file_size` de todas as entradas até 50 MB e no máximo 200 entradas; acima disso, recusado (400 `validacao`).
- `.xlsx`, ao abrir: `openpyxl.load_workbook(read_only=True, data_only=True, keep_links=False, keep_vba=False)`, com `defusedxml` instalado (protege de entidades XML e explosão quadrática). Dependências novas `openpyxl` e `defusedxml`, registrar no PR. As linhas são contadas no streaming (sem confiar em `max_row` nem `dimension`), parando em 5.001.
- `.csv`: `csv.field_size_limit` do tamanho máximo do arquivo (5 MB), para nenhuma célula interromper a leitura; a memória já está limitada pelos 5 MB. O limite de 1.000 caracteres é da validação da linha, não da leitura (T-164).
- As duas tasks têm limite de tempo (validar: 5 min; importar: 15 min).
- A planilha nunca é executada: só valores de célula, sem fórmulas, macros ou links externos.
- A auditoria não guarda o conteúdo das linhas (ADR 0014).

## Interface interna

| Item | Uso |
| --- | --- |
| `veiculos.services.validar_novo(dados)` e `clientes.services.validar_novo(dados)` | as mesmas validações do cadastro, sem gravar; devolvem a lista de erros. Os apps donos as expõem para a importação e para os próprios endpoints. |
| `veiculos.services.criar(...)`, `clientes.services.criar(...)` | gravação de cada linha. |
| `plataforma.services.exigir_limite` / `uso_do_plano` | `IMP-03`. |
| `plataforma.services.registrar_passo_implantacao("importar")` | `IMP-05`. |
| tarefas | `importacao_validar`, `importacao_importar` (recebem o ator, ver acima), `importacao_limpar` (diária). |

Testes da T-440 (`IMP-08`): `test_imp_08_*` em `tests/aceitacao/test_t440_importacao_sem_filial.py` (CA-440-01 a 12; o CA-440-13 segue em `test_imp_03_importa_ate_o_limite_e_avisa`).

Testes de segurança (revisão T-044): `test_importacao_xlsx_com_entidades_recusado`, `test_importacao_zip_acima_de_50mb_recusado`, `test_aud_09_suporte_ve_linha_de_cliente_resumida`, `test_aud_03_importacao_pelo_suporte_audita_ator_suporte`, `test_importacao_arquivo_de_clientes_apagado_apos_validar`.
