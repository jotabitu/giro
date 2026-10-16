# T-267 · Ficha do veículo de referência pelas regras · design-system → frontend (T-242)

**O que foi feito:** `Veiculo-Desktop` e `Veiculo-Mobile` agora seguem o "Estado do QXA-4B21 em 07 out" das regras e as `MOV-01` a `MOV-06`. Branch empilhada sobre `t-255-telas-movimentacao` (que traz a `t-246`).

**O que mudou, ponto a ponto:**
- **LOC-2841:** de 23 set a 28 out (era 30 set a 04 nov): selo "Alugada desde 23 set", período, linha da tabela de locações e "Devolve 28 out" no celular.
- **Vistoria de saída e km:** 23 set (era 30 set), nos dois textos de fotos e avarias, na avaria 2 e no cartão "Km atual" (18.950, "atualizado 23 set").
- **Chassi:** 9C2KC2210PR004401 (era ...4417).
- **Troca de óleo:** última aos 18.900 km (era 17.900; desktop e celular). O intervalo passou de 2.000 para 1.000 km (`MAN-03`), a barra de progresso de 52% para 5% (50 km de 1.000) e o texto "abre uma OS sozinha" para "faltando 500 km, abre uma OS agendada para a devolução". A próxima (19.900 km, faltam 950) não mudou.
- **Movimentações:** o bloco diz "Nenhuma movimentação" (veículo alugado não se movimenta, `MOV-03`). Saíram o "Pátio Maraponga → Centro" (`MOV-01`), a OS-0181, a lavagem de 29 set com a LOC-2841 e o "7 no ano". No desktop, o botão "Movimentar" fica desativado com a dica "Veículo alugado não se movimenta."
- **LOC-2702:** passou a terminar em 22 set, para não cruzar com a LOC-2841 (era até 29 set).

**Regras cobertas:** VEI-01, VEI-02, LOC-06, MAN-03, MOV-01, MOV-03.

**O que ficou de fora (fora do pedido; as regras não trazem o dado, então não mexi):**
- "Rendeu no ano R$ 9.870", "Ocupação 86%", "Custo de manutenção R$ 353", "14 locações", os valores e datas das manutenções antigas (pastilha, revisão 15 mil), o nome do vistoriador, Renavam, compra, FIPE, documentos e rastreador: dados de exemplo sem origem no seed. Na T-242, o frontend mostra o que a API manda; o que a API não manda vira pedido ao arquiteto.
- "Preço de hoje: Semanal R$ 329,00" ao lado da LOC-2841 a R$ 299,40: bate com o caso "Preço antigo LOC-2841", e não alterei.
- Na ficha de um veículo disponível (SAK-1D39, PMZ-3E17), o bloco Movimentações e o botão Movimentar ativo seguem os critérios da T-246; não há ficha de referência desenhada para esse caso.
- Render em navegador: conferi só por leitura do HTML (textos e contas); a estrutura das seções não mudou.

**Próximo passo para quem recebe:** o frontend copia as duas fichas na T-242 com os dados da API; o botão Movimentar e o bloco Movimentações dependem do status do veículo (`acoes` da API, sem regra de status na tela).
