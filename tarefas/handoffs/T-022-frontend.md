# T-022 · Telas de locação, vistoria e devolução · frontend → orquestrador, qa, design-system, produto

**O que foi feito:** as telas de Locações, Nova locação, Vistoria de saída, Devolução (vistoria de chegada, acerto e recibo) e a agenda do vistoriador, em desktop e celular, em cinco commits (uma parte por commit).
1. **Lista e detalhe** (`/locacoes`, `/locacoes/[id]`): indicadores, abas (Todas, Precisam de ação, Devolvem hoje, Encerradas; Canceladas e Rascunhos só com contagem), busca, filtro de plano, linhas com situação, pagamento e ação principal da API. Detalhe com veículo e cliente, pagamentos, contrato (imprimir e reenviar), prazo da devolução, resumo e histórico. Ações do `acoes` da API: Renovar (simular e confirmar, `LOC-08`), Trocar veículo (`LOC-09`; o 202 leva às duas vistorias), Cancelar ou Pedir cancelamento (simula; 200 ou 202 "Pedido enviado ao gerente"). Bloco de cancelamento com a frase "Estimativa para 07 out. O valor final sai na devolução." (T-116/T-117); as parcelas de locação aprovada e não devolvida ficam como a API manda.
2. **Nova locação** (`/locacoes/nova?cliente=&veiculo=&rascunho=`): simula a cada mudança, preços da categoria e planos especiais, extras, desconto (aviso quando precisa de aprovação), impedimentos (`CLI-05`, `LOC-03`...) e avisos (`CLI-03`, `IMP-04` com link). "Continuar para vistoria" e "Salvar como reserva" criam ou atualizam o rascunho e confirmam. Retoma rascunho pelo detalhe.
3. **Vistoria de saída** (`/locacoes/[id]/vistoria`): km, combustível, seis posições de foto (upload), itens, avarias (foto obrigatória), observações; cada mudança vai por `PATCH`. Concluir mostra todas as pendências do 422 (`VIS-01` a `VIS-03`, `VEI-01`, `CLI-*`) com link.
4. **Devolução** (`/locacoes/[id]/devolucao`): 1 · Vistoria (comparação saída × agora), 2 · Acerto (valores informados, multa de trânsito, forma de devolução, avisos `DEV-07`/`LOC-09`), 3 · Recibo (PDF e reenvio). O botão é o `resultado.botao` da API; o 422 `DEV-07` aparece como a API manda. Vistoriador não vê acerto nem valores.
5. **Agenda** (`/vistorias`, `/vistorias/avarias`): Hoje, Amanhã e Semana, próxima vistoria, grupos de saídas e devoluções no celular.

**Onde:** `frontend/src/components/locacoes/`, `components/vistorias/`, `components/lista/CampoSelecao.tsx`, `lib/locacoes.ts`, `lib/locacao-form.ts`, `lib/vistorias.ts`, `lib/api/{tipos-locacoes,tipos-vistorias,falso-locacoes,falso-vistorias}.ts`, rotas em `app/(empresa)/locacoes` e `app/(empresa)/vistorias`.

**API real: não liguei, e preciso de decisão.** Os tipos vêm do cliente gerado do OpenAPI (`src/lib/api/schema.d.ts`, `npm run api:gerar`, agora no `.gitignore` porque o CI gera). As chamadas ainda passam pela camada falsa de `lib/api/index.ts`, como todos os módulos do app: a sessão (T-011) é falsa e não há cliente HTTP nem JWT no frontend. Trocar para a API real é reescrever `locacoes` e `vistorias` em `index.ts` com `fetch` e apagar `falso-*.ts`; as telas não mudam. O falso segue o contrato (códigos de erro, 202, 422 com `detalhes.pendencias`, vistoriador sem `_centavos`).

**Regras cobertas:** LOC-01 a LOC-05, LOC-08, LOC-09, LOC-12, LOC-13, LOC-14, LOC-15, VIS-01 a VIS-05, DEV-01 a DEV-07, FIN-03 (descrição da parcela vem da API), CLI-03, CLI-05, VEI-01.

**[divergência] tela × contrato/regra (vale o contrato):**
1. Lista: a referência traz só quatro abas e o filtro "Veículo: todos". As abas Canceladas e Rascunhos entram quando há contagem; "Veículo" ficou desativado (falta seletor de veículo no design system).
2. Detalhe: o celular da referência não mostra o nome do cliente e tem barra fixa embaixo; a casca já tem a barra, então os botões ficam no fim. Datas de período sem hora na lista, exceto quando a API diz `devolve_hoje`.
3. Vistoria: a referência mostra "Total na retirada R$ 629,00" e "Semanal Street R$ 329,00", mas `resumo_locacao` não traz esses campos; ficaram "Diária" e "Caução (pago ou a receber)". Caução de Lucas aparece "a receber" porque a carteira do falso a deixa em aberto.
4. Devolução: a referência usa "à cliente" e "por Pix" no botão; usei "ao cliente" e o `botao` da API ("Encerrar e devolver R$ 183,00"), com a forma de devolução escolhida na etapa Acerto. A referência mostra o botão de encerrar já na etapa 1; como o encerrar exige a chegada concluída, a etapa 1 tem "Concluir vistoria" e o botão de encerrar aparece depois. "3 · Recibo" só aparece com a devolução encerrada.
5. Itens da vistoria têm três estados (sem resposta, ok, com problema), por causa do `VIS-02`; a referência só desenha marcado e desmarcado.
6. Sem screenshots: o portal do Maestri não renderiza com a janela minimizada. Conferi no navegador (Maestri) sem erro e sem rolagem horizontal em 1440 e 390 px nas sete rotas, e o texto de cada uma contra a referência pelos testes.

**Para o design-system:** faltam Select, Textarea, upload de foto e Stepper (usei `CampoSelecao` local, `<textarea class="wl-input">` e badges `wl-badge` nas etapas).

**Desatualizado por conta da T-121/T-122 (mergeada depois que comecei):** o contrato novo tem `POST /api/locacoes/{id}/trocar-veiculo/cancelar/` e o 409 `troca_pendente` em cancelar e renovar. Não implementei: abrir tarefa de frontend depois de o backend entregar e o OpenAPI regerar.

**Testes:** 242 passam (Vitest), `tsc`, `eslint` e `next build` limpos. Novos: `lib/locacoes.test.ts`, `lib/locacao-form.test.ts`, `components/locacoes/*.test.tsx`, `components/vistorias/*.test.tsx`, `lib/api/falso-vistorias.test.ts` (inclui os números do DEV-03: 3200 + 8500, devolve 18300; LOC-2836 Lucas 62900; DEV-07; LOC-09 de recusas).

**Próximo passo:** orquestrador abre o PR. QA: Playwright do fluxo login → nova locação → vistoria → devolução (T-025) quando a API real estiver ligada. Frontend: tarefa para ligar a API real.
