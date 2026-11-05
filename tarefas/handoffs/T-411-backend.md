# T-411 · Backend do copiar link · backend → frontend, seguranca, qa

**O que foi feito** (contrato `docs/api/copiar-link.md`, revisão `tarefas/handoffs/T-411-seguranca.md`, textos `tarefas/handoffs/T-411-T-420-produto-textos.md`):

1. **Copiar link para assinar** (`POST /api/locacoes/{id}/contrato/link/`): `contratos.services.gerar_link(contrato, por, ip)` gera o token na hora, com o contrato travado, e não envia nada. O status e o `enviado_em` não mudam. A resposta sai uma vez, com `Cache-Control: no-store`: `link` (`/assinar#<token>`), `expira_em` (7 dias), `aviso` e `contrato`. Os erros são 409 `sem_contrato`, `contrato_em_preparo`, `contrato_assinado`, `contrato_cancelado` (no serviço) e `titular_anonimizado`. Os perfis são os de `CRIAM`. O suporte recebe 403 `PLT-07` "No modo suporte você não gera link para o cliente." Os limites são `link_contrato_contrato` (5/h) e `link_contrato_usuario` (20/h), na ordem permissão, limite, serviço. Fica o evento `contrato.copiar_link` (`seguranca`), sem link e sem token. `acoes.copiar_link_contrato` entra no detalhe da locação.
2. **Prova da assinatura** (M-02, migração `contratos.0003_copiar_link`): o contrato ganha `token_assinatura_canal` (`whatsapp_email` ou `copiado`), `token_assinatura_gerado_por` e `token_assinatura_gerado_ip`. O IP fica fora da auditoria. A assinatura grava o evento `contratos.contrato_assinado` com o canal e, quando o link foi copiado, com `mesmo_ip_de_quem_copiou`. A página de registro do PDF ganha a linha "Como o link chegou", por exemplo "Link entregue por cópia, gerado por Bruna em 07/10/2026, 10:00".
3. **Fila sem matar o link copiado** (B-02): `contratos_preparar_e_enviar` e `contratos_reenviar` recebem `enfileirado_em`. Elas terminam sem enviar quando o token vivo foi gerado depois disso.
4. **Copiar link do recibo** (`POST /api/devolucoes/{id}/recibo/link/`, migração `vistorias.0005_copiar_link`): `Devolucao.token_recibo_hash` e `token_recibo_expira_em`, com 7 dias de validade. `vistorias.services.gerar_link_recibo` grava o PDF se ainda faltar. As regras de status, perfis (`FECHAM`), suporte e limites (`link_recibo_*`) são as mesmas do contrato. Fica o evento `devolucao.copiar_link_recibo`. A devolução ganha o bloco `acoes.copiar_link_recibo`.
5. **Página pública do recibo** (`POST /api/publico/recibos/consultar/`, B-03): sem login, no schema do host. Responde 404 para token desconhecido ou anulado e 410 `link_expirado` depois de vencido. Usa os escopos próprios `recibo_publico_ip` (10/min) e `recibo_publico_token` (20/min), com `no-store` e `X-Robots-Tag: noindex`. Fica o evento `devolucao.recibo_aberto` (ator sistema, IP /24, aparelho), no máximo um por token por dia. Vale com a empresa suspensa, por isso entrou nas exceções de `test_permissoes_das_rotas`.
6. **Anonimização** (`clientes/titular.py`): anula o token dos contratos não assinados e o do recibo.
7. **Cobrança** (M-01): para o token de suporte, `boleto_url` vem `null` (`representacao_cobranca(..., suporte=)`), e `acoes.copiar_cobranca` também. `copiar_cobranca` só vale com a conta `aberta` e a cobrança `aguardando` de hoje ou de depois.
8. **Fatura** (M-01): para o suporte, `url_boleto` e `url_pagina` vêm `null` no detalhe (`ContextoDasFaturas.suporte`).
9. **Cartão trocado** (B-01): `_guardar_cartao` manda o e-mail do produto aos administradores ativos depois do commit, com o assunto "O cartão da assinatura mudou". O texto traz a empresa, a bandeira, o final, o titular (quando vier), a fatura, a data e o endereço da Assinatura. O primeiro cartão e o mesmo cartão de novo não avisam. O evento `assinatura.cartao_guardado` leva sempre a bandeira, o final e o titular. `CartaoGuardado` ganhou o campo `titular`, que o Asaas não devolve na cobrança paga, então hoje sai sem "no nome de".

**Uma mudança fora do contrato, para o arquiteto conferir:** o contrato permite copiar o link de um contrato `gerado` com o PDF pronto e diz que ele continua `gerado`. Só que a assinatura recusava `gerado` (404), e a máquina não tinha `gerado → assinado`. Sem isso, o link copiado não abria. Agora `_pelo_token` aceita `gerado` com PDF, e `Contrato.TRANSICOES` ganhou `gerado → assinado`. Peço que o `contratos.md` registre isso.

**Ficou de fora:**
- O histórico da locação continua só com eventos de objeto `locacao`. Os textos "Copiou o link para assinar o contrato", "Copiou o link do recibo" e "O cliente abriu o recibo pelo link" saem na tela Auditoria (`auditoria/textos.py`). O último texto é meu: o produto pode trocar.
- O aviso "Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." é texto do frontend. A API devolve só o `aviso` comum, "O link anterior deixa de valer.".

**Testes:** `backend/tests/aceitacao/test_t411_copiar_link.py`, com `test_s_15_copiar_link_contrato_invalida_o_anterior`, `_estados`, `_titular_anonimizado`, `_perfis_e_suporte`, `_limite_por_hora` e `_evento_sem_token`. Também `test_loc_15_assinatura_por_link_copiado_registra_canal`, `test_loc_15_assinatura_pelo_whatsapp_registra_canal` e `test_s_15_reenvio_em_fila_nao_mata_link_copiado`. Do recibo: `test_dev_02_copiar_link_recibo_abre_o_pdf`, `_invalida_o_anterior`, `_rascunho_e_perfis`, `_limite_por_hora` e `_evento_sem_token`, mais `test_dev_02_recibo_publico_vencido_e_desconhecido`, `_nao_cruza_empresas`, `_limites_proprios` e `test_dev_02_recibo_aberto_um_por_dia`. Do resto: `test_aut_03_copiar_cobranca_so_com_a_cobranca_do_dia`, `test_aud_09_suporte_nao_recebe_boleto_url`, `test_aud_09_suporte_nao_recebe_link_da_fatura` e `test_plt_13_cartao_novo_avisa_o_administrador`.

**OpenAPI:** `docs/api/openapi.yaml` regerado. O que muda para o frontend:
- rotas novas `contrato/link/`, `recibo/link/` e `publico/recibos/consultar/`;
- `acoes.copiar_link_contrato` na locação;
- `acoes.copiar_cobranca` na conta;
- `acoes` (obrigatório) na devolução, o que quebra os falsos e mocks que montam `Devolucao` sem ele.

**Próximo passo:**
- frontend: `npm run api:gerar`. Ponha `acoes` nos falsos da devolução. Mostre os botões pelas `acoes`. Copie com `copiarQuandoChegar`. A página `/recibo` funciona como a `/assinar`.
- seguranca: revisão do código das rotas, como na T-252.
- qa: conferir no ambiente com `make migrate`.
