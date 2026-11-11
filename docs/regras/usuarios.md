# Usuários, perfis e permissões

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Cada usuário tem 1 perfil e uma lista de filiais. O perfil define o menu e as ações; a filial define quais dados ele vê. Telas: `Admin-Usuarios`, `Convite`, `Login`, e as iniciais de cada perfil (`Gerente`, `Vendedor`, `Vistoriador`, `Financeiro`, `Main`/`Pos-Dashboard`).

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver painel e relatórios | todas as filiais | sua filial | só os seus números | — | todas as filiais |
| Consultar veículos (Frota e ficha, só leitura) | sim | sim | sim | sim (Consultar veículo) | sim |
| Cadastrar e editar veículo | sim | sim | — | atualizar km e avarias | — |
| Ver rendimento e custo de manutenção do veículo (`VEI-05`) | sim | sim | — | — | sim |
| Cadastrar cliente | sim | sim | sim | — | — |
| Criar locação | sim | sim | sim | — | — |
| Fazer vistoria (saída e devolução) | sim | sim | sim | sim | — |
| Cancelar locação | sim | sim, e aprova os pedidos | pede | — | — |
| Desconto acima de 5% | sim | sim, e aprova os pedidos | pede | — | — |
| Registrar retirada à mão, antes da assinatura ou do pagamento (`LOC-17`) | sim | sim (sua filial) | — | — | — |
| Criar venda / proposta | sim | sim | sim | — | — |
| Receber pagamento no caixa | sim | sim | sim | — | sim |
| Abrir e fechar caixa, sangria | sim | sim | sim (sua filial) | — | sim |
| Lançar despesa | sim | sim | sim | sim (manutenção e peças) | sim |
| Aprovar despesa acima de R$ 500 | sim | aprova | — | — | — |
| Lançamento avulso em contas a receber (multa, avaria, outro), cancelar, renegociar, estornar | sim | sim | — | — | sim |
| Pagar contas, conciliação, comissões | sim | — | — | — | sim |
| Abrir ordem de serviço | sim | sim | — | sim | — |
| Criar e iniciar movimentação de veículo, cadastrar local de apoio (`MOV-02`; quem leva registra as chegadas) | sim | sim (sua filial) | — | — | — |
| Exportar as despesas em CSV (tela `Despesas`, `FIN-16`) | sim | — | — | — | sim |
| Administração (marca, filiais, usuários, preços, contratos, integrações, assinatura, auditoria, exportar) | sim | — | — | — | — |

**Regras**

- `USR-01` Convite por e-mail, com link válido por 7 dias. Na fase 1, o convite não vai pelo WhatsApp (decisão do dono de 11 nov 2026, ADR 0034: o WhatsApp fica só na régua da assinatura); a caixa "A pessoa aceita receber o convite pelo WhatsApp" continua como está e não muda o envio (seção Automações). O e-mail é obrigatório em todo usuário, porque é o login (`USR-06`); o celular é opcional. A pessoa cria a senha e entra já com perfil e filiais definidos. Convite pendente conta no limite de usuários do plano.
  - **Sem convite não há acesso.** O administrador não cria usuário com senha: o acesso sempre nasce por convite, e a senha só a própria pessoa cria.
  - **Copiar link do convite.** No painel da pessoa com convite pendente (`convite_pendente`, vencido ou não), o administrador tem "Copiar link do convite", para mandar o link por outro canal. Copiar gera um link novo de 7 dias e invalida o anterior, como o reenvio, porque o sistema guarda só o hash do link e não tem como mostrar o antigo. Quem abre um link substituído vê o mesmo aviso do convite vencido: "Este convite venceu. Peça um novo ao administrador.". O link novo aparece uma vez, para copiar, e não sai por e-mail nem por WhatsApp; a tela avisa "O link anterior deixa de valer.". Cada cópia grava evento de auditoria (`seguranca`, sem o link). Só o administrador copia; o suporte Giro não (`PLT-07`). Copiar não muda o status nem a contagem do plano.
- `USR-02` Verificação em 2 etapas obrigatória para administrador e financeiro; opcional para os demais (o administrador pode tornar obrigatória para todos).
  - **Tela Minha conta: fase 2** (decisão do dono do produto em 25 out 2026, T-356). É nela que a pessoa liga as 2 etapas por vontade própria e troca a senha. No MVP:
    - quem é obrigado liga as 2 etapas no primeiro acesso;
    - gerente, vendedor e vistoriador só usam as 2 etapas quando o administrador torna obrigatório para todos;
    - a senha se troca pelo "Esqueci a senha".
