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
- **Marca do produto:** o produto se chama **Giro** (kit de logotipo GIRO Motos: grafite `#111114`, verde-limão `#C8F04A`, cinza-claro `#ECEBF0`). A marca Giro aparece só no painel da plataforma, nas telas de compra, no assistente de implantação e no rodapé "Tecnologia Giro". Dentro do sistema da locadora vale a marca da locadora (white label). Logo sempre pelo arquivo SVG, nunca o nome digitado; nunca limão sobre fundo branco. Preços dos planos, parceiro de pagamento e domínio decididos em 07 out 2026 (ver "Decisões de 07 out 2026" no fim).

**Os 3 níveis do sistema**

| Nível | Quem usa | Onde entra | Telas |
| --- | --- | --- | --- |
| Plataforma | Você (dono do produto) e sua equipe interna | `admin.girolocadoras.com.br` | `Plat-*`, `Plataforma-*` |
| Empresa cliente (locadora) | Administrador, gerente, vendedor, vistoriador, financeiro | `<subdominio>.girolocadoras.com.br` | Todas as outras |
| Cliente final da locadora | Locatário ou comprador | Links recebidos por WhatsApp/e-mail (assinar contrato, pagar Pix) | Ainda não desenhadas |

## Entidades e relações

São 25 entidades principais. As 5 primeiras ficam no schema público (plataforma); as demais, no schema de cada empresa.

| Entidade | Campos-chave | Pertence a | Observações |
| --- | --- | --- | --- |
| Plano | nome, preço mensal, limite de veículos, filiais, usuários, recursos | plataforma | Essencial R$ 199 (30/1/3), Profissional R$ 449 (150/3/10), Completo R$ 899 (sem limite); anual = 10 mensalidades |
| Empresa (tenant) | razão social, CNPJ, subdomínio, plano, status, fim do teste | plataforma | um schema por empresa |
| Fatura da assinatura | número FAT-, competência, valor, vencimento, status, forma | Empresa | cobrada pelo parceiro de pagamento |
| Usuário da plataforma | nome, e-mail, função (dono, suporte, financeiro, sucesso), 2FA | plataforma | separado dos usuários das empresas |
| Acesso de suporte | quem, empresa, motivo, chamado, permissão (ver/editar), início, fim | plataforma | sempre com prazo |
| Filial | nome, CNPJ, endereço, horário, matriz sim/não | Empresa | ao menos 1 |
| Usuário | nome, e-mail, celular, perfil, filiais, permissões extras, 2FA, status | Empresa | perfis na seção Usuários |
| Categoria de veículo | nome, diária, semanal, mensal, caução | Empresa (ou filial) | ex.: Urbana 110–125 |
| Veículo | placa, chassi, renavam, modelo, ano, cor, km, categoria, filial, status, valor de compra, valor de venda | Filial | estados na seção Veículos |
| Documento do veículo | tipo (CRLV, IPVA, seguro, rastreador), validade, arquivo | Veículo | alerta 30 dias antes |
| Cliente | tipo (PF/PJ), nome, CPF/CNPJ, CNH, contato, endereço, referência, status | Empresa | compartilhado entre filiais |
| Plano de locação especial | nome, regra (preço fixo ou desconto), condições | Empresa | ex.: Entregador, Mensal fidelidade |
| Locação | LOC-, cliente, veículo, plano, início, fim previsto, valor do período, caução, extras, status | Filial | ciclo na seção Locação |
| Vistoria | tipo (saída/devolução), locação, km, combustível, itens, fotos, avarias, responsável | Locação |  |
| Contrato | modelo, versão do modelo, PDF, status de assinatura, IP, data | Locação ou Venda |  |
| Modelo de contrato | nome, texto com campos, versão, publicado | Empresa | versionado |
| Venda | VEN-, cliente, veículo, preço de tabela, desconto, preço final, forma, entrada, parcelas, troca, vendedor, status | Filial |  |
| Conta a receber (parcela) | origem (locação/venda/multa/avaria), vencimento, valor, status, forma, pago em | Filial |  |
| Despesa (conta a pagar) | descrição, categoria, valor, vencimento, veículo, nota, status | Filial |  |
| Ordem de serviço | OS-, veículo, serviço, oficina, previsão, custo, status | Veículo | gera despesa |
| Caixa do dia | filial, data, aberto por, troco, status | Filial | 1 por filial por dia |
| Movimento de caixa | tipo (entrada/saída/sangria), forma, valor, origem | Caixa do dia |  |
| Lançamento bancário | data, descrição do extrato, valor, conciliado com | Empresa | importado do extrato |
| Comissão | usuário, origem, base, regra, valor, status, mês de pagamento | Usuário |  |
| Evento de auditoria | quem, quando, ação, objeto, antes/depois, IP | Empresa e plataforma | imutável |

Um veículo só pode ter **uma** locação ativa por vez e só pode estar em **uma** venda aberta por vez. Venda aberta é a que está em `proposta`, `negociacao` ou `aguardando_aprovacao` (`VEN-10`); vários registros `interessado` podem existir para o mesmo veículo (decidido em 07 out 2026, T-031).

**Estados das entidades sem seção própria** (decidido em 07 out 2026, T-031). Os estados de empresa, cliente, locação, veículo, venda, conta a receber, despesa, ordem de serviço e comissão ficam nas seções de cada módulo.

| Entidade | Estados | Origem |
| --- | --- | --- |
| Fatura da assinatura | `aberta`, `paga`, `atrasada`, `cancelada` | estados da empresa, `PLT-02` |
| Usuário | `convite_pendente`, `ativo`, `desativado` | `USR-01`, `USR-04` |
| Vistoria | `rascunho`, `concluida` | `DEV-05`, `VIS-04` |
| Contrato | `gerado`, `enviado`, `assinado`, `cancelado` | fluxo da retirada, passo 3 |
| Caixa do dia | `aberto`, `aguardando_aprovacao`, `fechado`, `fechado_sem_conferencia` | `FIN-07`, `FIN-08`, `APR-04` |
| Acesso de suporte | `ativo`, `encerrado`, `revogado` | `PLT-07`, `AUT-15` |
| Pedido de aprovação | `pendente`, `aprovado`, `recusado`, `cancelado` | seção Aprovações |
| Lançamento bancário | `pendente`, `conciliado`, `ignorado` | `FIN-11` |

- Usuário: convite vencido (mais de 7 dias, `USR-01`) continua `convite_pendente`, com o link expirado, e conta no limite do plano até ser reenviado ou cancelado.
- Vistoria: correção de vistoria concluída é uma vistoria nova ligada à anterior, com motivo (`VIS-04`), não um estado.
- Acesso de suporte: `encerrado` quando o prazo acaba ou o suporte sai; `revogado` quando o administrador da empresa bloqueia (`PLT-07`).
- Pedido de aprovação: `cancelado` quando quem pediu desiste ou a origem deixa de existir.

## Plataforma e assinatura

A empresa cliente passa por 6 estados. Só `ativa` e `em_teste` operam normalmente; `suspensa` fica só leitura. Telas: `Compra-Planos`, `Compra-Checkout`, `Compra-Pronto`, `Plat-Empresas`, `Plat-Empresa-Detalhe`, `Plat-Cobranca`, `Admin-Assinatura`, `Admin-Cancelar`.

| Estado | Como entra | O que a empresa pode fazer | Saída |
| --- | --- | --- | --- |
| `em_teste` | compra concluída sem cartão | tudo, dentro do limite do plano escolhido | forma de pagamento cadastrada → `ativa`; 14 dias sem pagamento → `suspensa` |
| `ativa` | 1ª fatura paga | tudo | fatura vencida → `inadimplente` |
| `inadimplente` | fatura vence sem pagamento | tudo, com faixa de aviso no topo | pagou → `ativa`; D+15 → `suspensa` |
| `suspensa` | D+15 de atraso ou teste vencido | só ver e exportar dados; não cria locação, venda nem cobrança | pagou → `ativa` na hora |
| `pausada` | administrador pausa (até 3 meses) | só ver, sem cobrança | volta manual ou ao fim do prazo → `ativa` com nova fatura |
| `cancelada` | administrador confirma o cancelamento | nada; acesso até o fim do período pago | dados apagados 90 dias depois |

**Regras**

