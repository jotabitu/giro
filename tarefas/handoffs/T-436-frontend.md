# T-436 · Página pública do recibo (`/recibo`) · frontend → orquestrador, devops, qa

Branch `t-436-pagina-recibo` (a partir da `origin/develop`). Regras: DEV-02, S-15, AUD-05. Telas: `Recibo-Desktop.dc.html` e `Recibo-Mobile.dc.html`. Contrato: `docs/api/vistorias.md` ("POST /api/publico/recibos/consultar/") e `copiar-link.md`.

**O que foi feito**

1. **Rota** `(publico)/recibo/page.tsx`, fora da casca da empresa, igual à `/assinar`: `referrer: no-referrer` e `robots: noindex, nofollow`.
2. **Componente** `components/recibo/ReciboDevolucao.tsx`: lê o token do fragmento (`useTokenDoFragmento`, apaga da barra com `history.replaceState`), chama `recibo.consultar`, mostra a marca da locadora, "Recibo da devolução da LOC-xxxx", "Olá, <primeiro nome>", a data da devolução e "Baixar recibo". Rodapé "Tecnologia Giro".
3. **Baixar recibo** consulta de novo a cada clique e abre a `pdf_url` nova (AUD-05, a URL vale 15 min). A aba abre dentro do clique (sem bloqueio de pop-up) e recebe a URL depois; se a consulta falhar, a aba fecha e o erro aparece na página.
4. **404 e 410** (e link sem token): "Este link venceu ou não existe. Peça um novo à locadora."
5. **Cabeçalhos:** `next.config.ts` põe `Cache-Control: no-store` e `X-Robots-Tag: noindex, nofollow` em `/recibo`. Conferido no `next dev`; lá o Next acrescenta `must-revalidate`, e em produção o valor é o da configuração.
6. **API:** `lib/api/recibo.ts`, `tipos-recibo.ts` (do OpenAPI gerado) e falso `testes/falsos/falso-recibo.ts` (tokens `link-juliana`, `link-vencido`; outro, 404).

**Testes:** `components/recibo/ReciboDevolucao.test.tsx` (`test_dev_02_...`, `test_s_15_...` x2, `test_aud_05_...`). Suíte inteira: 862 passam. Lint e typecheck limpos.

**Limites**
- A página mostra só o que a API devolve (código, primeiro nome, data, PDF). Os blocos das telas de referência (veículo, acerto da caução, fotos com visualizador) não existem na resposta de `consultar`; ficam para quando o backend devolver esses dados (tarefa nova, a pedir ao Orquestrador).
- Conferida a 1440 e 390 px com a API simulada no navegador (Playwright): título, painel e botão corretos, fragmento apagado da barra. Não testei o clique no PDF real; os testes são de marcação estática.
- `GIRO_RECIBO_PUBLICO` segue desligado. **Devops:** ligar `GIRO_RECIBO_PUBLICO=1` em cada ambiente na entrega; com ele ligado o botão "Copiar link do recibo" aparece pela `acoes.copiar_link_recibo`, sem mudar a tela da devolução.
- **QA:** incluir `/recibo` na conferência quando o backend de dados do recibo estiver ligado.
