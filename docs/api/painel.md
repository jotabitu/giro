# Painel: início por perfil e contadores do menu

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-047) · **App:** `relatorios` (schema da empresa; só leitura, nível 13 da ADR 0011) · **Regras:** USR-05, USR-07, USR-08, IMP-01, VEI-06, LOC-07, LOC-10, FIN-01, FIN-07, APR-09, VIS-05 · **Telas:** Main, Pos-Dashboard, Gerente, Vendedor, Vistoriador, Financeiro, Menu

Convenções gerais em `docs/api/README.md`. A estrutura do menu e a variante do início vêm em `GET /api/auth/eu/` (`contas.md`, "Menu e início"). Este contrato traz os números.

## Regras gerais

- **A API decide, a tela mostra.** Contagens, somas, percentuais, tendências e textos de contexto vêm prontos. O frontend só formata dinheiro e percentual no padrão da tela (inclusive a forma curta "R$ 18,4 mil").
- **Valor tipado.** Todo número de KPI vem como `{ "tipo": "numero" | "centavos" | "pct", "valor": ... }`: dinheiro em centavos, percentual como texto com 2 casas.
- **Escopo (`USR-07`).** Administrador e financeiro: filial do `X-Filial` ou `todas`. Gerente: a filial escolhida, entre as dele. Vendedor: só os números dele (`painel: proprios`).
- **Módulo que ainda não existe (`USR-08`).** O bloco vem `null`, nunca com número de exemplo. Ex.: `em_manutencao` do gerente fica `null` até o app `manutencao` existir; os blocos de vendas, comissões e conciliação, até a fase 2. O frontend não mostra bloco `null`.
- **Fuso.** "Hoje", "esta semana" e a saudação usam `America/Sao_Paulo`, no fuso da filial.
- **Atualização.** Cada resposta traz `atualizado_em`; a tela mostra "atualizado há 6 min" a partir dele. Os números podem vir de cache de até 5 minutos por empresa, filial e pessoa.

---

## GET /api/painel/contadores/

Números ao lado dos itens do menu. Perfis: todos. Sem paginação. O frontend consulta ao abrir a casca e a cada 60 segundos.
200:
```json
{ "atualizado_em": "...",
  "contadores": { "veiculos": 86, "locacoes": 42, "aprovacoes": 3, "receber": 7, "despesas": 1, "usuarios": 2,
                  "agenda": 6, "avarias": 2, "contas_a_pagar": 4, "manutencoes": null, "conciliacao": null, "propostas": null } }
```
Só vêm as chaves dos itens que a pessoa vê; `null` = módulo ainda não existe (o item não mostra número). O que cada um conta:

| Chave | Conta | Escopo |
| --- | --- | --- |
| `veiculos` | veículos fora de `vendido` e `baixado` | filial |
| `locacoes` | locações abertas (`aguardando_retirada`, `ativa`, `devolucao_atrasada`) | filial; vendedor: as dele |
| `aprovacoes` | pedidos `pendente` que a pessoa pode decidir, **sem os que ela mesma fez** (`APR-09`) | filial |
| `receber` | contas `atrasada` (`FIN-01`) | filial |
| `despesas` | despesas `aguardando_aprovacao` que a pessoa pode aprovar; para quem não aprova, sem contador | filial |
| `contas_a_pagar` | despesas `a_pagar` com vencimento até hoje | filial ou todas |
| `usuarios` | convites pendentes | empresa |
| `agenda` | vistorias do dia não concluídas (`VIS-05`) | filial |
| `avarias` | avarias abertas | filial |
| `manutencoes`, `conciliacao`, `propostas` | fase 2 | — |

---

## GET /api/painel/inicio/

Perfis: todos. Query: `?periodo=hoje|7d|30d` (padrão `7d`; só muda os números que dependem de período, indicados abaixo).
A resposta tem sempre `variante` (a mesma de `eu.navegacao.inicio.variante`), `saudacao` e `atualizado_em`, e os blocos da variante.

```json
{ "variante": "geral", "saudacao": "Bom dia, Mariana", "atualizado_em": "...", "...": "blocos" }
```

### Variante `geral` (administrador, tela `Main`)

