# T-294 · Campos novos da fatura da assinatura no modelo de dados · arquiteto → backend, orquestrador

**O que foi feito:** o `docs/decisoes/modelo-de-dados.md` passou a ter o que as duas partes da T-185 mudaram no modelo (handoff `T-185-backend.md`, confrontado com `plataforma/models.py` e a migração `0010`).

**Na `FaturaAssinatura` (item 3):**
- `ciclo`, que já estava no model e faltava no documento.
- Os campos da migração `plataforma.0010`: `cobranca_tipo` (`pix`, `boleto`, `cartao_link`), `cobranca_pix_copia_e_cola`, `cobranca_linha_digitavel`, `cobranca_boleto_url`, `cobranca_url_pagina` e `recibo_url`.
- Duas notas novas:
  - a cobrança viva: uma por fatura, reaproveitada no mesmo meio e cancelada antes de pagar por outro meio;
  - a auditoria: a cobrança e o recibo ficam fora do evento.

**Na `Empresa` (item 2):** a chave `omitir_no_public`, que existe em `comum.classificacao` desde a parte 1. Os dados que o apagamento limpa vão como "alterado" no `public` e com o valor no schema da empresa. O endereço saiu do `omitir`.

**Na `FormaPagamentoAssinatura`:**
- as transições do `status` (`PLT-13`);
- o que a troca de forma limpa: autorização, token, bandeira, final e a cobrança viva de outra forma;
- o que a auditoria omite.

**Regras cobertas:** PLT-02, PLT-13, PLT-14, AUD-08 (sem regra nova).

**O que ficou de fora:** nada do modelo. As mensagens novas da parte 1 (`valor_mudou`, desfazer no dia da virada, `nao_encontrado`) são do contrato `assinatura.md`; a do `valor_mudou` já veio decidida pelo Produto na T-290.

**Próximo passo:** nenhum para o backend; o documento agora segue o código.
