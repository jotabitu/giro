# T-109 · Devolução e acerto · backend → orquestrador, frontend, qa, arquiteto, produto, seguranca

Parte 2 da T-016 original: a devolução e o acerto (CA-016-09 a 14, 16, 17, 19 e 20 de `docs/qa/criterios/T-016.md`). A troca de veículo (CA-016-15) fica com a T-092, e a devolução em dinheiro (CA-016-18) com o caixa da T-017; os dois seguem `xfail`.

**O que foi feito** (`docs/api/vistorias.md`, "Devolução"):

- **Rotas novas:**
  - `POST /api/locacoes/{id}/devolucao/`: só para locação `ativa` ou `devolucao_atrasada` (senão 409 `transicao_locacao`). Responde 201 com a devolução, a vistoria de chegada e o acerto em `rascunho`, ou 200 com a que já existe (`DEV-05`);
  - `GET /api/devolucoes/{id}/`: `{id, status, locacao: {id, codigo, status, cliente, veiculo, no_horario}, vistoria, comparacao, acerto, devolvida_em, concluida_em, recibo_enviado_em}`;
  - `PATCH .../acerto/` (`{forma_devolucao}`), `POST .../acerto/itens/`, `PATCH` e `DELETE .../acerto/itens/{item_id}/`;
  - `POST .../encerrar/`, `GET .../recibo/` e `POST .../recibo/reenviar/` (202).
- **Acerto** (recalculado a cada leitura e mudança enquanto é rascunho; concluído, não muda mais):
  - combustível `calculado` = capacidade do tanque × (nível da saída − nível da chegada) × preço do litro da filial + R$ 10,00 uma vez, só quando falta (`DEV-01`). Sem tanque, sem preço ou sem a vistoria de saída, vira `informado` e guarda o valor que a pessoa der;
  - atraso `calculado` por `locacoes.services.calcular_atraso` no momento da conclusão da chegada (`LOC-10`, `LOC-11`, `FIL-03`); a chegada corrigida (`VIS-04`) refaz o atraso pela hora dela;
  - km excedente sempre 0 (km livre);
  - `parcela_aberta`: uma por parcela da locação em aberto e com vencimento antes do dia da devolução, com `conta_id`. A que vence no próprio dia não entra;
  - `multa_encerramento` e o crédito (`semanas_nao_usadas` no mensal, `dias_nao_usados` na diária) só com o encerramento antecipado aprovado, pelos valores gravados na locação (`LOC-12`, `LOC-13`);
  - um item `avaria` (`informado`, com `avaria_id`) por avaria nova da chegada, com o valor da avaria ou 0. O vistoriador marca a avaria; quem fecha a conta dá o valor no item;
  - caução = soma das contas `caucao` pagas da locação. Saldo = caução + créditos − cobranças. `resultado` traz `tipo` (`devolver`, `cobrar` ou `zerado`), `valor_centavos`, `texto` e `botao` ("Encerrar e devolver R$ 183,00").
- **Encerrar**, numa transação (`DEV-06`):
  - 422 `vistoria_pendente` sem a chegada concluída; 400 em `forma_devolucao` quando há saldo a devolver e nenhuma forma escolhida; 409 `acerto_concluido` depois de encerrado;
  - `financeiro.services.pagar_com_caucao` (nova, da interface do `financeiro.md`): com a caução e os créditos, paga as parcelas em aberto (`forma = caucao`) e cria as cobranças como contas pagas com a caução (`combustivel`, `atraso` e `km_excedente` viram `acerto`, `avaria` vira `avaria`, as multas viram `multa`; origem `devolucao`). O que não couber vira uma conta `acerto` aberta, com vencimento em 3 dias (`DEV-02`);
  - saldo positivo: `Reembolso` `a_fazer` por `financeiro.services.devolver_ao_cliente`, origem `devolucao` e código da locação;
  - `locacoes.services.encerrar(locacao, devolvida_em=...)`, com `devolvida_em` = a conclusão da chegada ajustada pela `LOC-11`: `encerrada`, ou `cancelada` no encerramento antecipado;
  - veículo `alugado` → `em_manutencao` se alguma avaria nova tem "vai para oficina", senão `disponivel` (`DEV-04`); o km da chegada já tinha entrado na conclusão da vistoria;
  - publica `vistorias.devolucao_encerrada(devolucao_id, locacao_id, veiculo_id, avarias_para_oficina)`. Hoje ninguém assina; o app `manutencao` vai abrir a OS por ele;
  - o preço do litro fica gravado na devolução, e mudar o preço depois não muda o acerto (CA-016-10).