- `PLT-01` Teste grátis de 14 dias, sem cartão, no plano escolhido na compra. A 1ª fatura vence no dia seguinte ao fim do teste (ex.: Moto Rápida, teste de 07 a 21 out).
- `PLT-02` Régua de cobrança da assinatura: D-3 lembrete por e-mail; D0 e-mail + WhatsApp; D+3 e-mail + WhatsApp; D+7 aviso de suspensão (e-mail + ligação da equipe); D+15 suspensão automática. Cartão recusado tenta de novo no dia seguinte.
- `PLT-03` Limites do plano (veículos, filiais, usuários): aviso ao administrador em 90%; em 100% bloqueia só novos cadastros daquele item, nunca a operação do que já existe.
- `PLT-04` Mudança de plano: upgrade vale na hora e cobra a diferença proporcional; downgrade só se o uso couber no plano menor, e vale na próxima fatura.
- `PLT-05` Preço novo de plano vale só para novas assinaturas; reajuste de quem já assina exige aviso de 30 dias.
- `PLT-06` Cancelamento pede motivo, oferece pausar ou mudar para o Essencial, e exige digitar o nome da empresa. Contratos já assinados com clientes finais continuam válidos.
- `PLT-07` **Entrar como suporte:** só com motivo (de preferência um chamado), duração de 15 min, 30 min ou 1 h, permissão "só ver" ou "ver e editar". O administrador da empresa recebe e-mail na hora; aparece uma faixa "Modo suporte" no topo; entrada e saída ficam na auditoria da empresa e na da plataforma. O administrador pode bloquear o acesso do suporte. Mesmo com "ver e editar", o suporte vê dados pessoais mascarados (`AUD-09`).
- `PLT-08` Usuários da plataforma são obrigados a usar verificação em 2 etapas. 3 códigos errados bloqueiam o login por 15 minutos e geram evento de segurança.
- `PLT-09` Funções da equipe interna: **Dono** (tudo); **Suporte** (ver empresas, chamados, entrar como suporte); **Financeiro** (cobrança, faturas, suspender); **Sucesso do cliente** (ver empresas, implantações, entrar como suporte, estender teste, mudar plano). Só o Dono mexe em planos e na equipe.
- `PLT-10` Indicadores do painel (`Plataforma-Desktop`): receita recorrente = soma das assinaturas ativas e inadimplentes; cancelamentos do mês / empresas pagantes no início do mês = taxa de cancelamento.

## Implantação

Da compra até a 1ª locação são 12 etapas. As 4 primeiras são a compra e o primeiro acesso; as 8 seguintes formam o assistente, que pode ser pausado e retomado de onde parou. Telas: `Compra-Planos` → `Compra-Checkout` → `Compra-Pronto` → `Acesso-Senha` → `Onboarding-*` (8 passos) → `Pos-Dashboard`.

| # | Etapa | Tela | O que grava | Obrigatória |
| --- | --- | --- | --- | --- |
| 1 | Escolher plano | `Compra-Planos` | plano escolhido | sim |
| 2 | Dados e pagamento | `Compra-Checkout` | empresa, CNPJ, administrador, subdomínio; cartão opcional | sim |
| 3 | Conta criada | `Compra-Pronto` | cria schema da empresa, status `em_teste`, envia e-mail de acesso | automática |
| 4 | Criar senha | `Acesso-Senha` | senha + 2 etapas do administrador | sim |
| 5 | Marca | `Onboarding-Marca` | logo, cor, nome de exibição | não (usa padrão) |
| 6 | Primeira filial | `Onboarding-Filial` | filial matriz com endereço e horário | sim |
| 7 | Ramo | `Onboarding-Ramo` | trabalha com motos, carros ou os dois; aluga, vende ou os dois. Liga ou desliga módulos | sim |
| 8 | Preços | `Onboarding-Precos` | categorias com diária, semanal, mensal e caução | sim para quem aluga |
| 9 | Contrato | `Onboarding-Contrato` | publica o 1º modelo de contrato (a partir de um modelo pronto) | sim para alugar |
| 10 | Recebimentos | `Onboarding-Recebimentos` | conecta parceiro de pagamento (Pix, cartão, boleto) | não (só dinheiro e Pix manual) |
| 11 | Importar dados | `Onboarding-Importar` | veículos e clientes por planilha | não |
| 12 | Equipe | `Onboarding-Equipe` | convites com perfil e filial | não |

**Regras**

- `IMP-01` A implantação está "concluída" quando existe a 1ª locação ou venda. Antes disso, a tela inicial do administrador é `Pos-Dashboard`, com a lista do que falta.
- `IMP-02` A importação valida cada linha antes de gravar: placa única, chassi único com 17 caracteres (`VEI-01`), categoria existente. Linhas com erro não entram e ficam numa lista para corrigir (Moto Rápida: 83 prontos, 3 para corrigir; depois de corrigidos, 86 veículos).
- `IMP-03` Importar respeita o limite do plano (`PLT-03`). Se a planilha passa do limite, importa até o limite e avisa.
- `IMP-04` Sem modelo de contrato publicado, o sistema não deixa concluir uma locação (aparece o atalho para o passo 9). Foi o motivo do chamado #1042 da Moto Rápida.
- `IMP-05` O progresso de cada empresa alimenta o funil do painel da plataforma (`Plat-Implantacoes`): Conta → Marca → Filial → Preços → Dados → 1ª locação. Empresa que fica 3 dias ou mais no mesmo passo entra em "precisam de ajuda".
- `IMP-06` Mensagens automáticas durante o teste: parada há 2 dias (e-mail + WhatsApp), faltam 3 dias de teste (e-mail), teste acabou (e-mail).

## Usuários, perfis e permissões

Cada usuário tem 1 perfil e uma lista de filiais. O perfil define o menu e as ações; a filial define quais dados ele vê. Telas: `Admin-Usuarios`, `Convite`, `Login`, e as iniciais de cada perfil (`Gerente`, `Vendedor`, `Vistoriador`, `Financeiro`, `Main`/`Pos-Dashboard`).

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver painel e relatórios | todas as filiais | sua filial | só os seus números | — | todas as filiais |
| Cadastrar e editar veículo | sim | sim | — | atualizar km e avarias | — |
| Cadastrar cliente | sim | sim | sim | — | — |
| Criar locação | sim | sim | sim | — | — |
| Fazer vistoria (saída e devolução) | sim | sim | sim | sim | — |
| Cancelar locação | sim | aprova | pede | — | — |
| Desconto acima de 5% | sim | aprova | pede | — | — |
| Criar venda / proposta | sim | sim | sim | — | — |
| Receber pagamento no caixa | sim | sim | sim | — | sim |
| Abrir e fechar caixa, sangria | sim | sim | sim (sua filial) | — | sim |
| Lançar despesa | sim | sim | sim | sim (manutenção) | sim |
| Aprovar despesa acima de R$ 500 | sim | aprova | — | — | — |
| Pagar contas, conciliação, comissões | sim | — | — | — | sim |
| Abrir ordem de serviço | sim | sim | — | sim | — |
| Administração (marca, filiais, usuários, preços, contratos, integrações, assinatura, auditoria, exportar) | sim | — | — | — | — |

**Regras**

- `USR-01` Convite por e-mail, e também por WhatsApp quando a pessoa tem celular, com link válido por 7 dias. O e-mail é obrigatório em todo usuário, porque é o login (`USR-06`); o celular é opcional. A pessoa cria a senha e entra já com perfil e filiais definidos. Convite pendente conta no limite de usuários do plano.
- `USR-02` Verificação em 2 etapas obrigatória para administrador e financeiro; opcional para os demais (o administrador pode tornar obrigatória para todos).
- `USR-03` Permissões extras por pessoa (marcar em `Admin-Usuarios`): aprovar descontos acima de 5%, cancelar contratos, ver relatórios de todas as filiais. Elas somam ao perfil, nunca tiram.
- `USR-04` Desativar usuário encerra a sessão na hora. O histórico do que ele fez continua. Usuário desativado não conta no limite do plano.
- `USR-05` Menu: tela inicial de cada perfil usa o menu daquele perfil; telas compartilhadas usam o menu completo, escondendo os itens sem permissão. Itens sem permissão nunca aparecem desabilitados, simplesmente não aparecem.
- `USR-06` Login com e-mail e senha; 5 tentativas erradas bloqueiam por 15 minutos e avisam o administrador. Sessão expira após 12 h sem uso no desktop e 30 dias no celular. Não existe opção "manter conectado".
- `USR-07` Escopo de filial: o seletor de filial no topo do menu mostra só as filiais da pessoa. Administrador pode escolher "Todas as filiais".

