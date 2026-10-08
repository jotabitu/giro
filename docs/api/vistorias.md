# Vistorias, devolução e acerto

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-038) · **App:** `vistorias` (schema da empresa) · **Regras:** VIS-01 a VIS-05, DEV-01 a DEV-06, LOC-09 a LOC-13, VEI-01, VEI-02, CLI-02, CLI-03, CLI-05, FIL-03, FIL-05, AUD-05 · **ADRs:** 0011, 0015 · **Telas:** Vistoria, Devolucao, Vistoriador

Convenções gerais em `docs/api/README.md`. Modelo: item 14 e apoio (`FotoVistoria`, `Avaria`, `Devolucao`, `ItemAcerto`) em `docs/decisoes/modelo-de-dados.md`. A locação está em `locacoes.md`.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Agenda do dia | sim | sim | sim | sim (sua filial) | — |
| Fazer vistoria de saída e de chegada, marcar avaria | sim | sim | sim | sim | — |
| Ver e editar o acerto, encerrar a devolução | sim | sim | sim | — | — |
| Corrigir vistoria concluída (`VIS-04`) | sim | sim | — | — | — |

O vistoriador nunca recebe valores: nas respostas para ele, todo campo `_centavos` e o bloco `acerto` vêm ausentes, e `avaria.valor_centavos` não é aceito no corpo. Quem fecha a conta é quem recebe pagamento no caixa.

---

## Agenda do vistoriador (VIS-05)

### GET /api/vistorias/agenda/
Query: `?dia=hoje|amanha|semana` (padrão `hoje`). Filial pelo `X-Filial`.
200:
```json
{
  "resumo": "Terça, 07 out · 3 saídas e 3 devoluções",
  "proxima": { "item_id": "saida-2856", "em_minutos": 20 },
  "avarias_abertas": 2,
  "resultados": [
    { "id": "devolucao-2841", "tipo": "devolucao", "horario": "2026-10-06T21:00:00Z",
      "veiculo": { "id": 77, "placa": "QXA4B21", "modelo": "Honda CG 160" },
      "cliente": { "nome": "Carlos Menezes" }, "locacao": { "id": 2841, "codigo": "LOC-2841" },
      "situacao": { "codigo": "atrasada", "rotulo": "Atrasada", "tom": "perigo" },
      "vistoria_id": null, "acao": { "codigo": "abrir", "rotulo": "Abrir" } }
  ]
}
```
- Itens: retiradas de locações `aguardando_retirada` com início no dia e devoluções previstas (fim previsto no dia, ou locação `devolucao_atrasada`), da filial, em ordem de horário.
- `situacao`: `agendada`, `hoje`, `em_andamento` (vistoria em rascunho), `atrasada` (passou do horário), `concluida`.
- `acao`: `iniciar` (saída sem vistoria), `continuar` (rascunho), `abrir`.

---

## Vistoria (saída e chegada)

### Representação

```json
{
  "id": 3001, "tipo": "saida", "status": "rascunho",
  "locacao": { "id": 2856, "codigo": "LOC-2856" },
  "veiculo": { "id": 501, "placa": "SAK1D39", "modelo": "Honda CG 160 Fan", "ano": 2025 },
  "cliente": { "nome": "Lucas Ferreira", "cnh": "Categoria A · válida" },
  "km": 3120, "km_ultima_leitura": { "km": 3118, "em": "2026-10-05" },
  "combustivel": "cheio",
  "fotos": [
    { "id": 1, "posicao": "frente", "tirada_em": "...", "url": "...", "url_expira_em": "..." }
  ],
  "fotos_obrigatorias": { "feitas": 3, "total": 5, "faltam": ["lado_direito", "painel"] },
  "itens": [ { "codigo": "retrovisores", "rotulo": "Retrovisores", "ok": true, "observacao": null } ],
  "avarias": [ { "id": 51, "descricao": "Risco no tanque, lado esquerdo", "preexistente": true, "foto_id": 9,
                 "origem": "Registrado na vistoria anterior; não será cobrado do cliente na devolução." } ],
  "observacoes": null,
  "responsavel": { "id": 4, "nome": "João Silva" },
  "concluida_em": null,
  "pendencias": ["fotos", "km"],
  "pode_concluir": false,
  "resumo_locacao": { "periodicidade": "semanal", "inicio": "...", "fim_previsto": "...", "km_livre": true,
                      "diaria_centavos": 5490, "caucao_centavos": 30000, "caucao_paga": true }
}
```
- `fotos[].url`: URL assinada de 15 minutos (`AUD-05`), gerada a cada `GET`.
- `itens`: a lista padrão do ramo vem preenchida na criação (`VIS-02`): pneus e freios, luzes e buzina, retrovisores, documento e chave, acessórios entregues (capacete etc.). Os extras da locação entram como itens (ex.: "Capacete extra").
- `avarias` da saída já trazem as avarias abertas do veículo como `preexistente: true` (`VIS-01`): elas não são cobradas na devolução.
- `resumo_locacao` não traz os campos `_centavos` para o vistoriador.

