# Implantação

> Parte das regras de negócio do Giro. Convenções e índice: [`docs/regras-de-negocio.md`](../regras-de-negocio.md). O histórico de mudanças desta seção fica em [`historico.md`](historico.md).

Da compra até a 1ª locação são 12 etapas. As 4 primeiras são a compra e o primeiro acesso; as 8 seguintes formam o assistente, que pode ser pausado e retomado de onde parou. Telas: `Compra-Planos` → `Compra-Checkout` → `Compra-Pronto` → `Acesso-Senha` → `Onboarding-*` (8 passos) → `Pos-Dashboard`.

| # | Etapa | Tela | O que grava | Obrigatória |
| --- | --- | --- | --- | --- |
| 1 | Escolher plano | `Compra-Planos` | plano escolhido | sim |
| 2 | Dados e pagamento | `Compra-Checkout` | empresa, CNPJ, administrador, subdomínio; cartão opcional | sim |
| 3 | Conta criada | `Compra-Pronto` | cria schema da empresa, status `em_teste`, envia e-mail de acesso | automática |
| 4 | Criar senha | `Acesso-Senha` | senha + 2 etapas do administrador | sim |
| 5 | Marca | `Onboarding-Marca` | logo, cor, nome de exibição | não (usa padrão) |
| 6 | Primeira filial | `Onboarding-Filial` | filial matriz com endereço e horário | sim |
| 7 | Ramo | `Onboarding-Ramo` | trabalha com motos, carros ou os dois; aluga, vende ou os dois (no Essencial, "só vende" não aparece, `PLT-12`). Liga ou desliga módulos, com a lista que a API devolve. Mesmo conteúdo e mesmos textos da troca do ramo em Configurações (`Admin-Ramo`), sem "Como você aluga" nem "CNH exigida" (a CNH segue a `CLI-02`) | sim |
| 8 | Preços | `Onboarding-Precos` | categorias com diária, semanal, mensal e caução | sim para quem aluga |
| 9 | Contrato | `Onboarding-Contrato` | publica o 1º modelo de contrato (a partir de um modelo pronto) | sim para alugar |
| 10 | Recebimentos | `Onboarding-Recebimentos` | conecta parceiro de pagamento (Pix, cartão, boleto) | não (só dinheiro e Pix manual) |
| 11 | Importar dados | `Onboarding-Importar` | veículos e clientes por planilha | não |
| 12 | Equipe | `Onboarding-Equipe` | convites com perfil e filial | não |

**Regras**

- `IMP-01` A implantação está "concluída" quando existe a 1ª locação ou venda. Antes disso, a tela inicial do administrador é `Pos-Dashboard`, com a lista do que falta.
- `IMP-02` A importação valida cada linha antes de gravar: placa única, chassi único com 17 caracteres (`VEI-01`), categoria existente. Linhas com erro não entram e ficam numa lista para corrigir (Moto Rápida: 83 prontos, 3 para corrigir; depois de corrigidos, 86 veículos).
- `IMP-03` Importar respeita o limite do plano (`PLT-03`). Se a planilha passa do limite, importa até o limite e avisa.
- `IMP-04` Sem modelo de contrato publicado, o sistema não deixa concluir uma locação (aparece o atalho para o passo 9). Foi o motivo do chamado #1042 da Moto Rápida.
- `IMP-05` O progresso de cada empresa alimenta o funil do painel da plataforma (`Plat-Implantacoes`): Conta → Marca → Filial → Preços → Dados → 1ª locação. Empresa que fica 3 dias ou mais no mesmo passo entra em "precisam de ajuda".
- `IMP-06` **Fase 2** (decisão do dono do produto em 25 out 2026, T-356, com a `AUT-14` e a compra pública). Mensagens automáticas durante o teste: parada há 2 dias (e-mail + WhatsApp), faltam 3 dias de teste (e-mail), teste acabou (e-mail). No MVP, a equipe Giro cria cada empresa e acompanha a implantação à mão; os avisos da 1ª fatura seguem a régua da assinatura (`PLT-02`).
- `IMP-07` **Quando um passo do assistente conta como feito.** O passo conta como feito pela ação que grava o que ele pede (coluna "O que grava"), seja no assistente, seja na tela de Configurações que faz a mesma coisa. "Pular por agora" não marca, e o passo pulado continua na lista do que falta. Passo feito continua feito, mesmo que a pessoa desfaça depois (inative a categoria, cancele o convite).
  - **Primeira filial:** quando a filial matriz é criada.
  - **Preços:** quando a primeira categoria passa a ter preço vigente em pelo menos um plano (diária, semanal ou mensal), da empresa ou de uma filial (`LOC-01`, `FIL-04`).
  - **Contrato:** quando o primeiro modelo de contrato é publicado (`IMP-04`).
  - **Recebimentos:** quando a subconta do parceiro fica conectada e aprovada para receber (`FIN-04`). Só no plano com recebimento pelo parceiro (`PLT-12`).
  - **Equipe:** quando o primeiro convite é enviado (`USR-01`), mesmo que ainda não aceito.
  - **Marca e Importar dados** continuam marcados por "Continuar", porque não exigem nada: a marca usa o padrão, e a importação é opcional.
