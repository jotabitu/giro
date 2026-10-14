# Módulos por plano e por ramo, decididos por empresa

**Status:** aceita · 14 out 2026 · detalha a 0011 e a 0015 para a `PLT-12` (T-192)

## Contexto

Até a T-190, todas as empresas tinham os mesmos módulos. O que escondia um item do menu era `settings.GIRO_MODULOS_ATIVOS`, uma lista global dos apps já entregues, mais `Plano.recursos`, que só filtrava o menu e não fechava nenhuma rota. A `PLT-12` (decisão do dono de 14 out 2026) muda isso: o plano liga os módulos, junto com o ramo da implantação (passo 7, `ConfiguracaoEmpresa.atividade`); módulo fora some do menu, a API recusa as rotas dele, os dados ficam guardados, e o downgrade é recusado enquanto o módulo que sai tiver algo aberto. No Essencial, a régua (`AUT-03`) sai só por e-mail e o passo 10 (Recebimentos) não existe.

Três coisas tornam a decisão cara de desfazer: o módulo do plano não é o app Django (`financeiro` tem contas a receber, que é do Essencial, e despesas e conciliação, que não são); a recusa tem de valer em toda rota, tarefa e leitura composta, não só no menu; e o downgrade (`plataforma`, no `public`) precisa contar o que está aberto em apps que ele não pode importar (ADR 0011).

## Decisão

1. **O módulo do plano é um `Recurso`, não um app.** `plataforma.Recurso` vira a lista fechada dos módulos que o plano liga. Fica assim:

   | `Recurso` | O que liga | Ramo | Essencial | Profissional | Completo |
   | --- | --- | --- | --- | --- | --- |
   | `locacoes_vistoria` | apps `locacoes` e `vistorias` (locação, vistoria, devolução, planos especiais) | aluga | sim | sim | sim |
   | `contas_receber` | em `financeiro`: contas a receber, caixa do dia, caução | — | sim | sim | sim |
   | `contrato_digital` | assinatura do contrato no celular (`contratos`) | — | sim | sim | sim |
   | `vendas_comissoes` | app `vendas` e, em `financeiro`, as comissões (`FIN-09`) | vende | não | sim | sim |
   | `manutencao_despesas` | app `manutencao` e, em `financeiro`, despesas e contas a pagar | — | não | sim | sim |
   | `conciliacao` | em `financeiro`: conciliação bancária | — | não | sim | sim |
   | `relatorios` | rotas de relatórios e DRE (`relatorios`); o painel e Configurações não dependem dele | — | não | sim | sim |
   | `recebimento_parceiro` | Pix e boleto automáticos pela subconta (`FIN-04`, `AUT-04`, `AUT-05`) e o passo 10 da implantação | — | não | sim | sim |
   | `cobranca_whatsapp` | o canal WhatsApp da régua e do "Cobrar" (`AUT-03`) | — | não | sim | sim |
   | `suporte_prioritario` | nada no sistema da empresa; só catálogo e fila do suporte | — | não | não | sim |

   Saem `dominio_proprio` e `api_integracoes` (`PLT-11`: não existem). Entram `conciliacao`, `recebimento_parceiro` e `cobranca_whatsapp`. `contrato_digital` passa ao Essencial. O núcleo (veículos, clientes, filiais, usuários, aprovações, contratos, configurações, empresa e marca, assinatura, auditoria, painel) não tem `Recurso`: vale em todos os planos. Uma migração de dados regrava `Plano.recursos` dos três planos e um `CHECK` (ou validação no `clean` e no serviço) só aceita valores do enum.

2. **Os recursos ligados são da empresa, calculados a cada pedido.** `plataforma.selectors.recursos_da_empresa(empresa=None) -> frozenset[str]` = `Plano.recursos` do plano atual da empresa, menos `locacoes_vistoria` quando a atividade não aluga e menos `vendas_comissoes` quando não vende. A atividade vem de `comum.empresa.atividade()`, que o app `empresas` registra (como `exige_2fa_todos`); enquanto `ConfiguracaoEmpresa.atividade` não existe, vale `ambos`. Nada é guardado: mudar de plano ou de ramo vale no pedido seguinte. `comum.empresa.tem_recurso(recurso)` é a porta para os apps de cima, sem importar `plataforma` (`plataforma` registra a função no `ready()`; sem empresa no schema, `public`, devolve `True`).

3. **`GIRO_MODULOS_ATIVOS` continua global e só diz o que já foi entregue.** O conjunto de uma empresa é `GIRO_MODULOS_ATIVOS` (apps entregues) **e** `recursos_da_empresa()`. A configuração não liga módulo de plano nenhum; ela só esconde do menu o que ainda não tem tela, como antes. `contas.navegacao.modulos_ativos()` continua lendo a configuração; o que muda é que `recursos` passa a vir de `recursos_da_empresa()`, não de `plano.recursos` cru.

4. **A API recusa a rota do módulo desligado com 403 `PLT-12`.** Uma permissão nova, `comum.permissoes.ModuloDoPlano`, entra em `DEFAULT_PERMISSION_CLASSES` logo depois de `IsAuthenticated`. Cada view de módulo declara `recurso_do_plano = Recurso.X` (atributo de classe; viewset com ações de módulos diferentes declara por ação em `recurso_por_acao`). Sem o recurso, vale para leitura e escrita:

   ```json
   { "codigo": "PLT-12", "mensagem": "Seu plano não inclui Manutenção e despesas. Para usar, mude de plano.",
     "detalhes": { "recurso": "manutencao_despesas", "motivo": "plano" } }
   ```

   Quando o plano inclui e o ramo não pede: `motivo: "ramo"` e `"Sua empresa não está configurada para vender. Mude em Configurações."` (ou "alugar"). O nome do módulo na mensagem vem de `Recurso.label`. A permissão vem antes de perfil e filial: quem não tem o módulo recebe sempre o mesmo 403, seja qual for o perfil. Token de suporte segue a mesma recusa. Rotas do `public` (painel da plataforma) não passam por ela.

   `tests/test_permissoes_das_rotas.py` ganha a conferência: toda view dos apps `locacoes`, `vistorias`, `vendas` e `manutencao` declara um recurso, e as de `financeiro` e `relatorios` estão na tabela de "Rotas por recurso" de `docs/api/plataforma.md`.

