# T-305 · Pix do boleto no contrato de pagamentos · arquiteto → orquestrador, backend, devops, qa

Origem: achado do backend na T-297 (PR #310). O boleto da conta principal sai sem `pix_copia_e_cola`: o `Asaas._completar` só busca o `pixQrCode` na cobrança `pix`, e o falso faz igual. O e-mail do boleto (`plataforma/tasks.py`) imprime "Pix copia e cola:" vazio, e a T-298 conta com o Pix do boleto no "Pagar" sem `meio`.

**O que achei:**
- **Documentação do Asaas**, referência "Obter QR Code para pagamentos via Pix" (`GET /v3/payments/{id}/pixQrCode`): a rota "é compatível com cobranças `PIX`, `BOLETO` e `UNDEFINED` quando o Pix estiver disponível como forma de pagamento". A resposta traz `encodedImage`, `payload` (o copia e cola), `expirationDate` e `description`. Com chave Pix na conta, o QR expira 12 meses depois do vencimento; sem chave, só pode ser pago até 23:59 do dia, e a documentação diz que a geração sem chave vai ser descontinuada.
- **Gravação de contrato** (`backend/tests/integracoes/gravacoes/asaas.json`): o caso `boleto_rafael` só chama `POST /payments` e `GET .../identificationField`; nenhuma gravação tem `pixQrCode` de boleto. As gravações foram montadas pela documentação e não pelo sandbox (`_leia`), então nada ali confirma nem nega.

**O que foi feito:** em `docs/api/financeiro.md`:
- "Interface de pagamentos" ganhou "O que cada cobrança devolve", com uma tabela por `tipo`. O boleto traz `linha_digitavel`, `boleto_url` e o Pix dele em `pix_copia_e_cola`, pelo mesmo `pixQrCode`.
- Pix recusado no boleto (400): o boleto sai sem ele e não é cancelado. Parceiro fora do ar: cancela e tenta de novo, como já é.
- Ninguém imprime "Pix copia e cola:" sem código.
- 4 pontos a conferir no sandbox (abaixo).
- Em `POST .../contas-receber/{id}/cobranca/`, o exemplo do boleto com o Pix.

Vale para as contas a receber (subconta, T-029) e para as faturas da assinatura (conta principal). Sem rota nova; a resposta de `cobranca/` já tinha `pix_copia_e_cola`, então o OpenAPI não muda.

**A conferir no sandbox** (chave só de sandbox, pelo `test_t029_asaas_sandbox.py`, nunca chave real; o repositório é público):
1. `pixQrCode` de cobrança `BOLETO` na conta principal e numa subconta, e o erro quando a conta não tem chave Pix.
2. O `expirationDate` do Pix do boleto. Sem chave Pix, ele valeria só até 23:59 do dia da emissão, e o boleto da assinatura sai 5 dias antes. A conta principal e cada subconta precisam de chave Pix cadastrada: isso é com o devops (ambiente) e com quem abre a subconta (passo "Recebimentos").
3. O boleto pago pelo Pix: que `billingType` volta no `GET /payments/{id}` e no webhook. Disso depende se a baixa grava `forma = pix` ou `boleto` (`FIN-04`).
4. As respostas gravadas em `asaas.json`, só com dados fictícios.

**Regras:** FIN-04, PLT-02, PLT-13 (o Pix do boleto da T-296/T-298).

**Tarefa de backend (para o orquestrador numerar):**

> **Pix do boleto no Asaas e no falso** · **Agente:** backend · **Depende de:** T-305 · **Regras:** FIN-04, PLT-02, PLT-13 · **Pronto quando:**
> - `Asaas._completar`, no `boleto`: depois da `identificationField`, chama `GET /payments/{id}/pixQrCode` e põe o `payload` em `pix_copia_e_cola`. Com 400 do parceiro (`ParceiroRecusou`), devolve o boleto sem o Pix, com um aviso no log e sem cancelar. Com `ParceiroIndisponivel`, cancela e sobe, como hoje;
> - `PagamentosFalso.criar_cobranca`: o boleto também ganha `pix_copia_e_cola` (e continua sem `qr_code_url`), com uma forma de simular "Pix não disponível" para o teste do boleto sem Pix;
> - a `CobrancaExterna` (financeiro) e a `FaturaAssinatura` (plataforma) gravam o Pix do boleto. O e-mail do boleto da assinatura (`plataforma/tasks.py`) e a mensagem da régua `AUT-03` (`financeiro/services.py`) só escrevem a linha do Pix quando o código existe;
> - gravações novas em `gravacoes/asaas.json` (`boleto_rafael` com o `pixQrCode`, e um caso de boleto com o Pix recusado) e o caso no `test_t029_asaas_sandbox.py` para os pontos 1 a 3 acima, rodado só localmente com a chave de sandbox;
> - testes `test_fin_04_boleto_traz_o_pix`, `test_fin_04_boleto_sem_pix_disponivel_nao_cancela`, `test_plt_02_email_do_boleto_sem_linha_pix_vazia` e o "Pagar" sem `meio` da T-298 devolvendo o boleto com o Pix (`test_plt_13_pagar_devolve_o_boleto_com_pix`).
> - Depois, no handoff: o resultado dos pontos 1 a 3 do sandbox. Se o boleto pago pelo Pix voltar como `PIX`, a `forma` da baixa segue o parceiro. Se voltar `BOLETO`, o arquiteto e o produto decidem se a baixa olha outro campo.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar a tarefa acima e abrir o PR desta branch. Ela pode ir junto com a T-297, que já tem o e-mail do boleto aberto.
- **DevOps:** chave Pix cadastrada na conta principal do sandbox e, depois, na de produção (sem segredo no repositório).
- **QA:** CA-ASS-10 e CA-ASS-63 passam a conferir o Pix no e-mail do boleto.
