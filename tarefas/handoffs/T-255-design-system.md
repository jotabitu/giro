# T-255 · Telas de movimentação pelas regras da T-246 · design-system → frontend, arquiteto

**O que foi feito:** as cinco telas de movimentação (`Movimentacoes-Desktop/Mobile`, `Movimentacao-Nova-Desktop/Mobile`, `Movimentacao-Chegada-Mobile`) agora seguem `MOV-01` a `MOV-06` e usam só o seed de 07 out. A branch é empilhada sobre `t-246-regras-movimentacoes`.

**O que mudou, ponto a ponto (o que o Produto deixou para o design-system):**
- **Menu e contadores:** as telas de desktop usam o menu da `Frota` da `main` (86, 42, 2, 1...), no lugar dos contadores antigos.
- **Placas e modelos:** só SAK-1D39 (Honda CG 160 Fan, disponível) e PMZ-3E17 (Honda Pop 110i, em manutenção). Saíram SBM-3T03, QYC-4D72, PNB-9A11 e o RHT-9F02 (que é Kwid reservado e não se movimenta, `MOV-03`).
- **Origem:** sempre a Filial Centro (`MOV-01`); o "Pátio Maraponga" saiu.
- **Destino:** sempre uma filial (campo "Filial de destino"; "Filial ou local" saiu). Transferência vai para a Filial Caucaia, de exemplo.
- **OS:** a parada de oficina cita a OS (`OS-118`, o código-exemplo da `MAN-05`; o número real vem da API) e não gera despesa; o campo "Valor" some nessa parada. A OS-0193 saiu.
- **Quadro (dia 07 out):** Agendadas 1 (MOV-0003, Pop 110i, oficina, amanhã 08:00, "Iniciar"), Em trânsito 1 (MOV-0002, CG 160 Fan, lava-jato e Filial Caucaia, "Registrar chegada"), No local 0, Concluídas 1 (MOV-0001, lavagem de R$ 35,00, CA-246-01 a 03). O texto "Arraste um cartão" saiu: a movimentação muda de coluna pelo botão, não se cancela depois de sair, e só a agendada se cancela (estados e transições da seção).
- **Nova movimentação (MOV-0003):** Pop 110i em manutenção, agendada para 08 out 08:00 (campos Dia e Hora), quem leva é usuário da Filial Centro, vistoria rápida opcional na volta à mesma filial, rodapé com "continua em manutenção e a parada não gera despesa" (CA-246-07). O campo "Motivo" saiu: as regras não o definem.
- **Registrar chegada (MOV-0002):** CG 160 Fan, km 3.146 sobre 3.120 (não pode diminuir, `VEI-01`), combustível e 4 fotos obrigatórios na transferência (a tela mostra 2 de 4 e a nota "Faltam combustível e 2 fotos"), "Recebido por" um usuário da Filial Caucaia, e a lavagem de R$ 35,00 aparece como "despesa lançada": o valor se confirma ao sair da parada, não na chegada (`MOV-04`). Ao confirmar, o veículo passa a ser da Caucaia e fica disponível (`MOV-05`, `MOV-06`).

**Checagens:** as cinco telas renderizadas em Chromium (1440 e 390 px) e lidas lado a lado com as regras; links entre elas resolvem; sem emoji nem exclamação; sem token novo; índice de `docs/telas/README.md` com as regras `MOV-*` e a nota de fase 2.

**Regras cobertas:** MOV-01 a MOV-06, VEI-01, VEI-04, FIN-06, MAN-05 (critérios CA-246-01 a 03, 05, 07, 09, 11).

**O que ficou de fora:**
- Tela da parada (chegada e saída do local de apoio, com valor, nota e OS): a `MOV-04` a exige e não existe referência. Registrado como `[divergência]`; precisa de decisão do produto sobre a fase 2.
- Blocos de movimentação da ficha do veículo (`Veiculo-*`): trazem origem "Pátio Maraponga", a OS-0181 e um QXA-4B21 alugado em movimentação; ficam para a T-242 (`[divergência]` no backlog).
- Estados de erro (409 de Iniciar com o veículo reservado no meio, `CA-246-05`) e a tela de "Transferir" da ficha (`MOV-06`, fase 2): sem desenho ainda.

**Próximo passo para quem recebe:** o arquiteto escreve o contrato de movimentações com os estados, as transições e o 409; o frontend só liga as telas na fase 2, com `acoes` da API decidindo quais botões aparecem (Iniciar, Registrar chegada, Cancelar), sem regra de perfil na tela.
