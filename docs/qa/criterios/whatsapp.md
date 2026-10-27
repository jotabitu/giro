# WhatsApp: modelos da Meta e aceite · critérios de aceite

**Regras:** "Mensagens pelo WhatsApp" (seção Automações), CLI-12, USR-01, AUT-01, AUT-03, AUT-05, AUT-13, PLT-02, DEV-02 · **ADR:** 0034 (proposta) · **Origem:** T-387 (decisões do produto sobre a T-385)

## Os 13 modelos da fase 1

Os modelos são da categoria utilidade, em `pt_BR`. Cada texto começa e termina com texto fixo, sem emoji e sem exclamação. Os exemplos usam a Moto Rápida em 07 out.

Na Meta, as variáveis vão como `{{n}}`. Na tabela, cada uma vem com o que preenche e o formato.

| # | Modelo | Texto para a Meta | Exemplo |
| --- | --- | --- | --- |
| 1 | `convite_acesso` | Olá, {{1}}. {{2}} convidou você para acessar o sistema. Crie sua senha em {{3}} O link vale por 7 dias. | Olá, Carla. Moto Rápida convidou você para acessar o sistema. Crie sua senha em https://motorapida.girolocadoras.com.br/convite#… O link vale por 7 dias. |
| 2 | `contrato_assinar` | Olá, {{1}}. {{2}} informa: seu {{3}} da {{4}} está pronto. Leia e assine em {{5}} O link vale por 7 dias. | Olá, Juliana. Moto Rápida informa: seu contrato de locação da LOC-2836 está pronto. Leia e assine em https://… O link vale por 7 dias. |
| 3 | `contrato_assinado` | Olá, {{1}}. {{2}} informa: seu {{3}} assinado da {{4}} está em {{5}} O link vale por 15 minutos. | Olá, Juliana. Moto Rápida informa: seu contrato de locação assinado da LOC-2836 está em https://… O link vale por 15 minutos. |
| 4 | `cobranca_lembrete` (D-1 e "Cobrar" antes do D-1) | Olá, {{1}}. {{2}} informa: {{3}}, de {{4}}, vence {{5}}. Se você já pagou, desconsidere esta mensagem. | Olá, Carlos. Moto Rápida informa: a parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence amanhã, 07/10. Se você já pagou, desconsidere esta mensagem. |
| 5 | `cobranca_hoje` (D0, com Pix) | Olá, {{1}}. {{2}} informa: {{3}}, de {{4}}, vence hoje. Pague pelo Pix copia e cola: {{5}} Se você já pagou, desconsidere esta mensagem. | Olá, Carlos. Moto Rápida informa: a parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence hoje. Pague pelo Pix copia e cola: 00020126… Se você já pagou, desconsidere esta mensagem. |
| 6 | `cobranca_hoje_sem_pix` (D0, sem recebimentos) | Olá, {{1}}. {{2}} informa: {{3}}, de {{4}}, vence hoje. Pague na loja. Se você já pagou, desconsidere esta mensagem. | Olá, Carlos. Moto Rápida informa: a parcela 3 de 5 da locação LOC-2841, de R$ 299,40, vence hoje. Pague na loja. Se você já pagou, desconsidere esta mensagem. |
| 7 | `cobranca_atraso` (D+3, D+7 e "Cobrar" em atraso, com Pix) | Olá, {{1}}. {{2}} informa: {{3}} venceu em {{4}}. {{5}} Pague pelo Pix copia e cola: {{6}} Se você já pagou, desconsidere esta mensagem. | Olá, Carlos. Moto Rápida informa: a parcela 2 de 5 da locação LOC-2841 venceu em 30/09. O valor hoje é R$ 306,09, com multa e juros. Pague pelo Pix copia e cola: 00020126… Se você já pagou, desconsidere esta mensagem. |
| 8 | `cobranca_atraso_sem_pix` | Olá, {{1}}. {{2}} informa: {{3}} venceu em {{4}}. {{5}} Pague na loja. Se você já pagou, desconsidere esta mensagem. | Olá, Carlos. Moto Rápida informa: a parcela 2 de 5 da locação LOC-2841 venceu em 30/09. O valor hoje é R$ 306,09, com multa e juros. Pague na loja. Se você já pagou, desconsidere esta mensagem. |
| 9 | `recibo_pagamento` (`AUT-05`) | Olá, {{1}}. {{2}} recebeu {{3}} {{4}} em {{5}}, da {{6}}. Este é o seu recibo. | Olá, Carlos. Moto Rápida recebeu R$ 306,09 por Pix em 07/10, da parcela 2 de 5 da locação LOC-2841. Este é o seu recibo. |
| 10 | `recibo_devolucao` (`DEV-02`) | Olá, {{1}}. {{2}} informa: a devolução da {{3}} foi concluída. {{4}} Veja o recibo em {{5}} O link vale por 15 minutos. | Olá, Juliana. Moto Rápida informa: a devolução da LOC-2836 foi concluída. Devolução de R$ 183,00 por Pix em até 1 dia útil. Veja o recibo em https://… O link vale por 15 minutos. |
| 11 | `lembrete_devolucao` (`AUT-01`) | Olá, {{1}}. {{2}} informa: hoje é o dia da devolução da {{3}}, às {{4}}, no endereço {{5}}. Para mudar o horário, ligue para a loja. | Olá, Juliana. Moto Rápida informa: hoje é o dia da devolução da LOC-2836, às 18:00, no endereço Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza. Para mudar o horário, ligue para a loja. |
| 12 | `assinatura_vence_hoje` (D0, Giro) | Giro: a fatura {{1}} da empresa {{2}}, de {{3}}, vence hoje. {{4}} Se você já pagou, desconsidere esta mensagem. | Giro: a fatura FAT-0001 da empresa Moto Rápida, de R$ 449,00, vence hoje. Boleto: https://… Se você já pagou, desconsidere esta mensagem. |
| 13 | `assinatura_em_atraso` (D+3, Giro) | Giro: a fatura {{1}} da empresa {{2}}, de {{3}}, venceu em {{4}} e ainda não foi paga. Sem o pagamento, em {{5}} a empresa fica suspensa. {{6}} Se você já pagou, desconsidere esta mensagem. | Giro: a fatura FAT-0001 da empresa Moto Rápida, de R$ 449,00, venceu em 22 out e ainda não foi paga. Sem o pagamento, em 06 nov a empresa fica suspensa. Boleto: https://… Se você já pagou, desconsidere esta mensagem. |

