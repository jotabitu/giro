# Integração real do WhatsApp

**Status:** proposta · 25 out 2026 · T-385 (achado da ADR 0033) · detalha a 0011 (integrações atrás de interface) e a 0012 (tarefas por empresa); aceita quando o dono escolher a opção

## Contexto

Hoje o código só tem o provedor falso (`backend/integracoes/whatsapp`, `GIRO_PROVEDOR_WHATSAPP=falso`): `enviar_whatsapp(celular, texto)` guarda a mensagem numa caixa de saída em memória. A fase 1 manda WhatsApp em nove pontos:

| # | Quando | Regra | Onde no código | Marca |
| --- | --- | --- | --- | --- |
| 1 | Convite de acesso | `USR-01` | `contas/tasks.py` | locadora |
| 2 | Contrato para assinar (envio e reenvio do link) | contrato digital (`contratos.md`), `IMP-04` | `contratos/tasks.py` | locadora |
| 3 | Contrato assinado (reenvio do PDF) | contrato digital (`contratos.md`) | `contratos/tasks.py` | locadora |
| 4 | Régua de cobrança: D-1, D0, D+3, D+7 e "Cobrar" manual | `AUT-03` | `financeiro/services.py` (`cobrar`) | locadora |
| 5 | Recibo do pagamento | `AUT-05` | `financeiro/services.py` (`_enviar_recibo`) | locadora |
| 6 | Recibo da devolução | `DEV-02` | `vistorias/tasks.py` | locadora |
| 7 | Lembrete de devolução, às 08:00 do dia | `AUT-01` (T-367) | ainda não existe | locadora |
| 8 | Régua da assinatura: D0 e D+3, ao responsável | `PLT-02`, `AUT-13` | `plataforma/services.py` (`avisar_pela_regua`) | Giro |
| — | Aviso de implantação parada | `IMP-06`, `AUT-14` | fase 2 (D6) | Giro |

**O que a Meta exige, e vale para qualquer opção.** Toda mensagem que a empresa inicia fora da janela de 24 horas depois de uma mensagem do cliente tem de ser um **modelo aprovado** (*template*). Os nove pontos são todos iniciados pela empresa. Os modelos são da categoria **utilidade** (aviso de conta, pagamento, documento), não de marketing.

Regras dos modelos que afetam os textos de hoje:
- o texto **não pode começar nem terminar com uma variável**;
- o modelo tem texto fixo e variáveis `{{n}}`;
- botão de link só aceita variável no fim de um endereço com domínio fixo.

Desde julho de 2025, a Meta cobra **por mensagem de modelo entregue**, pela categoria e pelo país do destinatário. A resposta dentro da janela de 24 horas é gratuita.

## Decisão a tomar

São duas perguntas independentes:
1. **Por onde enviar:** pela API da Meta direta ou por um parceiro oficial (BSP).
2. **De que número:** um número só do Giro ou um número por locadora (white label).

As três opções abaixo combinam as duas.

**Volume estimado:** cerca de 600 mensagens por empresa por mês. A conta é de 40 locações ativas: parcelas com 2 mensagens da régua cada, recibos, contratos, devoluções e lembretes.
- **Piloto** (3 empresas): cerca de 1.800 mensagens por mês.
- **20 empresas:** cerca de 12.000 mensagens por mês.

**Preço da Meta no Brasil, utilidade:** cerca de US$ 0,007 por mensagem entregue, ou R$ 0,04 com o dólar a R$ 5,50. É uma estimativa de outubro de 2026; conferir na tabela da Meta ao contratar.

### Opção A · API da Meta direta, um número só do Giro

- **Como:**
  - uma conta WhatsApp Business (WABA) do Giro no Meta Business verificado, com um número dedicado e o nome de exibição aprovado pela Meta;
  - um app no Meta for Developers com token de usuário de sistema;
  - envio pela Graph API (`POST /{phone_number_id}/messages`), sem intermediário.
- **Custo:** piloto cerca de R$ 75 por mês; 20 empresas, cerca de R$ 500 por mês. Sem mensalidade: a Meta cobra no cartão da WABA.
- **Modelos:** aprovados uma vez, na WABA do Giro, e valem para todas as locadoras.
- **White label:**
  - o remetente aparece com o nome de exibição do Giro, por exemplo "Giro Avisos". A marca da locadora vai só no texto;
  - **a resposta do cliente chega ao Giro, não à locadora**: o texto "fale com a gente por aqui" de hoje (`financeiro.md`) deixa de ser verdade;
  - serve bem à régua da assinatura, que já é do Giro.
