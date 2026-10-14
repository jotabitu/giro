# T-211 · Regras dos pontos em aberto de 14 out · produto → orquestrador, arquiteto, design-system, qa

**O que foi feito:** registrei a aprovação do dono do produto (14 out 2026) nos três pontos em aberto da T-190 e nas duas `[decisão]` da T-193, todos pelo padrão. Branch `t-211-regras-pontos-abertos`, a partir da `origin/main` (T-190 e T-193 já mescladas).

- `docs/regras-de-negocio.md`:
  - `PLT-04` · **Downgrade agendado que deixa de caber (A):** é conferido quando a fatura do período seguinte é gerada (5 dias antes, `PLT-02`, como o contrato da T-193 já fazia). Se não couber, o downgrade não acontece: a fatura sai pelo plano atual e vai um e-mail com o motivo ao administrador e ao e-mail de cobrança. Se couber, o plano muda no vencimento. O que entrar nesses 5 dias segue a `PLT-03` e a `PLT-12`: bloqueia só novos cadastros e os dados ficam guardados.
  - `PLT-06` · **Pausa (A):** começa no fim do período pago; a fatura do período seguinte que já tiver sido emitida é cancelada. **Desfazer o cancelamento (A):** o administrador desfaz pela `Admin-Assinatura` até o último dia de acesso. A fatura que o cancelamento cancelou, ou deixou de gerar, nasce de novo com o mesmo valor, vencimento e período. **Reativar a `cancelada` com fatura em atraso (A):** a equipe só reativa depois de receber a atrasada ("Receba a fatura em atraso antes de reativar.").
  - `PLT-15` · **Endereço da NFS-e (B):** nasce do endereço da filial matriz do passo 6 e é copiado uma vez. Depois disso, o da filial e o da nota mudam cada um por conta própria. A compra não pede endereço, e o passo 6 avisa que o endereço também vai na nota. Sem endereço, a nota espera.
  - Dados de referência: linhas novas "Desfazer o cancelamento da Moto Rápida", "Reativação da Moto Rápida com fatura em atraso", "Downgrade agendado que deixa de caber" e "Dados fiscais da Moto Rápida" (Av. Bezerra de Menezes, 1200, São Gerardo, Fortaleza, CE, CEP 60325-000, o mesmo da Filial Centro). O caso "Pausa da Moto Rápida" ganhou a pausa feita depois de a fatura ser emitida.
  - "Decisões de 14 out 2026" com 5 linhas novas; os 3 pontos em aberto marcados `[x]`; notas de mudança na seção da plataforma e nos dados de referência.
- `docs/qa/criterios/assinatura.md`: CA-ASS-40 a 48; o CA-ASS-29 agora traz o endereço da nota.
- `tarefas/backlog.md`: as 2 `[decisão]` da T-193 marcadas como resolvidas; seção da T-211 com 4 propostas sem número (2 para o arquiteto, 1 para o design-system, 1 para o qa).
- `tarefas/feito.md`: linha da T-211, PR a abrir.

**Regras cobertas:** PLT-04, PLT-06, PLT-15.

**Números:** downgrade Completo → Profissional que deixa de caber: 11 de 10 usuários em 17 nov, e a fatura de 22 nov sai com R$ 899,00. Desfazer no teste: FAT-0001 continua cancelada, e a FAT-0002 de R$ 449,00 vence em 22 out. Desfazer na ativa em 20 nov: FAT-0003 de R$ 449,00 vencendo em 22 nov. Reativação em 01 dez: FAT-0002 de R$ 449,00 vencendo em 01 dez, e as seguintes todo dia 1.

**Para quem recebe:**
- **Arquiteto:** a proposta 1 entra na T-194 (rota de desfazer, `acoes.desfazer_cancelamento`, pausa que cancela a fatura já emitida). A proposta 2 vai no `assinatura.md`: o endereço é copiado da matriz, o seed deixa de ter `endereco` nulo, e a reativação deixa de ser `[decisão]` (o 409 `fatura_em_atraso` continua). Avise a T-184 e a T-185.
- **Design-system:** proposta 3. Na `Onboarding-Filial`, troque "Mesmo endereço do CNPJ · Rua Barão do Rio Branco..." pelo endereço com CEP e a nota sobre a nota fiscal. Na `Admin-Assinatura`, desenhe o estado de cancelamento marcado com "Desfazer cancelamento". Pode ir junto com a T-200.
- **Qa:** proposta 4 (seed e CA-ASS-40 a 48, junto com a T-204).

**Para o dono decidir, se quiser:** se a equipe reativar a empresa antes de acabar o período pago pela fatura atrasada (ex.: FAT-0001, de 22 out a 21 nov, paga e reativada em 10 nov), a fatura nova vence no dia da volta, e os dias de 10 a 21 nov são cobrados duas vezes. A regra atual ("como na volta da pausa") dá esse resultado. No exemplo usei 01 dez, que fica fora desse caso. Não abri ponto em aberto, porque a reativação é rara e quem faz é a equipe. Se o dono quiser, a fatura nova pode vencer no fim do período já pago.

**Próximo passo:** o orquestrador abre o PR e numera as propostas. Só documentos, sem teste para rodar.
