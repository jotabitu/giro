# T-016 · Vistoria de saída e devolução com acerto (parte 1: vistoria e agenda) · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca

A tarefa foi dividida em 09 out, e o orquestrador leva a divisão ao dono. Este PR é a parte 1: a vistoria de saída e de chegada como entidade, a agenda e as avarias abertas (CA-016-01 a 08 e 21). A devolução e o acerto (CA-016-09 a 14, 16, 17, 19 e 20) ficam com a "T-016 parte 2". A troca de veículo (CA-016-15) fica com a T-092, e a devolução em dinheiro (CA-016-18) com o caixa da T-017.

**O que foi feito** (`docs/api/vistorias.md`):

- **App `vistorias`:**
  - `POST /api/locacoes/{id}/vistorias/` com `{tipo: "saida"}`. Só vale para a locação `aguardando_retirada`; nos outros estados, 409 `transicao_locacao`. Responde 201 com a vistoria em `rascunho`, ou 200 com o rascunho que já existe;
  - `GET` e `PATCH /api/vistorias/{id}/`. O `PATCH` recebe `{km?, combustivel?, itens?: [{codigo, ok, observacao?}], observacoes?}`, e "Salvar e continuar depois" é só ele (`DEV-05`);
  - `POST .../fotos/` (multipart: `posicao` e `arquivo`), `POST .../avarias/` e `DELETE .../avarias/{avaria_id}/`;
  - `POST .../concluir/` e `POST .../corrigir/` (`{motivo}`);
  - `GET /api/vistorias/agenda/?dia=hoje|amanha|semana` e `GET /api/vistorias/avarias/?veiculo=`.
- **Criar (`VIS-02`):** a lista do ramo, com pneus e freios, luzes e buzina, retrovisores, documento e chave e acessórios entregues. Os extras da locação entram como itens ("Capacete extra"). As avarias abertas do veículo vêm com `preexistente: true` e a frase "não será cobrado do cliente na devolução".
- **Concluir:** responde 422 com **todas** as pendências em `detalhes.pendencias`, cada uma `{codigo, mensagem, ...}`:
  - `VIS-01`, com `faltam`;
  - `VIS-02`, com `itens`;
  - `VIS-03`;
  - `km_nao_informado`;
  - `VEI-01`, com `km_atual` e `corrigir_km` (o link da rota);
  - só na saída nova: `CLI-03`, `CLI-02` e `CLI-05` (de `impedimentos_para_retirada`) e `VEI-03`.
  - O `codigo` e a `mensagem` do 422 são os da primeira pendência; com mais de uma, a mensagem é "Resolva as N pendências antes de concluir". Os detalhes de cada pendência também sobem para `detalhes`: a recusa da retirada sai como `{codigo: "VEI-03", detalhes: {documentos: ["crlv", "seguro"]}}`, com a mensagem "Renove o CRLV vencido antes da retirada." (CA-016-21).
- **Efeitos da conclusão**, numa transação só:
  - a vistoria fica `concluida` e não se edita mais (409 `vistoria_concluida`);
  - o km do veículo é atualizado pela leitura de origem `vistoria` (`VEI-02`); com o km igual ao atual, não grava leitura nova;
  - a saída chama `locacoes.services.registrar_vistoria_saida(locacao, km=, concluida_em=)`, e a locação fica `ativa` com o contrato e o 1º pagamento;
  - a auditoria grava `vistoria.concluir_saida` ou `vistoria.concluir_devolucao`.
- **Correção (`VIS-04`):** só o administrador e o gerente; os outros recebem 403. A correção é uma vistoria nova em `rascunho`, com `substitui`, `motivo_correcao`, os dados, as fotos (o mesmo arquivo) e as avarias copiados. Concluída, ela passa a ser a vigente; a anterior fica `vigente: false` e guardada, e não se corrige mais (409). A auditoria grava `vistoria.corrigir` e `vistoria.substituir`, com o motivo.
- **Fotos (`AUD-05`):**
  - aceita JPG ou PNG até 10 MB; PDF ou arquivo maior respondem 400;
  - a foto é reprocessada por `comum.arquivos.sem_metadados`, e o GPS do EXIF não fica gravado;
  - a URL vale 15 minutos e muda a cada `GET`;
  - a nova foto de posição fixa deixa a anterior inativa e guardada.
- **Avarias:**
  - na saída, a avaria é sempre preexistente, sem valor e sem oficina; na chegada, tem `valor_centavos` (o vistoriador recebe 400 se informar) e `vai_para_oficina`;
  - a foto da avaria é obrigatória e tem de ser da mesma vistoria;
  - a avaria aberta fecha com `resolvida_em`, que a OS da manutenção vai preencher.
