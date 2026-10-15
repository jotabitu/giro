# T-223 · Regras dos módulos por plano · produto → orquestrador, arquiteto, backend, qa

**O que foi feito:** escrevi nas regras as três `[decisão]` da T-192 (ADR 0024). O dono aprovou o padrão do produto nas três em 15 out 2026. Branch `t-223-regras-modulos-plano`, a partir da `origin/main`.

- `docs/regras-de-negocio.md`:
  - `PLT-12` ganhou três itens:
    - **Mudar o ramo** em Configurações segue a conferência do downgrade (opção B). Deixar de alugar é recusado com locação `aguardando_retirada`, `ativa` ou `devolucao_atrasada`; deixar de vender, com venda aberta (`VEN-10`) ou comissão não paga. A recusa diz quanto falta em cada grupo.
    - **Ramo no Essencial** (opção A): o passo 7 oferece "aluga" e "aluga e vende", nunca "só vende", e "vende" aparece com o aviso "Vendas faz parte do plano Profissional." Vendas e comissões ligam sozinhas no upgrade. Daí decorre o downgrade para o Essencial de quem só vende: é recusado com "O plano Essencial não inclui vendas. Para mudar, sua empresa precisa alugar." Ver a observação abaixo.
    - **Comissão no Essencial** (opção A): a comissão de locação não é lançada. Depois do upgrade, nasce só para as locações confirmadas a partir dele.
  - Etapa 7 da implantação e `FIN-09` apontam para a `PLT-12`. Há notas de mudança na Plataforma e no Financeiro, e uma seção nova "Decisões de 15 out 2026".
- `docs/qa/criterios/assinatura.md`:
  - CA-ASS-15 ajustado. A recusa da Moto Rápida lista também 1 despesa aguardando aprovação (pneus, R$ 1.200,00) e 2 a pagar (IPVA ROE2A88 e luz). Conferi em `backend/seed/financeiro.py`: o óleo, o aluguel e os rastreadores estão pagos, e o seed não cria OS, venda nem comissão.
  - CA-ASS-50 a 53 novos: troca de ramo, passo 7 do Essencial, downgrade de quem só vende, comissão só depois do upgrade.
- `tarefas/backlog.md`: as três `[decisão]` e o item do CA-ASS-15 marcados como resolvidos. Há duas propostas sem número: uma para o arquiteto (ADR 0024 e contratos) e uma para a T-196.
- `tarefas/feito.md`: linha da T-223, PR a abrir.

**Regras cobertas:** PLT-12, PLT-04, FIN-09, IMP-01.

**Para quem recebe:**
- **Arquiteto:** a troca de ramo deixa de desligar sem conferir. Ela chama `pendencias_dos_modulos` com um grupo novo, `locacoes` (`locacoes_vistoria`), e a recusa usa o formato do downgrade. Também entram:
  - "só vende" recusado no Essencial, e as opções do passo 7 pela API;
  - a recusa do downgrade de quem só vende;
  - o exemplo do 422 em `assinatura.md` com `abertos`.
  A comissão já está coberta pelo "não é refeito ao subir de plano". Cabe a você escolher entre atualizar a ADR 0024 e escrever uma ADR nova.
- **Backend (T-196):** os testes `test_plt_12_*` dos CA-ASS-50 a 53, e o `test_plt_04_downgrade_nao_cabe` conferindo os `abertos` do seed.
- **Qa:** os CA-ASS-15 e 50 a 53. Os números do CA-ASS-15 saíram do seed em código. Perguntei a você em 15 out, e a resposta não tinha chegado quando entreguei.

**Observação:** a recusa do downgrade de quem só vende não foi perguntada ao dono. É consequência da decisão 2: sem ela, a empresa ficaria no Essencial sem nenhum módulo de operação. O texto da mensagem é meu.

**Próximo passo:** o orquestrador abre o PR e numera as propostas. Só documentos, sem teste para rodar.
