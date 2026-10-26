# Prévia do modelo de contrato sem HTML do cliente · 26 out 2026

**Tarefa:** T-388 · **Autor:** seguranca · **Base:** `origin/main` (943c1ca) e a tela da T-363 (PR #407, `origin/t-363-modelos-de-contrato`).
**Pergunta:** a tela põe o HTML de `POST /api/contratos/modelos/{id}/previa/` na página como veio (`PreviaDoModelo.tsx:28`, `dangerouslySetInnerHTML`). Um nome de cliente ou de veículo com `<script>` ou atributo `on*` chega à tela?

## Resposta: não chega. Nenhuma correção obrigatória

A sanitização não roda **depois** de preencher, mas não precisa, porque o caminho é seguro de outro jeito, em duas etapas:

1. **Ao salvar**, o texto do modelo passa por `sanitizacao.limpar` (`nh3`, `apps/contratos/sanitizacao.py:42`), em `criar_modelo`, `editar` e `criar_de_pronto` (`services.py:77-82`, `:98`, `:120`).
   - Ficam só as tags da lista e nenhum atributo, fora `colspan` e `rowspan` com número de 1 a 50.
   - Por isso um marcador nunca fica dentro de um atributo: `colspan="{{cliente.nome}}"` e `title="{{...}}"` saem no salvar.
   - Também nunca fica dentro de uma tag: `<{{veiculo.placa}} onerror=...>` vira texto (`&lt;`).
2. **Ao preencher** (`marcadores.substituir`, `marcadores.py:112-120`), cada valor passa por `html.escape` (com aspas) e cai em contexto de texto.
   - A única exceção é `locacao.parcelas`, uma tabela montada pelo sistema (`locacoes/contrato.py:74-85`). Ela usa só tags da lista e leva o número da parcela (inteiro), a data formatada e o valor escapado.
   - A troca é de uma passada só: um valor com `{{cliente.cpf}}` não é preenchido de novo.

**A tela `/assinar`** não põe HTML do contrato na página: mostra os dados e abre o PDF por link (`AssinarContrato.tsx:105-106`, `rel="noopener noreferrer"`). O PDF sai do WeasyPrint, que não roda script, com o `url_fetcher` restrito ao logo da empresa (S-09, `pdf.py:51`).

**Mais uma camada no navegador:** a CSP (`frontend/src/lib/csp.ts`) tem `script-src` com nonce e `strict-dynamic`, sem `unsafe-inline`. Mesmo que algo escapasse, um `<script>` ou um `onerror` posto pelo `innerHTML` não rodaria.

## Como conferi

Sonda fora do repositório, num contêiner descartável com Postgres próprio na rede de teste. O `giro-backend-pg` não subia: a porta 55432 caiu na faixa que o Windows reservou depois que o Docker reiniciou.
- **Pelo serviço:** um modelo com o marcador no texto, num `colspan`, num `title` e no lugar do nome da tag, preenchido com 5 cargas: `<script>`, `<img onerror>`, `"><svg onload>`, `{{cliente.cpf}}` e `&lt;script&gt;`.
- **Pela API com locação real:** nome do cliente `Ju<script>…<img onerror=…>`, modelo do veículo `CG <svg onload=…>` e a tabela de parcelas, com um texto gravado direto no banco, sem passar pelo salvar.
- **Checagem:** um `HTMLParser` lista as tags e os atributos que o navegador montaria. Em todos os casos, só `p`, `table`, `thead`, `tbody`, `tr`, `th` e `td`, **sem nenhum atributo**. Resultado: 2 passed.
- **Testes de contratos:** `test_t090_contratos.py` e `test_t263_gerar_contrato.py`, 23 passed.

## Achado

### B-01 · baixa · A prévia confia que o texto gravado já está limpo

**Onde:** `services.previa` (`services.py:191-194`) devolve `substituir(ultima.texto, ...)` sem limpar de novo.
**Quando importaria:** só se um texto de modelo entrasse no banco sem passar por `_texto_limpo`, por migração, seed, script de suporte ou um serviço novo que esqueça de chamá-lo. Hoje não existe caminho assim: o Admin é só leitura e os três caminhos de escrita limpam. Mesmo nesse caso, a CSP barraria script e `on*`, mas não barraria HTML visual (um formulário falso, por exemplo) na tela do administrador.
**Correção sugerida para o backend (defesa em profundidade, sem urgência):**
- `previa` devolve `sanitizacao.limpar(marcadores.substituir(...))`. A tabela de parcelas só usa tags da lista e sai igual, e o custo é um `nh3` sobre no máximo 200 mil caracteres.
- Teste `test_s_09_previa_limpa_texto_gravado_sem_sanitizar`: gravar por `ModeloContrato.objects.filter(...).update(texto="<p>{{cliente.nome}}</p><img src=x onerror=alert(1)>")`, chamar a prévia pela API e conferir que o `html` não tem `<img` nem `onerror`. Deve continuar passando `test_modelos_api_lista_marcadores_prontos_e_previa` (`{"html": "<p>Lucas Ferreira</p>"}`).
- O mesmo vale para `versao_texto_html` na geração do contrato, que só vai ao PDF. Lá é opcional.

Nada muda no contrato (`contratos.md` já diz "renderizado e sanitizado") nem na tela da T-363: o PR #407 pode seguir.