5. **O que não é rota segue o mesmo conjunto.**
   - **Leituras compostas (ADR 0015):** `registrar_anotacao`, `registrar_contador` e `registrar_total` ganham `recurso=`. Com o recurso desligado, o bloco vem `null` e o contador vale 0, sem rodar a query (ex.: a próxima revisão de `manutencao` na `Frota`).
   - **Painel e Configurações:** um número cuja fonte é de módulo desligado vem `null`, como um número sem fonte (`painel.md`); contador só existe para item do menu, que já some. O cartão `precos` só conta planos especiais com `locacoes_vistoria` ligado.
   - **Tarefas por empresa (ADR 0012):** `tarefa_de_empresa` e `para_cada_empresa` aceitam `recurso=`; a empresa sem ele é pulada sem erro (ex.: preventivas da `MAN-03`, conciliação).
   - **Eventos:** o assinante de módulo desligado não age (`if not tem_recurso(...)`: retorna). Ex.: `manutencao` ignora `locacoes.locacao_encerrada` no Essencial, e a comissão de locação (`FIN-09`) não nasce sem `vendas_comissoes`. O que deixou de acontecer não é refeito ao subir de plano.
   - **Régua (`AUT-03`):** sem `cobranca_whatsapp`, a régua e o "Cobrar" mandam só e-mail; sem `recebimento_parceiro`, não geram Pix nem boleto e usam o texto "Pague na loja", como sem subconta. O recibo da `AUT-05` só existe com `recebimento_parceiro`.
   - **Implantação:** sem `recebimento_parceiro`, o passo `recebimentos` não entra na lista: o Essencial tem 9 passos, e `concluidos`, `total` e `faltam` contam 9.

6. **Os dados nunca saem.** Desligar um recurso não muda status, não cancela nem apaga nada; a rota volta a responder com os mesmos dados quando o recurso volta (`PLT-12`, CA-ASS-23).

7. **O downgrade conta o que está aberto por registro em `comum`.** `comum.modulos.registrar_pendencia(recurso, grupo, contar)` é chamado no `ready()` dos apps donos; `contar()` roda no schema corrente e devolve um inteiro. Grupos (a ordem é a do texto da recusa):

   | Grupo | Recurso | App | Conta |
   | --- | --- | --- | --- |
   | `despesas_aguardando_aprovacao` | `manutencao_despesas` | `financeiro` | despesas `aguardando_aprovacao` |
   | `despesas_a_pagar` | `manutencao_despesas` | `financeiro` | despesas `a_pagar` |
   | `ordens_servico` | `manutencao_despesas` | `manutencao` | OS fora de `concluida` e `cancelada` |
   | `vendas` | `vendas_comissoes` | `vendas` | vendas abertas (`VEN-10`) |
   | `comissoes` | `vendas_comissoes` | `financeiro` | comissões ainda não pagas (`FIN-09`) |

   `plataforma.services.pendencias_dos_modulos(empresa, recursos_que_saem)` entra no schema da empresa (`schema_context`), soma só os grupos dos recursos que saem e devolve os grupos com quantidade maior que zero. Enquanto o app de um grupo não existe, o grupo vale 0 (como os contadores da `FIL-06`). A conferência é a mesma em `mudar_plano` (pedido e simulação, `excede` de `GET /api/assinatura/planos/`) e em `gerar_faturas` (downgrade agendado que deixou de caber). Recursos que saem = `recursos_da_empresa()` hoje menos o que o plano novo liga com o mesmo ramo. Formato da recusa em `docs/api/assinatura.md` (422 `PLT-04`, `detalhes.abertos`).

8. **Catálogo e recurso andam separados.** Os textos de "O que inclui" (`PLT-11`) continuam no catálogo de `plataforma` (`itens`, `oferta`); `Plano.recursos` é só o que o código liga. `GET /api/plataforma/planos/` mostra os dois.

## Consequências

- O menu, as rotas, as tarefas e o downgrade decidem pela mesma função; não há como o menu esconder e a rota responder.
- Cada view nova de módulo precisa declarar `recurso_do_plano`, e o teste das rotas cobra. View esquecida no núcleo fica aberta a todos os planos, que é o comportamento seguro para o núcleo e falha o teste para os quatro apps de módulo.
- Uma leitura do plano por pedido (`connection.tenant` já traz a `Empresa`; o plano é lido uma vez e guardado no próprio pedido). `Plano` muda pouco, então não há cache entre pedidos: mudar de plano vale no pedido seguinte.
- Quem sobe de plano vê tudo de volta na hora; quem desce só desce sem nada aberto nos módulos que saem.
- A régua do Essencial depende do e-mail do cliente; cliente só com celular não recebe cobrança (já era assim sem e-mail, `AUT-03`).
- Pontos registrados para o produto no backlog (`[decisão]`), com o padrão que o backend segue até a resposta: mudar o ramo também desliga módulos, sem conferir pendências (a `PLT-12` só pede a conferência no downgrade); empresa no Essencial que escolhe "só vende" no passo 7 fica sem locações e sem vendas (o conjunto é a interseção, como a regra diz); a comissão de locação de R$ 16,00 (`FIN-09`) não nasce no Essencial, porque comissões é módulo do Profissional.