- **Agenda (`VIS-05`):**
  - traz as retiradas das locações `aguardando_retirada` e as devoluções previstas (fim no período, mais as `devolucao_atrasada`, exceto em `amanha`) da filial, em ordem de horário;
  - a filial é a do `X-Filial` ou a única da pessoa; com "Todas as filiais", 400;
  - a `situacao` é `concluida`, `em_andamento` (rascunho), `atrasada` (passou do horário), `hoje` ou `agendada`, e a `acao` é `iniciar`, `continuar` ou `abrir`;
  - também traz `resumo` ("Quarta, 07 out · 1 saída e 1 devolução"), `proxima` e `avarias_abertas`.
- **Quem pode:** administrador, gerente, vendedor e vistoriador. O financeiro recebe 403. O vistoriador não recebe nenhum `_centavos` nem o bloco `acerto`; os valores saem depois do serializer.
- **`veiculos.services.documento_vencido(tipos, antes=...)`:** ganhou o texto do que espera a renovação ("da retirada"). O padrão continua "de desbloquear o veículo".
- **`GIRO_MODULOS_ATIVOS`:** `vistorias` entrou no padrão. Os itens "Vistorias de hoje" e "Avarias abertas" do menu passam a aparecer para quem faz vistoria.

**Onde:**
- `backend/apps/vistorias/`: `models.py`, `services.py`, `selectors.py`, `api/` (serializers, views e urls), a migração `0001` e o `README.md`.
- `backend/apps/veiculos/services.py`, `config/urls.py`, `config/settings/base.py` e `docs/api/openapi.yaml`.
- `tarefas/backlog.md`: a divergência abaixo.

**Testes** (`tests/aceitacao/test_t016_vistorias.py`):
- 18 testes passam, todos com o código da regra no nome. Cobrem do CA-016-01 ao 08 e o 21, o financeiro sem vistoria, a saída de locação cancelada (409), as avarias abertas, o 404 fora da filial e o isolamento entre empresas.
- 12 ficam `xfail`: 10 com "T-016 parte 2" (09 a 14, 16, 17, 19 e 20), o CA-016-15 com a T-092 e o CA-016-18 com a T-017.

**Check** (rodei com o `rodar.sh`, com `--rm` e `POSTGRES_HOST`, na imagem `giro-backend:latest`):
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `546 passed, 13 xfailed`. Antes eram 528 passed e 1 xfailed: são 18 testes novos e 12 xfail novos.
- O OpenAPI foi regerado com `--validate`, sem aviso e só com acréscimos.

**Para o qa:** [divergência] A carteira de outubro traz a LOC-2856 `ativa` desde 07 out 09:00, mas o CA-016-08 a quer `aguardando_retirada`, com retirada às 09:15. O teste da agenda tira a LOC-2856 da carteira e cria a do critério. A LOC-2836 vai a 14 out 18:00 só dentro do teste, por `update`, até a T-105.

**Para o arquiteto (diferenças do contrato):**
1. Rotas a mais: `GET /api/vistorias/{id}/`, para reabrir o rascunho.
2. Campos a mais na vistoria: `substitui`, `motivo_correcao` e `vigente`. As avarias trazem também `vai_para_oficina` e `valor_centavos`, e o item da agenda traz `tipo`.
3. O 422 da conclusão leva o código da primeira pendência e os detalhes de todas. O km que falta é `km_nao_informado`.
4. `Vistoria.vigente` (bool) é o "não substituída" do modelo de dados, com as restrições `uma_vistoria_vigente` e `um_rascunho_de_vistoria`.
5. `Avaria.ordem_servico_id` fica sem FK enquanto o app `manutencao` não existe. `FotoVistoria` é ativável e tem `tirada_em` e `por`.
6. A correção que já está aberta volta com 200. A correção da saída depois da retirada não chama `registrar_vistoria_saida`: a locação já está `ativa`.
7. `GET /api/vistorias/avarias/` devolve `{resultados}` sem paginação e só as abertas.

**Para a seguranca:** as fotos usam o armazenamento privado e saem sem metadados. A auditoria das vistorias guarda o caminho do arquivo, nunca o conteúdo. O vistoriador não recebe valores, e as rotas usam `com_padrao` e o escopo de filial (404 fora dele).

**Para o frontend:**
- **Vistoria (saída):** `POST .../vistorias/`, depois `fotos`, `PATCH` e `concluir`. No 422, mostrar `detalhes.pendencias`; a do `VEI-01` traz o link de Corrigir km.
- **Vistoriador:** a agenda e as avarias abertas.
- A chegada (devolução) chega na parte 2.

**Próximo passo:**
- O orquestrador abre o PR.
- Na parte 2: `POST /api/locacoes/{id}/devolucao/` cria a chegada por `services.criar(locacao, "devolucao", usuario)`. Também entram o acerto (com `calcular_atraso`, `multa_encerramento_centavos` e `credito_encerramento_centavos`), o encerramento (com `locacoes.services.encerrar`) e o recibo.