```json
{
  "atencao": { "quantidade": 7, "texto": "7 contratos pedem atenção" },
  "kpis": [
    { "chave": "frota_ativa", "rotulo": "Frota ativa", "valor": { "tipo": "numero", "valor": 86 }, "contexto": "52 motos · 34 carros", "destaque": true },
    { "chave": "alugados_agora", "rotulo": "Alugados agora", "valor": { "tipo": "numero", "valor": 42 }, "contexto": "6 a mais esta semana", "tendencia": "sobe" },
    { "chave": "receita_locacao", "rotulo": "Receita de locação", "valor": { "tipo": "centavos", "valor": 1840000 }, "contexto": "últimos 7 dias" },
    { "chave": "em_atraso", "rotulo": "Em atraso", "valor": { "tipo": "numero", "valor": 2 }, "contexto": "R$ 1.646,40 a receber" }
  ],
  "frota": {
    "ocupacao_pct": "71.00", "meta_ocupacao_pct": "80.00", "nota": "ocupação de 71% · meta de 80%",
    "segmentos": [ { "status": "disponivel", "rotulo": "Disponível", "quantidade": 16 },
                   { "status": "alugado", "rotulo": "Alugado", "quantidade": 42 },
                   { "status": "reservado", "rotulo": "Reservado", "quantidade": 9 },
                   { "status": "em_manutencao", "rotulo": "Manutenção", "quantidade": 7 },
                   { "status": "a_venda", "rotulo": "À venda", "quantidade": 12 } ]
  },
  "devolucoes_semana": {
    "subtitulo": "6 contratos",
    "linhas": [ { "locacao_id": 2841, "codigo": "LOC-2841", "placa": "QXA4B21", "veiculo": "Honda CG 160 Fan", "cliente": "Carlos Menezes",
                  "data": "2026-10-06", "situacao": { "rotulo": "Atrasado", "tom": "perigo" } } ]
  },
  "pendencias": {
    "titulo": "7 contratos precisam de ação hoje",
    "itens": [ { "texto": "3 devoluções estão atrasadas", "gravidade": "critica", "destino": { "chave": "locacoes", "filtro": "aba=precisam_acao" } },
               { "texto": "2 parcelas vencem até amanhã", "gravidade": "info", "destino": { "chave": "receber", "filtro": "situacao=vencem_hoje" } } ]
  },
  "caixa_hoje": { "filial": "Filial Centro", "data": "2026-10-07", "status": "aberto",
                  "recebido_centavos": 111190, "a_receber_hoje_centavos": 262580, "despesas_centavos": 4800, "saldo_dia_centavos": 106390 }
}
```
- `atencao` e `pendencias.titulo` contam as locações da aba `precisam_acao` (`locacoes.md`).
- `frota_ativa`: veículos fora de `vendido` e `baixado`. `ocupacao_pct` (`VEI-06`) no período escolhido. `meta_ocupacao_pct` vem de `ConfiguracaoEmpresa` (padrão 80,00; telas `Login` e `Main`).
- `receita_locacao` (depende do período): parcelas de locação pagas no período, sem caução (`FIN-13`).
- `em_atraso`: clientes com conta `atrasada`, e o total em atraso no contexto (seed: 2 clientes, R$ 1.646,40).
- `devolucoes_semana`: locações com fim previsto de hoje até 6 dias à frente, mais as `devolucao_atrasada`, em ordem de data; `situacao` como na lista de locações.
- `pendencias.itens`: devoluções atrasadas, parcelas que vencem até amanhã e, quando o app `manutencao` existir, preventivas vencidas. Cada item leva `destino` (chave do menu e filtro) para "Ver pendências".
- `caixa_hoje`: o caixa do dia da filial (`null` com `X-Filial: todas` ou sem caixa aberto); `saldo_dia_centavos` = recebido − despesas pagas no caixa. `a_receber_hoje_centavos` é o "vence hoje" da `FIN-15` (contas não pagas com vencimento hoje), o mesmo `vence_hoje_centavos` de `financeiro.md`. Seed em 07 out (`FIN-15`, carteira de outubro): R$ 2.625,80 em 6 parcelas. Caixa da Filial Centro: recebido 111190 (`FIN-07`), saldo 111190 − 4800 = 106390.

### Variante `implantacao` (administrador antes da 1ª locação ou venda, tela `Pos-Dashboard`)