### POST /api/locacoes/{id}/vistorias/
Corpo: `{ "tipo": "saida" }`. Saída só para locação `aguardando_retirada` (ou troca de veículo pendente, `LOC-09`). Na troca, a saída do veículo novo só conclui depois de paga a diferença de caução, quando a nova é maior (422 `{ "codigo": "LOC-09", "mensagem": "Receba a diferença da caução antes de entregar o veículo" }`).
201: vistoria em `rascunho`. Se já existe rascunho da mesma locação e tipo, devolve 200 com ele (o vistoriador continua de onde parou).
A chegada (`tipo = devolucao`) é criada por `POST /api/locacoes/{id}/devolucao/` (abaixo).

### PATCH /api/vistorias/{id}/
Só em `rascunho`. Corpo: `{ km?, combustivel?, itens?, observacoes? }`. 200. "Salvar e continuar depois" é só este `PATCH` (`DEV-05`).

### POST /api/vistorias/{id}/fotos/
Só em `rascunho`. `multipart/form-data`: `posicao` (`frente`, `traseira`, `lado_esquerdo`, `lado_direito`, `painel`, `avaria`), `arquivo` (JPG ou PNG até 10 MB; reprocessada, sem metadados de localização). 201: a foto. Nova foto de posição fixa substitui a anterior no rascunho.

### POST /api/vistorias/{id}/avarias/
Só em `rascunho`. Corpo: `{ descricao, foto_id, vai_para_oficina?: false, valor_centavos? }`. `valor_centavos` só na chegada e só para quem pode ver o acerto. 201. `DELETE /api/vistorias/{id}/avarias/{avaria_id}/` remove avaria nova enquanto a vistoria é rascunho (não é registro de negócio ainda).

### POST /api/vistorias/{id}/concluir/
200: vistoria `concluida`, que não se edita mais (`VIS-04`).
Recusas (422, com todos os problemas em `detalhes.pendencias`):
- `VIS-01`: faltam fotos obrigatórias (frente, traseira, lados, painel).
- `VIS-02`: item sem resposta.
- `VIS-03`: combustível não informado.
- `VEI-01`: km menor que o atual do veículo; a mensagem indica `POST /api/veiculos/{id}/corrigir-km/`.
- Só na saída: `clientes.selectors.impedimentos_para_retirada` → `CLI-03` (cadastro incompleto), `CLI-02` (CNH sem a categoria ou vencida há mais de 30 dias), `CLI-05` (bloqueado).
Efeitos:
- Saída: atualiza o km do veículo (`VEI-02`) e chama `locacoes.services.registrar_vistoria_saida`, que pode ativar a locação (`locacoes.md`).
- Chegada: atualiza o km e libera o passo de acerto; a locação continua `ativa` ou `devolucao_atrasada` até encerrar (`DEV-05`).

### POST /api/vistorias/{id}/corrigir/
Perfis: administrador, gerente. Corpo: `{ motivo }`. Só em vistoria `concluida`.
201: nova vistoria em `rascunho` com `substitui` = a anterior e os dados copiados (`VIS-04`). Concluída, ela passa a ser a vigente; a anterior continua guardada.

### GET /api/vistorias/avarias/
Query: `?veiculo=<id>`, `?abertas=true`. Avarias ainda não reparadas (tela `Vistoriador`, "Avarias abertas"). Uma avaria fecha quando a OS ligada a ela é concluída (`manutencao`).

---

## Devolução (tela `Devolucao`: Vistoria → Acerto → Recibo)

