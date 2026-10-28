# Handoff · T-363 · Modelos de contrato (frontend)

- **Agente:** frontend
- **Branch:** `t-363-modelos-de-contrato`
- **Contrato:** `docs/api/contratos.md` ("Modelos", "Marcadores", "HTML permitido")
- **Telas de referência:** `docs/telas/html/Contratos-Modelos-Desktop.dc.html`, `Contratos-Modelos-Mobile.dc.html`
- **Regras:** IMP-04, S-09, LOC-15

## O que foi entregue

1. **API (`frontend/src/lib/api/modelos-contrato.ts`, `tipos-contratos.ts`):** `modelosContrato` com listar, obter, marcadores, prontos, criar, alterar (PATCH), prévia, publicar e arquivar. Tipos do OpenAPI gerado.
2. **Tela `/admin/contratos` (`components/contratos/TelaDeModelosDeContrato.tsx`):** cabeçalho com "Novo modelo", aviso de sucesso e o painel reaproveitável. O cartão `modelos_contrato` de Configurações já apontava para `/admin/contratos`; a rota agora existe.
3. **`ModelosDeContrato` (reaproveitável pelo passo Modelo de contrato do assistente, T-364):** lista de modelos (nome, "usado em N locações", selo "Publicado · v3", "Rascunho" ou "Arquivado") e o painel do modelo escolhido, com "Ver com dados reais", "Editar texto", "Publicar versão N+1" (só quando há o que publicar), "Arquivar", campos automáticos usados, prévia, versões e o texto sobre contratos já assinados. Props: `criando`, `aoFecharCriacao`, `aoAvisar` e `aoPublicar` (o passo do assistente usa para seguir adiante depois de publicar). O botão "Novo modelo" fica fora do painel, como no `CategoriasDePreco`.
4. **Diálogos:** `DialogoNovoModelo` (em branco ou um dos prontos), `DialogoDoModelo` (nome, texto e a lista de campos automáticos da API, com clique para inserir `{{grupo.campo}}` no cursor; o erro `marcador_invalido` aparece no campo do texto) e a prévia em diálogo. Arquivar pede confirmação e mostra o 422 `IMP-04` com o texto da API.
5. **Falso (`testes/falsos/falso-modelos-contrato.ts`):** seed da Moto Rápida (Locação semanal v3 com 38 contratos, Compra e venda parcelada v1 com 3), prontos, marcadores, `marcador_invalido`, `IMP-04` e rascunho da versão seguinte.

## Pontos para o orquestrador e o produto

- **A API não devolve `acoes` para modelos.** A tela usa `eu.pode.administracao` e o estado do modelo (`status`, `tem_rascunho`, `arquivado`) para mostrar publicar e arquivar.
- **A prévia entra como HTML na página** (`dangerouslySetInnerHTML`). O HTML vem da API já sanitizado por lista branca (S-09); a tela não monta nem altera esse HTML. A segurança pode querer conferir.
- A prévia usa os dados de exemplo. O contrato aceita `locacao_id`, e a função `previa(id, locacaoId)` já existe, mas a tela ainda não tem seletor de locação: "Ver com dados reais" mostra o exemplo.
- Não há rota para listar os arquivados à parte: a lista traz todos, e os arquivados saem esmaecidos, sem ações.
- Esta branch parte da `origin/main` sem a T-376 (PR #405): o `node_modules` desta rodada é o do lock antigo (`vitest` 3). Quando o #405 entrar, nada aqui conflita.

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 77 arquivos, 714 testes passando.
- Testes novos: `lib/contratos.test.ts`, `components/contratos/ModelosDeContrato.test.tsx` (lista, permissão, diálogo de edição, contrato dos modelos) e `lib/api/modelos-contrato.test.ts` (rotas e corpos).
- Os testes rodam em `node`, sem DOM: os diálogos estão cobertos pelo markup e pelo contrato, não por clique. Vale uma passada manual ou do QA a 1440px e 390px.
- Nenhuma tela de Veículos foi tocada.
