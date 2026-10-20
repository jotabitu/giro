# API

- `openapi.yaml`: gerado pelo backend (`make api-schema`, drf-spectacular). Não edite à mão; o CI falha se estiver desatualizado.
- `<modulo>.md`: contrato escrito pelo arquiteto **antes** da implementação. É o que permite ao frontend começar em paralelo.

## Modelo de contrato

```
# Locações

## POST /api/locacoes/
Perfis: administrador, gerente, vendedor (só na própria filial)
Corpo: { cliente_id, veiculo_id, plano, inicio, fim_previsto, extras[] }
201: { id, codigo: "LOC-2856", status: "aguardando_retirada", valor_periodo_centavos, caucao_centavos, ... }
409: { codigo: "LOC-03", mensagem: "Veículo indisponível no período" }
Regras: LOC-01, LOC-02, LOC-03
```

## Convenções

Valem para todos os contratos; cada contrato só descreve o que foge daqui.

**Endereços**

- Prefixo `/api/`, recursos no plural em português (`/api/locacoes/`, `/api/veiculos/`), sempre com barra no fim.
- Plataforma em `admin.<dominio>/api/plataforma/` (schema `public`); empresa em `<subdominio>.<dominio>/api/` (schema da empresa). O mesmo caminho em outro host responde 404.
- Ações que mudam status são `POST /api/<recurso>/{id}/<acao>/` (`/api/filiais/7/desativar/`), nunca `PATCH` no campo `status`.
- Simulação de valor antes de salvar (ADR 0005): `POST /api/<recurso>/simular/`, sem gravar nada.

**Autenticação**

- `Authorization: Bearer <access>`. Token preso ao schema em que foi emitido (ADR 0008): token de outro host responde 401.
- 401 `{ "codigo": "nao_autenticado" }` sem token ou token vencido; o frontend tenta `renovar` uma vez e, se falhar, vai para o login.

**Formatos**

- Dinheiro: inteiro em centavos, sufixo `_centavos`. Percentual: texto decimal com 2 casas, sufixo `_pct` (`"8.00"`), para não perder precisão no JSON.
- Momento: ISO 8601 em UTC com `Z`, sem fração de segundo (`"2026-10-07T12:12:00Z"`); o frontend exibe em `America/Sao_Paulo` e compara por `Date`, nunca por texto. Na entrada, sempre com fuso (`Z` ou `-03:00`). Quem formata é só o renderizador JSON de `comum` (ADR 0020): serializer e view não escolhem fuso nem formato. Data sem hora (vencimento, competência): `"2026-10-21"`.
- Status e enums: texto do enum das regras e do `docs/decisoes/modelo-de-dados.md`.
- Documentos (CPF, CNPJ, CEP, placa) entram com ou sem máscara e saem só com dígitos (ou letras e dígitos, na placa); a máscara é do frontend. Em listas, CPF sai mascarado (`AUD-04`).
- Placa dentro de texto pronto (T-340): quando a API monta uma frase ou célula com a placa (`resumo`, `detalhe`, `titulo`, `rotulo`, `mensagem`, texto da auditoria, PDF, CSV), a placa sai **com hífen** depois do 3º caractere, como nas telas: `PMZ3E17` vira `PMZ-3E17` ("Honda Pop 110i · PMZ-3E17"). Placa guardada fora de 7 caracteres sai como está. O campo `placa` sozinho continua sem hífen, e a tela formata. Um formatador só, em `comum` (hoje existe `financeiro.exportacao.placa_com_hifen`, pela decisão do dono de 13 out 2026 no CSV das despesas, `FIN-16`). Não é regra nova: aplica a todos os textos a decisão do dono de mostrar a placa "como nas telas".
- Rótulos e textos prontos para o usuário vêm da API quando dependem de regra (ex.: `situacao` da empresa); o frontend não monta frase a partir de números.

**Listas**

