# Handoff · T-397 · Passo Recebimentos do assistente (frontend)

- **Agente:** frontend
- **Branch:** `t-397-passo-recebimentos`, a partir da `origin/main` com o #424 (T-366).
- **Contrato:** `docs/api/plataforma.md`, "Recebimentos da empresa"
- **Tela de referência:** `docs/telas/html/Onboarding-Recebimentos-Desktop|Mobile.dc.html`
- **Regras:** FIN-04, IMP-05, IMP-07, PLT-12

## O que foi entregue

- **`PassoRecebimentos.tsx`** (rota `/implantacao/recebimentos`, ligada em `PassoDoAssistente`): lê `GET /api/recebimentos/` e mostra o `rotulo` e a `mensagem` da API para as quatro situações (`desconectado`, `pendente`, `aprovada`, `recusada`). O formulário só aparece com `acoes.conectar`, pré-preenchido pela `sugestao` (razão social, CNPJ, e-mail, celular e endereço da matriz), com tipo de empresa e faturamento mensal em branco para a pessoa informar. O envio é `POST /api/recebimentos/`; o 201 (`pendente`) entra no cache e o andamento é relido.
- **Erros:** 400 aparece no campo certo; 409, 422, 429 e 503 aparecem no topo do formulário com a mensagem da API (o 429 diz quanto esperar).
- **Continuar** só vale quando o `GET /api/implantacao/` diz `feito` (a API marca o passo na aprovação, IMP-07). **Pular por agora** e **Voltar** só navegam (IMP-05). Em `pendente` a tela relê a situação a cada minuto; ao ver `aprovada` relê o andamento.
- **Essencial:** o passo nem vem na lista do andamento, e a casca já avisa e leva ao próximo. Se a rota for aberta à mão, o 403 `PLT-12` aparece com a mensagem da API.
- **Cliente e fixture:** `lib/api/recebimentos.ts`, `tipos-recebimentos.ts`, `testes/falsos/falso-recebimentos.ts`. `passoTemTela` vale agora para os oito passos; `SemTela` fica só para passo desconhecido.

## Pontos para o orquestrador e o backend

- **OpenAPI com o schema errado em `sugestao`.** `Recebimentos.sugestao` aponta para `#/components/schemas/Sugestao`, que é outro schema (`{ data, nome, ja_cadastrado }`, de outra rota). É colisão de nome no drf-spectacular. Tipei `sugestao` à mão em `tipos-recebimentos.ts` com o formato de `plataforma.md` e deixei o comentário. O backend deve dar nome próprio (ex.: `SugestaoDeRecebimentos`) via `@extend_schema_serializer(component_name=...)`; depois é só trocar o tipo pelo gerado.
- **Campos da referência que a API não tem** (banco, agência, conta, chave Pix, interruptores de Pix/boleto/cartão e lembretes no WhatsApp) ficaram de fora, como o contrato manda; o design-system ajusta a tela.
- **Recusada:** sem botão de novo pedido, porque `acoes.conectar` é `false` e o texto manda falar com a equipe Giro (decisão do produto, no contrato).
- O faturamento é digitado em reais ("50.000,00") e vira centavos no envio; a validação (maior que zero) é da API.

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 85 arquivos, 775 testes passando.
- Testes novos em `components/implantacao/PassoRecebimentos.test.tsx` (formulário pré-preenchido, as quatro situações, Continuar desligado até o passo feito, corpo do envio, erros do contrato). `Assistente.test.tsx` e `PassosDoAssistente.test.tsx` atualizados.
- Os testes rodam em `node`, sem DOM: o clique de enviar está coberto pelo corpo montado e pela fixture, não por clique. Vale uma passada manual ou do QA a 1440px e 390px.