*Mudanças em 07 out 2026 (T-037):* `USR-01` passou a dizer que o e-mail é obrigatório e o celular é opcional; `USR-06` deixou claro que não há "manter conectado".

## Filiais

A empresa tem ao menos uma filial ativa, e uma delas é a matriz. Veículos, locações, caixa do dia, vistorias e ordens de serviço são de uma filial; clientes, marca, modelos de contrato e usuários são da empresa (cada usuário com acesso escolhido por filial, `USR-07`). Telas: `Filiais`, `Filial`, `Onboarding-Filial`.

**Regras**

- `FIL-01` Cadastro: nome (único na empresa), CNPJ e inscrições (opcionais), endereço, contato, horário por dia da semana (até 2 intervalos por dia, para quem fecha no almoço) e feriados (`FIL-03`). A filial é ativa ou inativa, sem rascunho: só salva com os campos obrigatórios. A primeira filial é sempre a matriz, e só existe uma matriz.
- `FIL-02` Os gerentes da filial são os usuários com perfil gerente ligados a ela (`USR-07`), e não um campo da filial. Avisos e tarefas "para o gerente" vão a todos os gerentes da filial.
- `FIL-03` Feriados: cada filial tem uma lista de datas em que fica fechada, cadastrada pelo administrador. A cada ano o sistema sugere os feriados nacionais, e o administrador confirma ou acrescenta os locais. Em dia de feriado a filial conta como fechada para `LOC-11`.
- `FIL-04` O preço pode ser da empresa ou de uma filial, pela categoria (`LOC-01`, tela `Precos`). Não há "tabela de preço padrão", vagas no pátio nem centro de custo na filial: a própria filial é o centro de custo (DRE por filial, `FIN-13`). O recebimento é da empresa, numa única subconta do parceiro de pagamento (Decisões de 07 out 2026). O sistema não emite nota fiscal.
- `FIL-05` A frota é de cada filial. A devolução é feita na filial da locação, e não há frota compartilhada: para usar o veículo de outra filial, ele é transferido antes (`VEI-04`).
- `FIL-06` Desativar filial: só o administrador, com motivo. É recusado quando a filial é a matriz (escolher outra antes), quando é a última filial ativa, ou quando ainda tem operação. Operação aqui é: veículos fora de `vendido` e `baixado`; locações em `rascunho`, `aguardando_retirada`, `ativa` ou `devolucao_atrasada`; caixa do dia `aberto` ou `aguardando_aprovacao`. A recusa mostra quanto falta em cada grupo. Contas a receber em aberto e despesas a pagar não impedem: continuam na régua de cobrança (`AUT-03`), podem ser pagas por Pix ou boleto (`FIN-04`) ou no caixa de outra filial, e mantêm a filial de origem para relatório e DRE. Nada é apagado; reativar respeita o limite do plano (`PLT-03`).

*Criada em 07 out 2026 (T-037), a partir da tela `Filial` e das dúvidas da T-030 decididas pelo dono do produto.*

## Veículos

O veículo tem 8 estados e só muda de estado por um evento de outro módulo (locação, vistoria, manutenção, venda) ou por ação explícita do gerente. Telas: `Frota`, `Veiculo`, `Manutencao`, `Vendas`.

| Estado | Significa | Pode ser alugado? | Aparece em |
| --- | --- | --- | --- |
| `disponivel` | na filial, pronto | sim | Frota (filtro Disponíveis), Nova locação |
| `reservado` | separado para uma locação com retirada marcada | só por quem reservou | Frota, agenda do vistoriador |
| `alugado` | com uma locação ativa | não | Frota, Locações |
| `em_manutencao` | com uma ordem de serviço aberta | não | Frota, Manutenções |
| `indisponivel` | parado por documento vencido, sinistro ou decisão do gerente | não | Frota |
| `a_venda` | saiu da frota de locação e está à venda | não | Vendas, Veículos à venda |
| `vendido` | venda concluída | não | histórico |
| `baixado` | perda total, roubo, sucata | não | histórico |

**Transições permitidas**

| De | Para | Evento que dispara | Quem |
| --- | --- | --- | --- |
| `disponivel` | `reservado` | locação criada com retirada futura | vendedor, gerente |
| `disponivel` ou `reservado` | `alugado` | vistoria de saída concluída e contrato assinado | sistema |
| `alugado` | `disponivel` | devolução encerrada sem avaria | sistema |
| `alugado` | `em_manutencao` | devolução encerrada com avaria marcada "vai para oficina" | sistema |
| `disponivel` | `em_manutencao` | OS aberta (manual ou preventiva) | gerente, vistoriador |
| `em_manutencao` | `disponivel` | OS concluída e veículo liberado | gerente |
| `disponivel` | `indisponivel` | documento vence (automático) ou bloqueio manual | sistema, gerente |
| `indisponivel` | `disponivel` | documento renovado ou desbloqueio | gerente |
| `disponivel` | `a_venda` | "Colocar à venda" na ficha | gerente, administrador |
| `a_venda` | `disponivel` | "Voltar para a frota" | gerente, administrador |
| `a_venda` | `vendido` | venda concluída (pagamento ou contrato) | sistema |
| `vendido` | `a_venda` | venda cancelada (`VEN-07`) | sistema |
| `vendido` | `indisponivel` | veículo recomprado numa troca (`VEN-05`, `VEI-07`) | sistema |
| qualquer, exceto `alugado` | `baixado` | baixa com motivo | administrador |

Qualquer outra transição é recusada pelo backend com erro de regra (HTTP 409).

**Regras**

- `VEI-01` Placa e chassi únicos por empresa, em qualquer estado do veículo; chassi com 17 caracteres; km nunca diminui (vistoria com km menor que o anterior é recusada, salvo correção pelo gerente com motivo).
- `VEI-02` O km do veículo é atualizado a cada vistoria e a cada OS. Ele dispara as preventivas (`MAN-03`).
- `VEI-03` Documentos: alerta 30 dias antes do vencimento; no dia do vencimento de CRLV ou seguro, o veículo disponível vai para `indisponivel`. Veículo alugado não muda, mas gera tarefa urgente para o gerente.
- `VEI-04` Transferência entre filiais só com o veículo `disponivel`. Grava a filial de origem e destino. É o único jeito de um veículo mudar de filial: a devolução é sempre na filial da locação e a frota não é compartilhada (`FIL-05`).
- `VEI-05` "Rendeu no ano" na ficha = receitas de locação recebidas do veículo − custos de manutenção e despesas ligadas a ele, no ano corrente.
- `VEI-06` Ocupação = dias alugado ÷ dias que o veículo esteve na frota no período (exclui `a_venda`, `vendido`, `baixado`). Ocupação da frota = média ponderada pelos dias.
- `VEI-07` Veículo que volta para a empresa depois de vendido (recompra numa troca, `VEN-05`) reaproveita o cadastro existente, achado pelo chassi, e não ganha outro: vai de `vendido` para `indisponivel` até a vistoria, e o histórico continua no mesmo veículo.

*Mudanças em 07 out 2026 (T-031):* `VEI-01` passou a exigir chassi único, além da placa; criada a `VEI-07`; acrescentadas as transições `vendido` → `a_venda` e `vendido` → `indisponivel`.
*Mudanças em 07 out 2026 (T-037):* `VEI-04` passou a dizer que a devolução é na filial da locação e que não há frota compartilhada.

## Clientes

O cliente é da empresa (compartilhado entre filiais) e tem 4 estados: `incompleto`, `ativo`, `bloqueado`, `inativo`. Só cliente `ativo` pode retirar um veículo. Telas: `Clientes` (lista) e `Cliente` (cadastro, aberto pelo botão "Novo cliente").

**Cadastro**

