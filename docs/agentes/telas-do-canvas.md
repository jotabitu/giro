# Telas do canvas: importação e fidelidade

As telas são desenhadas e ajustadas no canvas do Claude Design (link em `docs/telas/README.md`). Os agentes só trabalham com o que está em `docs/telas/html`. Este documento diz como uma tela passa do canvas para o repositório e o quanto a página do app precisa seguir a tela.

## Fonte da verdade

- **Vale a tela do repositório**, na `develop`. O canvas é onde se desenha; o que está só nele não existe para os agentes.
- Print, link do canvas ou descrição de tela mandada por mensagem não substitui a importação. O agente que receber uma dessas pede a importação ao orquestrador e não implementa a partir dela.
- Quando a tela e `docs/regras-de-negocio.md` divergirem, vale a regra (`CLAUDE.md`).

## Quando o dono muda algo no canvas

1. O dono avisa o orquestrador quais telas mudaram ou nasceram (nome da tela no canvas basta).
2. O orquestrador abre uma tarefa de importação no quadro, `T-<numero> · Telas vindas do canvas: <assunto>`, para o design-system ou para ele mesmo, e lista as telas.
3. A importação segue os passos abaixo, numa branch `t-<numero>-telas-<slug>` a partir da `origin/develop`, com PR para a `develop` como qualquer tarefa.
4. Se a mudança afeta uma página que já existe no app, o orquestrador abre a tarefa de frontend que leva a página à tela nova. A tela importada sozinha não muda o app.

## Passos da importação

1. Ler o canvas e comparar com `docs/telas/html` tela a tela. Entra só o que é novo ou mudou.
2. Pôr o cabeçalho do repositório: `../../design-system/wl-theme.css` e `../../design-system/components/bundle.css`, sem estilo que repita token.
3. Trocar dados por dados do seed Moto Rápida ou fictícios (CNPJ, nomes, placas, valores). Nenhum dado pessoal real, o repositório é público.
4. Conferir textos e números com as regras. Divergência vira item `[decisão]` em `tarefas/backlog.md` e aviso ao **produto**; a tela entra com a versão da regra.
5. Carimbar a origem na linha logo abaixo do `<!doctype html>`:
   `<!-- origem: canvas, 29/10/2026, T-424 -->`
6. Atualizar o índice em `docs/telas/README.md` (tabela do módulo e "Última importação do canvas").
7. Commit `docs(telas): <assunto> [REGRA-NN] [T-NNN]`, com as telas que entraram e as que ficaram de fora no corpo.

## Tela ajustada no repositório

Ajuste feito direto no repositório (por regra, por contrato ou por revisão) também ganha carimbo, abaixo do de origem:

`<!-- ajustada no repositório: 21/10/2026, T-358 -->`

Na importação seguinte, uma tela do canvas mais antiga que o último ajuste do repositório não substitui a do repositório: o design-system leva a mudança do canvas para a tela do repositório à mão, sem perder o ajuste, ou ela fica de fora e vai para o backlog. Telas sem carimbo são anteriores a este fluxo; na dúvida, vale a do repositório (foi o caso das telas da locadora na T-409).

Para evitar o problema na origem, o dono pode pedir ao design-system a lista das telas ajustadas desde a última importação e repetir esses ajustes no canvas antes de desenhar em cima delas.

## O quanto a página segue a tela

**Obrigatório**, nos dois tamanhos (1440 e 390 px):

- textos, rótulos, títulos e mensagens, palavra por palavra;
- ordem dos campos, das colunas e dos blocos, e a hierarquia (o que é título, o que é ação principal);
- estados que a tela mostra (vazio, carregando, erro, aprovação pendente, só leitura);
- componentes do design system equivalentes aos da tela, com os tokens de cor, espaçamento, raio e tipografia.

**Não é obrigatório:**

- os números de exemplo (os reais vêm da API);
- o pixel exato: a página é recriada com os componentes de `frontend/src/design-system`, não copiada do HTML;
- o que a regra contradiz.

Se a tela pede algo que nenhum componente faz, o frontend pede ao design-system em vez de improvisar. Se a página não consegue seguir a tela por um motivo técnico, o handoff diz o que ficou diferente e por quê.

## Conferência lado a lado

- O frontend entrega, no handoff de toda tarefa que cria ou muda página, as capturas da tela de referência e da página a 1440 e 390 px, lado a lado, com o que ficou diferente.
- O design-system revisa essas capturas antes do merge. O orquestrador não mescla PR de página sem essa revisão.
- Uma conferência automática (captura da referência e da página pelo Playwright) está no backlog para a fase 2.

## Claude Design

O Claude Design avulso (claude.ai/design) fecha em 14 dez 2026 e passou a funcionar dentro do Claude. Antes de desenhar em outro lugar, o canvas atual deve ter sido importado por inteiro, para não perder o que só está nele.
