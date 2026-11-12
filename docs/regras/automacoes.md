# Automações e notificações

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

As tarefas automáticas rodam no Celery, por empresa, no fuso `America/Sao_Paulo`. Toda mensagem ao cliente final sai com a marca da locadora (nome, logo, cor), nunca com o nome Giro.

**Na fase 1, o WhatsApp fica só na régua da assinatura** (decisão do dono de 11 nov 2026, opção C da ADR 0034). Pelo número do Giro, o remetente que o cliente vê seria "Giro Avisos", contra a marca da locadora; por isso:
- **Ao cliente final, tudo vai por e-mail**, com a marca da locadora: contrato para assinar e assinado, cobrança (`AUT-03`), recibo do pagamento (`AUT-05`), recibo da devolução (`DEV-02`, com o PDF anexo) e lembrete de devolução (`AUT-01`). O aceite do cliente (`CLI-12`) não muda o canal.
- **À pessoa convidada, o convite vai por e-mail** (`USR-01`).
- **O WhatsApp sai só ao responsável pela assinatura**, com o aceite dele, na régua da assinatura (`AUT-13`, `PLT-02`), que é do Giro e leva a marca Giro. Dos 13 modelos de `docs/qa/criterios/whatsapp.md`, só os da assinatura (12 e 13) entram em uso; os outros ficam guardados.
- **O que já está feito fica como está**, sem entrar em uso: o envio pelo WhatsApp ao cliente e ao convidado, as caixas de aceite, a resposta automática e o "SAIR". A volta do WhatsApp ao cliente final é decisão do dono, com a escolha do remetente (ADR 0034).
- **Cliente sem e-mail** não recebe aviso automático: a falha fica no registro do envio, e quem atende manda o link por outro canal ("Copiar link", T-411). A conta é devida igual, e a régua continua contando os dias (`CLI-05`).

**Mensagens pelo WhatsApp** (ADR 0034, T-387). Valem para todo aviso que sai pelo WhatsApp; na fase 1, só a régua da assinatura (acima).
- **Modelos aprovados.** Cada aviso usa um modelo aprovado pela Meta. Os 13 textos estão em `docs/qa/criterios/whatsapp.md`; na fase 1, só os da assinatura são usados. Mudar um texto é tarefa do produto e pede nova aprovação da Meta.
- **Começo e fim fixos.** O texto começa com uma abertura fixa ("Olá, {nome}." ao cliente e à pessoa convidada; "Giro:" ao responsável pela assinatura) e termina com uma frase fixa. A marca da locadora vai no meio, sem artigo ("Moto Rápida informa:"), para não errar o gênero.
- **Sem pedir resposta.** Nenhum texto pede ao cliente que responda pelo WhatsApp, porque a resposta não chega à locadora. Onde o texto antigo dizia "Pague na loja ou fale com a gente por aqui", fica "Pague na loja.".
- **Resposta automática.** Quem responde recebe, uma vez por dia: "Este número só envia avisos. Para falar com {marca}, ligue para a loja: {telefone da filial}.". "SAIR", "PARAR" e "CANCELAR" desmarcam o aceite (`CLI-12`).
- **Aceite.** Só recebe WhatsApp quem aceitou receber: o cliente (`CLI-12`), a pessoa convidada (`USR-01`) e o responsável pela assinatura, marcado pela equipe Giro ao criar a empresa (`PLT-02`).
- **Queda para o e-mail.** Sem aceite, sem celular, ou com o envio recusado (pela Meta, ou depois das repetições do envio, ADR 0034), o aviso vai pelo e-mail, com o mesmo texto, se a pessoa tem e-mail. Vale também para os avisos que eram só por WhatsApp:
  - o recibo do pagamento (`AUT-05`);
  - o recibo da devolução (`DEV-02`), que no e-mail leva o PDF anexo, porque o link de 15 minutos venceria antes de a pessoa ler;
  - o lembrete de devolução (`AUT-01`).
  Sem e-mail, o aviso não sai, e a falha fica no registro do envio. A régua não para nem repete no mesmo dia por causa disso (`AUT-03`).