- Pessoa física: nome, CPF, nascimento, celular/WhatsApp, e-mail, profissão, CNH (número, categoria, validade, 1ª habilitação), endereço com CEP, referência pessoal (nome, parentesco, telefone).
- Pessoa jurídica: razão social, CNPJ, responsável (com os dados de pessoa física e CNH do condutor).
- Documentos: foto da CNH (frente e verso), selfie com documento, comprovante de residência.
- Consentimento para uso dos dados em locação e cobrança, com data e hora (LGPD).

**Regras**

- `CLI-01` CPF e CNPJ validados pelo dígito verificador e únicos por empresa. CEP preenche rua, bairro e cidade.
- `CLI-02` Para alugar moto, CNH categoria A; para carro, categoria B. CNH vencida há mais de 30 dias impede a retirada.
- `CLI-03` Cliente fica `incompleto` enquanto faltar algum documento obrigatório. Pode ser salvo e pode ter locação criada, mas a retirada (vistoria de saída) só libera com o cadastro completo.
- `CLI-04` Análise do cadastro (painel ao lado do formulário): CPF válido e regular, CNH válida na categoria, fora da lista de bloqueio da empresa, consulta de crédito (se a integração existir). Cada item mostra ok, pendente ou problema.
- `CLI-05` Bloqueio automático com 15 dias de atraso em qualquer valor (parcela, devolução, multa). Cliente bloqueado não faz nova locação nem compra; desbloqueia sozinho ao quitar. Gerente e administrador podem bloquear ou desbloquear manualmente, na hora, com motivo e evento de auditoria. O vendedor não desbloqueia: ele pede, e o gerente aprova (`APR-05`).
- `CLI-06` A lista mostra, por cliente: situação, locação atual, total pago, valor em aberto e "cliente desde". Filtros: todos, com locação, em aberto, bloqueados, cadastro incompleto.
- `CLI-07` Botão de ação na lista conforme a situação: em aberto → Cobrar; com locação → Ver locação; incompleto → Completar cadastro; sem locação → Nova locação.
- `CLI-08` "Salvar e iniciar locação" grava o cliente e abre a Nova locação com ele já escolhido.

*Mudanças em 07 out 2026 (T-041):* `CLI-05` e `APR-05` passaram a dizer que gerente e administrador desbloqueiam direto e só o vendedor pede aprovação (decisão do dono do produto, item 12).

## Locação

A locação é o centro do sistema: liga cliente, veículo, contrato, vistorias, parcelas e caixa. Ela tem 6 estados e 3 sinais que aparecem por cima do estado. Telas: `Locacoes` (lista), `Locacao` (Nova locação, 3 passos: Dados → Vistoria → Assinatura), `Vistoria`, `Locacao-Detalhe`, `Devolucao`.

| Estado | Significa |
| --- | --- |
| `rascunho` | dados preenchidos, nada confirmado; some após 24 h sem uso |
| `aguardando_retirada` | cliente e veículo definidos; falta vistoria de saída, assinatura ou 1º pagamento (ex.: LOC-2856, "Aguardando assinatura") |
| `ativa` | veículo com o cliente, dentro do prazo |
| `devolucao_atrasada` | passou do fim previsto + tolerância sem devolução (ex.: LOC-2790, 25 dias) |
| `encerrada` | devolução feita e acerto concluído |
| `cancelada` | cancelada antes ou durante, com aprovação |

Sinais (não são estados, são calculados): `pagamento_atrasado` (alguma parcela vencida e não paga, ex.: LOC-2841), `devolve_hoje` (fim previsto hoje, ex.: LOC-2836), `cancelamento_pendente` (pedido aguardando o gerente, ex.: LOC-2812).

**Fluxo da retirada**

1. **Dados** (`Locacao`, passo 1): cliente, veículo `disponivel` ou `reservado`, plano (diária, semanal, mensal ou plano especial), início, fim previsto, extras (capacete extra, baú etc.), forma de pagamento. O sistema calcula o valor e mostra o resumo.
2. **Vistoria de saída** (`Vistoria`): fotos obrigatórias, km, combustível, itens conferidos. Pode ser feita pelo vistoriador no celular.
3. **Assinatura** (`Locacao`, passo 3): contrato gerado do modelo publicado, enviado por WhatsApp; o cliente assina no celular (grava IP, data e hora).
4. **Pagamento**: 1ª parcela e caução recebidas (caixa, Pix ou cartão).
5. Com os 3 concluídos (vistoria, assinatura, 1º pagamento), a locação vira `ativa` e o veículo vira `alugado`. A ordem 2–4 pode variar.

**Cálculos**

- `LOC-01` Valor do período vem da categoria do veículo (`Precos`): diária × dias, semanal por semana, mensal por mês. Plano especial substitui ou desconta (ex.: Entregador R$ 279,00/semana; Mensal fidelidade −10% a partir do 3º mês).
- `LOC-02` Extras somam por período, com valor fixo configurado.
- `LOC-03` Desconto do vendedor até 5% sem aprovação; acima disso vai para o gerente (`APR-01`).
- `LOC-04` Caução é cobrada uma vez, na retirada, pelo valor da categoria (motos R$ 300 ou R$ 500, carros R$ 800). Não é receita: fica como valor a devolver até o acerto.
- `LOC-05` Parcelas são antecipadas. Diária: tudo na retirada. Semanal: 1ª na retirada, depois a cada 7 dias. Mensal: 1ª na retirada, depois a cada mês. Pode ser Pix automático (cobrança recorrente).
- `LOC-06` Exemplo LOC-2836 (Juliana, semanal R$ 329,00): parcela 1 em 30 set, parcela 2 em 07 out, caução R$ 300,00 → total pago R$ 958,00.

**Durante a locação**

- `LOC-07` Parcela vencida acende `pagamento_atrasado` e entra na régua de cobrança (`AUT-03`). Com 15 dias, o cliente é bloqueado (`CLI-05`).
- `LOC-08` Renovação estende o fim previsto e gera as novas parcelas na mesma locação (não cria outro LOC). Contrato ganha um aditivo automático.
- `LOC-09` Troca de veículo durante a locação: devolução do veículo antigo + vistoria de saída do novo, na mesma locação; o valor passa a ser o da nova categoria a partir da troca.

**Atraso e cancelamento**

- `LOC-10` Tolerância de 1 hora após o fim previsto. Depois disso, cada dia ou fração cobra 1 diária da categoria, e a locação vai para `devolucao_atrasada` no dia seguinte.
- `LOC-11` Devolução fora do horário da filial conta como feita na abertura seguinte, mas o atraso só é cobrado se já tinha passado da tolerância no horário em que a filial fechou. Feriado da filial (`FIL-03`) conta como dia fechado: o atraso não corre nesses dias, e a devolução prevista para um feriado pode ser feita na abertura seguinte sem atraso.
- `LOC-12` Cancelamento é pedido pelo vendedor e aprovado pelo gerente (`APR-02`). Antes da retirada: sem multa, devolve o que foi pago. Depois da retirada (encerramento antecipado): multa de 20% sobre o valor dos dias restantes do período em curso (preço do período ÷ dias do período × dias restantes), com mínimo de 1 diária da categoria, e acerto como numa devolução. Diária: sem multa, cobra só os dias usados. Ex.: Patrícia, LOC-2812, NMax mensal R$ 1.590,00, pede em 07 out com 8 dias restantes → restante R$ 424,00 → multa R$ 84,80.
- `LOC-13` Devolução antecipada (antes do fim) não devolve parcela já paga, salvo plano mensal, que devolve as semanas inteiras não usadas (7 × preço mensal ÷ 30 por semana), menos a multa do `LOC-12`. Se a multa for maior que a devolução, a diferença vira conta a receber. Ex.: Patrícia → 1 semana inteira R$ 371,00 − multa R$ 84,80 = devolve R$ 286,20.
- `LOC-14` Plano mensal é cobrado por mês fechado (valor da tabela, ex.: Urbana R$ 1.090), nunca como diária × 30. Pode ser pago à vista ou em 4 parcelas semanais. Período menor que um mês usa diária ou semanal.
- `LOC-15` Preço da tabela vale para contratos novos; contrato já assinado mantém o preço da data da assinatura até o fim (renovação usa o preço novo). A tabela guarda o histórico de preços.