**O que preenche cada variável**

Os nomes, as contas, os valores e as datas seguem os textos de `docs/api/financeiro.md` ("Régua de cobrança: textos"), sem a abertura antiga "{marca}: olá".
- **Nomes e marca:**
  - `{{1}}` dos modelos 1 a 11: o primeiro nome do cliente ou da pessoa convidada;
  - `{{2}}` dos modelos 1 a 11: o nome de exibição da locadora (`marca.nome`), sem artigo.
- **Conta:** a conta por extenso, com minúscula ("a parcela 3 de 5 da locação LOC-2841"). O valor vem formatado em reais ("R$ 299,40").
- **Vencimento no modelo 4:** "amanhã, 07/10" no D-1, ou "em 14/10" no "Cobrar" antes do D-1.
- **Valor do dia nos modelos 7 e 8:** a frase inteira, como hoje: "O valor hoje é R$ 306,09, com multa e juros." ou, sem a cláusula de juros, "O valor é R$ 299,40.".
- **Recibo:**
  - forma no modelo 9: "por Pix", "por boleto", "no cartão de crédito", "em dinheiro" e as outras de `financeiro.md`;
  - `{{6}}` do modelo 9: a conta sem o artigo ("parcela 2 de 5 da locação LOC-2841", "cobrança de acerto da locação LOC-2841");
  - `{{4}}` do modelo 10: a frase do saldo (`texto_do_saldo`, `DEV-02`).
