# T-375 (parte 2) · E2E do fechamento da fase 1 · qa → orquestrador

**Branch:** `t-375-e2e-fechamento`, a partir da `origin/main` com o #439 (`484f1621`). Nada de produção foi mexido.
**Onde rodou:** stack isolada do QA (projeto `giro-qa`, portas 3100 e 8100, banco próprio), não a stack de desenvolvimento em uso. Motivo: o harness do `npm run e2e` (`restaurarSeed`) faz `DROP DATABASE giro` e recria a partir do seed, o que apagaria a reativação de hoje da Moto Rápida (FAT-0001 paga, ativa até 21 nov). O dono confirmou "banco separado". A stack de desenvolvimento e o `giro-backend-pg` não foram tocados. Comando: `E2E_PORTA_FRONTEND=3100 E2E_PORTA_BACKEND=8100 npx playwright test ...` na pasta `frontend`.

## O que passou
- **Locação completa em 1440 px** (`desktop.spec.ts`, 3,9 min): login, cliente, locação, vistoria, assinatura, caixa, devolução, cobrança e baixa.
- **2 etapas** (`fechamento.spec.ts`): administradora pede o código, código errado é recusado, o certo entra; o gerente entra sem código.
- **Modo suporte**: entrada pelo link, fragmento apagado da barra, faixa com motivo e "Sair do suporte", que leva à página do suporte.
- **Implantação do zero** (Pedalada, plano Essencial, em `fechamento.spec.ts`): Marca, Primeira filial (matriz já existente), Ramo, Tabela de preços (sem categoria não segue; cria uma), Modelo de contrato (cria e publica), Importar (só aberto), Convidar equipe (convite criado e visível em Usuários). Os passos 1 a 5 ficam "feito" (IMP-07), e o fim da implantação volta ao início.
- **Passada visual a 1440 e 390 px** (`fechamento-visual.spec.ts`): Reembolsos, Pendências do pagamento, Recebimentos da implantação e Controle do suporte carregam sem erro de API e sem rolagem lateral. Capturas em `docs/qa/fechamento-fase-1/`.

## O que falhou (itens para o orquestrador; não corrigi produção)
1. **`/admin/suporte` bloqueada para a administradora** ("Seu perfil não tem acesso a esta página"). `rotaPermitida` (`frontend/src/lib/menu.ts`) não tem caso para a rota, e ela não está no menu. O cartão de Configurações abre uma página que a guarda barra. Correção provável: `if (rota === "/admin/suporte") return pode.administracao;`, com teste. Dono: frontend. Teste que cobre: "controle do suporte em Configurações".
2. **Reembolsos e Pendências do pagamento inalcançáveis pelo menu.** `docs/api/contas.md` (linhas 202 e 203) manda a API entregar `reembolsos` e `pendencias_pagamento` no menu, mas `backend/apps/contas/navegacao.py` não tem as duas chaves. Sem elas a guarda bloqueia as telas para todos os perfis. Dono: backend (a T-380 entregou as listas, não o menu). Para ver as telas, o teste visual acrescenta os dois itens à resposta de `auth/eu/` no navegador e registra a falha como `expect.soft`.
3. **Tabela de preços (passo do assistente) não se atualiza depois de salvar a categoria.** A mensagem "Para continuar, crie ao menos uma categoria com preço." e o "Continuar" desabilitado ficam até recarregar a página; depois do reload, segue. Dono: frontend (invalidar o andamento).
4. **Token do suporte nasce vencido com a data simulada.** O `exp` sai do relógio simulado (07 out) e o JWT é validado pelo relógio real (28 out): `/suporte/entrar` responde "O acesso de suporte terminou". Só acontece com `GIRO_DATA_REFERENCIA` ligada (desenvolvimento; produção recusa). O teste contorna pondo o relógio no dia real. Decidir se é aceitável (ADR 0021) ou se o `exp` deve usar o mesmo relógio.
5. **Leitura de CRLV-e real com o catálogo novo (#435), pedido da Segurança.** Com os 2 PDFs reais (Detran-CE): 7 dos 9 campos vêm nos dois (placa, chassi, renavam, anos, cor, combustível; exercício também), e marca e modelo caem em `dicas.marca_modelo` nos dois. Causas:
   - **Moto:** o PDF traz `RE/CLASSIC 350`. O catálogo tem Royal Enfield só com "Bullet 500" (sem Classic 350), e a sigla `RE` não vira "Royal Enfield". A previsão da Segurança ("a moto deve achar") não se confirma.
   - **Carro:** o PDF traz `CHEVROLET/CRUZE LT NB`. No catálogo a marca é "GM - Chevrolet", então o prefixo `CHEVROLET` não casa, e ainda há várias versões do Cruze LT. Cai na dica.
   - Sugestão: sigla e apelido de marca na `achar_modelo` (RE, CHEVROLET → GM - Chevrolet) e acrescentar à lista própria o que a Parallelum não traz (Royal Enfield Classic 350). Dono: backend. Os PDFs não saíram da pasta de downloads; só entram aqui os nomes de modelo genéricos.
6. **Visual (design-system):** placeholder da busca cortado ("Buscar client", "Buscar cliente, l" a 1440; "cobranç" a 390) e as abas "Abertas 0 / Resolvidas 0 / Todas 0" quebram linha a 390 em Pendências. As listas estão vazias porque o seed não tem reembolso nem pendência; **tabela, cartões, "Marcar como feito" e "Baixar a conta" não foram exercidos no navegador**.

## Não coberto (e por quê)
- **Recebimentos**: só a tela abre e carrega (1440 e 390). Enviar o cadastro depende do parceiro de pagamento, sem simulação na stack.
- **Reembolsos e Pendências com dados**: o seed não tem; falta tarefa de seed (ou de fixture de E2E) para a fase 2 ou um teste que crie um reembolso pela devolução.
- **Convite aceito e ativação do 2FA pela tela**: o convite é criado, mas o aceite não foi percorrido.
- **Celular (390) dos fluxos de implantação, suporte e 2FA**: só a passada visual; o fluxo completo é em 1440. A locação em 390 está no `celular.spec.ts`, que não rodei nesta passada.
- **Homologação**: fase 2.

## Para quem rodar de novo
- O contêiner de frontend do Docker no Windows não percebe pasta nova depois de um merge: `docker compose restart frontend` (aconteceu com `/admin/suporte` e as telas do #439).
- A imagem do backend do QA estava velha: sem `pypdf`. Instalei só no contêiner de teste. Reconstrua com `docker compose build backend` se for ler PDF.
- `fechamento.spec.ts` e `fechamento-visual.spec.ts` entram nos projetos `desktop` e `celular` em `playwright.config.ts`.
- Não rodei a suíte inteira de uma vez (um check pesado por vez): cada teste novo rodou isolado; o `desktop.spec.ts` rodou inteiro e passou.
