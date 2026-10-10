# T-115 · Regra do extra desativado na renovação · produto → orquestrador, qa, backend

Em 09 out 2026, o dono do produto decidiu a `[decisão]` que o backend levantou na T-111. Ficou a **opção A**: o extra por período desativado no cadastro antes da renovação continua nas locações que já o têm, renovações incluídas, pelo último valor do cadastro. Desativar só tira o extra das locações novas.

**O que foi feito:**

- **`docs/regras-de-negocio.md`:**
  - `LOC-08`: frase nova depois de "O período e os extras (`LOC-02`) saem pelo preço de hoje."
  - Nota de mudança da T-115 no fim da seção Locação.
  - Linha nova em "Decisões de 09 out 2026" ("Extra desativado antes da renovação").
- **`docs/qa/criterios/T-015.md`:** item novo no CA-015-27. Com o capacete extra desativado antes da renovação (último valor 2000), as 2 parcelas novas continuam 32900 + 2000 = 34900 cada.
- **`tarefas/backlog.md`:** a `[decisão]` da T-111 saiu e virou uma linha de registro.

**Por quê:** o extra (capacete, baú) está com o cliente e só volta na devolução. Tirá-lo da cobrança deixaria dias de graça. A renovação não tem onde escolher extras (a API só recebe `periodos` ou `fim_previsto`), e desativar um cadastro não muda o que já existe. O plano especial desativado volta para a tabela porque é um benefício, e o extra é uma cobrança.

**Casos de referência:** nenhum muda. Nenhum extra do seed nem da carteira de outubro é desativado. O CA-015-27 só ganhou um item.

**Código:** o comportamento já existe desde a T-111 (`montar_renovacao` usa o valor atual do cadastro mesmo com `Extra.ativo = False`). Não há mudança de contrato nem de tela.

**Próximo passo para quem recebe:**

- **Orquestrador:** abrir o PR. A T-115 não gera tarefa nova de código.
- **Backend (quando passar pela `locacoes`, sem tarefa própria):** um teste `test_loc_08_ca_015_27_extra_desativado_continua`. Ele desativa o capacete (2000) antes da renovação de 2 semanas da Street e confere as 2 parcelas novas de 34900.
- **QA:** validar o item novo do CA-015-27 com o teste acima.
