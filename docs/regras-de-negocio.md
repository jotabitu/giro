# Regras de negócio e fluxos do sistema

Oct 7, 2026 · @João Victor

Fonte única da lógica de negócio do sistema de gestão de locação e venda de motos e carros (SaaS white label, Django + DRF no backend, Next.js no frontend). Quem for desenvolver, pessoa ou IA, deve seguir estas regras; quando uma tela e este documento discordarem, vale este documento.

## Como usar este documento

Cada seção descreve um módulo: o que existe, os estados, as transições, os cálculos e as telas do [canvas de design](https://claude.ai/artifact/5BZCQjBRVfmKwvoDEjEFnb) onde aquilo aparece. Os nomes entre crases (`Locacoes-Desktop`) são os arquivos das telas no canvas. Regras numeradas (`LOC-07`) podem ser citadas em código, testes e commits.

**Convenções obrigatórias**

- **Multiempresa:** toda tabela de negócio tem `empresa_id` (via schema do django-tenants) e, quando faz sentido, `filial_id`. Nenhuma consulta cruza empresas. O painel da plataforma usa o schema público.
- **Dinheiro:** sempre em centavos, inteiro (`valor_centavos`). Percentuais guardados com 2 casas (`desconto_pct = 8.00`). Cálculos com percentual ou divisão (desconto, multa, juros, comissão, proporcional, parcelas) fazem as contas intermediárias em decimal, sem arredondar, e arredondam uma vez cada valor que é gravado ou exibido como linha própria, para o centavo, com meio centavo para cima (`ROUND_HALF_UP`). Ao dividir um total em parcelas, a diferença de centavos vai para a última parcela, e a soma sempre bate com o total. Fora isso, arredondamento só na exibição. (Decidido em 07 out 2026, T-031.)
- **Datas e horas:** gravadas em UTC, exibidas em `America/Sao_Paulo`. Vencimentos são datas (sem hora). Devoluções têm data e hora.
- **Status:** cada entidade com ciclo de vida tem um campo `status` com valores fechados (enum) listados neste documento. Mudança de status só por serviço de domínio (`services.py`), nunca por update direto, e sempre grava um evento de auditoria.
- **Exclusão:** nada de negócio é apagado. Usa `ativo=false` ou status de cancelado. Registros financeiros nunca são editados depois de pagos: corrige-se com estorno.
- **Números legíveis:** cada documento tem código sequencial por empresa: `LOC-2856` (locação), `VEN-0177` (venda), `OS-118` (ordem de serviço), `FAT-2209` (fatura da assinatura, plataforma).
- **Textos ao usuário:** português do Brasil, sem jargão ("devolução", não "check-in"; "caução", não "depósito de segurança").
- **Marca do produto:** o produto se chama **Giro** (kit de logotipo GIRO Motos: grafite `#111114`, verde-limão `#C8F04A`, cinza-claro `#ECEBF0`). A marca Giro aparece só no painel da plataforma, nas telas de compra, no assistente de implantação e no rodapé "Tecnologia Giro". Dentro do sistema da locadora vale a marca da locadora (white label). Logo sempre pelo arquivo SVG, nunca o nome digitado; nunca limão sobre fundo branco. Preços dos planos, parceiro de pagamento e domínio decididos em 07 out 2026 (ver `docs/regras/decisoes.md`).

**Os 3 níveis do sistema**

| Nível | Quem usa | Onde entra | Telas |
| --- | --- | --- | --- |
| Plataforma | Você (dono do produto) e sua equipe interna | `admin.girolocadoras.com.br` | `Plat-*`, `Plataforma-*` |
| Empresa cliente (locadora) | Administrador, gerente, vendedor, vistoriador, financeiro | `<subdominio>.girolocadoras.com.br` | Todas as outras |
| Cliente final da locadora | Locatário ou comprador | Links recebidos por WhatsApp/e-mail (assinar contrato, pagar Pix) | Ainda não desenhadas |

## Onde está cada regra

Leia só o arquivo do módulo da sua tarefa (e o de cada código citado nela). Os códigos continuam os mesmos (`LOC-07`, `FIN-09`).

| Módulo | Códigos | Arquivo |
| --- | --- | --- |
| Entidades e relações | — | [`docs/regras/entidades.md`](regras/entidades.md) |
| Plataforma e assinatura | `PLT` | [`docs/regras/plataforma.md`](regras/plataforma.md) |
| Implantação | `IMP` | [`docs/regras/implantacao.md`](regras/implantacao.md) |
| Usuários, perfis e permissões | `USR` | [`docs/regras/usuarios.md`](regras/usuarios.md) |
| Filiais | `FIL` | [`docs/regras/filiais.md`](regras/filiais.md) |
| Veículos | `VEI` | [`docs/regras/veiculos.md`](regras/veiculos.md) |
| Movimentações de veículos | `MOV` | [`docs/regras/movimentacoes.md`](regras/movimentacoes.md) |
| Clientes | `CLI` | [`docs/regras/clientes.md`](regras/clientes.md) |
| Locação | `LOC` | [`docs/regras/locacao.md`](regras/locacao.md) |
| Vistoria e devolução | `VIS`, `DEV` | [`docs/regras/vistoria-e-devolucao.md`](regras/vistoria-e-devolucao.md) |
| Vendas | `VEN` | [`docs/regras/vendas.md`](regras/vendas.md) |
| Financeiro | `FIN` | [`docs/regras/financeiro.md`](regras/financeiro.md) |
| Manutenção e despesas | `MAN` | [`docs/regras/manutencao-e-despesas.md`](regras/manutencao-e-despesas.md) |
| Aprovações | `APR` | [`docs/regras/aprovacoes.md`](regras/aprovacoes.md) |
| Automações e notificações | `AUT` | [`docs/regras/automacoes.md`](regras/automacoes.md) |
| Auditoria, LGPD e exportação | `AUD` | [`docs/regras/auditoria-e-lgpd.md`](regras/auditoria-e-lgpd.md) |
| Dados de referência para testes | — | [`docs/regras/dados-de-teste.md`](regras/dados-de-teste.md) |
| Pontos em aberto (dúvidas para o dono) | — | [`docs/regras/pontos-em-aberto.md`](regras/pontos-em-aberto.md) |
| Decisões do dono por data (o porquê) | — | [`docs/regras/decisoes.md`](regras/decisoes.md) |
| Histórico de mudanças até 09 nov 2026 | — | [`docs/regras/historico.md`](regras/historico.md) |

**Mudou uma regra?** Edite o arquivo do módulo e diga o que mudou e por quê na descrição do PR. Não escreva "Mudanças em …" no arquivo: o histórico é o do git.
