# Como reproduzir o acerto da LOC-2836 (R$ 183,00)

Caso de referência (`DEV-02`, `DEV-03`; "Dados de referência para testes", linha "Acerto da devolução LOC-2836"): caução R$ 300,00, combustível R$ 32,00 e retrovisor R$ 85,00 dão **devolver R$ 183,00**.

O acerto só fecha com a devolução no dia do fim previsto (14 out 2026, 18:00; `DEV-07`, `LOC-10`). O sistema usa o relógio real depois do seed, então há três caminhos. Escolha pelo que você quer provar.

## 1. Teste automatizado (vale hoje, qualquer dia)

O relógio do teste é trocado pela fixture `relogio`, que põe o "agora" em 14 out 17:40:

```
pytest backend/tests/aceitacao/test_t016_vistorias.py -k "test_dev_03_ca_016_09_acerto_loc_2836"
```

A Juliana chega às 17:40 com 3/4 de tanque (faltam 4 L × R$ 5,50 + R$ 10,00 de taxa = R$ 32,00) e o retrovisor riscado (R$ 85,00): cobranças R$ 117,00, saldo R$ 183,00, "Encerrar e devolver R$ 183,00". Rode com o Postgres do worktree (ver `docs/agentes/retomada.md`).

## 2. Na tela, com a data de referência (depende da T-136)

A ADR 0021 (T-135) define `GIRO_DATA_REFERENCIA`, lida só no desenvolvimento. A T-136 (backend) ainda vai implementar; quando entrar:

1. No `.env` do compose: `GIRO_DATA_REFERENCIA=2026-10-14`, e `make relogio` (recria backend, worker e beat).
2. `make seed` não precisa rodar de novo: a LOC-2836 do seed já está com fim em 14 out 18:00.
3. Entre como Rodrigo ou Bruna (sem 2 etapas), abra a LOC-2836 e "Registrar devolução". A tela mostra "no horário" enquanto for antes das 19:00 do horário real (fim previsto 18:00 + 1 hora de tolerância, `LOC-10`).
4. Km agora: qualquer valor acima de 21.870 (a locação é de km livre). Combustível: 3/4. Registre a avaria "Retrovisor esquerdo riscado" e informe R$ 85,00.
5. Passo 2, "Acerto": combustível R$ 32,00, avaria R$ 85,00, atraso R$ 0,00; "Encerrar e devolver R$ 183,00".

Depois das 19:00 reais, a devolução vira atrasada (`LOC-10`) e o número muda. Para o caso de hora exata, o teste do caminho 1 é o que vale (ADR 0021, item 2).

## 3. Na tela, sem a T-136 (hoje)

Não dá para chegar em R$ 183,00 pela tela: no dia real a LOC-2836 só tem "faltam N dias" e a devolução antes do fim previsto pede o encerramento antecipado (`LOC-12`, `LOC-13`), cujo acerto é outro. Use o caminho 1.

## O que o seed deixa pronto para isso

- LOC-2836: Juliana Rocha, Yamaha Factor 150 (PNB-7C04), semanal de 2 semanas, 30 set 18:00 a 14 out 18:00, confirmada em 01 out, parcelas 1 e 2 pagas, caução de R$ 300,00 paga, saiu com 21.870 km.
- O histórico da locação traz os eventos nas datas do caso (rascunho e confirmação em 01 out 09:00, retirada às 09:10), e não na hora em que o seed rodou. A parcela 2 aparece com o pagamento em 07 out 10:00 no financeiro, mas o evento dela sai em 01 out 09:10, porque o seed a baixa junto da retirada.