**Lista de locações** (`Locacoes`): filtros Todas, Precisam de ação (atraso de devolução, parcela atrasada, aguardando assinatura, cancelamento pendente), Devolvem hoje, Encerradas. O botão de cada linha muda: Cobrar, Receber devolução ou Abrir.

*Mudanças em 07 out 2026 (T-037):* `LOC-11` passou a contar os feriados da filial como dias fechados (`FIL-03`).

## Vistoria e devolução

Toda retirada e toda devolução têm uma vistoria, e a devolução é sempre comparada com a vistoria de saída da mesma locação. Telas: `Vistoria` (saída), `Devolucao` (3 passos: Vistoria → Acerto → Recibo), `Vistoriador` (agenda do dia).

**Vistoria de saída**

- `VIS-01` Fotos obrigatórias: frente, traseira, lado esquerdo, lado direito, painel com km e combustível. Avarias já existentes são marcadas com foto e descrição, para não serem cobradas depois.
- `VIS-02` Itens conferidos (lista configurável por ramo): pneus e freios, luzes e buzina, retrovisores, documento e chave, acessórios entregues (capacete etc.).
- `VIS-03` Combustível em 5 níveis: reserva, 1/4, 1/2, 3/4, cheio.
- `VIS-04` A vistoria fica presa à locação e não pode ser editada depois de concluída; correção vira uma nova vistoria com motivo.
- `VIS-05` Agenda do vistoriador = retiradas reservadas + devoluções previstas do dia na sua filial, em ordem de horário. Item passado do horário aparece como atrasado.

**Devolução**

1. **Vistoria de chegada:** km atual, combustível, mesmas fotos e itens da saída. A tela mostra lado a lado "Saída" e "Agora". Avaria nova é marcada com foto, descrição e valor.
2. **Acerto:** o sistema monta a conta (abaixo) e mostra quanto devolver ou cobrar.
3. **Recibo:** encerra a locação e envia recibo com fotos por WhatsApp.

**Acerto da caução**

- `DEV-01` Cobranças possíveis: combustível faltante (preço da bomba por litro + R$ 10 de taxa), avarias novas (valor da tabela de peças ou orçamento), atraso (`LOC-10`), km excedente (se o plano tiver limite), parcelas em aberto, multas de trânsito já identificadas.
- `DEV-02` Saldo = caução − soma das cobranças. Saldo positivo é devolvido ao cliente (Pix, dinheiro ou estorno do cartão). Saldo negativo vira uma conta a receber do cliente, com vencimento em 3 dias.
- `DEV-03` Exemplo LOC-2836: combustível R$ 32,00 + retrovisor R$ 85,00 = R$ 117,00; caução R$ 300,00 → devolver R$ 183,00 por Pix.
- `DEV-04` Avaria marcada como "vai para oficina" abre uma OS e o veículo vai para `em_manutencao`. Sem isso, volta para `disponivel`.
- `DEV-05` "Salvar e continuar depois" guarda a devolução como rascunho; a locação continua `ativa` (ou `devolucao_atrasada`) até o encerramento.
- `DEV-06` Ao encerrar: locação `encerrada`, km do veículo atualizado, devolução da caução lançada no caixa ou no financeiro, preventivas recalculadas.

## Vendas

A venda tem 7 estados (o funil da tela mostra os 4 principais) e só vende veículo `a_venda`. Telas: `Vendas` (lista), `Venda` (Nova venda, 3 passos: Negócio → Documentos → Assinatura), `Vendedor` (início da vendedora), `Gerente` (aprovações), `Comissoes`.

| Estado | Significa |
| --- | --- |
| `interessado` | contato registrado, sem proposta |
| `proposta` | proposta com valor e forma de pagamento enviada ao cliente |
| `negociacao` | cliente respondeu; contraproposta, troca ou financiamento em análise |
| `aguardando_aprovacao` | desconto acima do limite; espera o gerente |
| `vendida` | contrato assinado e entrada (ou valor total) recebida |
| `perdida` | cliente desistiu ou proposta venceu (7 dias sem resposta) |
| `cancelada` | venda concluída desfeita (`VEN-07`); só a partir de `vendida` |

**Regras**

- `VEN-01` Preço de tabela = valor de venda definido ao colocar o veículo à venda (referência FIPE exibida ao lado).
- `VEN-02` Desconto até 5% o vendedor dá sozinho; acima de 5% a venda vai para `aguardando_aprovacao` e o gerente aprova ou recusa pelo celular (`APR-01`). Ex.: VEN-0177, CB 300F, R$ 22.900 com 8% = R$ 21.068.
- `VEN-03` Formas: à vista (Pix ou TED), entrada + parcelas (boleto ou Pix mensal, gera contas a receber), financiamento pelo banco parceiro (venda fica em `negociacao` até o banco aprovar).
- `VEN-04` Parcelas: saldo ÷ número de parcelas, sem juros por padrão; juros configuráveis por empresa. Ex.: R$ 21.068 − R$ 5.000 = R$ 16.068 em 12 × R$ 1.339.
- `VEN-05` Troca: o veículo do cliente entra com valor de avaliação, abate do preço e é cadastrado na frota como `indisponivel` até a vistoria. Se o chassi já existe na empresa (veículo vendido antes), o cadastro é reaproveitado (`VEI-07`).
- `VEN-06` Ao virar `vendida`: gera o contrato de compra e venda, cria as parcelas em contas a receber, o veículo vai para `vendido` e sai de todos os indicadores da frota, e a comissão do vendedor é lançada (`FIN-09`).
- `VEN-07` Venda `vendida` pode ser cancelada (desistência dentro do prazo legal) só por gerente ou administrador, com motivo obrigatório e evento de auditoria. Ao cancelar: parcelas em aberto vão para `cancelada`, parcelas pagas são estornadas, a comissão vai para `estornada` (`FIN-09`) e o veículo volta de `vendido` para `a_venda`. Antes de `vendida`, desistência é `perdida`.
- `VEN-08` Funil do mês na lista e no início da vendedora: interessados, proposta, negociação, vendido. Conversão = vendidas ÷ interessados dos últimos 30 dias.
- `VEN-09` Meta de vendas por vendedor e mês (valor em R$), definida pelo gerente. A barra mostra vendido ÷ meta.
- `VEN-10` Uma venda aberta por veículo (`proposta`, `negociacao` ou `aguardando_aprovacao`); `interessado` não conta. Quando o veículo vira `vendido`, os outros registros `interessado` dele vão para `perdida` com o motivo "veículo vendido".

*Mudanças em 07 out 2026 (T-031):* criado o estado `cancelada` e reescrita a `VEN-07` (quem cancela e o que acontece); `VEN-05` ganhou o reaproveitamento do cadastro; criada a `VEN-10`.

## Financeiro

Todo dinheiro que entra ou sai passa por uma conta a receber, uma despesa ou um movimento de caixa, e todo pagamento aponta para a origem (locação, venda, OS, despesa). Telas: `Receber`, `Despesas`, `Caixa`, `Conciliacao`, `Comissoes`, `Relatorios`, `Financeiro` (início da financeira).

**Contas a receber**

- `FIN-01` Estados: `aberta`, `vence_hoje`, `atrasada`, `paga`, `cancelada`, `renegociada`. Pagamento parcial não existe: ou paga a parcela inteira ou renegocia.
- `FIN-02` Faixas de atraso para a tela: 1–7 dias, 8–30 dias, mais de 30 dias.
- `FIN-03` Juros e multa por atraso configuráveis por empresa, com teto: multa de até 2% (CDC, art. 52, §1º) e juros de mora de até 1% ao mês, pro rata dia. Padrão: 2% + 1% ao mês. Calculados na hora do pagamento e escritos no contrato (sem cláusula no contrato, não cobra juros).
- `FIN-04` Pagamento por Pix ou boleto do parceiro baixa a conta sozinho (webhook). Dinheiro e cartão na maquininha são baixados no caixa.

**Contas a pagar e despesas**

- `FIN-05` Estados: `aguardando_aprovacao`, `a_pagar`, `paga`, `recusada`. Despesa acima de R$ 500 nasce `aguardando_aprovacao` (`APR-03`); até R$ 500 nasce `a_pagar` (ou `paga`, se lançada como paga no caixa).
- `FIN-06` Categorias: fixas (aluguel, luz, internet), manutenção, rastreamento, impostos, pessoal, outros. Despesa pode ser ligada a um veículo (entra no custo dele) e deve ter foto da nota.

