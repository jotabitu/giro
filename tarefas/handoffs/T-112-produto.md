# T-112 · Estado do QXA-4B21 nas telas de referência · produto → orquestrador, design-system, frontend, arquiteto

**O que foi feito:** defini o estado do QXA-4B21 no dia de referência (07 out) a partir das regras e do seed, sem regra nova e sem `[decisão]`. Ficou registrado no caso "Estado do QXA-4B21 em 07 out" dos dados de referência, com nota de mudança (T-112). As telas, os contratos e os dados falsos que discordam estão no backlog, em "Levantadas pelo produto em T-112".

**Estado em 07 out:**

| Campo | Valor | De onde vem |
| --- | --- | --- |
| Veículo | Honda CG 160 Fan 2023, vermelha, chassi 9C2KC2210PR004401, Street, Filial Centro | seed (`backend/tests/aceitacao/frota.py`) |
| Situação | `alugado`, rótulo "Alugado", tom `solido`, sem alerta | `docs/api/veiculos.md`: "Atrasado" só com a locação em `devolucao_atrasada` |
| Km | 18.950, atualizado 23 set (vistoria de saída da LOC-2841) | `VEI-02`: km só muda em vistoria ou OS |
| Locação | LOC-2841, Carlos Menezes, semanal R$ 299,40, `ativa`, "Em andamento", de 23 set 09:00 a 28 out 09:00; sinal `pagamento_atrasado` (parcela 2 de 30 set) | caso "Preço antigo LOC-2841", carteira de outubro |
| Devolução | prevista em 28 out 09:00; atraso só depois de 28 out 10:00 | `LOC-10` |
| Próxima manutenção | troca de óleo aos 19.900 km (faltam 950); a última foi aos 18.900 km | `MAN-03` (a cada 1.000 km) |

Em 07 out o QXA-4B21 não entra em "Devoluções da semana" nem na agenda do vistoriador. A única devolução atrasada do seed é a LOC-2790 (Rafael).

**Para quem:**
- **design-system (T-028):** `Frota` (Desktop e Mobile), `Veiculo` (Desktop e Mobile), `Main`, `Vistoriador` (Desktop e Mobile) e `Manutencao-Desktop` (OS-119). Lista campo a campo no backlog. Na ficha, a LOC-2702 precisa terminar até 12 set (hoje vai a 29 set e cruza com a LOC-2841), e o Renavam 01289934410 é o da SAK1D39.
- **frontend:** `falso-frota.ts` passa a "Alugado" (`solido`) com a LOC-2841 de 23 set a 28 out; `falso-painel.ts` tira a LOC-2841 das devoluções da semana e da agenda.
- **arquiteto:** exemplos de `docs/api/painel.md` (`devolucoes_semana`) e `docs/api/vistorias.md` (agenda) trocam a LOC-2841 atrasada pela LOC-2790.

**Onde:** `docs/regras-de-negocio.md` (caso novo em "Dados de referência para testes" e nota de mudança T-112), `tarefas/backlog.md` (divergências da T-112).

**Regras cobertas:** `VEI-01`, `VEI-02`, `LOC-06`, `LOC-10`, `MAN-03`.

**Check:** só documentação. Datas: 07 out 2026 é quarta, 28 out também (21 dias depois). 23 set + 5 semanas = 28 out. 19.900 − 18.950 = 950 km. O seed (`frota.py`, `carteira.py`) já tem esse estado, então o backend e o qa não mudam.

**Leitura minha (pode contestar):** a OS-119 automática com 950 km faltando contraria a `MAN-03` (cria quando faltam 500). Tratei como erro da tela, não da regra.