- **Prós e contras:** é a mais simples e barata e começa em dias. Mas é um meio-termo do white label, e o Giro passa a receber respostas de clientes das locadoras.

### Opção B · API da Meta direta, um número por locadora

- **Como:**
  - o Giro se cadastra como *Tech Provider* da Meta;
  - cada locadora conecta a própria WABA e o próprio número pelo *Embedded Signup*, numa tela do Giro;
  - o Giro envia com o `phone_number_id` de cada empresa;
  - a régua da assinatura continua pelo número do Giro.
- **Custo:** o mesmo preço por mensagem da A, cobrado na WABA de cada locadora, no cartão dela, ou repassado.
- **Modelos:** criados pela API em cada WABA nova, e cada um passa pela aprovação da Meta. Uma locadora só começa a enviar quando os modelos dela estão aprovados.
- **White label:** completo. O remetente é a locadora, e a resposta chega a ela.
- **Prós e contras:**
  - Pede tela de conexão, guarda do token de cada empresa (cifrado, ADR 0014), suporte ao cadastro de cada locadora no Meta Business e acompanhamento da aprovação dos modelos por empresa.
  - A locadora sem Meta Business verificado fica sem WhatsApp até se verificar.
  - É trabalho de fase 2.

### Opção C · Parceiro oficial (BSP)

- **Exemplos:** 360dialog, Twilio, Gupshup, Zenvia, Blip.
- **Como:** o parceiro hospeda a WABA e dá uma API própria. Os bons oferecem cadastro de números de clientes por API, o que serve tanto para a A quanto para a B.
- **Custo:** o preço da Meta mais o do parceiro.
  - 360dialog: cerca de R$ 300 por número por mês.
  - Twilio: cerca de US$ 0,005 por mensagem a mais.
  - Piloto: cerca de R$ 375 a 400 por mês.
  - 20 empresas, com um número: cerca de R$ 800 a 850 por mês.
  - Com um número por locadora na 360dialog, a mensalidade multiplica.
- **Prós e contras:**
  - Painel pronto, suporte em português (Zenvia e Blip) e menos trabalho no cadastro de números.
  - Custo maior, mais um fornecedor com dados pessoais (operador, LGPD) e a API presa ao parceiro.

## O que vale para a opção escolhida

### Modelos de mensagem da fase 1

São todos da categoria utilidade, em `pt_BR`, com a marca da locadora como variável no meio do texto. Os textos de hoje (`financeiro.md`, "Régua de cobrança: textos"; `docs/qa/criterios/assinatura.md`, CA-ASS-64 a 67) começam com a variável `{marca}:` e às vezes terminam com o código Pix. A Meta recusa as duas coisas. A proposta abaixo muda só a abertura e o fim. **Mudança de texto é do produto: fica como `[decisão]` para ele.**

| Modelo | Texto proposto (variáveis numeradas) |
| --- | --- |
| `convite_acesso` | "Olá, {{1}}. A {{2}} convidou você para acessar o sistema. Crie sua senha em {{3}}. O link vale por 7 dias." |
| `contrato_assinar` | "Olá, {{1}}. Seu {{2}} da {{3}}, com a {{4}}, está pronto. Leia e assine em {{5}}. O link vale por 7 dias." |
| `contrato_assinado` | "Olá, {{1}}. Seu {{2}} assinado da {{3}}, com a {{4}}, está em {{5}}. O link vale 15 minutos." |
| `cobranca_lembrete` (D-1 e manual antes) | "Olá, {{1}}. Aqui é a {{2}}. {{3}}, de {{4}}, vence {{5}}. Obrigado." |
| `cobranca_hoje` (D0, com Pix) | "Olá, {{1}}. Aqui é a {{2}}. {{3}}, de {{4}}, vence hoje. Pague pelo Pix copia e cola: {{5}} . Obrigado." |
| `cobranca_hoje_sem_pix` (D0, sem recebimentos) | "Olá, {{1}}. Aqui é a {{2}}. {{3}}, de {{4}}, vence hoje. Pague na loja. Obrigado." |
| `cobranca_atraso` (D+3, D+7 e manual, com Pix) | "Olá, {{1}}. Aqui é a {{2}}. {{3}} venceu em {{4}}. {{5}} Pague pelo Pix copia e cola: {{6}} . Obrigado." ({{5}} = "O valor hoje é R$ 306,09, com multa e juros.") |
| `cobranca_atraso_sem_pix` | o mesmo, com "Pague na loja." no lugar do Pix |
| `recibo_pagamento` (`AUT-05`) | "Olá, {{1}}. A {{2}} recebeu {{3}} {{4}} em {{5}}, da {{6}}. Este é o seu recibo." |
| `recibo_devolucao` | "Olá, {{1}}. Recibo da devolução da {{2}}, na {{3}}. {{4}} Veja o recibo em {{5}}. O link vale 15 minutos." |
| `lembrete_devolucao` (`AUT-01`) | "Olá, {{1}}. Hoje é o dia da devolução da {{2}} na {{3}}, às {{4}}, no endereço {{5}}. Até logo." |
| `assinatura_vence_hoje` (D0, Giro) | "Giro: a fatura {{1}} da empresa {{2}}, de {{3}}, vence hoje. {{4}} Obrigado." |
| `assinatura_em_atraso` (D+3, Giro) | "Giro: a fatura {{1}} da empresa {{2}}, de {{3}}, venceu em {{4}} e ainda não foi paga. Sem o pagamento, em {{5}} a empresa fica suspensa. {{6}} Obrigado." |