**Caixa do dia**

- `FIN-07` Um caixa por filial por dia. Abre com o troco (ex.: R$ 200,00); registra entradas por forma (Pix, cartão, dinheiro), saídas e sangrias. No fechamento a pessoa conta o dinheiro; o sistema compara com "deve ter na gaveta" = troco + entradas em dinheiro − saídas em dinheiro. Diferença exige motivo e avisa o gerente. Ex.: 200 + 629 − 548 = R$ 281,00.
- `FIN-08` Caixa não fechado até 23h59 fecha sozinho com status `fechado_sem_conferencia` e gera tarefa para o gerente.

**Comissões**

- `FIN-09` Regras padrão (configuráveis): 3% do preço final em vendas; R$ 16,00 por locação nova; renovação não gera comissão. Comissão nasce `pendente` quando a venda espera aprovação, `confirmada` quando vira vendida, `paga` no dia 5 do mês seguinte, `estornada` se a venda for cancelada.
- `FIN-10` Exemplo outubro, Bruna: 4 vendas (R$ 31.200 × 3% = R$ 936,00) + 2 locações (R$ 32,00) = R$ 968,00 confirmados; R$ 632,04 da CB 300F pendentes.

**Conciliação bancária**

- `FIN-11` O extrato é importado (integração ou arquivo OFX). Para cada linha o sistema sugere um par por valor e data (±3 dias) e nome do pagador. A pessoa confirma, cria o lançamento que falta ou ignora.
- `FIN-12` Diferença entre saldo do banco e do sistema = soma das linhas sem par. Ex.: +R$ 150,00 (Pix sem lançamento) − R$ 12,90 (tarifa) = R$ 137,10.

**Relatórios e DRE**

- `FIN-13` DRE simplificada por mês e filial: receita de locações + multas, extras e avarias − taxas de pagamento = receita líquida; − despesas − comissões = resultado. Caução não entra como receita. Venda de veículo entra em linha separada (receita de venda − valor contábil do veículo).
- `FIN-14` Relatórios prontos (planilha e PDF): DRE, locações por cliente, rentabilidade por veículo, inadimplência por faixa, comissões, manutenções por veículo e oficina.

## Manutenção e despesas

Toda manutenção é uma ordem de serviço ligada a um veículo, e todo custo dela vira uma despesa. Telas: `Manutencao` (quadro de OS), `Veiculo` (histórico), `Despesas`.

| Estado da OS | Significa | Veículo fica |
| --- | --- | --- |
| `agendada` | preventiva prevista por km ou data | no estado atual |
| `aguardando` | aberta, esperando aprovação do orçamento ou vaga na oficina | `em_manutencao` se já parado |
| `na_oficina` | veículo entregue à oficina | `em_manutencao` |
| `concluida` | serviço pronto e veículo liberado | `disponivel` |
| `cancelada` | não será feita | volta ao estado anterior |

**Regras**

- `MAN-01` OS tem: veículo, serviço, oficina (cadastro de oficinas parceiras), previsão de volta, orçamento e custo final. OS sem previsão não pode ir para `na_oficina`.
- `MAN-02` Orçamento acima de R$ 500 precisa de aprovação do gerente antes de executar (`APR-03`). Ex.: OS-118, pneus R$ 1.200,00.
- `MAN-03` Preventivas automáticas por regra da empresa: troca de óleo a cada 1.000 km, revisão a cada 5.000 km, pneus conferidos em toda devolução. Quando faltam 500 km, cria OS `agendada`; se o veículo está alugado, a OS é marcada para a devolução.
- `MAN-04` OS que passa da previsão vira atrasada (destaque vermelho) e avisa o gerente.
- `MAN-05` Ao concluir: lança a despesa com o custo final (ligada ao veículo), atualiza km e data da última manutenção, recalcula a próxima preventiva e libera o veículo.
- `MAN-06` Indicadores: veículos fora de operação, gasto do mês, tempo médio na oficina (meta 2 dias), preventivas nos próximos 500 km.

## Aprovações

Tudo que precisa de aprovação usa o mesmo mecanismo: o pedido fica `pendente`, aparece no topo do início do gerente (`Gerente`) e só tem efeito quando aprovado. Recusado, a origem volta ao estado anterior e quem pediu é avisado com o motivo.

| Código | O que | Limite | Quem pede | Quem aprova | Efeito ao aprovar |
| --- | --- | --- | --- | --- | --- |
| `APR-01` | Desconto em locação ou venda | acima de 5% | vendedor | gerente (ou permissão extra) | libera o preço com desconto; venda segue o funil |
| `APR-02` | Cancelamento de locação | sempre | vendedor | gerente | cancela e calcula multa e acerto |
| `APR-03` | Despesa ou orçamento de OS | acima de R$ 500 | qualquer perfil que lança despesa | gerente | despesa vai para `a_pagar`; OS pode executar |
| `APR-04` | Diferença no fechamento do caixa | qualquer valor | quem fecha o caixa | gerente | caixa fechado com a diferença registrada |
| `APR-05` | Desbloqueio manual de cliente | pedido pelo vendedor (gerente e administrador desbloqueiam direto, `CLI-05`) | vendedor | gerente | cliente volta a `ativo` (ou `incompleto`, se faltar cadastro) |
| `APR-06` | Correção de km para baixo | sempre | vistoriador | gerente | km corrigido com motivo |

**Regras**

- `APR-07` Aprovação pelo celular com 1 toque (aprovar / recusar / detalhes). Recusar exige motivo.
- `APR-08` Pedido sem resposta em 4 horas úteis avisa o administrador.
- `APR-09` Quem pediu não pode aprovar o próprio pedido, mesmo tendo a permissão.
- `APR-10` Todo pedido, aprovação e recusa entra na auditoria.

*Mudanças em 07 out 2026 (T-041):* `APR-05` passou a ser pedido só pelo vendedor (`CLI-05`).

## Automações e notificações

As tarefas automáticas rodam no Celery, por empresa, no fuso `America/Sao_Paulo`. Toda mensagem ao cliente final sai com a marca da locadora (nome, logo, cor), nunca com o nome Giro.

| Código | Tarefa | Quando roda | O que faz | Canal |
| --- | --- | --- | --- | --- |
| `AUT-01` | Lembrete de devolução | 08:00 no dia da devolução | avisa o cliente o horário e o endereço | WhatsApp |
| `AUT-02` | Marcar devolução atrasada | a cada hora | aplica `LOC-10` | interno |
| `AUT-03` | Régua de cobrança do cliente | 09:00 | D-1 lembrete; D0 cobrança com Pix; D+3 e D+7 nova cobrança; D+15 bloqueio (`CLI-05`) | WhatsApp + e-mail |
| `AUT-04` | Cobrança recorrente | no vencimento | dispara o Pix automático ou cartão | parceiro de pagamento |
| `AUT-05` | Baixa de pagamentos | ao receber webhook | baixa a conta e envia recibo | WhatsApp |
| `AUT-06` | Vencimento de documentos | 07:00 | alerta 30 dias antes; aplica `VEI-03` | interno + e-mail ao gerente |
| `AUT-07` | Preventivas | após cada vistoria e 07:00 | aplica `MAN-03` | interno |
| `AUT-08` | Fechamento automático do caixa | 23:59 | aplica `FIN-08` | interno |
| `AUT-09` | Aprovação esquecida | a cada hora | aplica `APR-08` | push + e-mail |
| `AUT-10` | Comissões do mês | dia 1, 06:00 | fecha o mês anterior e agenda pagamento para o dia 5 | interno |
| `AUT-11` | Backup mensal | dia 1, 09:00 | gera o arquivo completo e envia o link | e-mail ao administrador |
| `AUT-12` | Importar extrato | 06:00 | busca o extrato e sugere pares (`FIN-11`) | interno |
| `AUT-13` | Régua da assinatura | 09:00 | aplica `PLT-02` | e-mail + WhatsApp |
| `AUT-14` | Implantação parada | 10:00 | aplica `IMP-06` | e-mail + WhatsApp |
| `AUT-15` | Fim do acesso de suporte | a cada minuto | encerra acessos vencidos (`PLT-07`) | interno |

