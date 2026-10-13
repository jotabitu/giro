# T-029 · Integração com o Asaas (sandbox) · backend → orquestrador, arquiteto, devops, qa, seguranca

**O que foi feito:**
- `backend/integracoes/pagamentos/asaas.py`: a implementação real da interface (ADR 0007), só com a biblioteca padrão (`urllib`, como o ViaCEP). **Nenhuma dependência nova.**
  - Subconta: `criar_subconta` (`POST /v3/accounts` pela chave da conta principal, já com o webhook da subconta: URL, `authToken` de 43 caracteres e os eventos de pagamento) e `consultar_subconta` (`GET /v3/myAccount/status` pela chave da subconta).
  - Cobrança Pix e boleto: o pagador é achado pelo CPF (`GET /customers?cpfCnpj=`) ou criado uma vez com `notificationDisabled: true`, para o cliente só receber as mensagens do Giro com a marca da locadora (CA-029-03). Antes de criar, cancela a cobrança `PENDING` que tenha a mesma referência externa (o id da conta), para não deixar duas abertas se uma tentativa anterior falhou do lado do Giro (CA-029-16). Depois busca o Pix copia e cola (`/pixQrCode`) ou a linha digitável (`/identificationField`). Se essa segunda chamada falhar, a cobrança é cancelada no Asaas: nada fica pela metade.
  - `cancelar_cobranca`: 400 ou 404 do Asaas (já paga ou já removida) só gera log e não trava a nova cobrança. Se ela foi paga, o webhook vira pendência (CA-029-07, CA-029-13).
  - `consultar_cobranca`: a tabela `STATUS_COBRANCA` faz a tradução. `PENDING` e `AWAITING_RISK_ANALYSIS` → `aguardando`; `RECEIVED` e `CONFIRMED` → `paga`; `OVERDUE` → `vencida`; estorno e contestação → `estornada` (que vira pendência); `deleted` ou 404 → `cancelada`. Qualquer outro status levanta `StatusDesconhecido` (CA-029-08). O Asaas só informa o dia do pagamento: pago hoje, `pago_em` é agora; pago em outro dia, é a meia-noite desse dia no fuso de São Paulo.
  - Pix Automático (AUT-04): `criar_autorizacao_recorrente` (`POST /v3/pix/automatic/authorizations`, modo `MANUAL`, primeira cobrança no `immediateQrCode`), `cobrar_com_autorizacao` (`POST /payments` com `pixAutomaticAuthorizationId`) e `cancelar_autorizacao` (`DELETE`).
  - `validar_webhook`: igual ao do falso (lê o evento e o token do cabeçalho `asaas-access-token`).
  - Dinheiro: centavos → `Decimal` → número no JSON (306.09) e de volta por `parse_float=Decimal`, sem `float` (CA-029-05). Fração de centavo é recusada.
  - Falhas: tempo limite de 10 s. Sem resposta ou 5xx → `ParceiroIndisponivel`; 4xx → `ParceiroRecusou`, com a mensagem do Asaas (em português, com "Asaas" trocado por "parceiro de pagamento"). Só HTTPS.
  - Log: só o método, o caminho sem a consulta (que pode ter CPF) e o status HTTP. Nunca a chave, o corpo nem o CPF. `repr` da referência, da subconta e do provedor sem a chave.
- `base.py`: a interface do contrato completa (`criar_subconta`, `DadosEmpresa`, `Subconta`, `PedidoRecorrencia`, `Autorizacao`, recorrência) e mais:
  - `consultar_subconta`;
  - `Pagador.email`;
  - as exceções `ParceiroIndisponivel`, `ParceiroRecusou` e `StatusDesconhecido`;
  - `ContaPagamentoRef.decifrar_chave`, que passa a chave adiante sem decifrar: ela só é decifrada dentro da implementação, na hora da chamada (S-05).

  O `falso.py` ganhou os métodos novos (subcontas e autorizações na memória).
