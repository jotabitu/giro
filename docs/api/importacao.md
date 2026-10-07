# Importação por planilha

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-044) · **App:** `importacao` (schema da empresa, ADR 0017) · **Regras:** IMP-02, IMP-03, IMP-05, PLT-03, VEI-01, CLI-01, CLI-03, AUD-04, AUD-09 · **ADRs:** 0012, 0014, 0017 · **Telas:** Onboarding-Importar (passo 11 da implantação)

Convenções gerais em `docs/api/README.md`. Base: `/api/importacoes/`.

## Quem pode

Administrador (é parte da Administração e do assistente de implantação). Os demais perfis: 403.
O suporte com permissão `ver_editar` pode importar ("nossa equipe faz a importação por você"); nas respostas, para ele, CPF e CNH das linhas de clientes vêm sempre mascarados (`AUD-09`).

## Fluxo

```
enviar planilha ──► validando ──► validada (prontas + com erro) ──importar──► concluida
                                      ▲   │                                    │
                         corrigir linha┘   └── importar de novo as corrigidas ◄─┘
```

1. O administrador envia o arquivo; a API responde na hora e uma task valida linha por linha (`IMP-02`), sem gravar nada nos cadastros.
2. A tela mostra "83 prontos · 3 com erro", com o erro de cada linha. As linhas com erro podem ser corrigidas ali mesmo ("Corrigir aqui").
3. "Importar os 83" grava as prontas, até o limite do plano (`IMP-03`).
4. Corrigidas as 3, "Importar" de novo grava só as que faltam. Caso do seed: 83 + 3 = **86 veículos**.

Uma importação em andamento por tipo de cada vez: enviar outra planilha do mesmo tipo com uma importação `validando` ou `importando` → 409 `{ "codigo": "importacao_em_andamento" }`.

## Planilha

- `.xlsx` ou `.csv` (UTF-8, separador `;` ou `,`), até 5 MB e 5.000 linhas, primeira linha com os nomes das colunas. O `.xlsx` é lido sem fórmulas (só valores) e recusado se descompactado passar de 50 MB.
- Colunas reconhecidas pelo nome, sem diferenciar maiúsculas e acentos; colunas a mais são ignoradas.

### GET /api/importacoes/modelo/?tipo=veiculos|clientes
200: arquivo `.xlsx` com as colunas abaixo, uma linha de exemplo e uma aba "Instruções".

**Veículos** (obrigatórias em negrito): **placa**, **chassi**, renavam, **marca**, **modelo**, **ano_fabricacao**, **ano_modelo**, cor, **km**, **categoria** (nome, como em `Precos`), filial (nome; vazio = filial escolhida no envio), capacidade_tanque_litros, valor_compra, data_compra.
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
  "aviso": null,
  "enviada_por": "Mariana Costa", "enviada_em": "...", "concluida_em": null,
  "apagar_em": "2026-11-06"
}
```

`status`: `validando`, `validada`, `importando`, `concluida` (importou tudo o que estava pronto; pode haver linhas com erro esperando correção), `falhou` (arquivo ilegível), `cancelada`.

### Linha
```json
{ "numero": 14, "status": "com_erro",
  "dados": { "placa": "QXA4B2", "chassi": "9C2KC2210PR004417", "modelo": "CG 160 Fan", "...": "..." },
  "erros": [ { "campo": "placa", "codigo": "VEI-01", "mensagem": "Placa QXA4B2 está incompleta" } ],
  "objeto": null }