- **Recibo:** depois do commit, a tarefa `vistorias_enviar_recibo` (idempotente, 60 s) gera o PDF com WeasyPrint, a marca da locadora e as fotos da chegada, grava no armazenamento privado e manda por WhatsApp o link de 15 minutos com a frase do saldo ("Devolução de R$ 183,00 por Pix em até 1 dia útil."). `GET .../recibo/` gera o PDF se a tarefa ainda não rodou; em rascunho responde 409 `devolucao_em_rascunho`. O recibo usa "devolução" e "caução".
- **Quem pode:** abrir e ver a devolução é de quem faz vistoria (o vistoriador sem `_centavos` e sem `acerto`); itens, forma, encerrar e recibo são de administrador, gerente e vendedor (o vistoriador recebe 403). O financeiro recebe 403 em tudo. Fora da filial, 404.

**Onde:**
- `backend/apps/vistorias/`: `models.py` (`Devolucao`, `ItemAcerto`), migração `0002`, `acerto.py` (contas puras), `services.py`, `selectors.py`, `recibo.py`, `tasks.py`, `api/` e `README.md`.
- `backend/apps/financeiro/services.py`: `Cobranca`, `Acerto` e `pagar_com_caucao`.
- `backend/apps/contratos/`: `selectors.marca_e_host` (veio de `tasks.py`, que agora usa ela) e `pdf.gerar(..., imagens=)`, que entrega ao WeasyPrint só as imagens que quem monta o PDF passou, por endereço interno.
- `backend/config/settings/base.py`: nomes fixos dos enums `FormaDevolucaoEnum` (cancelamento, sem dinheiro) e `FormaDevolucaoAcertoEnum` (acerto). Sem isso, o enum do cancelamento mudava de nome no OpenAPI.
- `docs/api/openapi.yaml` regerado com `--validate`: só acréscimos.

**Testes** (`tests/aceitacao/test_t016_vistorias.py`, com o código da regra no nome): saíram os 10 `xfail` da T-109.
- CA-016-09 (LOC-2836: 3200 + 8500 = 11700, caução 30000, devolve R$ 183,00 por Pix), 10 (níveis, sem tanque ou preço, preço congelado), 11 (−13200 vira conta para 10 out), 12 (19:00 → 0; correção às 19:01 → 5490; 409 `item_calculado`), 13 (parcela de 29940 paga com a caução), 14 (Patrícia: 50000 + 37100 − 8480 = 78620, `cancelada`), 16, 17 (encerrada, km 19.630, Factor `disponivel`, contas, reembolso marcado feito com comprovante, evento, recibo com 6 fotos e WhatsApp), "vai para oficina" → `em_manutencao`, 19, 20, isolamento entre empresas e 404 fora da filial.
- Check com o `rodar.sh` (`--rm`, `POSTGRES_HOST`, imagem `giro-backend:latest`): ruff, `ruff format --check`, mypy e `makemigrations --check` limpos; pytest `567 passed, 3 xfailed` (antes 546 e 13).

**Para o qa:**
- [divergência] O seed de teste não tem o que o critério dá: o preço do litro da Filial Centro (R$ 5,50), a vistoria de saída da LOC-2836 (cheio, 18.402 km; a PNB7C04 está com 21.870 km na frota) e a caução paga da LOC-2841 e da LOC-2812 (a carteira grava `caucao_centavos = 0` e nenhuma conta de caução). O teste grava esses dados na própria fixture. A LOC-2836 vai a 14 out 18:00 por `update`, como na T-016, até a T-105.
- A marca no WhatsApp é a `nome_exibicao` da empresa de teste ("Empresa A"), e não "Moto Rápida".

