# T-259 · Cartão do ramo em Configurações · arquiteto → orquestrador, backend, frontend, design-system

**O que foi feito:** o contrato do cartão "O que a empresa faz" e a rota da tela `Admin-Ramo`, que resolvem a divergência (1) da T-253, e a seção da T-257 no backlog. Branch `t-259-cartao-ramo`, a partir da `origin/main`. Só documentos, sem teste para rodar.

**Onde:**
- `docs/api/configuracoes.md`:
  - cartão `ramo`, "O que a empresa faz", logo depois de `marca`;
  - o resumo é montado pela API a partir do ramo guardado: "{atividades} · {tipos}", com "Locação", "Venda" ou "Locação e venda" e "motos", "carros" ou "motos e carros". No seed, "Locação e venda · motos";
  - o cartão vem quando o app `empresas` está ativo, como o `marca`, e não vem para o token de suporte, porque a tela só troca o ramo e a escrita do suporte é 403 `PLT-07`;
  - a fonte é `empresas.selectors.configuracao()`, que já existe;
  - rota `/admin/ramo` na tabela de rotas, e casos novos de teste.
- `docs/api/empresas.md`: a troca do ramo aponta para a tela `Admin-Ramo`, a rota e o cartão.
- `docs/telas/README.md`: `ramo` → `/admin/ramo` na tabela "Rotas dos cartões de Configurações". A proposta `(empresa)/admin/ramo` da T-253 está confirmada.
- `tarefas/backlog.md`:
  - seção da T-259;
  - seção da T-257 (catálogo de marcas e modelos): o que o contrato do PR #250 já diz, mais o desenho (CSV versionado, comando de atualização, `achar_modelo`) e o Pronto quando para o backend.
- `tarefas/feito.md` (PR a abrir).

**Regras cobertas:** PLT-12; VEI-08 (na T-257).

**O que ficou de fora:**
- O backend do cartão não tem número. Proposta: entrar na T-196 (módulos por plano e ramo, ainda aberta), ou ir numa tarefa pequena junto do frontend da `Admin-Ramo`.
- A referência `Config-*` da T-253 mostra o texto fixo "Locação, venda e tipos de veículo". O contrato manda o texto da API, e o design-system pode trocar a referência na próxima passada.
- As divergências (2) a (4) da T-253 não são do arquiteto (produto e design-system).
- A T-257 depende do #250 mesclado. O conteúdo completo da tabela FIPE fica com quem a tiver; o CSV inicial só precisa dos modelos do seed e dos arquivos de teste.

**Próximo passo para quem recebe:**
- **Backend:** o cartão em `relatorios/configuracoes.py` (texto puro, testado com os casos da tabela) e no seletor. O limite de 10 consultas continua.
- **Frontend:** `ramo` → `/admin/ramo`; o resumo como vem.
- **Orquestrador:** numerar o backend do cartão e abrir o PR.
