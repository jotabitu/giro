# Vendas

**Dono:** arquiteto · **Versão:** 03 nov 2026 (T-420, só a venda da quitação, `VEN-11`) · **App:** `vendas` (schema da empresa) · **Regras:** VEN-06, VEN-07, VEN-11, LOC-16, FIL-02, FIN-09, PLT-12 · **ADRs:** 0011, 0015, 0024, 0037 · **Telas:** Vendas (fase 2, ainda não feita no frontend), Locacao-Detalhe, Veiculo · **Critérios:** `docs/qa/criterios/T-420.md` (CA-420-11, 12, 16)

Convenções gerais em `docs/api/README.md`. Modelo: item 17 (`Venda`) em `docs/decisoes/modelo-de-dados.md`.

Este contrato cobre só o que a T-420 precisa: a venda de R$ 0,00 que nasce na quitação da locação com intenção de compra e a tarefa da transferência. O módulo de vendas (proposta, negociação, funil, meta, comissão, catálogo) é da T-418 e seguintes, e entra aqui quando for escrito.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver a lista e o detalhe (`/api/vendas/`, com o recurso `vendas_comissoes`) | sim | sim | só as dele (`USR-08`) | — | sim |
| Ver a venda da quitação no detalhe da locação e no histórico do veículo | sim | sim | sim | sem valores | sim |
| Registrar a transferência no Detran | sim | sim (filiais dele) | — | — | — |

- As rotas `/api/vendas/...` só abrem com o recurso `vendas_comissoes` (`PLT-12`, `plataforma.md`). A venda da quitação nasce em qualquer plano, porque a locação com intenção de compra é de `locacoes_vistoria`; sem o recurso, ela aparece pela locação e pelo veículo, e a transferência se registra pela rota da locação (abaixo).

## A venda da quitação

```json
{
  "id": 18, "codigo": "VEN-0178", "status": "vendida", "origem": "quitacao_locacao",
  "origem_rotulo": "Quitação de locação",
  "descricao": "Quitação da LOC-2901",
  "cliente": { "id": 1310, "nome": "Lucas Ferreira" },
  "veiculo": { "id": 640, "placa": "RTA2C55", "modelo": "Honda CG 160 Fan" },
  "filial": { "id": 1, "nome": "Filial Centro" },
  "vendedor": { "id": 3, "nome": "Bruna Alves" },
  "locacao": { "id": 2901, "codigo": "LOC-2901" },
  "preco_final_centavos": 0,
  "vendida_em": "2028-10-10T13:20:00Z",
  "transferencia": { "feita_em": null, "registrada_por": null, "pendente": true },
  "acoes": { "cancelar": false, "registrar_transferencia": true }
}
```

- `origem`: `quitacao_locacao` (esta) ou `balcao` (as do módulo de vendas, quando existirem). `origem_rotulo` "Quitação de locação" é o rótulo da lista (CA-420-12).
- Nasce pelo assinante de `locacoes.locacao_quitada`, na transação da quitação (`vendas.services.criar_venda_da_quitacao`, ADR 0037, item 4): já `vendida`, R$ 0,00, cliente, veículo e filial da locação, vendedor da locação, `vendida_em` = `quitada_em`. Sem contas a receber, sem contrato de compra e venda e sem comissão (`FIN-09`). Auditoria `venda.criar_da_quitacao`, ator Sistema, regra `VEN-11`.
- No banco, a venda da quitação nasce com `forma` vazia (string vazia `""`, não nula: o repositório não usa `null` em campo de texto), `preco_tabela_centavos`, `entrada_centavos` e `num_parcelas` nulos, `desconto_pct` e `juros_pct` 0. Quando `forma` entrar na representação (T-418), a venda da quitação a traz como `""`.
- Na mesma transação, o veículo vai de `alugado` para `vendido` por `veiculos.services.transicionar`, com a origem na venda e o motivo "Quitação da LOC-2901" (`VEN-06`, tabela de transições do veículo).
- `acoes.cancelar` é sempre `false`; o cancelamento (`VEN-07`), quando existir, responde 409 `{ "codigo": "VEN-11", "mensagem": "A venda da quitação de uma locação não se cancela." }`.
- Fica fora de funil, conversão, meta e comissão (`VEN-08`, `VEN-09`, `FIN-09`): toda conta dessas, quando existir, filtra `origem = "balcao"`.

