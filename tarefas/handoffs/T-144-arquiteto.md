# T-144 · Revisão das diferenças de contrato da T-017 · arquiteto → orquestrador, backend, frontend, seguranca

Branch `t-144-contrato-t017`, criada a partir de `origin/t-017-financeiro` (PR #150). Abrir o PR depois do merge do #150.

**O que revisei:** a seção "Para o arquiteto" e as "Decisões técnicas" de `tarefas/handoffs/T-017-backend.md`, contra o código da branch (`apps/financeiro`, `apps/relatorios`, `integracoes/pagamentos`) e o `openapi.yaml`.

**Diferenças, todas aprovadas e escritas no contrato:**
- **Campos a mais na conta** (`financeiro.md`, representação): `dias_atraso` (o mesmo `valor_hoje.dias_atraso`, 0 sem atraso), `observacao` (só leitura, `null` vazio), `estorno_de` e `estornada_em`.
- **`no_caixa: true` em `cobranca/`:** é como a tela `Caixa` gera o Pix. Caixa `aberto` da filial do `X-Filial`; sem caixa, 422 `FIN-07`; com `todas`, 400 `validacao`. Se o caixa fechar antes do pagamento, a baixa acontece sem movimento (Pix não passa pela gaveta e caixa fechado não recebe movimento).
- **`cobrar/` e lote:** 202 `{ "enviadas": N }`. Conta fechada, cliente sem celular ou já cobrada hoje não conta e não é erro.
- **`historico` do detalhe:** `[{em, acao, por, motivo}]`. `acao` é o código da auditoria (`conta_receber.*`) ou `cobranca.pix|boleto`; o frontend traduz.
- **`GET /api/financeiro/despesas/{id}/`:** mesmos perfis e `X-Filial` da lista.
- **`caixa_hoje` em qualquer status** (`painel.md`): aprovado. O `status` existe para isso, e o caixa fechado à tarde continua mostrando o recebido do dia. `null` só com `todas` ou sem caixa hoje. `caixas_do_dia` e `sai_hoje` também passaram a "sim" na tabela do corte do MVP; `caixas_do_dia` vazio é `[]`, não `null`.
- **`chave_api_cifrada`** fica para a T-029.

**Decisões técnicas da T-017, aprovadas:** 1 (receber e gerar Pix acham a conta em qualquer filial, `FIL-06`), 3 (a baixa pelo webhook grava multa e juros do dia da geração), 4 (estorno de movimento repete tipo e forma; conta paga com caução → 422 `DEV-02`), 5 (conciliação com `modulo="conciliacao"` na navegação) e 6 (avisos para administradores e financeiros ativos). As de 1, 3, 4 e 6 estão no contrato.

**Webhook (S-14), conferido no código:**
- A conferência do token saiu do provedor para a view (decisão 2): o provedor só extrai evento e token, a view busca a `ContaPagamento` pelo SHA-256 do token (coluna única) e confere com `compare_digest`. Aprovado: o token é aleatório e longo, então hash sem sal basta e a busca pelo hash não vaza nada por tempo. A interface em `financeiro.md` foi ajustada.
- 401 `webhook_invalido` sem gravar nada; `WebhookRecebido` com `evento_id` único (repetido não faz nada); 200 na hora e baixa só na task; a task trava o webhook, consulta o parceiro, compara o valor com a cobrança e manda para pendência valor diferente, estorno no parceiro e conta que não está mais aberta. Limite de 120/min por IP, contando os recusados.
- Nada a ajustar no código. Fica para a T-029: a conta principal (`FaturaAssinatura`) e o IP real atrás do proxy no limite por IP (S-17).

**Ajuste de código pedido:** **T-145** (backend, no backlog): `status` de `caixa_hoje` e `caixas_do_dia` como `ChoiceField`. Hoje o OpenAPI sai `string`, e o cliente tipado não recebe o enum. É pequeno e não bloqueia a T-023.

**Regras:** FIN-01, FIN-03, FIN-04, FIN-07, FIN-08, FIL-06, DEV-02, AUT-03, AUT-05; S-14.

**Próximo passo:**
- **Orquestrador:** abrir o PR depois do #150; pôr a T-145 na fila do backend.
- **Frontend (T-023):** usar `financeiro.md` e `painel.md` desta branch; `caixa_hoje` pode vir `fechado` ou `aguardando_aprovacao`, então mostre o status; traduza os códigos do `historico`.
- **Segurança:** a conferência do webhook está descrita no passo 1 dos Webhooks de `financeiro.md`.
