# Entidades e relações

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

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
| Movimentação | MOV-, veículo, saída, paradas (local de apoio, serviço, valor), destino, quem leva, agendada para, km e vistoria rápida da chegada, status | Filial (de saída) | MVP (decisão de 16 out 2026); seção Movimentações de veículos |
| Local de apoio | nome, tipo (lava-jato, oficina, despachante, outro), ativo | Empresa | parada da movimentação (`MOV-01`) |
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
| Vistoria | `rascunho`, `concluida`, `descartada` | `DEV-05`, `VIS-04`, `LOC-09` |
| Contrato | `gerado`, `enviado`, `assinado`, `cancelado` | fluxo da retirada, passo 3 |
| Caixa do dia | `aberto`, `aguardando_aprovacao`, `fechado`, `fechado_sem_conferencia` | `FIN-07`, `FIN-08`, `APR-04` |
| Acesso de suporte | `ativo`, `encerrado`, `revogado` | `PLT-07`, `AUT-15` |
| Pedido de aprovação | `pendente`, `aprovado`, `recusado`, `cancelado` | seção Aprovações |
| Lançamento bancário | `pendente`, `conciliado`, `ignorado` | `FIN-11` |
| Troca de veículo | `pendente`, `concluida`, `cancelada` | `LOC-09` |

- Usuário: convite vencido (mais de 7 dias, `USR-01`) continua `convite_pendente`, com o link expirado, e conta no limite do plano até ser reenviado (ou ter o link copiado) ou cancelado.
- Vistoria: correção de vistoria concluída é uma vistoria nova ligada à anterior, com motivo (`VIS-04`), não um estado. `descartada` é o rascunho descartado no cancelamento da troca (`LOC-09`), com data e motivo: não muda mais, não sai na agenda e não aceita edição. Vistoria concluída nunca é descartada.
- Acesso de suporte: `encerrado` quando o prazo acaba ou o suporte sai; `revogado` quando o administrador da empresa bloqueia (`PLT-07`).
- Pedido de aprovação: `cancelado` quando quem pediu desiste ou a origem deixa de existir.
- Troca de veículo: nasce `pendente` no pedido; vai para `concluida` quando a chegada do veículo antigo e a saída do novo concluem, e para `cancelada` pela rota de cancelar a troca pendente (`LOC-09`). Uma troca pendente por locação; `concluida` e `cancelada` não mudam mais.
