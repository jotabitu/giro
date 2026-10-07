# API

- `openapi.yaml`: gerado pelo backend (`make api-schema`, drf-spectacular). Não edite à mão; o CI falha se estiver desatualizado.
- `<modulo>.md`: contrato escrito pelo arquiteto **antes** da implementação. É o que permite ao frontend começar em paralelo.

## Modelo de contrato

```
# Locações

## POST /api/locacoes/
Perfis: administrador, gerente, vendedor (só na própria filial)
Corpo: { cliente_id, veiculo_id, plano, inicio, fim_previsto, extras[] }
201: { id, codigo: "LOC-2856", status: "aguardando_assinatura", valor_periodo_centavos, caucao_centavos, ... }
409: { codigo: "LOC-03", mensagem: "Veículo indisponível no período" }
Regras: LOC-01, LOC-02, LOC-03
```

## Convenções

- Prefixo `/api/`, recursos no plural em português (`/api/locacoes/`, `/api/veiculos/`).
- Valores em centavos com sufixo `_centavos`; datas ISO 8601; status como texto do enum das regras.
- Erros de negócio: HTTP 409 ou 422 com `{ "codigo": "<REGRA>", "mensagem": "<texto para o usuário>" }`.
- Paginação por cursor nas listas; filtros por query string.
- Plataforma em `admin.<dominio>/api/plataforma/`; empresa em `<subdominio>.<dominio>/api/`.
