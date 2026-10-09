# app `contratos`

**Schema:** empresa
**Escopo:** Modelos de contrato versionados, contratos gerados (locação e venda), assinatura eletrônica, PDF (ADR 0011).
**Regras:** LOC-08, LOC-15, FIN-03, IMP-04 (ver `docs/regras-de-negocio.md`)
**Segurança:** S-09 e S-15 (`docs/seguranca/2026-10-07-fundacao.md`)
**Telas:** Contratos-Modelos, Onboarding-Contrato (ver `docs/telas/README.md`)

Contrato da API: `docs/api/contratos.md` (escrito pelo arquiteto antes da implementação).

## O que tem (T-090)

- `ModeloContrato` versionado: editar o publicado cria o rascunho da versão seguinte (`LOC-15`).
- `Contrato`: origem genérica, `gerado` → `enviado` → `assinado` (ou `cancelado`). Um vigente por
  origem (restrição no banco); aditivos são vários.
- `marcadores.py`: a lista fechada de `{{grupo.campo}}` (S-09). Troca por expressão regular, com
  o valor escapado; nada de motor de template.
- `sanitizacao.py`: lista branca de tags com `nh3` (S-09), ao salvar o modelo.
- `pdf.py`: WeasyPrint com o `url_fetcher` que só entrega o logo da empresa (S-09).
- `prontos.py`: os 6 modelos prontos e o texto padrão do aditivo (`LOC-08`).
- `origens.py`: o app de cima registra como montar os valores (a prévia com dados reais).
- `tasks.py`: PDF e envio do link (tempo limite de 60 s), PDF assinado com a página de registro e
  o aviso do aditivo sem assinatura em 7 dias (Beat, 08:00).

## Interface para os outros apps

| Item | Uso |
| --- | --- |
| `selectors.modelo_publicado(finalidade)` | `IMP-04` |
| `services.gerar(DadosDoContrato)` / `gerar_aditivo(...)` / `reenviar(contrato)` / `cancelar(contrato, motivo)` | `locacoes` (`locacoes/contrato.py`) |
| `selectors.contrato_vigente`, `resumo`, `url_do_pdf` | detalhe da locação |
| `selectors.permite_juros(origem_tipo, origem_id)` | `FIN-03`, para o financeiro (T-017) |
| evento `contratos.contrato_assinado` | `locacoes` (só `tipo = contrato` ativa) |