```json
{
  "teste": { "fim": "2026-10-21", "dias_restantes": 14, "texto": "Seu teste grátis termina em 14 dias (21 out)." },
  "primeiros_passos": { "concluidos": 2, "total": 3, "pct": "66.67",
    "itens": [ { "chave": "configuracao_inicial", "rotulo": "Configuração inicial", "detalhe": "Marca, filial, preços, contrato e 83 veículos importados", "concluido": true },
               { "chave": "convidar_equipe", "rotulo": "Convidar a equipe", "detalhe": "3 convites enviados", "concluido": true },
               { "chave": "primeira_locacao", "rotulo": "Fazer uma locação de teste", "detalhe": "Contrato, vistoria e assinatura com um cliente seu ou de teste", "concluido": false, "acao": { "rotulo": "Começar", "destino": "nova_locacao" } } ] },
  "convites": [ { "nome": "Rodrigo Pinheiro", "contato": "rodrigo@motorapida.com.br", "perfil": "gerente", "status": "aceito" } ],
  "indicadores": { "frota_cadastrada": 83, "alugados_agora": 0, "clientes": 0, "a_receber_centavos": 0 }
}
```
- `teste` vem `null` quando a empresa não está `em_teste`.
- `primeiros_passos` vem dos passos da implantação (`IMP-05`, `plataforma.UsoEmpresa.passos_implantacao`). Os itens "Instalar o app no celular do vistoriador" e "Conectar o WhatsApp da loja" da tela só entram quando esses recursos existirem; até lá, não vêm.
- Ao existir a 1ª locação ou venda (`IMP-01`), a variante passa a `geral`.

### Variante `gerente` (tela `Gerente`)

```json
{
  "aprovacoes": { "total": 3, "mais_antigo": "há 2 h",
    "itens": [ { "id": 88, "tipo": "APR-01", "titulo": "Desconto de 8% para Diego Martins", "detalhe": "Bruna · ... (limite dela: 5%)", "acoes": ["recusar", "aprovar"] } ] },
  "kpis": [
    { "chave": "ocupacao", "rotulo": "Ocupação", "valor": { "tipo": "pct", "valor": "71.00" }, "contexto": "meta de 80%" },
    { "chave": "receita_semana", "rotulo": "Receita da semana", "valor": { "tipo": "centavos", "valor": 1840000 }, "contexto": "6% a mais que a anterior", "tendencia": "sobe" },
    { "chave": "devolucoes_atrasadas", "rotulo": "Devoluções atrasadas", "valor": { "tipo": "numero", "valor": 3 }, "contexto": "1 há mais de 2 dias" },
    { "chave": "em_manutencao", "rotulo": "Em manutenção", "valor": null, "contexto": null }
  ],
  "equipe_hoje": [ { "usuario_id": 4, "nome": "João Silva", "perfil": "vistoriador", "resumo": "2 de 6 vistorias feitas", "online": true } ],
  "frota_filial": { "total": 83, "segmentos": [ { "rotulo": "Livres", "quantidade": 16 }, { "rotulo": "Alugados", "quantidade": 42 }, { "rotulo": "Reserv.", "quantidade": 9 }, { "rotulo": "Oficina e venda", "quantidade": 16 } ] }
}
```
- `aprovacoes`: pedidos `pendente` da filial que ele pode decidir, **sem os que ele mesmo fez** (`APR-09`), do mais antigo para o mais novo, até 5 itens. As ações usam `aprovacoes.md`.
- `equipe_hoje`: só pessoas ativas ligadas à filial (`USR-08`). `online` = sessão usada nos últimos 5 minutos (`contas.Sessao.ultimo_uso`). `resumo` é texto pronto do dia: vistoriador "2 de 6 vistorias feitas"; vendedor "3 locações hoje" (metas e propostas na fase 2); quem não fez nada hoje, "último acesso ontem".
- `em_manutencao` vem com `valor: null` até o app `manutencao` existir (o frontend esconde o cartão).

### Variante `vendedor` (fase 1: locação; tela `Vendedor` completa na fase 2)