- `USR-03` Permissões extras por pessoa (marcar em `Admin-Usuarios`): aprovar descontos acima de 5%, cancelar contratos, ver relatórios de todas as filiais. Elas somam ao perfil, nunca tiram.
- `USR-04` Desativar usuário encerra a sessão na hora. O histórico do que ele fez continua. Usuário desativado não conta no limite do plano. Reativar depende de a pessoa já ter chegado a `ativo`: quem já foi `ativo` volta `ativo`; quem nunca chegou a `ativo` (convite cancelado, mesmo que já tenha criado a senha) volta para `convite_pendente`, com convite novo de 7 dias pelos mesmos canais (`USR-01`). Nos dois casos, reativar respeita o limite do plano (`PLT-03`).
- `USR-05` Menu. Cada perfil tem o seu menu (o da tela inicial dele), que vale no início e nas telas próprias do perfil: as telas que os itens desse menu abrem, com as telas de dentro delas. As demais telas usam o menu completo do perfil, que traz só os itens que a tabela de perfis permite a ele. O item do início leva o nome do início do perfil: "Visão geral" do administrador, "Visão da filial" do gerente, "Início" do vendedor e do financeiro. Itens sem permissão nunca aparecem desabilitados, simplesmente não aparecem.
  - **Vistoriador:** um menu só, em todas as telas: Vistorias de hoje (agenda), Consultar veículo e Avarias abertas. A tabela de perfis dá a ele só vistorias e veículos, então o menu completo dele é o próprio menu do perfil: sem Visão geral (ele não vê painel) e sem Locações (a lista de locações não é dele; ele chega à vistoria e à devolução pela agenda, `VIS-05`).
  - **Gerente:** telas próprias são o início, Aprovações, Veículos, Locações, Vendas, Clientes, Manutenções, Caixa da filial e Relatórios. Contas a receber e Despesas usam o menu completo.
  - **Vendedor:** telas próprias são o início, Locações, Veículos e Clientes, nessa ordem; na fase 2, também Vendas, Veículos à venda e Minhas comissões. Veículos é só leitura: a Frota e a ficha, sem as ações de cadastro e de status, e sem o rendimento e o custo (`USR-09`). Caixa do dia, Contas a receber e Despesas usam o menu completo.
  - **Financeiro:** telas próprias são o início, Contas a receber, Contas a pagar (Despesas), Caixa e bancos (Caixa do dia), Veículos e Comissões, nessa ordem. Veículos é só leitura, como no vendedor, mas com o rendimento e o custo (`VEI-05`, `USR-09`). Clientes, Conciliação e Relatórios usam o menu completo.
  - **Administrador:** não tem menu próprio; usa o menu completo em todas as telas, inclusive no início. O menu completo dele traz, em Operação, Vistorias de hoje (a agenda, `VIS-05`) e Avarias abertas, logo depois de Locações (decisão do dono de 09 nov 2026, T-442). Com todas as filiais escolhidas, a agenda junta as filiais em ordem de horário e mostra a filial de cada item. O gerente e o vendedor continuam chegando à vistoria pela ficha da locação.
  - **Movimentações para quem leva:** o vendedor e o vistoriador ganham o item Movimentações, no menu do perfil e no completo, só enquanto houver uma movimentação não concluída que eles levam (`MOV-02`); a tela mostra só as deles. Administrador e gerente têm o item sempre.
