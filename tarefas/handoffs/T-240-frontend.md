# T-240 · Bug: cadastrar veículo mostra erro mas grava · frontend → backend, orquestrador, qa

**Causa (dois defeitos que se somam):**
1. **Backend (VEI-06):** `GET /api/veiculos/<id>/` responde 500 `decimal.InvalidOperation [DivisionUndefined]` quando o veículo acabou de ser criado. Em `backend/apps/veiculos/selectors.py:441` (`_pct`), `if not na_frota` só pega `timedelta(0)`; com menos de 1 s na frota o `na_frota` não é zero, mas `int(total_seconds())` vira 0 e `Decimal(0) / Decimal(0)` levanta. Traceback: `views.py:169 get` → `_representacao` → `selectors.representacao:374` → `ocupacao:461` → `_pct:441`. Passado 1 s o mesmo GET devolve 200. Pedido enviado ao Backend (correção: checar os segundos inteiros, não o timedelta, e devolver "0.00"; teste de veículo criado e lido na hora).
2. **Frontend:** `veiculosApi.criar` fazia o `POST` (201, veículo gravado) e depois um `GET` da ficha, dentro do mesmo cadastro. O 500 do GET virava "Não foi possível concluir agora. Tente de novo." no formulário; com o botão liberado, o segundo clique fazia outro POST e a API respondia "placa já cadastrada" (`VEI-01`).

**Como reproduzi:** seed, `rodrigo`, `/veiculos/novo`, formulário preenchido e "Salvar veículo": `POST /api/veiculos/` 201, `GET /api/veiculos/90/` 500, a tela fica em `/veiculos/novo` com o alerta genérico.

**O que foi feito:**
- `frontend/src/lib/api/veiculos.ts`: `criar` devolve o veículo do 201 e não lê mais a ficha (a página da ficha lê a dela, com seus estados de carregando e erro). O formulário só usa `id`, `marca`, `modelo` e `placa`.
- `frontend/src/components/frota/NovoVeiculoForm.tsx`: trava (`useRef`) contra duplo clique: dois cliques antes do primeiro render não criam duas vezes.
- Teste `frontend/src/lib/api/veiculos.test.ts`: POST 201 com GET respondendo 500: o cadastro conclui e só o POST sai. `tsc`, `eslint` e os testes de `lib/api`, `components/frota` e do falso de frota passam.

**O que ficou de fora:**
- O 500 em si é do backend (item 1); até a correção, a ficha aberta em menos de 1 s depois de criar pode mostrar o erro da própria página (ela tem estado de erro). O teste do backend é do Backend.
- Não há etapa de fotos ou documentos no formulário atual, então "etapa depois de criar falhar" só existia nessa leitura da ficha. Teste do clique duplo (precisa de DOM interativo; o Vitest do projeto roda em `node`, sem dependência nova): coberto pela trava, sem teste automatizado.

**Ambiente (pilha giro-integracao):** meus testes criaram os veículos TST1A23 (id 88), TST1A24 (id 89, filial 2) e TST2B34 (id 90) na Moto Rápida; `make seed` os limpa. Nada de migração nesta tarefa.

**Próximo passo para quem recebe:** Backend corrige `_pct`; QA repete o cadastro na tela depois disso.