```json
{
  "kpis": [
    { "chave": "minhas_locacoes_ativas", "rotulo": "Minhas locações ativas", "valor": { "tipo": "numero", "valor": 12 }, "contexto": null },
    { "chave": "devolvem_hoje", "rotulo": "Devolvem hoje", "valor": { "tipo": "numero", "valor": 2 }, "contexto": null },
    { "chave": "parcelas_atrasadas", "rotulo": "Parcelas atrasadas", "valor": { "tipo": "numero", "valor": 1 }, "contexto": "R$ 299,40 de 1 cliente" }
  ],
  "parcelas_atrasadas": [ { "conta_id": 9010, "cliente": "Carlos Menezes", "locacao": "LOC-2841", "vencimento": "2026-09-30", "valor_centavos": 29940, "dias": 7, "acao": "cobrar" } ],
  "precisam_acao": [ { "locacao_id": 2856, "codigo": "LOC-2856", "cliente": "Lucas Ferreira", "situacao": { "rotulo": "Aguardando assinatura", "tom": "alerta" } } ],
  "meta": null, "funil": null, "comissao_prevista": null, "propostas": null
}
```
- "Meus" (`USR-08`): as locações que o vendedor criou (`Locacao.vendedor`). `parcelas_atrasadas`: contas atrasadas dessas locações.
- `meta`, `funil`, `comissao_prevista` e `propostas` vêm `null` até vendas e comissões existirem (fase 2, `FIN-09`).

### Variante `vistoriador` (tela `Vistoriador`)

```json
{ "agenda": { "...": "o mesmo corpo de GET /api/vistorias/agenda/?dia=hoje" }, "avarias_abertas": 2 }
```
Sem valores em dinheiro. As abas Amanhã e Semana chamam `GET /api/vistorias/agenda/` direto (`vistorias.md`).

### Variante `financeiro` (tela `Financeiro`, sem o que é fase 2)

```json
{
  "kpis": [
    { "chave": "entra_hoje", "rotulo": "Entra hoje", "valor": { "tipo": "centavos", "valor": 262580 }, "contexto": "6 parcelas" },
    { "chave": "sai_hoje", "rotulo": "Sai hoje", "valor": { "tipo": "centavos", "valor": 41230 }, "contexto": "1 conta a pagar" },
    { "chave": "em_atraso", "rotulo": "Em atraso", "valor": { "tipo": "centavos", "valor": 164640 }, "contexto": "2 clientes" },
    { "chave": "saldo_em_contas", "rotulo": "Saldo em contas", "valor": null, "contexto": null }
  ],
  "caixas_do_dia": [ { "filial": "Filial Centro", "status": "aberto", "aberto_por": "Bruna Alves", "esperado_gaveta_centavos": 28100 } ],
  "para_hoje": [
    { "texto": "Devolver R$ 183,00 a Juliana Rocha por Pix", "tipo": "reembolso", "destino": { "chave": "reembolsos", "id": 31 } },
    { "texto": "Pagar conta de luz · R$ 412,30", "tipo": "despesa", "destino": { "chave": "contas_a_pagar", "id": 803 } }
  ],
  "fluxo_previsto": null, "conciliacao": null
}
```
- `entra_hoje`: o "vence hoje" da `FIN-15` (contas não pagas com vencimento hoje, sem caução), com a quantidade de parcelas no contexto; mesmo número de `caixa_hoje.a_receber_hoje_centavos` e de `vence_hoje_*` em `financeiro.md` (seed em 07 out: 262580 em 6 parcelas); `sai_hoje`: despesas `a_pagar` com vencimento hoje; `em_atraso`: total `atrasada` e número de clientes.
- `para_hoje` (`USR-08`): só reembolsos `a_fazer` e despesas a pagar vencendo até hoje. **Sem aprovações**: o financeiro não decide `APR-03` nem `APR-04`.
- `saldo_em_contas`, `fluxo_previsto` e `conciliacao` vêm `null` até a fase 2 (conciliação bancária).

---

## Interface interna

`relatorios.selectors.inicio(usuario, variante, filial, periodo)` e `contadores(usuario, filial)` leem dos outros apps só por `selectors` (ADR 0011, nível 13). Um teste por variante com o seed Moto Rápida em 07 out confere os números citados nos contratos de origem: em atraso R$ 1.646,40 em 2 clientes; caixa da Filial Centro com R$ 1.111,90 recebidos; entra hoje R$ 2.625,80 em 6 parcelas; a despesa de R$ 1.200,00 pedida por João aparece nas aprovações de Rodrigo; um pedido feito pelo próprio Rodrigo não aparece para ele (`APR-09`).