**Notificações internas** (sino no topo e push no celular): aprovações pendentes (gerente), devoluções do dia (vistoriador), OS atrasada (gerente), diferença de caixa (gerente), documento vencendo (gerente), convite aceito (administrador), limite do plano em 90% (administrador). Cada pessoa escolhe os canais em Notificações.

## Auditoria, LGPD e exportação

Toda ação que muda dado de negócio grava um evento de auditoria que ninguém consegue editar ou apagar, nem o dono do produto. Telas: `Admin-Auditoria` (da empresa), `Plat-Auditoria` (da plataforma), `Admin-Exportar`, `Admin-Cancelar`.

- `AUD-01` O evento guarda: quem (usuário ou "Sistema" ou "Suporte Giro"), quando, ação, objeto (tipo e código), valores antes e depois dos campos mudados, IP e aparelho.
- `AUD-02` Categorias para filtro: financeiro, operação, configurações, segurança, suporte. Guardado por 5 anos.
- `AUD-03` Entradas do suporte da plataforma aparecem na auditoria da empresa com destaque e com o motivo (`PLT-07`).
- `AUD-04` Dados pessoais de clientes (CPF, CNH, endereço, fotos de documento) só aparecem completos para quem tem permissão de cadastro; nas listas, o CPF aparece mascarado (`***.218.330-**`).
- `AUD-05` Fotos de documentos e vistorias ficam em armazenamento privado, com link temporário (15 minutos) a cada visualização.
- `AUD-06` Pedido do titular (LGPD): o administrador exporta os dados de um cliente ou anonimiza o cadastro. Contratos e registros financeiros ficam guardados pelo prazo legal, anonimizados.
- `AUD-07` Exportação (`Admin-Exportar`): escolhe o que (clientes, veículos, locações e contratos, financeiro, vistorias e fotos, auditoria), formato (planilha, CSV, backup completo em ZIP) e período. O arquivo fica pronto em segundo plano e o link vale 7 dias.
- `AUD-08` Após o cancelamento da assinatura, os dados ficam 90 dias disponíveis para exportação e depois são apagados de vez (com aviso 7 dias antes).
- `AUD-09` O suporte Giro, dentro de uma empresa (`PLT-07`), vê CPF e CNH sempre mascarados, como nas listas (`AUD-04`), em qualquer tela e com qualquer permissão de acesso ("só ver" ou "ver e editar"). Nunca vê os dados completos.

*Mudanças em 07 out 2026 (T-037):* criada a `AUD-09` (achado S-02 da segurança, T-032, decidido pelo dono do produto); `PLT-07` passou a citá-la.

## Dados de referência para testes

Todas as telas usam a mesma empresa de exemplo. Use estes dados como seed do banco de desenvolvimento e como casos de teste: os cálculos do sistema têm que chegar exatamente nestes números.

**Empresa:** Moto Rápida Locações Ltda, CNPJ 12.345.678/0001-10, subdomínio `motorapida`, plano Profissional, teste de 07 a 21 out 2026, Filial Centro (Fortaleza, CE), 86 veículos (83 importados + 3 corrigidos), 612 clientes, 42 locações ativas.

**Pessoas:** Mariana Costa (administradora), Rodrigo Pinheiro (gerente), Bruna Alves (vendedora), João Silva (vistoriador), Lúcia Freitas (financeiro). Plataforma: você (dono), Diego Santos (suporte), Paula Andrade (financeiro), Caio Ribeiro (sucesso), Larissa Melo (suporte, convite pendente).

**Tabela de preços da Filial Centro** (tela `Precos`; base do `LOC-01`):

| Categoria | Modelos | Diária | Semanal | Mensal | Caução |
| --- | --- | --- | --- | --- | --- |
| Urbana 110–125 | Pop 110i, Biz 125 (42 veículos) | 44,90 | 299,40 | 1.090,00 | 300,00 |
| Street 150–160 | CG 160, Factor 150 (32 veículos) | 54,90 | 329,00 | 1.190,00 | 300,00 |
| Scooter premium | NMax 160 (6 veículos) | 79,90 | 449,00 | 1.590,00 | 500,00 |
| Carro compacto | Kwid, Mobi (6 veículos) | 109,00 | 649,00 | 2.290,00 | 800,00 |

Lucas Ferreira (LOC-2856) aluga uma Honda CG 160 Fan (SAK-1D39) no semanal Street: R$ 329,00 + caução R$ 300,00 = R$ 629,00 na retirada.

Planos especiais: Entregador R$ 279,00/semana (km livre, troca de óleo inclusa); Mensal fidelidade −10% a partir do 3º mês seguido. Regras de cobrança: tolerância de atraso 1 hora, combustível = preço da bomba + R$ 10, km livre em todos os planos, desconto do vendedor até 5% sem aprovação.

| Caso | Entrada | Resultado esperado | Regra |
| --- | --- | --- | --- |
| Acerto da devolução LOC-2836 | caução 300,00; combustível 32,00; retrovisor 85,00 | devolver R$ 183,00 | `DEV-02` |
| Total pago LOC-2836 | 2 semanas de 329,00 + caução 300,00 | R$ 958,00 | `LOC-05` |
| Venda VEN-0177 | tabela 22.900,00; desconto 8%; entrada 5.000,00; 12 parcelas | final 21.068,00; 12 × 1.339,00; vai para aprovação | `VEN-02`, `VEN-04` |
| Comissão da venda VEN-0177 | 3% de 21.068,00 | R$ 632,04 pendente | `FIN-09` |
| Comissões de outubro (Bruna) | 4 vendas somando 31.200,00 + 2 locações | R$ 968,00 confirmados | `FIN-10` |
| Comissões de setembro | Bruna: 3 vendas (36.000,00) + 10 locações; Felipe: 1 venda (19.000,00) + 5 locações | R$ 1.240,00 + R$ 650,00 = R$ 1.890,00 | `FIN-09` |
| Caixa de 07 out | troco 200,00; entradas em dinheiro 629,00; saídas em dinheiro 548,00 | gaveta R$ 281,00; total recebido R$ 1.182,60 | `FIN-07` |
| Conciliação | Pix sem par +150,00; tarifa −12,90 | diferença R$ 137,10 | `FIN-12` |
| DRE de setembro | locações 56.420,00; extras 2.310,00; taxas 1.128,40; despesas 21.480,30; comissões 1.890,00 | resultado R$ 34.231,30 (margem 58%) | `FIN-13` |
| Despesas de outubro | 6 lançamentos: pneus 1.200,00; óleo 48,00 (pago no caixa); luz 412,30; aluguel 3.500,00; IPVA 186,40; rastreadores 1.720,00 | R$ 7.066,70; aguardando aprovação R$ 1.200,00 (só os pneus; o IPVA está abaixo de R$ 500 e nasce `a_pagar`) | `FIN-05` |
| Em aberto dos clientes | Carlos 299,40; Rafael 1.347,00 | R$ 1.646,40 (2 clientes) | `FIN-01` |
| Encerramento antecipado LOC-2812 | NMax mensal 1.590,00; pedido em 07 out; fim 15 out | multa R$ 84,80; devolve R$ 286,20 | `LOC-12`, `LOC-13` |
| Preço antigo LOC-2841 | Carlos, CG 160 Fan, assinado em 30 set, quando a Street semanal era 299,40 (passou a 329,00 em 01 out) | parcelas continuam R$ 299,40 | `LOC-15` |
| Bloqueio | Rafael Sousa, 25 dias de atraso | cliente `bloqueado`, LOC-2790 `devolucao_atrasada` | `CLI-05`, `LOC-10` |
| Uso do plano | 86 veículos, 1 filial, 5 usuários | 86 de 150, 1 de 3, 5 de 10; sem aviso | `PLT-03` |
| Implantação da plataforma | 23 empresas em teste | funil 23 → 19 → 17 → 14 → 11 → 8 | `IMP-05` |

*Mudanças em 07 out 2026 (T-041):* "Despesas de outubro" passou de "aguardando aprovação R$ 1.386,40" para R$ 1.200,00. O valor antigo somava o IPVA de R$ 186,40, que pela `FIN-05` (até R$ 500 nasce `a_pagar`) não vai para aprovação. A tela `Despesas` vai para a T-028.

