# T-335 · Casca do assistente de implantação · frontend → orquestrador, backend, qa

**O que foi feito:**
- Rota `/implantacao` (`InicioDoAssistente`): leva ao passo atual que a API manda (`proximo`; tudo feito, o primeiro). Rota `/implantacao/[passo]` (`PassoDoAssistente`): moldura e o passo da vez. `/implantacao/importar` segue como página própria e agora usa a mesma moldura.
- `CascaDoAssistente`: marca da empresa, "Configuração inicial", "Salvar e sair", lista de passos no desktop (links só para passos com tela) e barra de progresso no celular. A ordem, o "Passo N de M", os rótulos e o que está feito vêm de `GET /api/implantacao/`; a tela não conta nada. Passo fora do plano (ex.: `recebimentos` no Essencial) mostra aviso e leva ao próximo da API. Só o administrador.
- Avanço e volta: `lib/implantacao.ts` (`destinoDepoisDe`, `destinoAntesDe`) segue a lista da API; nas pontas vai para `/inicio`.
- Passos ligados: **Marca** (`PassoMarca` da T-154; Continuar e Pular por agora avançam) e **Ramo** (novo `PassoRamo`, `GET` e `PUT /api/ramo/`; Continuar sempre chama o `PUT`, que marca o passo, `IMP-05`; recusa `PLT-12` com a mensagem e o link da API). `OpcaoDoRamo` saiu de `AdminRamo` para `components/ramo/` e as duas telas a usam. **Importar** já existia; seus botões passam a seguir a ordem da API (antes iam para `/admin/usuarios`).
- Passos sem tela (`filial`, `precos`, `contrato`, `recebimentos`, `equipe`): a rota existe só com o rótulo da API, o texto "Esta etapa ainda não está disponível aqui." e os botões Voltar e Pular por agora. Nenhum número ou campo inventado.

**Passos sem contrato (ou sem tela) que ficam para outras tarefas, na ordem da API:** 2 Primeira filial (`Onboarding-Filial`), 4 Tabela de preços (`Onboarding-Precos`), 5 Modelo de contrato (`Onboarding-Contrato`), 6 Recebimentos (`Onboarding-Recebimentos`, só com `recebimento_parceiro`), 8 Convidar equipe (`Onboarding-Equipe`). Cada um precisa da tela e do contrato do que ele grava.

**Atualização (rota da T-202):** feito o merge da `origin/t-202-telas-resolvidas`, `npm run api:gerar` e `lib/api/tipos-implantacao.ts` agora usa `AndamentoDoAssistente` e `PassoDoAssistente` gerados (o campo `passo` vem como `string`, então a lista de chaves com tela fica só em `lib/implantacao.ts`). Conferido com `selectors.andamento_do_assistente`: mesmas chaves, ordem e rótulos da fixture, e `recebimentos` sai fora do plano sem a função. **A T-335 entra depois do PR da T-202** (esta branch contém os commits dela). Ainda falta o `acao.passo` da Configurações apontar para o `proximo` (backend/arquiteto).

**Onde:** `frontend/src/components/implantacao/` (`CascaDoAssistente`, `PassoDoAssistente`, `InicioDoAssistente`, `PassoRamo`, `ImportarDados`, `Assistente.test.tsx`), `components/ramo/OpcaoDoRamo.tsx`, `app/(empresa)/implantacao/page.tsx` e `[passo]/page.tsx`, `lib/implantacao.ts`, `lib/api/implantacao.ts`, `lib/api/tipos-implantacao.ts` (gerado), `testes/falsos/falso-implantacao.ts`.

**Regras cobertas:** IMP-05 (passos pela API; Continuar marca, pular não), PLT-12 (ramo no Essencial), IMP-01 (a API diz `concluida`). Testes em `Assistente.test.tsx`: ordem e vizinhos, Essencial com 7 passos ("Passo 6 de 7", sem Recebimentos), passo fora do plano, links só dos passos com tela, carregando, não administrador, Marca, Ramo (módulos e aviso da API) e passo sem tela.

**Verificação:** `tsc` sem nenhum erro (com o `schema.d.ts` novo), `eslint` nos arquivos tocados e `vitest` em `components/implantacao`, `components/admin`, `components/marca` e `lib/menu`: 160 testes verdes. Testes de marcação estática: **não conferi no navegador (1440px e 390px)** nem o avanço entre passos contra o backend no ar.

**Próximo passo para quem recebe:**
- **orquestrador:** abrir o PR da T-335 depois do da T-202; numerar as tarefas dos cinco passos sem tela quando houver contrato.
- **backend/arquiteto:** `acao.passo` na Configurações apontando para o `proximo`.
- **qa:** conferir `/implantacao` → Marca → Ramo → Importar em 1440px e 390px, também no Essencial.
