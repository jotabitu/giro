# T-375 (parte 2) · E2E do fechamento da fase 1 · qa → orquestrador

**Branch:** `t-375-e2e-fechamento`, com a `origin/main` até o #444 (T-403, T-404, T-405 e T-406 dentro). Sem PR. Nada de produção foi mexido; o que o QA mexeu: o seed (dono), os testes dele e os E2E.
**Onde rodou:** stack isolada do QA (projeto `giro-qa`, portas 3100 e 8100, banco próprio, imagem do backend reconstruída com o `pypdf`), não a stack de desenvolvimento. O harness do `npm run e2e` faz `DROP DATABASE giro` e apagaria a reativação da Moto Rápida; o dono pediu banco separado. Comando: `E2E_PORTA_FRONTEND=3100 E2E_PORTA_BACKEND=8100 npx playwright test ...` em `frontend`. Um teste por vez.

## Resultado final: tudo passou
| Item | Spec | Resultado |
| --- | --- | --- |
| Locação, vistoria, assinatura, caixa, devolução e baixa, 1440 px | `desktop.spec.ts` | passou (rodada 1; o código desse fluxo não mudou) |
| Locação completa no celular, 390 px | `celular.spec.ts` | passou (2,2 min) |
| 2 etapas: código errado recusado, certo entra; gerente sem código | `fechamento.spec.ts` | passou |
| Modo suporte sem contornar o relógio: entrada, faixa, Sair do suporte | `fechamento.spec.ts` | passou (T-405) |
| Controle do suporte em Configurações: abrir, ver o acesso, bloquear e liberar | `fechamento.spec.ts` | passou (T-403) |
| Implantação do zero (Pedalada, Essencial): Marca, Primeira filial, Ramo, Preços, Contrato, Equipe; Continuar dos preços sem recarregar | `fechamento.spec.ts` | passou (T-403) |
| Aceite do convite (Financeiro) com ativação das 2 etapas pela tela: chave, código calculado no teste, códigos de recuperação, início | `fechamento.spec.ts` | passou |
| Reembolsos: "Marcar como feito" (Patrícia, R$ 286,20) e Pendências: "Baixar a conta" (Carlos, R$ 299,40), no navegador | `fechamento.spec.ts` | passou |
| Passada visual 1440 e 390 px: Reembolsos, Pendências, Recebimentos da implantação, Controle do suporte, sem injeção de menu | `fechamento-visual.spec.ts` | passou; capturas em `docs/qa/fechamento-fase-1/` |
| CRLV-e reais com o catálogo (#435) e as siglas (#441) | shell na stack isolada | moto 9/9: **Royal Enfield / Classic 350**; carro 7/9, marca e modelo na dica `CHEVROLET/CRUZE LT NB` (CA-247-05, esperado) |

Os 6 itens da rodada anterior: 1 (`/admin/suporte`), 2 (menu), 3 (preços), 4 (token do suporte), 5 (CRLV-e) e 6 (abas e busca) estão resolvidos, com a ressalva do item 6 abaixo.

## Seed (dono: QA)
Um reembolso a fazer e uma pendência aberta na Moto Rápida, `seed/financeiro.py` (`garantir_reembolso_e_pendencia`), chamado também em banco já semeado (idempotente, `get_or_create`):
- **Reembolso:** Patrícia (LOC-2812), Pix R$ 286,20 = 371,00 − 84,80 (`LOC-13`). A locação não muda: o encerramento segue pendente para o Rodrigo (`APR-02`).
- **Pendência:** Carlos (LOC-2841), parcela de 30 set; Pix de R$ 306,09 (`FIN-03`) pago como R$ 299,40 (`valor_diferente`, `AUT-05`). A conta segue aberta; "em aberto" do Carlos continua R$ 299,40.
- Gravados direto (como as cobranças da T-380), com `criado_em` em 07 out 11:00, para não avisar o sino nem mexer nos contadores fixos.
- Testes: `test_dev_02_seed_reembolso_a_fazer_da_patricia`, `test_aut_05_seed_pendencia_aberta_do_carlos`, `test_dev_02_seed_reembolso_e_pendencia_idempotentes`. `test_t019_seed_completo` 40 passed, 5 xfail; `test_t127_seed`, `test_seed_banco_limpo`, `test_t018_auditoria` e `test_t181_configuracoes` passam. ruff e mypy limpos.
- **Mudou uma conferência:** o "Para hoje" da Lúcia (CA-019-24) era vazio e agora tem o item "Devolver R$ 286,20 a Patrícia Gomes por Pix". Nenhum número de referência mudou. Critério e teste atualizados.

## Pontos que ficaram para o orquestrador
1. **Placeholder da busca ainda cortado a 1440 px** ("Buscar cliente ou loca" em Reembolsos, "Buscar cliente, locação ou c" em Pendências), por causa do chip "Ctrl K". A 390 px ficou inteiro em Reembolsos. As abas já não quebram linha. O item "Pendências do pagamento" no menu quebra em duas linhas. Cosmético; vale decidir se entra na T-403 de novo.
2. **Os testes de seed não passam todos juntos num processo só** (1 falha e 31 erros ao rodar `test_t019`, `test_t127`, `test_seed_banco_limpo`, `test_t018` e `test_t181` numa chamada; cada um sozinho passa). Não investiguei a ordem; o CI roda tudo junto. Se o CI não reclamar, ignorar.
3. **Coerência do reembolso do seed:** ele existe antes de o encerramento da LOC-2812 ser aprovado, porque não há outra devolução de referência em 07 out. Se o Produto preferir outro caso, é trocar uma linha em `seed/financeiro.py`.

## Não coberto
- Enviar o cadastro de **Recebimentos** (depende do parceiro; sem simulação na stack). A tela abre e carrega a 1440 e 390 px.
- Fluxo completo de implantação, suporte e 2 etapas a 390 px (só a passada visual); a locação em 390 px está no `celular.spec.ts`.
- Homologação: fase 2.

## Para quem rodar de novo
- Depois de um merge com rota nova: `docker compose restart frontend` (o Docker no Windows não percebe pasta nova).
- Depois de mexer em `requirements.txt`: `docker compose build backend`.
- Copiar PDF para o contêiner no Windows: pelo PowerShell (`docker cp` com caminho do Windows); o Git Bash converte o destino. Apague os PDFs do contêiner depois; eles não entram no repositório.
- `fechamento.spec.ts` e `fechamento-visual.spec.ts` estão nos projetos `desktop` e `celular` de `playwright.config.ts`.
