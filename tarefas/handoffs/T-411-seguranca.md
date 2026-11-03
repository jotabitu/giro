# T-411 · Revisão de segurança do contrato do copiar link · seguranca → arquiteto, depois backend e frontend

**Data:** 03 nov 2026 · **Agente:** segurança · **Regras:** S-15, S-17, USR-01, PLT-07, AUD-01, AUD-05, AUD-06, AUD-09, LOC-15, DEV-02, AUT-03, PLT-13
**Base:** PR #460 (branch `t-411-copiar-link`): `docs/api/copiar-link.md`, `locacoes.md`, `contratos.md`, `vistorias.md`, `financeiro.md`, `assinatura.md`, `modelo-de-dados.md` e `tarefas/handoffs/T-411-arquiteto.md`. Conferido contra o código atual da `develop`: `financeiro/selectors.py` (`representacao_cobranca`), `financeiro/services.py` (`_gerar_cobranca`, `Pagador` com o CPF em claro), `plataforma/services.py` (`_guardar_cartao`), `plataforma/api/assinatura.py` (o suporte lê), `vistorias/recibo.py` (o que vai no PDF), `comum/limites.py` e a revisão do convite (`docs/seguranca/2026-10-16-t252-link-convite.md`).
**Método:** leitura do contrato e do código. Não rodei testes; é revisão de contrato.

## Resumo

O desenho está certo e segue o copiar link do convite, que já foi revisado (T-252):
- token só em hash, mostrado uma vez, com `no-store`;
- token no fragmento, que a página apaga;
- um link vivo por objeto, válido por 7 dias;
- 403 `PLT-07` para o suporte;
- limite conferido antes da transação;
- evento sem o token;
- tokens anulados na anonimização.

**Nenhum achado alto.** Pela regra da tarefa, o backend pode começar, desde que os dois achados médios entrem no contrato antes. São ajustes pequenos no texto, não mudam o desenho.

| # | Gravidade | Achado | Quem muda |
| --- | --- | --- | --- |
| M-01 | média | O suporte vê o `boleto_url` (PDF do parceiro com nome e CPF completos), e `acoes.copiar_cobranca` não exclui o suporte | arquiteto (contrato), backend |
| M-02 | média | Quem copia o link do contrato pode assinar no lugar do cliente, e a prova da assinatura não registra que o link foi copiado | arquiteto (contrato), backend |
| B-01 | baixa | O link de pagamento da fatura que vazar deixa um terceiro trocar o cartão guardado da empresa, sem aviso ao administrador | arquiteto, backend |
| B-02 | baixa | A tarefa de envio do contrato pode trocar o token de um link já copiado (o B-01 da T-252, agora no contrato) | backend |
| B-03 | baixa | A página `/recibo`: falta pedir `noindex`, `no-store` na página e o teste de isolamento entre empresas | arquiteto (contrato), backend, frontend |

## Os pontos que o arquiteto pediu para olhar

| Ponto | Parecer |
| --- | --- |
| Página pública `/recibo`, token só em hash na `Devolucao` | Certo. O PDF (`vistorias/recibo.py`) tem o nome completo, a placa, as fotos e os valores, mas não tem CPF nem CNH. Ter vários acessos durante 7 dias equivale ao PDF que já vai anexo no e-mail. O token de 32 bytes com hash SHA-256 e índice único está bom. O `pdf_url` de 15 minutos pedido a cada clique segue a `AUD-05`. A resposta 404/410 está certa: o 410 só diz "venceu" a quem já tem o token (como na T-252). O que falta está no B-03. |
| `boleto_url` para o suporte (`PLT-07`) | Fere a `AUD-09`: ver M-01. O problema já existe hoje e não nasceu nesta tarefa, mas a T-411 cria o botão que copia esse link. |
| Aviso do cartão na fatura | O texto está certo e basta para quem copia. Ainda falta o aviso para quem administra: ver B-01. |
| 5 por hora por objeto e 20 por hora por pessoa | Bons, os mesmos do convite. A chave leva o schema (`make_key`), então não cruza empresas. A ordem da view tem de ser a da T-252: permissão e 403 `PLT-07` primeiro, depois o limite, depois o serviço. Assim um 403 não gasta o limite, e um 429 não gera link nem invalida o anterior. |
| Resposta única com `no-store` | Certa. Valem para o frontend as mesmas conferências da T-252: o link fica só na mutação, sem `setQueryData`, sem armazenamento e sem `console`. Copiar com `copiarQuandoChegar` (`lib/area-de-transferencia.ts`) é obrigatório nas duas rotas novas. Sem isso, o Safari recusa a cópia, e cada tentativa gera um link, invalida o anterior e gasta o limite (B-02 da T-252). Hoje o `copiar-link.md` cita só `navigator.clipboard.writeText`: troque pela função. |
| Validade de 7 dias | Certa, igual à do convite e à do contrato (`S-15`). |
| `S-15` e `USR-01` | O contrato continua de uso único, com 7 dias e com o limite da página pública. O recibo segue o mesmo modelo, menos o uso único, e a diferença está justificada. |

