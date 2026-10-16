# T-301 · Tela da parada e acertos da Nova movimentação · design-system → frontend, orquestrador

**O que foi feito:**
- (a) Tela da parada no local de apoio (`MOV-04`, `MOV-02`), em três arquivos: **Chegada na parada** (celular; só o botão "Cheguei ao <local>", a hora fica registrada) e **Saída da parada** (desktop e celular; "Valor pago" com a dica "Confira com o recibo. Previsto na criação: R$ 35,00", "Nota" opcional com foto ou PDF até 10 MB, aviso da despesa, "Confirmar saída"). No desktop a saída abre em gaveta de 520 px sobre o quadro, a partir do botão "Registrar saída" do cartão em "No local de apoio". O texto avisa que valor acima de zero lança despesa do veículo (categoria Outros, vencimento hoje, aprovação acima do limite da empresa), que valor zero não lança e que a nota pode ser anexada depois em Despesas ("sem nota").
- (b) `Movimentacao-Nova-Desktop` e `-Mobile`: a parada de oficina saiu de "Serviço · Da OS" e "Ordem de serviço OS-118". Agora tem o campo Serviço (texto) e "Valor previsto", como o contrato (`paradas[]`: `local_id`, `servico`, `valor_previsto_centavos`, `categoria`). O aviso do rodapé deixou de dizer "a parada não gera despesa: o custo é o da OS".
- (c) O código `MOV-0003` saiu do cabeçalho da Nova movimentação (a API só devolve o código no `201`); no lugar, "Sai da Filial Centro".
- Quadro: `docs/telas/README.md` com as duas linhas novas e o parágrafo das telas de movimentação atualizado; as duas `[divergência]` (Parada da T-255 e a da OS da T-286) saíram do `backlog.md`.

**Onde:** `docs/telas/html/Movimentacao-Parada-Chegada-Mobile.dc.html`, `Movimentacao-Parada-Mobile.dc.html`, `Movimentacao-Parada-Desktop.dc.html`; `Movimentacao-Nova-Desktop.dc.html`, `Movimentacao-Nova-Mobile.dc.html`; `docs/telas/README.md`.
**Contrato:** `docs/api/movimentacoes.md`: `POST /api/movimentacoes/{id}/paradas/{parada_id}/chegada/` (`acoes.chegar_parada`) e `.../saida/` (`multipart`: `valor_pago_centavos` ≥ 0, `nota?`; `acoes.sair_parada`). ADR 0028.
**Regras cobertas:** MOV-02 (quem registra: quem leva, gerente, administrador), MOV-03 (status do veículo não muda na parada), MOV-04 (valor pago, nota, despesa, sem OS no MVP). Valores de exemplo: MOV-0002, SAK-1D39, Lava Rápido Aldeota, R$ 35,00 (os do contrato e do seed).

**O que ficou de fora:**
- Rota e nome da página da parada são propostas (`(empresa)/veiculos/movimentacoes/[id]/parada`); o frontend decide, e pode ser uma gaveta ou tela só para `no_local`.
- Valor previsto vem preenchido do `valor_previsto_centavos` da parada; a tela não calcula diferença entre previsto e pago.
- Os cartões do quadro (`Movimentacoes-*`) não ganharam os botões "Cheguei na parada" e "Registrar saída" nos arquivos antigos; só a tela nova do desktop os mostra, em "No local de apoio". Os botões devem seguir `acoes` da API.
- Verificação visual feita no Chromium headless (390 px e 1600 px), sem dois temas; usa só tokens existentes (`ups` e `now-card` são classes locais da página, sem token novo).

**Próximo passo para quem recebe:** frontend (T-289, na ligação com a API): montar a parada pelas três telas, com `acoes.chegar_parada` e `acoes.sair_parada` no cartão; na saída, enviar `multipart` com o valor em centavos e a nota. Seguir também o ajuste da Nova movimentação: serviço e valor previsto, sem OS e sem o código antes do `201`.