Observações sobre os modelos:
- **"Fale com a gente por aqui" sai** de todos os textos na A e na C com um número só, porque a resposta chegaria ao Giro.
- **Links como variável no texto:** é o mais simples, porque o subdomínio muda por empresa e o botão de link só aceita variável no fim de um domínio fixo. Se a Meta recusar, o plano B é um botão com um link curto num domínio fixo, `https://admin.<dominio>/l/{{1}}`, que redireciona para o endereço com o token no fragmento. O código curto não é o token, vence junto com o link e não guarda o fragmento em log.
- **A marca da locadora como variável** (`{{2}}`) pode ser vista pela Meta como "remetente variável" num número só. É mais um ponto a confirmar na aprovação dos modelos.

### Opt-in e LGPD

- **A Meta exige opt-in** antes de mensagens iniciadas pela empresa, dizendo o nome de quem envia e o canal.
- **Cliente final:**
  - campo `aceita_whatsapp` no cadastro do cliente, uma caixa no Novo cliente e no detalhe ("Aceita receber avisos da {marca} pelo WhatsApp"), com data e quem marcou;
  - sem a marca, o cliente só recebe e-mail;
  - a importação traz a coluna, e o padrão é desmarcado.
  Isso é `[decisão]` do produto: muda `CLI` e as telas.
- **Pessoa convidada:** o convite por WhatsApp só sai se o administrador marcar que a pessoa aceitou receber. Sem isso, só o e-mail (`USR-01` muda; `[decisão]` do produto).
- **Responsável pela assinatura:** o opt-in fica na forma de pagamento ou no cadastro da empresa (`PLT-02`).
- **Saída:** a resposta "SAIR", "PARAR" ou "CANCELAR" pelo webhook desmarca `aceita_whatsapp` daquele celular, com evento na auditoria. Outras respostas recebem a resposta automática gratuita: "Este número só envia avisos. Para falar com a {marca}, use o telefone da loja." O telefone vem da filial.
- **Base legal:**
  - cobrança, recibo, contrato e lembrete são execução de contrato (LGPD, art. 7º, V);
  - o opt-in é exigência da Meta, não da LGPD;
  - a Meta e o BSP passam a ser operadores e entram no aviso de privacidade;
  - na A e na C, os dados passam por servidores fora do Brasil (mesmo ponto da ADR 0033, a confirmar com o produto).
- **O que se guarda:** o modelo, o `wamid`, o status, o celular mascarado e o erro. **O texto montado não se guarda**: as variáveis têm nome, valor e link, e já ficam no objeto de origem.

### Se o envio falhar