### POST /api/locacoes/{id}/devolucao/
Perfis: quem faz vistoria. Locação `ativa` ou `devolucao_atrasada`.
201: a devolução, com a vistoria de chegada em `rascunho` e o acerto em `rascunho`. Se já existe, 200 com ela (`DEV-05`).

### GET /api/devolucoes/{id}/
200:
```json
{
  "id": 701, "status": "rascunho",
  "locacao": { "id": 2836, "codigo": "LOC-2836", "cliente": "Juliana Rocha",
               "veiculo": "Yamaha Factor 150 · PNB7C04", "no_horario": true },
  "vistoria": { ...representação da vistoria de chegada... },
  "comparacao": {
    "km": { "saida": 18402, "agora": 19630, "rodou": 1228, "texto": "Rodou 1.228 km · plano com km livre" },
    "combustivel": { "saida": "cheio", "agora": "tres_quartos", "faltou": "1/4 tanque", "litros_faltantes": "4.0" },
    "fotos": [ { "posicao": "lado_esquerdo", "saida": { "url": "..." }, "agora": { "url": "..." } } ],
    "itens": [ { "codigo": "retrovisor_esquerdo", "rotulo": "Retrovisor esquerdo", "saida": "ok", "agora": "riscado", "novo": true } ]
  },
  "acerto": { ...ver abaixo... }
}
```
`comparacao` sempre usa a vistoria de saída vigente do mesmo veículo e da mesma locação (com troca de veículo, a do trecho atual).

**Um acerto só por locação** (`LOC-09`): na troca de veículo, a vistoria de chegada do veículo antigo não fecha conta. A devolução da locação é criada nessa hora, em `rascunho`, e recebe os itens do veículo antigo (avarias, combustível); o acerto final, na devolução do último veículo, soma tudo e desconta da caução total paga.

### Acerto (DEV-01, DEV-02)

O acerto é recalculado a cada `GET` e a cada mudança, enquanto está em `rascunho`.

```json
"acerto": {
  "status": "rascunho",
  "caucao_centavos": 30000,
  "itens": [
    { "id": 1, "tipo": "combustivel", "descricao": "Combustível (faltou 1/4 tanque, 4 L × R$ 5,50 + R$ 10,00)", "valor_centavos": 3200, "modo": "calculado" },
    { "id": 2, "tipo": "avaria", "descricao": "Retrovisor esquerdo", "valor_centavos": 8500, "modo": "informado", "avaria_id": 52 },
    { "id": 3, "tipo": "atraso", "descricao": "Atraso", "valor_centavos": 0, "modo": "calculado" }
  ],
  "creditos": [],
  "total_cobrancas_centavos": 11700,
  "saldo_centavos": 18300,
  "resultado": { "tipo": "devolver", "valor_centavos": 18300,
                 "texto": "Desconta R$ 117,00 da caução de R$ 300,00", "botao": "Encerrar e devolver R$ 183,00" },
  "forma_devolucao": "pix"
}
```

**Caso do seed (`DEV-03`):** LOC-2836, PNB7C04 com tanque de 16 L, Filial Centro com litro a R$ 5,50, saída cheio e chegada 3/4 → combustível 16 × 1/4 = 4 L × 550 + 1000 = **3200**; retrovisor 8500; cobranças 11700; caução 30000 → saldo **18300**: devolver **R$ 183,00** por Pix.

Itens (`ItemAcerto.tipo`):

| Tipo | Como entra | Regra |
| --- | --- | --- |
| `combustivel` | `calculado`: litros faltantes = capacidade do tanque do veículo × (nível na saída − nível na chegada), com os níveis valendo 0, 1/4, 1/2, 3/4 e 1; valor = litros × preço do litro da filial + R$ 10,00 uma vez por devolução, só quando falta combustível. Sem capacidade do tanque ou sem preço da filial, vira `informado` e a tela pede o valor | `DEV-01` (decidido em 07 out 2026, T-041) |
| `avaria` | um item por avaria nova com valor (tabela de peças ou orçamento) | `DEV-01` |
| `atraso` | `calculado` por `locacoes.selectors.calcular_atraso` no momento da conclusão da vistoria de chegada | `LOC-10`, `LOC-11`, `FIL-03` |
| `km_excedente` | `calculado`; hoje sempre 0 (km livre em todos os planos) | `DEV-01` |
| `parcela_aberta` | `calculado`: contas da locação vencidas e não pagas | `DEV-01` |
| `multa_transito` | `informado`, com descrição (multas já identificadas) | `DEV-01` |
| `multa_encerramento` | `calculado`, só em encerramento antecipado aprovado | `LOC-12` |

