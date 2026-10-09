# app `contratos`

**Schema:** empresa
**Escopo:** Modelos de contrato versionados, contratos gerados (locação e venda), assinatura eletrônica, PDF (ADR 0011).
**Regras:** LOC (contrato), VEN (recibo e contrato) (ver `docs/regras-de-negocio.md`)
**Telas:** Contratos-Modelos, Onboarding-Contrato (ver `docs/telas/README.md`)

Criado vazio na T-001 para constar na lista de apps; o conteúdo entra com a T-015.

Contrato da API: `docs/api/contratos.md` (escrito pelo arquiteto antes da implementação).

## Implementado (mínimo, com a T-015)

- `ModeloContrato` (item 16 do modelo de dados), com o único `(grupo, versao)` e um publicado por grupo.
- `selectors.modelo_publicado(finalidade)`, para a `IMP-04` da locação.

A API dos modelos (S-09), o contrato gerado, o PDF e a assinatura (S-15) são da T-090.
