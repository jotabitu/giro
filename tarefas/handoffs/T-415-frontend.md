# T-415 · CRLV-e: escolher a versão (frontend) · frontend → orquestrador

**O que foi feito (na mesma branch e no mesmo PR #463 do backend):**
- `npm run api:gerar`; `dicas.candidatos` (obrigatório) acertado no falso `falso-frota.ts` e em `veiculos.test.ts`, que quebravam o typecheck.
- `PreencherPeloCrlv.tsx`: com `dicas.candidatos` preenchido, a tela mostra "No documento: … Escolha a versão:" e uma lista de botões (44 px, `aria-pressed`) com as versões que a API achou. A escolha chama `aoEscolherVersao`; `NovoVeiculoForm` preenche marca e modelo como a escolha da lista. A marca já vem pela leitura (`campos.marca` em `lidos`). Sem versões (vazio, inclusive acima de 20), a mensagem de sempre manda escolher da lista, com a marca já preenchida e a busca de modelo aberta. Trocar ou remover o CRLV-e limpa a escolha. Nada é calculado na tela; a lista de modelos com apelidos vem da API.
- Falso: arquivo com "cruze" no nome devolve o caso real (marca "GM - Chevrolet", modelo `null`, 8 campos, 3 versões). `VersoesDoCrlv.test.tsx`: o caso do Cruze, a tela com as 3 versões e o CA-247-05 (sem versões).

**O que ficou de fora:** o clique que preenche o formulário não tem teste de interação (o projeto só testa por markup estático); fica para o E2E do QA. Não conferi a 1440 e a 390 px no navegador. Rodei só os testes do que mudou, a suíte inteira fica para o CI.

**Próximo passo para quem recebe:** conferir o CI do #463; QA com o PDF do Cruze (8 campos e 3 versões) e o "SUZUKI/YES 125" (7 campos, sem versões).
