# T-261 · Pendências do produto no backlog · produto → orquestrador, backend, frontend, qa

**O que foi feito:** respondi as dúvidas abertas que são do produto no backlog. A branch `t-261-pendencias-produto` sai da `origin/main`.

**Respondidas pelo produto (não mudam regra):**
- **(a) T-181, cartão Filiais sem filial ativa:** fica "Nenhuma filial ativa". Só acontece antes do passo 6, porque a última filial ativa não se desativa (`FIL-06`), e o texto vale nos dois casos. O backend não muda nada.
- **(b) T-224, item 1:** fica o texto do arquiteto para a recusa de "só vende" no Essencial: "O plano Essencial não inclui vendas. Escolha locação, ou locação e venda.". A tela não deixa chegar à recusa. O item 2 foi resolvido na T-256 (PR #251).
- **(d) T-105, LOC-2856 da carteira:** o seed está certo, com a LOC-2856 `ativa` desde 07 out, a 1ª semana e a caução pagas no caixa. O CA-016-01 e o CA-016-08 descrevem o momento antes da retirada, como fixture, e o CA-016-08 passou a dizer isso (`docs/qa/criterios/T-016.md`).

**Para o dono (mudam regra), em "Pontos em aberto" das regras, com o padrão valendo até a resposta:**
- **(c) T-209, item d, "Veículos no menu do vendedor" (`USR-05`).** A regra dá a Frota ao vendedor pelo menu completo, mas ele nunca chega ao menu completo: todas as telas que ele abre pelo próprio menu usam o menu do perfil. Padrão A: o menu do vendedor ganha "Veículos" na fase 1, só leitura.
- **Pix Automático nas parcelas (`AUT-04`, `LOC-05`, T-029).** Padrão em três partes:
  1. a cobrança é criada 5 dias úteis antes do vencimento;
  2. a autorização nasce na 1ª parcela paga na retirada, e a parcela que vencer antes segue a régua comum (`AUT-03`);
  3. só a semanal e a mensal têm Pix Automático.

**Outras linhas do backlog:** as demais `[decisão]` e `[divergência]` abertas são de outros agentes:
- telas para o design-system (T-028);
- contratos para o arquiteto;
- dados para o qa;
- a T-208 para o backend;
- as duas do qa na T-019 para o orquestrador.

A `[decisão]` do lançamento avulso (T-162) já estava respondida.

**Arquivos:** `docs/regras-de-negocio.md` ("Pontos em aberto"), `docs/qa/criterios/T-016.md`, `tarefas/backlog.md` (seção da T-261, e as linhas respondidas marcadas), `tarefas/em-andamento.md`.

**Para quem recebe:**
- **Orquestrador:** com o padrão A do menu do vendedor, numerar backend (o `menu` do vendedor em `GET /api/auth/eu/`, `contas.md`) e frontend. O Pix Automático espera o dono, ou segue o padrão quando o fluxo da locação for numerado (handoff da T-029, item 1).
- **QA:** a nota do CA-016-08.
