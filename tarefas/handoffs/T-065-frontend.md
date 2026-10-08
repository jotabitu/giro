# T-065 · Login trata o 401 e o 429 da T-058 · frontend → orquestrador, qa, backend (T-011)

**O que foi feito (`docs/api/plataforma.md`, `docs/api/contas.md`):**
- `mensagemDoErro` (`lib/erros.ts`) trata os dois 429: bloqueio (`PLT-08`, `USR-06`) mostra a mensagem da API e "Você pode tentar de novo às 14:32." (horário de Brasília, de `detalhes.tentar_de_novo_em`); `muitas_requisicoes` mostra "Muitas tentativas seguidas. Espere 42 segundos e tente de novo." (`tentar_de_novo_em_segundos`, arredondado para cima; passa de 60 s vira minutos). Sem o detalhe, vale a mensagem da API.
- 401 `credenciais_invalidas` já aparece como a API manda, sem dizer qual dado errou. Quem tem autenticador e não manda código recebe esse 401 só na tela da plataforma, e o frontend ainda não tem login dela; o login da empresa manda o código na segunda etapa, então nada muda.
- Dados falsos (`falso.ts`): 5 erros seguidos viram 429 de bloqueio com horário; mais de 10 entradas por minuto por e-mail viram 429 `muitas_requisicoes` com segundos.
- Todas as telas de acesso passam por `mensagemDoErro` (entrar, código, convite, esqueci/redefinir), então o texto vale em todas.

**Onde:** `frontend/src/lib/erros.ts`, `erros.test.ts`, `lib/api/falso.ts`.
**Check:** `eslint`, `tsc --noEmit`, 120 testes e `next build` verdes. Não abri o navegador.
**Dependências novas:** nenhuma.

**O que ficou de fora:**
- Tela de login da plataforma (`Plat-Login`): não existe no frontend; entra com a tarefa da plataforma e já usa `mensagemDoErro`.
- O falso usa a mensagem de senha do `USR-06` ("5 tentativas erradas"); a de "5 senhas erradas" da `PLT-08` vem da API real.
- Botão de entrar não fica desabilitado durante a espera; a tela só mostra o aviso.