- **Erro na hora** (rede, 5xx, limite `130429`): a tarefa repete com espera crescente (1, 5 e 15 minutos). Depois disso, vale como falha.
- **Falha pelo webhook** (`failed`: número sem WhatsApp, `131026`, ou fora do opt-in) ou falha depois das repetições: **cai para o e-mail quando o ponto já tem versão por e-mail** e o destinatário tem e-mail. Têm versão por e-mail: convite, contrato, régua de cobrança e régua da assinatura.
- **Recibo de pagamento e recibo e lembrete de devolução:** hoje são só WhatsApp. Cair para o e-mail é `[decisão]` do produto. O padrão proposto é cair para o e-mail, com o mesmo texto.
- **A régua não para por um cliente:** a falha não desfaz o marco já gravado e não repete no mesmo dia (`AUT-03`, uma vez por conta por dia; M-02 da T-304).
- Falhas repetidas de um celular (3 seguidas) marcam o celular como "sem WhatsApp" no cliente, e as próximas mensagens vão direto ao e-mail.

### Webhook de status

- **Rota:** `GET` e `POST /api/webhooks/whatsapp/`, no host da plataforma, como o do Asaas (`urls_publico`, fora do OpenAPI).
  - O `GET` responde o desafio de verificação da Meta com `GIRO_WHATSAPP_VERIFY_TOKEN`.
  - O `POST` confere `X-Hub-Signature-256` (HMAC do corpo com `GIRO_WHATSAPP_APP_SECRET`). Sem assinatura válida, responde 401 e não grava nada.
  - Responde 200 na hora e processa numa tarefa.
- **Como acha a empresa:** pelo `wamid` da mensagem enviada. Uma tabela no `public` (`EnvioWhatsApp`: `wamid` único, schema e data, sem conteúdo) leva o status ao schema certo. As mensagens recebidas acham a empresa pela última mensagem enviada àquele celular; sem nenhuma, só recebem a resposta automática.
- **Status:** `sent`, `delivered`, `read` e `failed` atualizam o envio. O `failed` dispara a regra da seção anterior. É idempotente pelo `wamid` mais o status.
- **Proxy:** a rota entra no limite de borda de `/api/webhooks/` e no Sentry sem corpo (T-270).

### O que o dono precisa contratar

| Item | A | B | C |
| --- | --- | --- | --- |
| Meta Business do Giro verificado (CNPJ, documentos, site) | sim | sim, mais o cadastro como *Tech Provider* | sim |
| Número de telefone dedicado, nunca usado no app do WhatsApp | um, do Giro | um do Giro (assinatura) e um de cada locadora, que é dela | um (ou vários) |
| Nome de exibição aprovado pela Meta | o do Giro (por exemplo, "Giro Avisos") | o de cada locadora | como na A ou na B |
| Forma de pagamento na WABA (cartão internacional ou linha de crédito da Meta) | a do Giro | a de cada locadora, ou a do Giro com repasse | pelo parceiro |
| Contrato com o parceiro | — | — | sim (mensalidade, DPA para a LGPD) |
| App no Meta for Developers e token de usuário de sistema | sim | sim | não (é do parceiro) |

## Recomendação do arquiteto

**Opção A agora, com a interface pronta para a B na fase 2.** É a que entra antes do primeiro cliente:
- um cadastro só;
- o menor custo (cerca de R$ 500 por mês com 20 empresas);
- sem mais um operador de dados pessoais.

A régua da assinatura, que é do Giro, já fica no lugar certo.

O meio-termo do white label (remetente "Giro Avisos", marca da locadora no texto) e a resposta que chega ao Giro são o preço dessa escolha. A resposta automática e a saída por "SAIR" contornam a segunda. Quando houver locadora pedindo o próprio número, a B entra pelo mesmo provedor: o envio já recebe o `phone_number_id` por empresa.

A C só compensa se o dono preferir não operar o cadastro na Meta.

**Antes de aceitar,** o produto precisa decidir:
- os textos com abertura e fim fixos;
- o opt-in do cliente e da pessoa convidada;
- a queda para o e-mail dos recibos e do lembrete;
- o remetente "Giro Avisos".

## Esboço do contrato do provedor no backend

