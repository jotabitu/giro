# Manutenção (fase 2) · critérios de aceite

**Regras:** MAN-05, VEI-03, AUT-06 · **Contrato:** ainda não escrito · **Seed:** PMZ3E17 (Honda Pop 110i, `em_manutencao`, Filial Centro)

O módulo de manutenção ainda não tem tarefa. Quando tiver, este arquivo passa a se chamar `T-<numero>.md`, e os critérios ganham o número da tarefa. Fuso `America/Sao_Paulo`. O nome do teste leva o código da regra (`test_man_05_...`).

## Concluir a OS (`MAN-05`)

**CA-MAN-01 · Documento vencido durante a OS** (`MAN-05`, `VEI-03`, decisão de 08 out 2026)
PMZ3E17 está `em_manutencao`, com uma OS `na_oficina` (o seed não tem OS para ele; o teste cria). O seguro dele venceu em 25 out, e a `AUT-06` das 07:00 desse dia só gerou a tarefa urgente aos gerentes (CA-013-28).
- Concluir a OS em 27 out → a OS vai para `concluida`, e o veículo vai para `indisponivel`, com motivo "Seguro vencido" e origem `documento`, e não para `disponivel`. A despesa da OS e o km saem como num fim de OS normal.
- Com o CRLV e o seguro vencidos, o motivo cita os dois documentos.
- O evento de auditoria da transição `em_manutencao` → `indisponivel` cita a `MAN-05`.
- Enviar o seguro novo → 201, e o veículo continua `indisponivel` (CA-013-19). `desbloquear` → 200, `disponivel`.
- Com os documentos em dia, concluir a OS → `disponivel`, como antes.
- IPVA ou rastreador vencidos não mudam o destino: o veículo vai para `disponivel`.