- **Contrato:** `{{3}}` dos modelos 2 e 3 é o título do modelo de contrato em minúscula ("contrato de locação"), e `{{4}}` é o código da origem.
- **Assinatura:** `{{4}}` do modelo 12 e `{{6}}` do 13 são o caminho de pagar do CA-ASS-66: "Boleto: {link}" no boleto, ou a mesma frase do e-mail nos outros caminhos.
- **Links:** o link vai seguido de espaço, sem ponto colado, para não quebrar o endereço. Por isso a frase seguinte começa com maiúscula, sem ponto antes ("em {{3}} O link vale...").

**Notas para a aprovação na Meta**
- Os textos têm frase fixa entre as variáveis e não começam nem terminam com variável.
- Se a Meta recusar uma variável que é frase inteira (valor do dia nos modelos 7 e 8, caminho de pagar nos modelos 12 e 13, saldo no modelo 10), a saída é dividir o modelo em dois. Por exemplo, `cobranca_atraso_juros` com "O valor hoje é {{5}}, com multa e juros." e `cobranca_atraso` com "O valor é {{5}}.". O texto que o cliente lê não muda.
- Se a Meta recusar o link no meio do texto, vale o plano B da ADR 0034: botão com link curto em domínio fixo, e a frase do link sai do texto.

## Critérios

**CA-WPP-01 · Começo e fim fixos**
Dado os 13 modelos, então nenhum começa nem termina com variável, nenhum tem emoji, exclamação, "fale com a gente" nem pedido de resposta, e cada texto montado com os dados do exemplo é exatamente o da coluna "Exemplo". `test_aut_03_modelos_do_whatsapp`.

**CA-WPP-02 · Cliente sem o aceite recebe só o e-mail** (`CLI-12`)
Dado o Carlos com celular, e-mail e o aceite desmarcado, quando a régua roda em 06/10 (D-1 da parcela 3), então nada sai pelo WhatsApp, e o e-mail "Moto Rápida: lembrete de vencimento" sai com o mesmo texto do modelo 4. Com o aceite marcado, saem os dois, e a conta conta uma vez no dia (`AUT-03`).

**CA-WPP-03 · Aceite no cadastro e na importação** (`CLI-12`)
Dado o Novo cliente, então a caixa "Aceita receber avisos pelo WhatsApp" começa desmarcada. Quando a Bruna marca e salva, ficam gravados a data e "Bruna Alves". Dado uma planilha de importação sem a coluna do aceite, então todos os clientes entram desmarcados.

**CA-WPP-04 · SAIR desmarca**
Dado o Carlos com o aceite marcado, quando ele responde "sair" ao WhatsApp, em qualquer caixa, então o aceite fica desmarcado na hora, com evento na auditoria. O próximo aviso dele vai só por e-mail. Quando ele responde "bom dia", recebe uma vez "Este número só envia avisos. Para falar com Moto Rápida, ligue para a loja: {telefone da Filial Centro}.", e o aceite não muda.

**CA-WPP-05 · Recibos e lembrete caem para o e-mail**
Dado a Juliana sem o aceite e com e-mail:
- na baixa da parcela por Pix, o recibo (modelo 9) sai por e-mail;
- em 14 out às 08:00, o lembrete (modelo 11) sai por e-mail;
- na devolução da LOC-2836, o recibo da devolução sai por e-mail com o PDF anexo, no lugar do link de 15 minutos.

Dado um cliente sem o aceite e sem e-mail, então nada sai, a falha fica no registro do envio, e a baixa e a devolução não mudam.

**CA-WPP-06 · Falha da Meta cai para o e-mail e marca "sem WhatsApp"**
Dado o Carlos com o aceite marcado, quando a Meta devolve `failed` (número sem WhatsApp) para o D0, então o mesmo aviso sai por e-mail no mesmo dia, e a régua não repete o WhatsApp. Depois da 3ª falha seguida, o cadastro mostra o celular "sem WhatsApp", e os avisos seguintes vão direto ao e-mail.

**CA-WPP-07 · Convite com o aceite** (`USR-01`)
Dado a Mariana convidando a Carla Nunes (fictícia) com celular, quando a caixa "A pessoa aceita receber o convite pelo WhatsApp" fica desmarcada, então o convite sai só por e-mail. Marcada, sai também pelo modelo 1.