- `integracoes/pagamentos/__init__.py`: `provedor()` aceita `asaas`. `referencia(conta)` monta a referência a partir da `ContaPagamento`.
- `plataforma.ContaPagamento`:
  - ganhou `chave_api_cifrada` (`CampoCifrado` com a chave dos segredos, ADR 0014), `id_cifra` (`ModeloComCifra`, com `empresa_id_da_cifra` = a empresa da subconta) e `carteira_id`;
  - passou a ser `MaquinaDeEstados`: `pendente` → `aprovada` ou `recusada`, com auditoria (categoria `configuracoes`, regra FIN-04);
  - a chave e o hash do token ficam omitidos na auditoria.

  Migração `plataforma/0008` em três passos: o `id_cifra` nasce nulo, é preenchido e só então fica único.
- `plataforma.services.conectar_recebimentos(...)` (CA-029-01 e CA-029-02):
  - abre a subconta com um token aleatório de 32 bytes e guarda só o hash dele e a chave cifrada;
  - marca o passo `recebimentos` da implantação;
  - se o Asaas recusa, levanta 422 `parceiro_recusou` com o motivo, e nada é gravado;
  - se a empresa já tem subconta, levanta 409 `recebimentos_conectados`.

  `atualizar_recebimentos()` consulta a aprovação no Asaas. A URL do webhook é `https://admin.<DOMINIO_BASE>/api/webhooks/pagamentos/asaas/`, ou `GIRO_URL_WEBHOOK_PAGAMENTOS` (para usar um túnel no desenvolvimento).
- `financeiro`:
  - `gerar_cobranca` usa a chave da subconta. Com o Asaas fora do ar, responde 503 `parceiro_indisponivel` com a mensagem do critério ("Não conseguimos falar com o parceiro de pagamento. Tente de novo em alguns minutos."), sem gravar nada (`comum.erros.ParceiroForaDoAr`, novo). Com o Asaas recusando, 422 `parceiro_recusou`.
  - A régua (AUT-03) manda a mensagem sem o Pix se o Asaas falhar, em vez de parar.
  - `_processar` trata o `StatusDesconhecido`: resultado `status_desconhecido`, aviso para administradores e financeiros, e nenhuma baixa.
  - `aut_05_processar_webhook` tenta de novo com o Asaas fora do ar (`autoretry_for`, espera crescente de 60 s até 1 h, 24 vezes). O aviso fica sem `processado_em` até lá.
- **Defeito da T-017 corrigido no caminho:** a baixa pelo webhook gravava a multa e os juros do dia do `criado_em` da cobrança (o relógio real), e não do dia de referência em que ela foi gerada. Com a data de referência do desenvolvimento (ADR 0021) e nos testes, o Carlos recebia 130 de juros em vez de 70. Agora a `CobrancaExterna` guarda `gerada_no_dia` (pelo `comum.relogio`; migração `financeiro/0005`), e a baixa e o `resolver_pendencia` usam esse dia. As cobranças antigas continuam pelo `criado_em`.
- Settings: `GIRO_ASAAS_URL` (padrão: sandbox `https://api-sandbox.asaas.com/v3`), `GIRO_ASAAS_CHAVE_API` e `GIRO_URL_WEBHOOK_PAGAMENTOS`. Em `test.py`, `GIRO_PROVEDOR_PAGAMENTOS = "falso"` fixo: os testes nunca falam com o Asaas, nem com a chave no ambiente.

**Onde:** `backend/integracoes/pagamentos/{asaas,base,falso,__init__}.py`, `backend/apps/plataforma/{models,services}.py`, `backend/apps/plataforma/migrations/0008_chave_da_subconta.py`, `backend/apps/financeiro/{models,services,tasks}.py`, `backend/apps/financeiro/migrations/0005_dia_da_cobranca.py`, `backend/comum/erros.py`, `backend/config/settings/{base,test}.py`, `backend/tests/integracoes/` (gravações, transporte de reprodução, testes de contrato e do sandbox) e `backend/tests/aceitacao/test_t029_asaas.py`.