### GET /api/vendas/ · GET /api/vendas/{id}/

Com o recurso `vendas_comissoes`. Lista paginada das vendas das filiais da pessoa, mais nova primeiro, no formato acima. Query: `?origem=`, `?transferencia_pendente=true`, `?veiculo=<id>`, `?cliente=<id>`. Enquanto o módulo de vendas não existe, só há vendas de quitação. O vistoriador recebe 403.

## A tarefa da transferência

Não há entidade de tarefa: a pendência é a venda da quitação com `transferencia.feita_em` nula (ADR 0037, item 6).

**Aviso.** Ao nascer a venda, depois do commit, os gerentes ativos da filial (`filiais.selectors.gerentes`, `FIL-02`) recebem no sino e por e-mail (`notificacoes.services.avisar(..., por_email=True)`):
```
tipo: "transferencia_quitacao"
titulo: "Fazer a transferência no Detran: RTA-2C55 para Lucas Ferreira. LOC-2901 quitada em 10/10/2028."
link: "/locacoes/2901"
urgente: false
chave: "quitacao-transferencia-{venda_id}"
```
O texto é o da `LOC-16`, com a placa com hífen e a data no fuso da filial (CA-420-11).

**Pendência no painel.** `vendas.selectors.transferencias_pendentes(filiais)` devolve as vendas da quitação sem transferência, para `relatorios` pôr nas `pendencias.itens` do painel do gerente e do administrador (`painel.md`): `{ "tipo": "transferencia_quitacao", "rotulo": "Transferência no Detran · RTA-2C55", "detalhe": "Lucas Ferreira · LOC-2901 quitada em 10/10/2028", "link": "/locacoes/2901" }`.

### POST /api/locacoes/{id}/transferencia/

Perfis: administrador e gerente da filial. A rota fica sob a locação, em `apps/vendas/api`, para abrir em qualquer plano (é do recurso `locacoes_vistoria`, como a locação; `vendas` está abaixo de `locacoes`, ADR 0011, como a troca está em `vistorias`). Botão "Transferência feita" no detalhe da locação quitada, com a data.
Corpo: `{ "feita_em": "2028-10-15" }` (data, não depois de hoje, não antes de `quitada_em`).
- 200: o detalhe da locação, com `compra.venda.transferencia = { "feita_em": "2028-10-15", "registrada_por": { "id", "nome" }, "pendente": false }`. A pendência sai do painel; o veículo continua `vendido` (CA-420-16).
- Auditoria `venda.registrar_transferencia` (objeto: a venda) e uma linha no histórico do veículo ("Transferência no Detran feita em 15/10/2028 · Rodrigo Pinheiro").
- 409 `{ "codigo": "VEN-11", "mensagem": "A transferência desta venda já foi registrada." }`; 404 se a locação não tem venda da quitação; 400 `validacao` em `feita_em`; 403 para os outros perfis e para o suporte em "só ver".
- `compra.venda.acoes.registrar_transferencia`, no detalhe da locação quitada (`locacoes.md`), segue as mesmas condições.

## Interface interna

| Item | Uso |
| --- | --- |
| `vendas.eventos.locacao_quitada` | assinante de `locacoes.locacao_quitada`: chama `criar_venda_da_quitacao`. |
| `vendas.services.criar_venda_da_quitacao(locacao_id, codigo, filial_id, cliente_id, veiculo_id, vendedor_id, quitada_em)` | idempotente pela `locacao` única; cria a venda, passa o veículo a `vendido` e agenda o aviso para depois do commit. |
| `vendas.services.registrar_transferencia(venda, feita_em, usuario)` | a rota acima. |
| `vendas.selectors.venda_da_locacao(locacao_id)` | bloco `compra.venda` do detalhe da locação (anotação fornecida a `locacoes`, ADR 0015). |
| `vendas.selectors.transferencias_pendentes(filiais)` | painel (`relatorios`). |
| `vendas.selectors.vendas_do_veiculo(veiculo_id)` | histórico do veículo (anotação para `veiculos`, ADR 0015). |
