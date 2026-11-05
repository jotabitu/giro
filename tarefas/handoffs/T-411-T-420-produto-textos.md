# T-411 e T-420 · Textos que o arquiteto deixou para o produto · produto → orquestrador, backend, frontend, qa

**O que foi feito:** os textos que os contratos marcavam "a confirmar com o produto" foram fixados nas regras e nos contratos. Nenhum comportamento muda, com uma exceção: a `LOC-16` agora diz que o encerramento por atraso só vale com uma parcela atrasada. O contrato já exigia isso.

## T-411 · Copiar link

| Onde | Antes (proposta) | Agora |
| --- | --- | --- |
| Aviso junto do link do contrato (passo 3 do fluxo da locação; `copiar-link.md`, `locacoes.md`) | "Mande o link ao cliente. Só ele pode assinar." | "Mande o link só ao cliente. Só ele pode assinar, e o contrato registra que você copiou o link." |
| E-mail do cartão guardado que muda (`PLT-13`, `assinatura.md`) | "Giro: o cartão das próximas faturas mudou para Visa final 4242. Se não foi você, troque a forma de pagamento em Assinatura." | Assunto "O cartão da assinatura mudou". Texto "O cartão das próximas faturas da empresa {empresa} mudou para {bandeira} final {final}, no nome de {titular}, no pagamento da {fatura} em {data}. Se ninguém da empresa fez essa troca, troque a forma de pagamento em Assinatura: {endereço}." |

**Por quê:**
- **Aviso do link:** o aviso diz a quem atende o que fica registrado, que é a prova da M-02.
- **E-mail do cartão:**
  - A troca pode ter sido feita por outro administrador, então "Se não foi você" assustaria à toa.
  - O nome do titular, a fatura e a data deixam ver na hora se a troca é estranha.
  - Todo e-mail da assinatura leva o endereço da página (T-299).
  - Se o parceiro não devolver o titular, a frase sai sem "no nome de …".

## T-420 · Intenção de compra

| Onde | Antes (proposta) | Agora |
| --- | --- | --- |
| `andamento` com uma parcela a pagar | "Parcela 23 de 24 · faltam 1 para a transferência" (pelo molde) | "Parcela 23 de 24 · falta 1 para a transferência" |
| `andamento` com todas pagas e outra conta aberta | "24 de 24 parcelas pagas · falta pagar o que está abaixo para a transferência" | "24 de 24 parcelas pagas · faltam as contas abaixo para a transferência" |
| `andamento` quitada | "Quitada · veículo do cliente" | "Quitada em 10/10/2028 · falta a transferência no Detran" e, depois de registrar, "Quitada em 10/10/2028 · transferência feita em 15/10/2028" |
| 409 encerrar por atraso sem parcela atrasada | "Só se encerra por atraso com uma parcela atrasada." | "Esta locação não tem parcela atrasada. Para encerrar a pedido do cliente, use Cancelar locação." |
| 409 renovar e trocar | os do contrato | confirmados, sem mudança |
| `VEN-11`: cancelar a venda, registrar a transferência de novo | os de `vendas.md` | confirmados e registrados na regra |
| Aviso do encerramento antes do fim | "O que foi pago fica como aluguel do período usado." | confirmado |

**Por quê:**
- **Texto da quitada:** o anterior dava o veículo como do cliente antes da transferência no Detran. O novo mostra a pendência que o gerente tem de fechar e não precisa de outro selo.
- **Recusa do encerramento por atraso:** agora diz o caminho certo ("Cancelar locação", o botão do gerente na ficha).
- **Encerramento só com parcela atrasada:** é leitura do produto, porque a decisão de 30 out fala em encerrar "pelo atraso". Fica registrado na `LOC-16`, sem ponto em aberto. Se o dono quiser o encerramento pela locadora também sem atraso, é só tirar a condição.

## Arquivos

- `docs/regras-de-negocio.md`:
  - passo 3 do fluxo da locação ("Copiar link para assinar");
  - `PLT-13` ("Cartão guardado que muda");
  - `LOC-16` ("Atraso", "Na tela", "Recusas");
  - `VEN-11`;
  - notas de mudança em 05 nov 2026 nas seções Plataforma, Locação e Vendas;
  - linha "Copiar o link (29 out, T-411)" na tabela de decisões de 29 e 30 out.
- `docs/api/copiar-link.md`, `docs/api/locacoes.md` e `docs/api/assinatura.md`: os textos acima.
- `docs/qa/criterios/T-420.md`:
  - CA-420-06 ganhou as mensagens;
  - novos CA-420-18 (andamento) e CA-420-19 (encerrar por atraso sem parcela atrasada).

## Próximo passo

- **Backend:** montar os textos como estão. Os testes `test_loc_16_*` conferem o singular, a quitada com a transferência e o 409. Os testes `test_plt_13_cartao_novo_avisa_o_administrador` conferem o assunto e o texto do e-mail.
- **Frontend:** o aviso do link copiado na Locacao-Detalhe. O andamento e as recusas vêm prontos da API.
- **QA:** CA-420-18 e 19. A T-411 não tem arquivo de critérios. Os textos ficam nos contratos para os testes do backend.