**Contrato:** sem mudança no OpenAPI (nenhuma rota nova; o webhook segue fora do OpenAPI). A interface interna mudou (ver "Para o arquiteto").

**Regras cobertas:** FIN-04, AUT-04 (só a parte do provedor), AUT-05, S-05, S-14 e CA-029-01 a 08, 10, 11, 13, 16 e 17.
- Testes de contrato (`tests/integracoes/test_t029_asaas_contrato.py`, 35): sem rede, sem chave e sem banco, contra as gravações de `tests/integracoes/gravacoes/asaas.json`.
- Testes de aceitação (`tests/aceitacao/test_t029_asaas.py`, 13): o financeiro e a plataforma com `GIRO_PROVEDOR_PAGAMENTOS=asaas` e o transporte trocado pelas gravações. Cobrem:
  - o Pix do Carlos de 30609 pela API;
  - o 503;
  - o webhook recebido, repetido e confirmado, com uma baixa só e multa de 599 + juros de 70;
  - o recibo "recebemos R$ 306,09";
  - o status desconhecido e o aviso dele;
  - o Asaas fora do ar sem perder o aviso;
  - a subconta: chave cifrada, auditoria sem a chave e o passo da implantação;
  - a subconta em análise (422 `recebimentos_desligados`) e depois aprovada;
  - a subconta recusada;
  - a importação de `integracoes.pagamentos` só por `financeiro` e `plataforma`, e a do `asaas` só pela interface.
- A suíte inteira passou (ver "Antes do push"). Os testes da T-017 continuam com o `falso`, sem mudança.

**Sandbox: não rodou.** Não tenho chave do sandbox. Os testes estão em `tests/integracoes/test_t029_asaas_sandbox.py` e pulam sem `GIRO_ASAAS_SANDBOX_CHAVE`. Para rodar na máquina:

    GIRO_ASAAS_SANDBOX_CHAVE=<chave da conta de sandbox> pytest tests/integracoes/test_t029_asaas_sandbox.py -v

A abertura de subconta só roda com `GIRO_ASAAS_SANDBOX_SUBCONTA=1` e `GIRO_ASAAS_SANDBOX_CHAVE_PRINCIPAL`. **As gravações foram montadas pelo formato da documentação do Asaas (docs.asaas.com), e não capturadas do sandbox.** Quem rodar o sandbox confere se as respostas batem com as gravações e as ajusta se preciso, sempre com dados fictícios. O critério pede a saída do sandbox no handoff antes do PR: isso fica pendente até alguém com a chave rodar.