`creditos` (somam ao saldo): `semanas_nao_usadas`, só no mensal com encerramento antecipado (`LOC-13`, ex.: Patrícia 37100).

`saldo_centavos = caucao_centavos + soma(creditos) − total_cobrancas_centavos` (`DEV-02`).
- `resultado.tipo = "devolver"`: saldo positivo, devolvido por Pix, dinheiro ou estorno do cartão (`forma_devolucao`).
- `resultado.tipo = "cobrar"`: saldo negativo vira conta a receber do cliente, com vencimento em 3 dias.
- `resultado.tipo = "zerado"`: saldo 0.

### POST /api/devolucoes/{id}/acerto/itens/ · PATCH .../itens/{item_id}/ · DELETE .../itens/{item_id}/
Perfis: quem vê o acerto. Só itens `informado` (`avaria`, `multa_transito`, e `combustivel` quando não pôde ser calculado). Corpo: `{ tipo, descricao, valor_centavos }`. Itens `calculado` não se editam: 409 `{ "codigo": "item_calculado" }`. 200: a devolução.

### PATCH /api/devolucoes/{id}/acerto/
Corpo: `{ "forma_devolucao": "pix" | "dinheiro" | "estorno_cartao" }`. 200.

### POST /api/devolucoes/{id}/encerrar/
Perfis: quem vê o acerto. Exige a vistoria de chegada `concluida` (senão 422 `{ "codigo": "vistoria_pendente" }`) e `forma_devolucao` quando há valor a devolver.
200: a devolução `concluida` e o resumo da locação. Na mesma transação (`DEV-06`):
- Acerto congelado (`concluido`); itens viram registros no `financeiro`: as cobranças são pagas com a caução (`forma = caucao`); o saldo a devolver é lançado como devolução de caução pela `forma_devolucao` (dinheiro sai no caixa do dia da filial, que precisa estar aberto, `FIN-07`); o saldo negativo vira conta a receber com vencimento em 3 dias (`DEV-02`). O detalhe de cada lançamento está no contrato de financeiro (T-017).
- Locação `encerrada` (ou `cancelada` no encerramento antecipado aprovado) por `locacoes.services.encerrar`, com `devolvida_em` = conclusão da vistoria de chegada, ajustada pela `LOC-11` quando a filial estava fechada.
- Km do veículo atualizado (`VEI-02`). Avaria com `vai_para_oficina` abre uma OS (`manutencao`) e o veículo vai para `em_manutencao`; sem isso, volta para `disponivel` (`DEV-04`).
- Evento `locacoes.locacao_encerrada` recalcula as preventivas (`MAN-03`).
- Depois do commit: recibo em PDF com as fotos, enviado por WhatsApp com a marca da locadora. Com saldo a devolver por Pix, o recibo diz "devolução de R$ 183,00 por Pix em até 1 dia útil" (o Pix é feito pela locadora e marcado como feito, `financeiro.md`).
Erros: 422 `{ "codigo": "FIN-07", "mensagem": "Abra o caixa do dia para devolver em dinheiro" }`; 409 `transicao_locacao`.
Regras: DEV-01 a DEV-06, LOC-10 a LOC-13.

### GET /api/devolucoes/{id}/recibo/
200: `{ "url", "url_expira_em" }` (PDF, URL assinada de 15 min). `POST /api/devolucoes/{id}/recibo/reenviar/` reenvia por WhatsApp.

---

## Interface interna

| Item | Uso |
| --- | --- |
| chamadas a `locacoes.services` | `registrar_vistoria_saida`, `encerrar` (`vistorias` está abaixo de `locacoes`, ADR 0011). |
| chamadas a `veiculos.services` | `atualizar_km`, `transicionar` (via `locacoes.encerrar` e `manutencao`). |
| chamada a `manutencao.services.abrir_os_de_avaria` | `DEV-04`. |
| anotação fornecida (ADR 0015) | vistorias da locação para `locacoes` (histórico). |
| `CAMPOS_AUDITORIA` | nenhum dado pessoal; fotos não entram no evento, só a contagem. |
