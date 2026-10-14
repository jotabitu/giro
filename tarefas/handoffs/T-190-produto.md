# T-190 · Regras das decisões do dono de 14 out 2026 · produto → orquestrador, arquiteto, backend, frontend, design-system, segurança, qa

**O que foi feito:** registrei as decisões do dono do produto de 14 out 2026: padrão aprovado nos 18 itens da "Lista única" (U1 a U18) da análise `C:/Users/Jota/Documents/giro-produto/analise-decisoes-telas.md` (fora do git), que junta as D1 a D13 do produto com as [D-1] a [D-10] do contrato da Assinatura (T-183). Nas divergências: U1, U10 e U11 pelo produto (U10 com ADR do arquiteto), U4 e U13 pelo arquiteto.

- `docs/regras-de-negocio.md`:
  - Tabela de estados da empresa: `em_teste` só vira `ativa` com a 1ª fatura paga (no dia seguinte ao fim do teste, ou na hora, se paga depois); sem forma no fim do teste → `suspensa`; `cancelada` entra no fim do acesso.
  - `PLT-01` (teste até o fim; faturas seguintes no mesmo dia, período até a véspera, último dia do mês quando falta o dia; anual de 10 mensalidades por 12 meses), `PLT-02` (D+1 `inadimplente`, emissão 5 dias antes, cartão no dia, uma tentativa a mais só, e-mails para o e-mail de cobrança), `PLT-03` (adicionais fora do MVP), `PLT-04` (fórmula e fatura avulsa do upgrade, downgrade agendado e desfeito, troca livre no teste, ciclo pelo suporte, só `em_teste` e `ativa`), `PLT-06` (cancelar em cada estado, pausa, 90 dias, reativação pela equipe, exportar antes).
  - Novas: `PLT-11` (catálogo único; Completo sem NF-e, domínio próprio, portal do cliente e API; cartão "Precisa de mais veículos ou filiais?"), `PLT-12` (módulos por plano e ramo; Essencial sem vendas, manutenção, despesas, comissões, conciliação, relatórios e recebimento pelo parceiro; downgrade recusado com algo aberto), `PLT-13` (forma de pagamento; cartão só no parceiro), `PLT-14` (faturas; Django Admin até a `Plat-Cobranca`), `PLT-15` (NFS-e pelo Asaas, e-mail de cobrança, CNPJ só pela equipe).
  - `FIL-01` (nome curto; preço do litro no bloco Operação), `DEV-01` (preço do litro pelo administrador; gerente na fase 2; sem preço, à mão), `APR-08` (fase 2), `APR-12` (números da tela Aprovações), `AUT-03` (só e-mail no Essencial), `AUD-08` (90 dias a partir de `cancelada`, dados pedidos à equipe), nota de 14 out na auditoria ("Baixe a auditoria em CSV").
  - Dados de referência: "Assinatura da Moto Rápida", "Mudança de plano da Moto Rápida", "Cancelamento da Moto Rápida", "Pausa da Moto Rápida", "Números da tela Aprovações em 07 out" (horas dos dois pedidos aprovados, novas no seed).
  - Tabela "Decisões de 14 out 2026" e três "Pontos em aberto" com padrão: downgrade agendado que deixa de caber (A: não acontece, aviso), início da pausa (A: no fim do período pago), desfazer o cancelamento (A: pela tela, até o último dia de acesso).
- `docs/plano.md`: planos, cobrança, cancelar e pausar entram na fase 1 (antes, fase 3).
- `docs/qa/criterios/assinatura.md` (CA-ASS-01 a 39), `aprovacoes.md` (CA-APR-01 a 10), `filiais.md` (CA-FIL-01 a 06), com o seed Moto Rápida.
- `tarefas/backlog.md`: seção da T-190 com 13 propostas sem número; nota na T-183 ([D-1] a [D-10] respondidas, o que muda em relação ao contrato); T-170 sem "pausar e cancelar na fase 2"; 5 `[decisão]` das telas e a do cartão Exportar (T-173) marcadas como resolvidas; parágrafo da fase 2 acertado.
- `tarefas/feito.md`: linha da T-190, PR a abrir.

**Regras cobertas:** PLT-01 a PLT-06, PLT-11 a PLT-15, FIL-01, DEV-01, APR-08, APR-12, AUT-03, AUD-07, AUD-08.

**Números:** upgrade Profissional → Completo em 01 nov: 45000 × 21 ÷ 31 = 30483,87 → R$ 304,84, vence 04 nov. Régua da FAT-0001: boleto 17 out, D-3 19 out, `inadimplente` 23 out, D+3 25 out, D+7 29 out, `suspensa` 06 nov. Cancelada em 22 out → apagamento em 20 jan 2027 (aviso 13 jan). Aprovações em 07 out: 2 aprovadas, tempo médio 1 h 30 min.

**O que ficou de fora / para quem recebe:**
- **Arquiteto:** o contrato `assinatura.md` recomendava em [D-1] que a forma de pagamento ativasse a empresa e, em [D-10], o cartão do Completo com domínio próprio e API; as duas mudam (propostas 1 e 2). O contrato de cancelar e pausar (proposta 3) segue os três pontos em aberto pelo padrão até o dono responder.
- **Backend:** T-185 e T-186 seguem a tabela de estados nova; o resto das [D-n] ficou como o contrato recomendava.
- **Design-system:** a proposta 9 complementa a T-188.
- **Segurança:** proposta 8; se a T-189 ainda estiver aberta, pode ir junto.
- A NFS-e (proposta 6) depende do contador e do cadastro municipal do Giro.

**Próximo passo:** o orquestrador abre o PR da T-190 e numera as propostas. Só documentos.
