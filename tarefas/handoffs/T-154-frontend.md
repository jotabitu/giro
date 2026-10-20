# T-154 · Tela Empresa e marca e passo Marca do assistente · frontend → qa, orquestrador

**O que foi feito:**
- `/admin/marca` (`AdminMarca`): bloco "Marca" (Logo com "Trocar logo" e "Remover", "Cor principal" com bolinhas e campo `#RRGGBB`, "Nome que aparece para clientes") e "Prévia", ligados a `GET /api/marca/`, `POST /api/marca/simular/` e `PATCH /api/marca/`. "Dados da empresa" e "Endereço do sistema" ficam fora (sem contrato).
- `PassoMarca` (assistente): só "Logo" e "Cor de destaque" com as seis cores e a pré-visualização; "Continuar" sempre chama o `PATCH` (também sem mudança, que marca o passo, `IMP-05`) e "Pular por agora" não chama rota. **A casca do assistente ainda não existe** (só `implantacao/importar`), então o componente fica pronto: recebe `guardada`, `aoContinuar` e `aoPular`.
- Prévia: só os valores da simulação (`cor`, `cor_sobre`, `cor_suave`, iniciais, nome), aplicados em variáveis de CSS do bloco; nenhuma conta de cor no frontend. A cor digitada espera 300 ms; as bolinhas simulam na hora. Sem simulação, vale a marca salva.
- Logo não salvo por `URL.createObjectURL` em `<img>` (revogada ao trocar e ao sair); `accept="image/png,image/svg+xml,.png,.svg"`; ajuda "PNG ou SVG, fundo transparente, até 2 MB". Tamanho e formato quem confere é a API.
- Depois de salvar: a consulta `marca` recebe o corpo e é invalidada (a casca troca as cores); a edição recomeça do salvo. Erro 400 aparece no campo (`cor`, `nome_exibicao`, `logo`) com a `mensagem` da API; outro erro vira alerta geral.
- Rota `/admin/marca` só do administrador em `rotaPermitida`.

**Onde:** `frontend/src/components/marca/` (`useEdicaoDaMarca`, `PreviaDaMarca`, `EscolhaDoLogo`, `EscolhaDaCor`, `Marca.test.tsx`), `components/admin/AdminMarca.tsx`, `components/implantacao/PassoMarca.tsx`, `app/(empresa)/admin/marca/page.tsx`, `lib/marca-edicao.ts`, `lib/api/marca.ts` (`simular`, `salvar`), `lib/api/tipos.ts`, `lib/menu.ts`, `testes/falsos/falso.ts` (simular e salvar com a tabela das seis cores do contrato).

**Contrato:** `docs/api/empresas.md`, "Escrita da marca". `npm run api:gerar` sem diferença (o cliente já vinha da T-153).

**Regras cobertas:** IMP-05 (Continuar marca o passo), S-12 (logo sempre em `<img>`), ADR 0004 e 0005 (a API decide, a tela mostra; simulação sem gravar). Testes em `Marca.test.tsx`: prévia com `#2F6FED` → `#FFFFFF` e `#DBF3FF` da API mockada, logo por `<img>`, Remover volta às iniciais, `accept` e ajuda, erro 400 no campo, corpo do PATCH só com o que mudou, simulação só com cor inteira, páginas sem Dados da empresa/Endereço do sistema, passo com as seis cores, rota só do administrador.

**Verificação:** `npm run typecheck`, `eslint` nos arquivos tocados e `vitest` em `components/marca`, `lib/menu` e `lib/marca`: verdes. Os testes são de marcação estática (ambiente `node`); o fluxo de escolher arquivo, digitar a cor e salvar **não foi exercitado no navegador** (sem backend no ar nesta sessão), nem a conferência visual em 1440px e 390px.

**O que ficou de fora:** blocos "Dados da empresa" e "Endereço do sistema"; CNPJ, razão social, nome fantasia e endereço de acesso do assistente; a casca do assistente. Na Prévia a cor suave do tema escuro (`cor_suave_escuro`) não é usada, só `cor_suave`.

**Próximo passo para quem recebe:**
- **qa:** conferir no navegador `/admin/marca` (troca de logo SVG e PNG, remover, cor digitada inválida, nome com mais de 80 caracteres) em 1440px e 390px.
- **orquestrador:** abrir o PR sobre a T-153 (#358); a casca do assistente precisa de tarefa própria para montar o `PassoMarca`.