```
`status` da linha: `pronta`, `com_erro`, `importada` (com `objeto: { "tipo": "veiculo", "id": 501 }`), `acima_do_limite`, `ignorada`.

---

## POST /api/importacoes/
`multipart/form-data`: `tipo` (`veiculos` | `clientes`), `arquivo`, `filial_id?` (padrão para a coluna filial vazia; obrigatório se a empresa tem mais de uma filial e a coluna não vem).
202: a importação em `validando`. A task `importacao_validar(schema, id)` lê o arquivo e valida cada linha.
400 `validacao`: extensão, tamanho, arquivo vazio, coluna obrigatória faltando no cabeçalho (`detalhes.colunas_faltando`).

### Validação de cada linha (IMP-02)

Cada linha passa pelas mesmas validações do cadastro pela tela, sem gravar:

| Tipo | Validações |
| --- | --- |
| Veículos | placa no formato antigo ou Mercosul e **única** na empresa e na planilha (`VEI-01`); chassi com 17 caracteres e **único** na empresa, em qualquer estado, e na planilha (`VEI-01`); categoria existente e ativa, da empresa ou da filial da linha; filial existente e ativa; campos obrigatórios; ano e km numéricos |
| Clientes | documento com dígito verificador válido e **único** na empresa (pelo hash, ADR 0014) e na planilha (`CLI-01`); nome e celular; formatos de e-mail, CEP, UF, datas e categoria de CNH |

- Repetição dentro da planilha: a primeira ocorrência fica pronta e as seguintes ficam com erro ("Chassi repetido na linha 12").
- Mensagens prontas, uma por problema, com o código da regra quando existe (`VEI-01`, `CLI-01`) ou `validacao`.
- A linha já existente na empresa (placa, chassi ou documento) é erro, não atualização: importar não altera cadastros existentes.

### GET /api/importacoes/
`{ "resultados": [ ...importações recentes... ] }` (últimos 30 dias).

### GET /api/importacoes/{id}/
200: representação.

### GET /api/importacoes/{id}/linhas/
Query: `?status=com_erro|pronta|importada|acima_do_limite`. Paginação por cursor. 200: `{ "resultados": [ ...linhas... ] }`.

### PATCH /api/importacoes/{id}/linhas/{numero}/
"Corrigir aqui". Corpo: `{ "dados": { "placa": "QXA4B21" } }` (só os campos corrigidos). Só linhas `com_erro` ou `pronta`, em importação `validada` ou `concluida`.
200: a linha revalidada na hora (`pronta` ou ainda `com_erro`); as contagens da importação são atualizadas.

### POST /api/importacoes/{id}/linhas/{numero}/ignorar/
Tira a linha da importação (`ignorada`). 200.

### POST /api/importacoes/{id}/importar/
Corpo vazio. Importação `validada` ou `concluida` com linhas `pronta`.
202: `importando`; a task `importacao_importar(schema, id)` grava as linhas prontas, na ordem da planilha:
- Cada linha pelo serviço do app dono (`veiculos.services.criar`, `clientes.services.criar`), cada uma no próprio savepoint: uma linha que falhe na hora de gravar (ex.: alguém cadastrou a mesma placa pela tela no meio do caminho) volta a `com_erro` e as outras seguem.
- Veículos entram `disponivel`; clientes entram `incompleto`, porque a planilha não traz fotos de documento nem o consentimento (`CLI-03`).
- **Limite do plano (`IMP-03`, `PLT-03`):** antes de começar, a task trava o `UsoEmpresa` (`SELECT ... FOR UPDATE`) e calcula quantos cabem. Importa até o limite; as linhas prontas que sobram vão para `acima_do_limite`, e a importação termina com `aviso`: `{ "codigo": "IMP-03", "mensagem": "Importamos 30 veículos, o limite do plano Essencial. 12 ficaram de fora: mude de plano para importar o resto." }`. Mudando de plano, `importar` de novo pega as `acima_do_limite` como prontas.
- Clientes não têm limite de plano.
Ao terminar: `concluida`, `concluida_em`, evento de auditoria `importacao.concluir` (categoria `configuracoes`, com as contagens) além do evento de cada cadastro criado; marca o passo `importar` da implantação e a etapa `dados` do funil (`IMP-05`); aviso no sino do administrador.
422 `{ "codigo": "nada_para_importar" }` sem linha pronta.

### POST /api/importacoes/{id}/cancelar/
Só `validada`. 200 `cancelada`; nada é gravado nos cadastros.

---

## Dados temporários e segurança

- O arquivo enviado fica no storage privado, sob o prefixo do schema (`AUD-05`), e é apagado com as linhas 30 dias depois do envio (`apagar_em`), pela tarefa diária de limpeza. Arquivo e linhas não são registro de negócio; o que importa fica nos cadastros criados e na auditoria.
- `LinhaImportacao.dados` de **clientes** é gravado cifrado (`CampoCifrado`, chave de dados pessoais, ADR 0014). Nas respostas, CPF e CNH saem mascarados para o suporte (`AUD-09`) e completos só para o administrador.
- A planilha nunca é executada: só valores de célula, sem fórmulas, macros ou links externos. Leitura com `openpyxl` em modo somente leitura (dependência nova, registrar no PR).
- A auditoria não guarda o conteúdo das linhas (ADR 0014).

## Interface interna

| Item | Uso |
| --- | --- |
| `veiculos.services.validar_novo(dados)` e `clientes.services.validar_novo(dados)` | as mesmas validações do cadastro, sem gravar; devolvem a lista de erros. Os apps donos as expõem para a importação e para os próprios endpoints. |
| `veiculos.services.criar(...)`, `clientes.services.criar(...)` | gravação de cada linha. |
| `plataforma.services.exigir_limite` / `uso_do_plano` | `IMP-03`. |
| `plataforma.services.registrar_passo_implantacao("importar")` | `IMP-05`. |
| tarefas | `importacao_validar`, `importacao_importar`, `importacao_limpar` (diária). |