## Achados

### M-01 · O suporte vê o boleto com o CPF completo do pagador · média

**Onde:**
- `financeiro.selectors.representacao_cobranca` devolve `boleto_url` sem olhar o suporte. É o que aparece na `cobranca_aberta` da conta e no 201 de `POST .../cobranca/`.
- No contrato novo, `acoes.copiar_cobranca` "não depende do perfil".

**Problema:**
- O `boleto_url` é a página do boleto no parceiro. `_gerar_cobranca` manda ao parceiro `Pagador(nome, cliente.documento_claro(), ...)`, e o boleto mostra o nome e o CPF completos do cliente.
- Com o token de suporte, nos dois modos, basta abrir o link para ver o CPF sem máscara. A `AUD-09` diz "nunca vê os dados completos".
- A T-411 piora o caso, porque dá ao suporte um botão "Copiar boleto" que tira o link da tela.
- O mesmo vale para a fatura da assinatura de uma empresa MEI: o pagador é a pessoa, com CPF. O suporte lê o detalhe da fatura (`plataforma/api/assinatura.py`, `suporte_somente_leitura`), e o `url_boleto` e o `url_pagina` vêm nele.

**Reprodução (para o backend virar teste):**
1. Com o token de suporte em "só ver", faça `GET` na conta a receber que tem um boleto `aguardando`.
2. Hoje `cobranca_aberta.boleto_url` vem preenchido.

**O que mudar:**
- **`financeiro.md`:** com o token de suporte, `cobranca_aberta` e as respostas que trazem a cobrança vêm com `boleto_url: null`. A `linha_digitavel` e o `pix_copia_e_cola` não têm dado pessoal e continuam. `acoes.copiar_cobranca` vem `false` com o token de suporte. Teste: `test_aud_09_suporte_nao_recebe_boleto_url`.
- **`assinatura.md`:** com o token de suporte, o `cobranca` da fatura vem com `url_boleto` e `url_pagina` `null` quando a empresa é MEI (titular pessoa física). Também serve anular sempre: o suporte não tem motivo para abrir o boleto da empresa. Escolha do arquiteto; a minha recomendação é **sempre `null` para o suporte**, que é mais simples e não depende do tipo da empresa.
- `copiar-link.md`, linha "Não depende do perfil": acrescentar "menos o suporte Giro (`AUD-09`)".

### M-02 · Quem copia o link do contrato pode assinar no lugar do cliente · média

**Onde:** `POST /api/locacoes/{id}/contrato/link/` e `POST /api/publico/assinaturas/assinar/` (corpo `{ token, aceite, nome_completo }`).

**Problema:**
- Até hoje, o token de assinatura só saía para o WhatsApp e o e-mail do cliente, e ninguém da locadora o via.
- Com o copiar, o vendedor recebe o token na mão. Ele pode abrir o link e assinar digitando o nome do cliente, que está na tela.
- No convite, a T-252 aceitou esse risco porque o administrador já escolhe o perfil de quem convida, e não há ganho. Aqui é diferente. A assinatura é a prova do aceite do **cliente** (`LOC-15`): contrato, caução e multas. Uma assinatura forjada pela equipe prejudica um terceiro e enfraquece a prova da locadora numa disputa.
- Bloquear não é o caminho. No balcão, o cliente costuma assinar no celular, na rede da loja, e o mesmo IP de quem copiou é normal. O que falta é **a prova registrar como o link chegou ao cliente**.

**O que mudar (`contratos.md` e `locacoes.md`):**
- O contrato guarda a origem do token vivo: `token_assinatura_canal` (enum `whatsapp`, `email`, `copiado`) e `token_assinatura_gerado_por` (o usuário, quando é `copiado`).
- Na assinatura, o evento `contratos.contrato_assinado` e o bloco de evidência do PDF assinado levam o canal. Por exemplo: "Link entregue por cópia, gerado por Carla Mendes em 03/11, 10:12". O bloco já leva o IP e o aparelho.
- Se o IP da assinatura for o mesmo do evento `contrato.copiar_link`, o evento de assinatura marca `mesmo_ip_de_quem_copiou: true`. Não bloqueia nada; serve para a auditoria e uma disputa.
- Teste: `test_loc_15_assinatura_por_link_copiado_registra_canal`.
- Na tela (frontend), junto do link copiado: "Mande o link ao cliente. Só ele pode assinar.". O texto é do produto; vale avisar.