- `GET` de lista devolve `{ "resultados": [...], "proximo": "<cursor>" | null, "anterior": "<cursor>" | null }`, 25 itens por página (`?tamanho=` até 100). Contadores para abas e filtros, quando a tela mostra, vêm em `"contagens": { ... }` no mesmo corpo.
- Filtros por query string com os nomes dos campos (`?status=ativa&plano=2`); busca livre em `?busca=`; ordenação em `?ordem=campo` ou `?ordem=-campo`, só nos campos que o contrato lista.

**Erros**

| HTTP | Quando | Corpo |
| --- | --- | --- |
| 400 | campo inválido ou faltando | `{ "codigo": "validacao", "mensagem": "Confira os campos destacados", "campos": { "cnpj": ["CNPJ inválido"] } }` |
| 401 | sem token, token vencido ou de outro schema | `{ "codigo": "nao_autenticado", "mensagem": ... }` |
| 403 | perfil, função, filial, empresa sem operação ou módulo fora do plano (`PLT-12`, `plataforma.md`) | `{ "codigo": "<REGRA>" ou "permissao", "mensagem": ... }` |
| 404 | não existe ou fora do escopo da pessoa (filial de outra pessoa responde 404, não 403) | `{ "codigo": "nao_encontrado", "mensagem": ... }` |
| 409 | transição de status recusada ou conflito de unicidade | `{ "codigo": "<REGRA>", "mensagem": ..., "detalhes": { ... } }` |
| 422 | regra de negócio recusou | `{ "codigo": "<REGRA>", "mensagem": ..., "detalhes": { ... } }` |
| 429 | muitas tentativas (login): bloqueio da conta por regra | `{ "codigo": "<REGRA>", "mensagem": ..., "detalhes": { "tentar_de_novo_em": "<momento>" } }` |
| 429 | limite de requisições (por IP ou por e-mail, `comum.limites`, IP de `comum.rede.ip_do_cliente`, ADR 0018) | `{ "codigo": "muitas_requisicoes", "mensagem": "Muitas tentativas seguidas. Espere um pouco e tente de novo.", "detalhes": { "tentar_de_novo_em_segundos": 42 } }` e cabeçalho `Retry-After` |

`codigo` é o código da regra (`PLT-03`) quando existe; senão, um identificador fixo em minúsculas listado no contrato do módulo. `mensagem` é o texto que o frontend mostra como está.

**Arquivos gerados (planilha e CSV)**

Toda célula de texto que começa com `=`, `+`, `-`, `@`, tabulação ou retorno de carro sai com um apóstrofo na frente (`'=HYPERLINK(...)`), para a planilha não executar fórmula vinda de dado digitado ou importado. Vale para exportações (`AUD-07`), relatórios e qualquer download em `.xlsx` ou `.csv`. Números e datas saem como tipo próprio, sem esse tratamento.

**Auditoria**

Todo endpoint que muda dado grava evento (ADR 0010). O contrato só cita a `acao` gravada quando ela não é óbvia.

## Ambiente

`GET /api/ambiente/` (empresa) e `GET /api/plataforma/ambiente/` (plataforma). ADR 0021.

Perfis: público, sem login. `Cache-Control: no-store`. Throttle padrão de anônimo.

200:

```json
{ "hoje": "2026-10-07", "data_simulada": true }
```

- `hoje`: o dia do relógio do domínio em `America/Sao_Paulo` (`comum.relogio.hoje()`). É o "hoje" de toda tela que precisa de um (agenda, "vence hoje", data padrão de formulário); o frontend não usa a data do navegador para isso.
- `data_simulada`: `true` só no desenvolvimento com `GIRO_DATA_REFERENCIA` ligada; em produção, sempre `false`. Com `true`, o frontend mostra a faixa "Data simulada: 07/10/2026. Ambiente de desenvolvimento." no topo de todas as telas.

Com a data ligada, toda resposta da API traz também o cabeçalho `X-Giro-Data-Simulada: 2026-10-07`.
