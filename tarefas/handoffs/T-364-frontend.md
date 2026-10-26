# Handoff · T-364 · Passos que faltam no assistente (frontend)

- **Agente:** frontend
- **Branch:** `t-364-passos-assistente`, empilhada: parte da `origin/main` com `origin/t-359-tabelas-de-preco` (#402) e `origin/t-363-modelos-de-contrato` (#407) mescladas. Os conflitos da mescla foram só de linhas vizinhas (`feito.md`, `api/index.ts`, `api-falsa.ts`), com as duas versões mantidas.
- **Contrato:** `docs/api/plataforma.md` ("Quando cada passo conta como feito" e "Rotas de cada passo do assistente")
- **Telas de referência:** `docs/telas/html/Onboarding-Filial|Precos|Contrato|Equipe-Desktop|Mobile.dc.html`
- **Regras:** IMP-04, IMP-05, IMP-07, USR-01, LOC-01, PLT-03

## O que foi entregue

Os quatro passos agora têm tela dentro da `CascaDoAssistente`, pela rota `/implantacao/[passo]`. `passoTemTela` vale para todos menos `recebimentos` (T-366), e é só neste que sobra o aviso "Esta etapa ainda não está disponível aqui."

1. **Primeira filial (`PassoFilial.tsx`):** lê `GET /api/filiais/`. Se já há matriz, mostra ela e libera o Continuar. Se não, pede endereço (CEP preenche rua, bairro, cidade e UF), nome, nome curto, WhatsApp e um de dois horários prontos (Comercial ou Estendido), e grava `POST /api/filiais/` com `matriz: true`. O limite do plano (422 `PLT-03`) aparece com o texto da API.
2. **Tabela de preços (`PassoPrecos.tsx`):** o painel `CategoriasDePreco` da T-359, com "Nova categoria" no cabeçalho. Extras e planos especiais ficam na tela `Precos`, como diz o contrato.
3. **Modelo de contrato (`PassoContrato.tsx`):** o painel `ModelosDeContrato` da T-363 (modelo pronto, prévia, edição, publicar). Publicar relê o andamento; o Continuar vale quando a API marca o passo.
4. **Convidar equipe (`PassoEquipe.tsx`):** lista `GET /api/usuarios/?situacao=convites` e reaproveita o diálogo `ConvidarPessoa` (`POST /api/usuarios/convites/`, um por pessoa). Por ser o último passo, "Convidar depois" e "Concluir" levam ao início.
5. **`RodapeDoPasso`:** Voltar e Pular só navegam (não marcam passo, IMP-05). Continuar fica desligado até o `GET /api/implantacao/` dizer `feito: true` para o passo, e então relê o andamento e segue.

## Pontos para o orquestrador e o produto

- **Continuar só vale com o passo feito.** Nos passos de preços, contrato e equipe a gravação é feita dentro do painel (criar categoria, publicar, convidar), e a API marca o passo. A tela não decide o que está feito; ela espera o `feito` da API. Quem quer seguir sem gravar usa "Pular por agora".
- **As telas de referência trazem campos que o contrato não tem.** O contrato do passo de contrato (regras de multa, "Usar meu modelo (.docx)", cláusulas por opção) e as "Regras que valem para todos os contratos" do passo de preços não têm rota. Segui o contrato de `plataforma.md`, que manda editar o texto na tela Modelos de contrato. Se o produto quiser esses campos no assistente, precisa de contrato novo.
- **Horário da primeira filial:** só os dois horários prontos (o terceiro, "Personalizado", fica em Administração › Filiais).
- **No contrato, só um modelo de locação publicado marca o passo** (IMP-04). Publicar um modelo de venda não libera o Continuar, e a tela não tenta adivinhar isso.
- **Recebimentos** continua sem tela, como combinado (T-366 e T-381).

## Verificação

- `npx tsc --noEmit` e `npm run lint`: limpos. `npx vitest run`: 81 arquivos, 742 testes passando.
- Testes novos: `components/implantacao/PassosDoAssistente.test.tsx` (nenhum passo com tela mostra o aviso; cada passo com e sem o passo feito; Pular e Voltar seguem a ordem da API, no Essencial também). `Assistente.test.tsx` atualizado: agora só `recebimentos` fica sem tela.
- Os testes rodam em `node`, sem DOM: o Continuar, os diálogos e as gravações estão cobertos pelo markup e pelo contrato do falso, não por clique. Vale uma passada manual ou do QA a 1440px e 390px.
- O `node_modules` desta rodada é o do lock antigo (`vitest` 3), até o #405 entrar.
- Nenhuma tela de Veículos foi tocada.
