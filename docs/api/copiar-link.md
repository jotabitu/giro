# Copiar o link nas ações que enviam ao cliente

**Dono:** arquiteto · **Versão:** 03 nov 2026 (T-411) · **Apps:** `locacoes` e `contratos` (contrato), `financeiro` (cobrança), `vistorias` (recibo), `plataforma` (fatura) · **Regras:** `USR-01` (modelo do "Copiar link do convite"), `LOC-15`, `AUT-03`, `AUT-05`, `DEV-02`, `PLT-13`, `PLT-14`, `AUD-05`, `AUD-06`, `AUD-09`, `PLT-07`, `CLI-12` · **Segurança:** `S-15`, `S-17` · **Telas:** Locacao-Detalhe, Receber, Caixa, Devolucao (recibo), Admin-Assinatura · **Revisão de segurança:** `tarefas/handoffs/T-411-seguranca.md` (PR #462; M-01, M-02, B-01 a B-03 incorporados em 03 nov 2026)

Decisão do dono de 29 out 2026 (nota "Função de copiar links", T-411): além de enviar, a tela mostra o link para a pessoa copiar e mandar à mão em quatro ações: contrato para assinar, cobrança da parcela, recibo da devolução e fatura da assinatura. Este documento junta o que vale para as quatro; o detalhe de cada rota está no contrato do módulo, citado em cada linha.

## As quatro ações

| Ação | O que se copia | Rota | Novo? | Contrato |
| --- | --- | --- | --- | --- |
| Contrato para assinar | o link de assinatura (`/assinar#<token>`) | `POST /api/locacoes/{id}/contrato/link/` | rota nova | `locacoes.md`, `contratos.md` |
| Cobrança da parcela | o Pix copia e cola, a linha digitável e o link do boleto da cobrança aberta | `cobranca_aberta` da conta e o 201 de `POST .../cobranca/` | só `acoes.copiar_cobranca` | `financeiro.md` |
| Recibo da devolução | o link do recibo (`/recibo#<token>`) | `POST /api/devolucoes/{id}/recibo/link/` e a página pública `POST /api/publico/recibos/consultar/` | rota nova, campos novos na `Devolucao` | `vistorias.md` |
| Fatura da assinatura | a 2ª via do parceiro: Pix copia e cola, linha digitável, link do boleto ou a página do cartão | `cobranca` de `GET /api/assinatura/faturas/{codigo}/` e o 200 de `POST .../pagar/` | nada novo na API | `assinatura.md` |

Por que duas formas:

- **Contrato e recibo** abrem uma página do Giro com dado pessoal (o contrato tem CPF e endereço; o recibo, as fotos e os valores). O link carrega um token cujo banco guarda só o hash (`S-15`, ADR 0014). O token em claro só existe na hora em que é gerado, então o link só pode aparecer nessa hora, como no `POST /api/usuarios/{id}/link-convite/` (`contas.md`). Copiar **gera um link novo** e o anterior deixa de valer.
- **Cobrança e fatura** são dados de pagamento do parceiro que a API já devolve, sem token do Giro: o Pix copia e cola, a linha digitável e a URL do boleto ou da página do cartão. Não há o que gerar; a tela mostra o que já veio, com um botão de copiar ao lado de cada um.

## O que vale para as rotas novas (contrato e recibo)

Igual ao copiar link do convite (`contas.md`, T-249), com as diferenças de cada uma no contrato do módulo:

- **Resposta única.** 200 com `Cache-Control: no-store`, no formato
  ```json
  { "link": "https://motorapida.girolocadoras.com.br/assinar#<token>",
    "expira_em": "2026-11-10T14:00:00Z",
    "aviso": "O link anterior deixa de valer." }
  ```
  mais o bloco do objeto (o contrato ou a devolução). O link não volta em nenhum `GET`: para ter outro, copia de novo.
- **Token no fragmento.** `https://<subdominio>.<dominio>/<pagina>#<token>`: o token não chega a log de servidor nem ao cabeçalho `Referer`. A página lê o fragmento, apaga-o da barra com `history.replaceState` e manda o token no corpo do `POST`.
- **Não envia nada.** Nem WhatsApp nem e-mail. Quem copia manda por onde quiser. O envio continua pelas rotas de sempre (`contrato/`, `contrato/reenviar/`, o recibo no encerramento e `recibo/reenviar/`).
- **Um link vivo por objeto.** O banco guarda um hash só. Copiar invalida o link enviado antes (pelo WhatsApp, pelo e-mail ou copiado), e reenviar invalida o copiado. A tela avisa com o `aviso` da resposta.
- **Validade de 7 dias** a partir da geração, como o convite, o contrato e a exportação (`S-15`).
- **Suporte Giro:** 403 `PLT-07` ("No modo suporte você não gera link para o cliente."), com qualquer permissão de acesso. O link abre o documento completo, com CPF e endereço, e o suporte só vê dado pessoal mascarado (`AUD-09`).
- **Limite** (`comum.limites`, números do arquiteto): **5 por hora por objeto** (contrato ou devolução) e **20 por hora por pessoa**, o que vier primeiro. Acima, 429 `muitas_requisicoes` (`README.md`), e nenhum link é gerado nem o anterior invalidado: o limite é conferido antes da transação. Os mesmos números do convite: 5 cobre quem erra o canal algumas vezes; mais que isso é sinal de link vazando. Os 20 por pessoa cobrem um balcão cheio.
- **Auditoria.** Um evento por link gerado, categoria `seguranca`, com o ator, o objeto e o `expira_em` novo, **sem o link nem o token**. O link também não vai para log: a view não registra o corpo da resposta, e o Sentry roda com `send_default_pii=False` e não manda corpo de resposta.
- **Ordem na view** (a do `link-convite`, T-252): permissão e 403 `PLT-07`, depois o limite, depois o serviço.
- **Prova da assinatura** (só o contrato, `LOC-15`): o contrato guarda o canal do token vivo (`whatsapp_email` ou `copiado`), quem copiou e o IP da cópia, e a página de registro do PDF assinado diz como o link chegou ("Link entregue por cópia, gerado por Carla Mendes em 03/11/2026, 10:12"). A tarefa de envio não troca um token mais novo que ela (um link copiado depois de ela entrar na fila). Detalhe em `locacoes.md` e `contratos.md`.
- **Suporte e dados do parceiro** (`AUD-09`): o suporte não recebe `boleto_url` da conta nem `url_boleto` e `url_pagina` da fatura (o boleto mostra o CPF completo do pagador), e `acoes.copiar_cobranca` vem `false` para ele.
- **Titular anonimizado** (`AUD-06`, `clientes/titular.py`): a anonimização anula os tokens vivos do titular (o de assinatura dos contratos não assinados e o do recibo das devoluções), e o link copiado antes deixa de abrir (404). Copiar de novo depois disso responde 409 `titular_anonimizado` ("Os dados deste cliente foram anonimizados.").

## Na tela

- O componente é o mesmo do copiar link do convite (`frontend/src/components/admin/PainelDoUsuario.tsx`): o campo só leitura com o link, o botão "Copiar", a validade ("Vale até 10/11, 11:00") e o `aviso`. A cópia é sempre por `copiarQuandoChegar` (`frontend/src/lib/area-de-transferencia.ts`), obrigatória nas duas rotas novas: sem ela, o Safari recusa a cópia, e cada tentativa gera um link, invalida o anterior e gasta o limite (B-02 da T-252). Se a cópia falhar, o campo fica selecionado para a pessoa copiar com o teclado.
- O link fica só no resultado da mutação: some ao fechar o pop-up, sem `setQueryData`, e nunca vai para `localStorage`, `sessionStorage`, URL, `console` nem cache persistido do TanStack Query.
- No contrato, junto do link: "Mande o link ao cliente. Só ele pode assinar." (texto a confirmar com o produto).
- Botão por `acoes` da API, nunca por conta da tela (`acoes.copiar_link_contrato`, `acoes.copiar_link_recibo`, `acoes.copiar_cobranca`; na fatura, `acoes.pagar`).
- Nomes dos botões: "Copiar link para assinar" (contrato), "Copiar Pix" e "Copiar boleto" (cobrança), "Copiar link do recibo" (recibo), "Copiar link de pagamento" (fatura).

## Fica para depois

- **Aditivo da renovação** (`LOC-08`): o copiar vale para o contrato vigente da locação. O aditivo não assinado continua só com o envio; entra quando houver pedido.
- **WhatsApp do recibo com o link novo.** O modelo 10 (`recibo_devolucao`, `docs/qa/criterios/whatsapp.md`) continua com a URL de 15 minutos do storage, e o e-mail, com o PDF anexo. Passar o envio para o link de 7 dias desta tarefa muda o texto aprovado pela Meta ("O link vale por 15 minutos") e é tarefa do produto.
- **Página de pagamento do cliente final** ("Telas que faltam desenhar", nas regras): a cobrança copia o que o parceiro devolve. Uma página do Giro, com a marca da locadora, juntando Pix e boleto num link só, é outra tarefa.
