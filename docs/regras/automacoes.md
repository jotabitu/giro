# Automações e notificações

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

As tarefas automáticas rodam no Celery, por empresa, no fuso `America/Sao_Paulo`. Toda mensagem ao cliente final sai com a marca da locadora (nome, logo, cor), nunca com o nome Giro.

**Mensagens pelo WhatsApp** (ADR 0034, T-387). Valem para todo aviso que a empresa manda pelo WhatsApp.
- **Modelos aprovados.** Cada aviso usa um modelo aprovado pela Meta. Os 13 textos da fase 1 estão em `docs/qa/criterios/whatsapp.md`. Mudar um texto é tarefa do produto e pede nova aprovação da Meta.
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
| `AUT-01` | Lembrete de devolução | 08:00 no dia da devolução | avisa o cliente o horário e o endereço | WhatsApp, ou e-mail sem o aceite (`CLI-12`) |
| `AUT-02` | Marcar devolução atrasada | a cada hora | aplica `LOC-10` | interno |
| `AUT-03` | Régua de cobrança do cliente | 09:00 | D-1 lembrete; D0 cobrança com Pix; D+3 e D+7 nova cobrança com o valor do dia (`FIN-03`); D+15 bloqueio (`CLI-05`), uma vez por conta: se a tarefa não rodar no 15º dia, o bloqueio sai na próxima vez que ela rodar. Textos em `docs/api/financeiro.md` (régua de cobrança). No plano Essencial, só e-mail e sem o Pix do parceiro (`PLT-12`) | WhatsApp + e-mail |
| `AUT-04` | Cobrança recorrente | **fase 2** | dispara o Pix Automático (ou o cartão) das parcelas da locação. No MVP, a parcela segue boleto e Pix comum pela régua (`AUT-03`) | parceiro de pagamento |
| `AUT-05` | Baixa de pagamentos | ao receber webhook | baixa a conta e envia recibo com o valor, a forma e o dia do pagamento | WhatsApp, ou e-mail sem o aceite (`CLI-12`) |
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
