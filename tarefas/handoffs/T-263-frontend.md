# T-263 · Ação gerar_contrato na locação (tela) · frontend → qa, orquestrador

**O que foi feito:**
- O cartão Contrato de `DetalheDaLocacao` mostra "Enviar contrato" só quando `l.acoes.gerar_contrato` é verdadeiro; a tela não olha mais status, desconto, perfil nem contrato vigente.
- Saiu `podeEnviarContrato` de `src/lib/locacoes.ts` e o teste dele.
- Erros do `POST /api/locacoes/{id}/contrato/` aparecem com a mensagem da API (`mensagemDoErro`), inclusive o 409 `cancelamento_em_curso` ("A locação tem um cancelamento em andamento."). O 422 `IMP-04` continua com o atalho "Publicar um modelo".
- API falsa (`falso-locacoes.ts`): `gerarContrato` agora checa o perfil que cria (não mais `acoes.cancelar`) e recusa com 409 `cancelamento_em_curso`.

**Onde:** `frontend/src/components/locacoes/DetalheDaLocacao.tsx`, `src/lib/locacoes.ts`, `src/testes/falsos/falso-locacoes.ts`.

**Regras cobertas:** IMP-04, APR-01, LOC-12. Testes em `DetalheDaLocacao.test.tsx`: ação `true` mostra o botão e a ordem do cartão, ação `false` não mostra, `contrato_existente` e `cancelamento_em_curso` na API falsa com a mensagem da API.

**O que ficou de fora:** conferência visual em 1440 e 390 px (sem backend no ar); a tela do 409 em tempo real não é coberta por teste de componente (os testes renderizam markup estático).

**Próximo passo:** qa confere o botão no seed (aguardando retirada, com desconto pendente, com cancelamento em curso); orquestrador abre o PR (depende do #345).