### B-01 · O link de pagamento da fatura troca o cartão guardado sem aviso · baixa

**Onde:** `plataforma/services.py`, `_guardar_cartao`, chamado pelo webhook depois do pagamento na página do parceiro (ADR 0023).

**Problema:**
- Com a forma `cartao`, qualquer cartão digitado no link copiado substitui o token guardado. Isso vale para o contador e também para quem receber um link vazado.
- O evento `assinatura.cartao_guardado` é gravado, mas o administrador não é avisado.
- Um link que vazar deixa um terceiro pôr um cartão alheio (até um cartão roubado) como forma da empresa. A conta e o estorno caem na empresa.
- Não vaza dado e não dá acesso, mas é dinheiro (o checklist pede atenção a isso).

**O que mudar:** quando o cartão guardado muda, o administrador recebe o e-mail "O cartão das próximas faturas mudou para Visa final 4242. Se não foi você, troque a forma de pagamento em Assinatura.". O evento passa a mostrar no histórico da assinatura quem pagou (o parceiro devolve o nome do titular) e o final. Teste: `test_plt_13_cartao_novo_avisa_o_administrador`.

### B-02 · A tarefa de envio pode matar um link copiado · baixa

**Onde:** a tarefa `contratos_preparar_e_enviar`, que gera o token e envia.

**Problema:**
- O contrato barra o copiar com o PDF ainda em preparo (409 `contrato_em_preparo`), e isso está certo.
- Sobra a repetição da fila: um retry do envio depois de o link ter sido copiado gera um token novo e mata o copiado sem aviso.
- É o B-01 da T-252, agora no contrato.

**O que mudar (backend):** a tarefa trava o contrato e não gera token se `token_assinatura_expira_em` for mais novo que o momento em que ela entrou na fila, ou se já houver um link copiado depois disso. Teste: `test_s_15_reenvio_em_fila_nao_mata_link_copiado`.

### B-03 · A página `/recibo` · baixa

**O que mudar:**
- **Isolamento:** o token é procurado só no schema do host. Teste com duas empresas, `test_dev_02_recibo_publico_nao_cruza_empresas`: o token da Moto Rápida no host de outra empresa dá 404. A chave do limite público leva o schema.
- **Página:** `/recibo` responde com `Cache-Control: no-store` e com `X-Robots-Tag: noindex` (ou a meta `robots`), como deve valer para `/assinar` e `/convite`. A `Referrer-Policy: same-origin` já está em `next.config.ts` e em `prod.py`, então o clique no PDF não leva a URL da página ao storage.
- **Escopos próprios** para a rota pública do recibo (`recibo_publico_ip`, `recibo_publico_token`), com os números da assinatura. Não reaproveitar os escopos da assinatura, para que um não gaste o limite do outro.
- **Abertura na auditoria (opcional):** registrar `devolucao.recibo_aberto` com IP e aparelho, no máximo um por token por dia. Ajuda a locadora a provar que o cliente recebeu o recibo, e ajuda a perceber um link que vazou. Fica com o arquiteto decidir; não bloqueia.

## Sem achado

- A cobrança da parcela: copiar o que já está na tela não cria nada nem gera evento, e está certo. Barrar a cobrança de um dia que já passou evita mandar valor errado (`FIN-03`). Com o M-01 feito, fica fechado.
- Anonimização (`AUD-06`): anular os dois tokens e responder 409 `titular_anonimizado` está certo. Lembrete para o backend: o PDF do recibo guardado tem o nome do cliente, então confira se `clientes/titular.py` já trata o arquivo do recibo como trata os outros documentos do titular. Se não tratar, abra tarefa; não é desta.
- Auditoria, logs e Sentry: igual à T-252, que já foi conferida no código.

## Próximos passos

1. **Arquiteto:** pôr M-01, M-02, B-01 e B-03 no contrato (PR #460 ou uma emenda).
2. **Backend:** implementar com os testes citados.
3. **Segurança:** revisão do código da rota e da tela, como na T-252, quando o backend e o frontend entregarem.
