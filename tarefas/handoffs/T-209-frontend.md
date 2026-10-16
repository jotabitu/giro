# T-209 · Ajustes de cadastro e caixa achados no E2E · frontend → orquestrador, qa

**O que foi feito:** (b) no Novo cliente, as quatro fotos aceitam arquivo antes do primeiro "Salvar cliente"; os arquivos ficam na tela e sobem logo após o POST (`/api/clientes/{id}/documentos/`), então "Salvar e iniciar locação" já abre a locação com as fotos. Se uma foto falhar, o cliente fica salvo, a tela avisa quais não foram e oferece abrir a ficha. (c) o CEP preenche rua, bairro, cidade e UF pelo `GET /api/enderecos/cep/{cep}/` que já existia (o mesmo das filiais, sem serviço externo novo); CEP desconhecido pede o preenchimento à mão. (e) no celular, o cartão "Entrou hoje" do caixa mostra "N recebimentos" (valor da API).
**Onde:** frontend/src/components/clientes/NovoClienteForm.tsx, frontend/src/components/financeiro/CaixaDoDia.tsx
**Regras cobertas:** CLI-01, FIN-01 (testes em NovoClienteForm.test.tsx e Financeiro.test.tsx)
**O que ficou de fora:** o item (d) é da T-261. Os testes são de marcação estática (sem jsdom), então o envio das fotos após o POST e o preenchimento ao digitar o CEP não têm teste de interação; ficam para o E2E do qa.
**Próximo passo para quem recebe:** orquestrador abre o PR; qa repete no E2E o cadastro com fotos antes do Salvar e o CEP.