- `USR-06` Login com e-mail e senha; 5 tentativas erradas bloqueiam por 15 minutos e avisam o administrador. Sessão expira após 12 h sem uso no desktop e 30 dias no celular. Não existe opção "manter conectado".
- `USR-07` Escopo de filial: o seletor de filial no topo do menu mostra só as filiais da pessoa. Administrador e financeiro veem todas as filiais ativas, sem depender das filiais ligadas a eles, e podem escolher "Todas as filiais" (tabela de perfis e `USR-08`). Quem tem a permissão extra de ver relatórios de todas as filiais (`USR-03`) escolhe "Todas as filiais" só no painel e nos relatórios. "Todas as filiais" inclui os dados das filiais desativadas que ainda têm contas ou histórico (`FIL-06`). A lista de Clientes não segue o seletor: o cliente é da empresa, e a lista tem filtro de filial próprio (`CLI-10`).
- `USR-08` Tela inicial por perfil. Todos entram pela mesma rota de início, e o sistema mostra a variante do perfil:
  - **Administrador:** `Pos-Dashboard` (o que falta da implantação) até a `IMP-01` concluir; depois, o painel geral de todas as filiais.
  - **Gerente** (`Gerente`, só a sua filial): aprovações pendentes da filial, sem os pedidos que ele mesmo fez (`APR-09`); ocupação; receita da semana; devoluções atrasadas; manutenções; frota da filial por estado; e a equipe da filial hoje, com "online" quando a pessoa usou o sistema nos últimos 5 minutos.
  - **Vendedor**, só os próprios números: na fase 1, as locações que ele criou e estão abertas, as que devolvem hoje, as parcelas atrasadas dessas locações e o atalho Nova locação; o funil, a meta e as comissões de `Vendedor` entram com vendas (fase 2).
  - **Vistoriador:** `Vistoriador`, com a agenda do dia (`VIS-05`).
  - **Financeiro** (`Financeiro`, todas as filiais): entra hoje, em atraso, caixas do dia por filial e "Para hoje" (reembolsos a fazer e despesas a pagar vencendo; o financeiro não aprova pedidos, conforme a tabela de perfis); saldo em contas, fluxo previsto e conciliação entram na fase 2.
  
  O início e as telas próprias do perfil usam o menu do perfil, e as demais telas usam o menu completo do perfil, sem os itens sem permissão (`USR-05`). Cada bloco que depende de um módulo que ainda não existe vem vazio, e não com número de exemplo. Um número aparece assim que a fonte dele existe, mesmo antes da tela do módulo: a receita da semana do gerente e a do administrador saem das contas a receber pagas (`FIN-15`), que nascem com a locação, e por isso aparecem antes do módulo financeiro completo. No início do financeiro, enquanto o caixa e as despesas não existem, "caixas do dia" fica vazio e "Para hoje" traz só os reembolsos a fazer; entra hoje e em atraso já aparecem.
- `USR-09` O que cada perfil vê nas fichas de locação, de cliente e de veículo, além da tabela de perfis. Rota que o perfil não pode abrir mostra "Seu perfil não tem acesso", e a API responde 403; ação sem permissão não aparece (`USR-05`), e a API recusa.
  - **Financeiro, ficha da locação:** vê a ficha inteira, só para leitura: cliente, veículo, período, parcelas, pagamentos, caução, contrato e histórico. Das ações, só as do dinheiro que a tabela de perfis dá a ele: receber pagamento e marcar reembolso como feito (`DEV-02`). Não faz vistoria, devolução, renovação, troca, cancelamento nem pedido de encerramento antecipado.
  - **Financeiro, ficha do cliente:** vê nome, situação (com o motivo do bloqueio), CPF ou CNPJ mascarado, celular e e-mail, as locações do cliente (abrindo a ficha da locação como acima) e o financeiro do cliente: total pago, valor em aberto, parcelas atrasadas com os dias de atraso e os pagamentos feitos. A ação é Cobrar (`CLI-07`). Não vê documentos e fotos, endereço nem a análise do cadastro (`CLI-04`); não edita, não bloqueia, não desbloqueia e não inativa.
  - **Vistoriador:** não abre a lista nem a ficha do cliente. Na vistoria, vê do cliente só o que a vistoria usa: nome, celular e se a retirada está liberada (cadastro completo, `CLI-03`; CNH na categoria e na validade, `CLI-02`), vindos com a própria vistoria. Nenhum valor em dinheiro aparece para ele.
  - **Administrador, gerente e vendedor:** ficha inteira, com as ações da tabela de perfis.
  - **Ficha do veículo:** "Rendeu no ano" e "Custo de manutenção" (`VEI-05`) só para administrador, gerente e financeiro. Para o vendedor e o vistoriador, a API não manda os dois números (o bloco vem ausente, e não zerado) e a ficha não mostra os dois cartões, sem deixar espaço vazio. O valor e a data de compra são só de administrador e gerente. O resto da ficha (situação, ocupação, km, documentos, preços de tabela) não muda. Vendedor e financeiro abrem a Frota e a ficha só para leitura: nenhuma ação de cadastro, documento, km, status ou transferência aparece para eles.
