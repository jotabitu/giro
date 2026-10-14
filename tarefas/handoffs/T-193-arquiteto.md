# T-193 · Contrato da assinatura pelas decisões · arquiteto → orquestrador, backend, frontend, segurança, qa

**O que foi feito:** `docs/api/assinatura.md` ajustado às decisões do dono de 14 out 2026 (regras da T-190, PR #199), sem as marcas [D-n]. Branch `t-193-contrato-assinatura-decisoes`, a partir da `origin/t-190-regras-decisoes-telas`.

- **Forma de pagamento não ativa a empresa (U1, `PLT-13`):** `em_teste` até o fim do teste mesmo com a forma ou a 1ª fatura paga; `prazo` só com `forma` nula. Tabela de transições nova (`plataforma.virar_estados`): 1ª paga no teste → `ativa` no dia seguinte ao fim; paga depois → na hora; sem forma → `suspensa` no dia seguinte; com forma e sem pagar → `inadimplente` em D+1.
- **Cartão (U8, `PLT-02`):** uma tentativa a mais, no dia seguinte; depois, `pagar/` aceita `meio` (`cartao`, `pix`, `boleto`) para pagar por outro meio sem trocar a forma. Rótulos da 2ª recusa. A troca da forma vale para a fatura em aberto (uma cobrança viva por fatura).
- **NFS-e (U9, `PLT-15`):** tarefa `plataforma.emitir_nota_fatura` depois da baixa, pelo Asaas da conta principal, atrás de `GIRO_NFSE_ASSINATURA_ATIVA` (desligada até o cadastro municipal; T-197 bloqueada); `nota_fiscal` no detalhe e `acoes.nota_fiscal`; endereço nos dados fiscais; e-mails para o `email_cobranca` e os administradores.
- **Cartão do plano acima (U11, `PLT-11`):** `oferta` com `titulo` "Precisa de mais veículos ou filiais?" e `itens` prontos do catálogo (`plataforma/catalogo.py`), sem domínio próprio nem API; `planos/` com `itens` no lugar de `recursos`.
- **`PLT-04`:** upgrade no teste com a 1ª fatura paga (período da 1ª; ex. 45000 vencendo 22 out), downgrade agendado que deixa de caber (padrão A), 409 para segunda mudança agendada, `acoes.desfazer_mudanca_plano`.
- **Equipe (U4, U13, `PLT-06`, `PLT-14`):** mudança de ciclo (`ciclo_proximo`) e reativação da `cancelada` em 90 dias pelo Django Admin, com os mesmos serviços das ações da plataforma; `plataforma.md` com "Faturas de todas as empresas · Django Admin (fase 1)", `faturas_recentes` e `fatura_atrasada` com dados reais, fases acertadas.
- `Empresa.dia_vencimento` (`PLT-01`, muda na volta da pausa e na reativação), `ciclo_proximo`, `endereco_*`; campos da nota em `FaturaAssinatura`; `tentativas_cartao` até 2 (modelo de dados). Nota de resolução na ADR 0023.

**Regras cobertas:** PLT-01, PLT-02, PLT-04, PLT-05, PLT-06 (só no que mexe nas faturas), PLT-11, PLT-13, PLT-14, PLT-15, AUT-13. Critérios CA-ASS-01 a 21 e 26 a 29.

**Para quem recebe:** a seção "O que muda para as tarefas abertas", no fim do contrato, diz o que muda na T-184, T-185, T-186, T-187, T-189 e T-197. Cancelar e pausar ficam para a T-194; módulos por plano (`excede` com o que está aberto) para a T-192.

**Pontos em aberto (backlog, `[decisão]` para o produto):** reativar a `cancelada` com fatura em atraso (contrato recusa até a resposta); origem do endereço da empresa para a NFS-e e o endereço do seed.

**Fora do escopo, respondido no caminho:** T-181, backend: concordei com a chave `configuracoes` para o item `config` do menu, `marca` continua em `empresas`; o backend ajusta `configuracoes.md` e `contas.md` na branch dele.

**Próximo passo:** orquestrador abre o PR (merge depois do #199). Só documentos, sem teste para rodar. Sigo para a T-192.