| Código | Tarefa | Quando roda | O que faz | Canal |
| --- | --- | --- | --- | --- |
| `AUT-01` | Lembrete de devolução | 08:00 no dia da devolução | avisa o cliente o horário e o endereço | e-mail (na fase 1, sem WhatsApp ao cliente) |
| `AUT-02` | Marcar devolução atrasada | a cada hora | aplica `LOC-10` | interno |
| `AUT-03` | Régua de cobrança do cliente | 09:00 | D-1 lembrete; D0 cobrança com Pix; D+3 e D+7 nova cobrança com o valor do dia (`FIN-03`); D+15 bloqueio (`CLI-05`), uma vez por conta: se a tarefa não rodar no 15º dia, o bloqueio sai na próxima vez que ela rodar. Textos em `docs/api/financeiro.md` (régua de cobrança). Na fase 1, em todos os planos, os marcos, os dias e os textos são os mesmos, só por e-mail; o Profissional manda o Pix e o boleto do parceiro, e o Essencial, não (`PLT-12`): "Pague na loja." | e-mail (na fase 1, sem WhatsApp ao cliente) |
| `AUT-04` | Cobrança recorrente | **fase 2** | dispara o Pix Automático (ou o cartão) das parcelas da locação. No MVP, a parcela segue boleto e Pix comum pela régua (`AUT-03`) | parceiro de pagamento |
| `AUT-05` | Baixa de pagamentos | ao receber webhook | baixa a conta e envia recibo com o valor, a forma e o dia do pagamento | e-mail (na fase 1, sem WhatsApp ao cliente) |
| `AUT-06` | Vencimento de documentos | 07:00 | alerta 30 dias antes; no dia, aplica `VEI-03`: `disponivel` vai para `indisponivel`; `alugado`, `reservado` e `em_manutencao` geram tarefa urgente aos gerentes | interno + e-mail ao gerente |
| `AUT-07` | Preventivas | após cada vistoria e 07:00 | aplica `MAN-03` | interno |
| `AUT-08` | Fechamento automático do caixa | 23:59 | aplica `FIN-08` | interno |
| `AUT-09` | Aprovação esquecida | a cada hora | aplica `APR-08` | push + e-mail |
| `AUT-10` | Comissões do mês | **fase 2** (com a `FIN-09`); dia 1, 06:00 | fecha o mês anterior e agenda pagamento para o dia 5 | interno |
| `AUT-11` | Backup mensal | **fase 2** (com o backup completo e o cartão de `Admin-Exportar`, nota de 12 out 2026 na auditoria); dia 1, 09:00 | gera o arquivo completo e envia o link | e-mail ao administrador |
| `AUT-12` | Importar extrato | 06:00 | busca o extrato e sugere pares (`FIN-11`) | interno |
| `AUT-13` | Régua da assinatura | 09:00 | aplica `PLT-02`. Marco perdido: só o D+7 sai depois, na próxima execução até o D+14, uma vez, com a ligação (`PLT-02`, T-308). Textos em `docs/qa/criterios/assinatura.md` ("Textos da régua da assinatura", T-299) | e-mail + WhatsApp |
| `AUT-14` | Implantação parada | **fase 2** (com a `IMP-06`); 10:00 | aplica `IMP-06` | e-mail + WhatsApp |
| `AUT-15` | Fim do acesso de suporte | a cada minuto | encerra acessos vencidos (`PLT-07`) | interno |
| `AUT-16` | Expurgo da auditoria | **fase 2**; dia 1, 03:00 | apaga os eventos de auditoria com mais de 5 anos (`AUD-02`), em cada empresa e na plataforma, e grava um evento do Sistema (categoria segurança) com a data limite e quantos eventos saíram | interno |
| `AUT-17` | Locação não retirada | 00:10 (cancelamento) e 08:00 (aviso) | aplica a `LOC-12` na locação `aguardando_retirada`: às 00:10, cancela a que passou do último dia para retirar (3º dia depois da data de início); às 08:00, avisa os gerentes da filial das que vencem o prazo hoje. Cancelamento perdido sai na próxima execução, uma vez por locação | sino + push + e-mail ao gerente |

**Notificações internas** (sino no topo e push no celular): aprovações pendentes (gerente), devoluções do dia (vistoriador), OS atrasada (gerente), diferença de caixa (gerente), documento vencendo (gerente), locação não retirada que será cancelada amanhã (gerente, `AUT-17`), convite aceito (administrador), limite do plano em 90% (administrador). Cada pessoa escolhe os canais em Notificações.
