# T-411 · Frontend do copiar link · frontend → backend, seguranca, qa, orquestrador

Na branch do PR #482 (contrato `docs/api/copiar-link.md`). Regras: LOC-15, DEV-02, AUT-03, PLT-13, S-15, AUD-09.

**O que foi feito**

1. **Cliente tipado** regerado (`npm run api:gerar`). Falsos acertados: `acoes.copiar_cobranca` (conta), `acoes.copiar_link_contrato` (locação), `acoes` na devolução, mais `copiarLinkDoContrato` e `copiarLinkDoRecibo` nas APIs e nos falsos (cada chamada devolve um link novo).
2. **Contrato para assinar** (Detalhe da locação): botão "Copiar link para assinar" por `acoes.copiar_link_contrato`. O link aparece num campo só de leitura, com a validade e o `aviso` da API, e o texto "Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link."
3. **Recibo da devolução**: "Copiar link do recibo" por `acoes.copiar_link_recibo`, mesmo painel.
4. **Cobrança da parcela**: "Copiar Pix" e "Copiar boleto" só com `acoes.copiar_cobranca` (o suporte não vê).
5. **Fatura da assinatura** (pop-up Pagar): "Copiar Pix", "Copiar boleto" e "Copiar link de pagamento" (boleto ou página do cartão). O suporte não recebe os campos, então nada aparece.
6. **Componente comum** `components/comum/LinkParaCopiar.tsx`: a cópia começa no clique por `copiarQuandoChegar` (Safari). O link fica só no estado da mutação: some ao fechar, sem cache, URL, storage nem console. Se a cópia falhar, o campo vem selecionado.

**Testes:** `components/comum/CopiarLink.test.tsx`. Rodei também os testes de Assinatura, Financeiro, Detalhe da locação, Devolução e dos falsos: 128 passam. Lint e typecheck limpos.

**Limites**
- Os testes são de marcação estática: não clicam. O comportamento de clique (cópia, link novo a cada clique) não tem teste de interação.
- Não conferi no navegador a 1440 e 390 px.
- A página pública `/recibo` (`POST /api/publico/recibos/consultar/`) NÃO foi feita aqui: o link do recibo ainda não abre uma página no frontend. Peço tarefa própria ao Orquestrador, como a `/assinar`.
- "Copiar boleto" copia a linha digitável; o link do boleto fica em "Copiar link de pagamento" na fatura.