**Para o arquiteto (diferenças do contrato):**
1. `ItemAcerto.tipo` ganhou `dias_nao_usados` (crédito da diária encerrada antes do fim, `LOC-12`); o modelo de dados só tinha `semanas_nao_usadas`.
2. `ItemAcerto.conta_id` (a parcela em aberto) e, na `Devolucao`, `preco_litro_centavos`, `devolvida_em`, `encerrada_por`, `recibo` e `recibo_enviado_em`.
3. A representação traz a mais `locacao.status`, `acerto.total_creditos_centavos`, `devolvida_em`, `concluida_em`, `recibo_enviado_em` e, em cada item, `avaria_id` e `conta_id` (nulos quando não se aplicam).
4. `POST .../recibo/reenviar/` responde 202 sem corpo; o contrato não dizia.
5. Itens: o `POST` só aceita `avaria` e `multa_transito` (400 nos outros); o item da avaria e o do combustível não se removem (409 `item_da_vistoria`); item que não é do acerto responde 404 `item_nao_encontrado`.
6. O evento `vistorias.devolucao_encerrada` é novo (para a OS do `DEV-04`).
7. A interface `pagar_com_caucao` ficou `(origem, *, filial_id, cliente_id, disponivel_centavos, abertas, cobrancas, vencimento_do_saldo)`, e não `(conta_caucao, cobrancas)`: a caução da locação continua `paga`, e o que ela cobre vira conta paga com `forma = caucao`.

**Para o produto:**
- [decisão] Saldo negativo com parcela em aberto: a caução paga primeiro as parcelas inteiras e depois as cobranças novas; a parcela que não cabe continua em aberto, com o vencimento dela, e só o resto das cobranças vira a conta de 3 dias. A regra não diz a ordem.
- [decisão] A parcela que vence no dia da devolução não entra no acerto ("vencidas e não pagas"); ela continua em aberto na locação encerrada. Vale o mesmo para as parcelas futuras de quem devolve antes do fim sem encerramento antecipado aprovado.

**Para a seguranca:** o recibo fica no armazenamento privado e sai só por URL de 15 minutos. O PDF do recibo usa o mesmo `url_fetcher` fechado do contrato: só o logo e as fotos lidas pelo próprio servidor, por endereço interno; o texto do cadastro passa por `html.escape`. A tarefa recebe só ids. O vistoriador não recebe valores nem o acerto.

**Para o frontend (tela Devolucao: Vistoria → Acerto → Recibo):**
- Vistoria: `POST /api/locacoes/{id}/devolucao/`, depois a vistoria de chegada pelas rotas de vistoria (`fotos`, `avarias`, `PATCH`, `concluir`), com o `vistoria.id` da devolução.
- Acerto: `GET /api/devolucoes/{id}/`; o valor da avaria é um `PATCH` no item; forma por `PATCH .../acerto/`; o botão é `acerto.resultado.botao`. Tudo calculado vem da API.
- Recibo: `GET .../recibo/` e `POST .../recibo/reenviar/`.
- O reembolso a fazer é marcado como feito em `POST /api/financeiro/reembolsos/{id}/feito/`, que ainda não existe (T-017); o teste usa o serviço.

**O que ficou de fora:**
- A OS da avaria que vai para a oficina: o veículo vai para `em_manutencao`, e o evento leva as avarias; o app `manutencao` abre a OS.
- Devolução em dinheiro: `devolver_ao_cliente` recusa (400) até o caixa da T-017 (CA-016-18 em `xfail`).
- Troca de veículo e acerto único (T-092): a devolução já é uma por locação, e a comparação usa a saída do mesmo veículo.
- A `aut_02` ainda pode marcar `devolucao_atrasada` uma locação com a chegada concluída e o acerto aberto (só o status; o atraso do acerto usa a hora da chegada). `locacoes` não lê `vistorias` (ADR 0011).
- Avaria recriada por uma correção da chegada (`VIS-04`) ganha item novo, com o valor da avaria (0 se foi o vistoriador); o valor dado no item antigo não passa para o novo.

**Próximo passo:** o orquestrador abre o PR. A T-111 pode começar (dependia da T-109).