## Decisões de 07 out 2026

Pendências fechadas com base em pesquisa de mercado (locadoras de moto, sistemas parecidos, meios de pagamento e legislação). Cada uma pode mudar depois; vale registrar a mudança aqui.

| Pendência | Decisão | Por quê |
| --- | --- | --- |
| Preço semanal da Biz (299,40 × 329,00) | Vale a tabela: Urbana 110–125 semanal **R$ 299,40**. A locação de exemplo do Lucas passou a ser uma CG 160 Fan (Street, R$ 329,00), e assim os valores de caixa e comissão continuam certos. | A tabela é a fonte do preço (`LOC-01`); a tela só mostra exemplo. |
| Diária de atraso da Factor 150 (54,90 × 59,90) | **R$ 54,90**, a diária da categoria Street. | `LOC-10` já diz que o atraso cobra a diária da categoria. |
| Mensal por mês ou por dia | **Por mês fechado** (`LOC-14`), com desconto embutido em relação a 4 semanas. | Mercado cobra mensal mais barato que semanas avulsas (Mottu dá até 10% no mensal antecipado). |
| Multa do encerramento antecipado | **20% dos dias restantes do período, mínimo 1 diária** (`LOC-12`, `LOC-13`). | Proporcional ao que falta, como pede o Código Civil (art. 413); sem multa na diária. |
| Juros e multa do cliente final | **2% de multa + 1% ao mês pro rata** (teto e padrão) (`FIN-03`). | Teto do CDC (art. 52, §1º) para a multa; 1% ao mês é o usual para empresas que não são bancos. |
| Parceiro de pagamento | **Asaas**, com uma subconta white label por locadora criada pela API, e também para cobrar a assinatura do Giro. Pix, boleto, cartão, assinatura recorrente, Pix Automático e webhooks. Efí Bank fica como plano B. | Subcontas permitem cobrar com a marca da locadora sem citar o Asaas nas mensagens; Pix a R$ 1,99 por cobrança recebida e boleto cobrado só quando pago. |
| Preços da assinatura | Essencial **R$ 199**, Profissional **R$ 449**, Completo **R$ 899** por mês; anual = 10 mensalidades. Adicionais: filial R$ 79/mês, pacote de 10 veículos R$ 49/mês, assinatura digital avulsa R$ 4,90/contrato. | Sistemas de locação lá fora custam de US$ 29 a 99 por mês e ERPs genéricos no Brasil ficam perto de R$ 200; o Essencial custa menos que 1 semana de aluguel de uma moto. |
| Domínio | **girolocadoras.com.br** (plataforma em `admin.girolocadoras.com.br`, empresas em `<subdominio>.girolocadoras.com.br`). Registrar também girolocacao.com.br para proteção. | giro.com.br e quase todas as variações (giroapp, girogestao, girofrota, girorent, meugiro, usegiro) já têm dono. Disponíveis em 07 out 2026: girolocadoras.com.br, girolocacao.com.br, girogestao.app.br, giromotos.app.br. |
| Dúvidas do modelo de dados (T-006, respondidas em T-031) | Estados das entidades sem seção própria (Entidades); venda `cancelada` só a partir de `vendida`, cancelada por gerente ou administrador (`VEN-07`); venda aberta = `proposta`, `negociacao`, `aguardando_aprovacao` (`VEN-10`); `ROUND_HALF_UP` no centavo com diferença na última parcela (Convenções); chassi único e reaproveitamento do cadastro na recompra (`VEI-01`, `VEI-07`). | Recomendação do produto aprovada pelo dono do produto em 07 out 2026. |
| Dúvidas dos contratos de filiais e contas (T-030 e T-036, respondidas em T-037) | Nova seção Filiais (`FIL-01` a `FIL-06`): campos da tela `Filial` aprovados como o produto recomendou, recebimento por empresa, devolução só na filial da locação e frota por filial, feriados por filial (`LOC-11` não corre nesses dias), desativação recusada com operação. `USR-01`: e-mail obrigatório, celular opcional. `USR-06`: sem "manter conectado". 2 etapas segue a `USR-02` (correção das telas na T-028). | Recomendação do produto aprovada pelo dono do produto em 07 out 2026. |
| Desbloqueio manual de cliente (T-036, item 12) | Gerente e administrador desbloqueiam direto, com motivo e auditoria; o vendedor pede e o gerente aprova (`CLI-05`, `APR-05`). | Opção A, recomendada pelo produto e aprovada pelo dono do produto em 07 out 2026. Evita que toda filial com um gerente só dependa do administrador. |
| Consulta de crédito | **Fora do MVP.** No MVP a análise do cliente (`CLI-04`) usa CPF, CNH, lista de bloqueio e histórico na empresa. Na fase 2, consulta paga por uso via parceiro (Serasa ou o próprio Asaas). | Custa por consulta e não trava a operação; o histórico interno já resolve a maior parte. |

## Pontos em aberto

- [ ] **Registrar o domínio** girolocadoras.com.br (e girolocacao.com.br) no registro.br antes que alguém registre.
- [ ] **Busca de marca no INPI**: "Giro" é um nome muito usado (o domínio principal já pertence a outra empresa). Antes de investir na marca, buscar "GIRO" nas classes 42 (software como serviço) e 9 (software), não só 39 e 12, e considerar registrar a marca mista "Giro Locadoras". Se houver conflito, trocar o nome agora sai mais barato.
- [ ] **Abrir a conta no Asaas** e confirmar as taxas de boleto e cartão para o volume esperado.
- [ ] **Telas que faltam desenhar:** esqueci a senha, 2 etapas, meu perfil, notificações, contas a pagar separada, multas de trânsito, documentos dos veículos, avarias abertas, pagamento e assinatura pelo cliente final, site de vendas.

### Dúvidas do contrato de clientes (T-036, 07 out 2026)

Levantadas pelo arquiteto em `docs/api/clientes.md`. Nenhuma bloqueia a T-014.

- [ ] **11. Botão da lista quando duas situações valem (`CLI-07`).** Exemplo: Lucas está com cadastro incompleto e tem locação. Recomendação: aceitar a ordem da tela, que já é a proposta. Vale o primeiro que se aplicar: em aberto → Cobrar; incompleto → Completar cadastro; com venda aberta (`VEN-10`) → Ver proposta; com locação → Ver locação; nenhum desses → Nova locação. É a ordem da tela `Clientes`: Lucas (incompleto, com LOC-2856) → Completar cadastro; Diego Martins (LOC-2848 e proposta da CB 300F) → Ver proposta. Corrigido em 07 out 2026: a primeira versão deste item punha a locação antes da proposta, o que contradiz a tela. Só completa a `CLI-07`, **sem impacto de negócio**.

- [ ] **13. Como o cliente fica `inativo`.** Nenhuma regra diz como se entra nesse estado. Recomendação: aceitar a proposta. Gerente ou administrador inativa, com motivo; a ação é recusada se o cliente tem locação aberta, venda aberta ou valor em aberto. Cliente inativo sai da lista padrão (aparece no filtro "todos") e não faz locação nem compra. Gerente ou administrador reativa, e ele volta a `ativo` ou `incompleto`, conforme o cadastro (`CLI-03`). **Impacto de negócio pequeno.** Padrão até a aprovação: esta recomendação.

### Dúvida de cálculo do financeiro (T-041, 07 out 2026)

- [ ] **14. O que é "pro rata dia" nos juros (`FIN-03`).** A regra diz 1% ao mês pro rata dia, mas não diz como o mês vira dia, e isso muda o valor em centavos. **Precisa do dono:** A) mês comercial: juros = valor × 1% ÷ 30 × dias corridos de atraso, contados do dia seguinte ao vencimento até o dia do pagamento, arredondado uma vez (`ROUND_HALF_UP`) (padrão recomendado, o mais usado em boletos); B) mês civil: divide pelos dias do mês do vencimento (28 a 31). Com A, Carlos (R$ 299,40, 7 dias) paga juros de R$ 0,70 e multa de R$ 5,99; Rafael (R$ 1.347,00, 25 dias) paga juros de R$ 11,23 e multa de R$ 26,94. A multa de 2% é cobrada uma vez, em qualquer atraso a partir de 1 dia. Até a resposta vale A, que já está nos critérios da T-017.