```python
# backend/integracoes/whatsapp/__init__.py
class Modelo(StrEnum):                      # os nomes da tabela "Modelos de mensagem"
    CONVITE_ACESSO = "convite_acesso"
    CONTRATO_ASSINAR = "contrato_assinar"
    ...

@dataclass(frozen=True)
class Aviso:
    celular: str                            # só dígitos, com DDD; o provedor põe o 55
    modelo: Modelo
    parametros: tuple[str, ...]             # na ordem das {{n}} do modelo, já formatados
    texto: str                              # o texto montado, para o falso e para o e-mail
    reserva_email: Email | None = None      # a queda (assunto, texto, destinatários)
    numero_id: str | None = None            # opção B: o número da empresa; None = do Giro

@dataclass(frozen=True)
class Resultado:
    wamid: str | None                       # None no falso
    aceito: bool                            # a Meta aceitou para envio (não é entrega)

class ProvedorDeWhatsApp(Protocol):
    def enviar(self, aviso: Aviso) -> Resultado: ...   # levanta FalhaTemporaria ou FalhaDefinitiva

def avisar(aviso: Aviso, *, origem: object | None = None) -> None:
    """Põe na fila `whatsapp_enviar` (Celery, ADR 0012), depois do commit."""
```

- **`MetaCloud`** (`integracoes/whatsapp/meta.py`):
  - usa `urllib`, sem dependência nova, como o `asaas.py`;
  - fala com a Graph API em versão fixada em `GIRO_WHATSAPP_VERSAO_API`;
  - corpo `type: "template"`, com `components[body].parameters` a partir de `parametros`;
  - o erro `130429` e o 5xx viram `FalhaTemporaria`; o `131026`, o 4xx e o modelo não aprovado viram `FalhaDefinitiva`.
- **`WhatsAppFalso`** continua igual para o dev e os testes, e passa a guardar o `Aviso` inteiro: os testes conferem o modelo e os parâmetros, não só o texto.
- **Configuração:**
  - `GIRO_PROVEDOR_WHATSAPP` (`falso` ou `meta`), `GIRO_WHATSAPP_TOKEN`, `GIRO_WHATSAPP_NUMERO_ID`, `GIRO_WHATSAPP_WABA_ID`, `GIRO_WHATSAPP_APP_SECRET`, `GIRO_WHATSAPP_VERIFY_TOKEN` e `GIRO_WHATSAPP_VERSAO_API`, todas do cofre;
  - `prod.py` recusa `falso` e token vazio, como faz com o Asaas.
- **Modelos na Meta:** `manage.py sincronizar_modelos_whatsapp` cria ou confere os modelos da tabela na WABA e mostra a situação de cada um (aprovado, pendente ou recusado). Nada sai com modelo não aprovado.
- **Registro:** `EnvioWhatsApp` no `public` (roteamento do webhook) e `MensagemWhatsApp` no schema da empresa, com origem, modelo, status, erro, celular mascarado e datas. Sem o texto.
- **Chamadores:** os nove pontos trocam `enviar_whatsapp(celular, texto)` por `avisar(Aviso(...))`. O texto de hoje continua sendo montado (para o e-mail e para o falso) pela mesma função que já existe, e os parâmetros saem das mesmas partes.

## Consequências

- Com a escolha e as decisões do produto, esta ADR passa a aceita, e saem as tarefas de backend abaixo. A integração entra antes do primeiro cliente que use convite ou cobrança por WhatsApp.
- Sem a integração, a fase 1 roda com o falso: convite e cobrança só por e-mail, de fato. O `prod.py` recusa subir com o falso, então a escolha tem de vir antes da subida de produção (ADR 0033).

### Tarefas de backend que saem daqui (sem número)

1. **Provedor e fila:** `Aviso`, `avisar`, a tarefa `whatsapp_enviar` com repetição, `MetaCloud` com `urllib`, o falso guardando o `Aviso`, as variáveis no `prod.py` e no `producao.env.example`, e `EnvioWhatsApp` e `MensagemWhatsApp` com migração. Testes com o falso e com respostas da Meta gravadas (`test_whatsapp_*`).
2. **Os nove pontos:** trocar pelos modelos, com os parâmetros na ordem da tabela, e a queda para o e-mail onde houver. O teste de cada ponto confere o modelo e os parâmetros com o seed (Carlos, LOC-2841; Juliana, LOC-2836).
3. **Webhook de status** em `urls_publico`: desafio, assinatura, roteamento pelo `wamid`, status, queda para o e-mail no `failed`, saída por "SAIR" e resposta automática. Testes `test_whatsapp_webhook_*`.
4. **Opt-in** (depois da decisão do produto): `aceita_whatsapp` em `Cliente` e no convite, na importação e na API de clientes, e o bloqueio do envio sem opt-in. Testes `test_cli_*_opt_in_whatsapp`.
5. **`sincronizar_modelos_whatsapp`** e o passo a passo no `infra/README.md` (devops) para cadastrar os modelos na WABA de produção.