**O que ficou de fora:**
1. **CA-029-09 (recorrente na locação):** o provedor está pronto, mas falta o fluxo no Giro. Faltam o model `AutorizacaoRecorrente` (modelo de dados, item 441), a autorização criada quando a locação fica `ativa`, a `aut_04_cobranca_recorrente` e o cancelamento no encerramento. Esse fluxo depende de uma decisão e de um evento que hoje não existe. Pela documentação do Asaas, **a cobrança do Pix Automático tem que ser criada de 2 a 10 dias úteis antes do vencimento**, e o contrato diz "no vencimento de cada parcela". Registrei como `[decisão]` no backlog (para o produto). Além disso, `locacoes` não publica evento de ativação nem de encerramento, e o financeiro não pode importar `locacoes` (ADR 0011): o arquiteto precisa dizer por onde o financeiro fica sabendo.
2. **Rota do passo "Recebimentos":** `conectar_recebimentos` e `atualizar_recebimentos` existem como serviço, mas não há contrato de API para o passo 10 nem para a consulta da aprovação (tarefa periódica ou botão). Pedido ao arquiteto.
3. **CA-029-15 (Pix gerado no caixa):** o caminho é o mesmo da T-017 (já testado com o falso). Com o Asaas, só depende do sandbox.
4. **CA-029-12 e CA-029-14** (token errado e limite de 120 por minuto): sem mudança, já cobertos pela T-017.
5. **CA-029-18:** a conta principal e as faturas `FAT-` ficam para a fase 2; a interface aceita a referência sem chave da subconta, e aí usa a chave do ambiente.
6. **Trava de produção (T-157):** `prod.py` ainda aceita `GIRO_PROVEDOR_PAGAMENTOS=falso`. Fica na T-157, que já prevê isso.
7. **QR code como imagem:** o Asaas devolve o QR em base64, e `CobrancaExterna.url` tem 300 caracteres. Com o Asaas, `qr_code_url` sai vazio e a tela desenha o QR a partir do copia e cola. Hoje o frontend não usa `qr_code_url`. Se a imagem for necessária, ela precisa de armazenamento (arquiteto).
8. **Dados bancários da subconta:** o `POST /v3/accounts` não recebe conta bancária (o critério CA-029-01 cita "dados bancários"). Pela documentação, ela fica para depois, no próprio Asaas. Também fica para depois a proteção de saque da S-05, item 4. Ver com o produto e a segurança.

**Para o arquiteto:** atualizar a "Interface de pagamentos" em `docs/api/financeiro.md` com:
- `consultar_subconta`;
- `Pagador.email`;
- as três exceções e os códigos `parceiro_indisponivel` (503) e `parceiro_recusou` (422);
- `ContaPagamentoRef.decifrar_chave` e `referencia(conta)`;
- `CobrancaExterna.gerada_no_dia`.

Precisam de contrato ou decisão: a rota do passo 10, o modo de saber a aprovação da subconta e o evento de locação ativada e encerrada para o AUT-04. Nada disso mudou o OpenAPI.

**Para o devops (`.env.example`):** variáveis novas, todas vazias no exemplo e nunca no repositório:
- `GIRO_PROVEDOR_PAGAMENTOS`: `falso` | `asaas`. O padrão é `falso`; homologação e produção usam `asaas`.
- `GIRO_ASAAS_URL`: o padrão é o sandbox (`https://api-sandbox.asaas.com/v3`); em produção, `https://api.asaas.com/v3`.
- `GIRO_ASAAS_CHAVE_API`: a chave da conta principal do Giro, que só abre subcontas. Vai no cofre de segredos do ambiente.
- `GIRO_URL_WEBHOOK_PAGAMENTOS`: vazia em homologação e produção. No desenvolvimento com o sandbox, é o endereço HTTPS de um túnel.
- Só local, para os testes do sandbox: `GIRO_ASAAS_SANDBOX_CHAVE`, `GIRO_ASAAS_SANDBOX_SUBCONTA` e `GIRO_ASAAS_SANDBOX_CHAVE_PRINCIPAL`.
- O proxy (T-158) precisa deixar passar o cabeçalho `asaas-access-token` no webhook.

**Para a segurança:** conferir:
- a chave da subconta cifrada com a chave dos segredos, com o dado associado amarrado à empresa e à linha;
- a decifração só em `asaas.py`, por `ContaPagamentoRef.decifrar_chave`;
- o log sem chave e sem CPF;
- o token do webhook de 32 bytes, com só o SHA-256 guardado;
- a mensagem de erro do Asaas indo para a tela da locadora (só para quem trabalha nela, nunca para o cliente final).

**Próximo passo para quem recebe:**
- **Orquestrador:** decidir quem roda o sandbox com uma chave local (o dono do produto, ou passar a chave ao backend por variável de ambiente, nunca por arquivo) e criar as tarefas dos itens 1, 2 e 7.
- **QA:** conferir os critérios cobertos com as gravações e, com a chave, rodar o arquivo do sandbox.
