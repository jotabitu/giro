# T-063 · Contratos com o caixa da T-059 e conferência da T-058 e da T-012 · arquiteto → orquestrador, backend, frontend, qa

**O que foi feito:**

*T-059 (divergência "Contratos" do backlog) e carteira de outubro:*
- `docs/api/financeiro.md`: caixa de 07 out com 111190 em 5 recebimentos, sendo cartão 10900 (Diego, LOC-2848, renovação de 1 diária, `LOC-08`). O caso do CA-017-13 foi reescrito com a origem de cada entrada; a gaveta continua 28100.
- `docs/api/painel.md`: `caixa_hoje` com `recebido_centavos` 111190 e `saldo_dia_centavos` 106390.
- `docs/api/veiculos.md`: LOC-2841 "assinada em 23 set".
- O "contas a receber" de `financeiro.md` e o "vence hoje" do `painel.md` trocaram os números ilustrativos da T-055 pelos da carteira de outubro (linha "Contas a receber de outubro em 07 out" das regras):

  | Número | Valor |
  | --- | --- |
  | Previsto | 5200210 em 128 parcelas |
  | Recebido | 1340170, `recebido_pct` "25.77" |
  | Vence hoje | 262580 em 6 parcelas (também `entra_hoje` e `a_receber_hoje_centavos`) |
  | Abas | 130 / 2 / 6 / 92 / 30 |

*Decisões da T-012:* nenhuma muda decisão de ADR, então não há ADR nova.
1. Detalhe da filial para todos dentro do escopo; fora do escopo responde 404, e administrar responde 403 a quem não é administrador. **De acordo**, e escrito em `filiais.md`.
2. Texto opcional vazio sai `null`. **De acordo** com os exemplos do contrato.
3. Lista paginada por `nome`, sem `?ordem=`. **De acordo**: o nome é único sem diferenciar maiúsculas, então o cursor é estável.
4. Sugestão com os 10 feriados nacionais de lei; Carnaval e Corpus Christi entram como feriado local. **De acordo**, e escrito no contrato.
5. `X-Filial: todas` só para o administrador. **Divergia** de `financeiro.md`, `painel.md` e da tabela de perfis. O produto confirmou que o financeiro tem o mesmo escopo do administrador: vê todas as filiais ativas, sem depender das ligadas a ele, e escolhe "Todas". Quem tem `relatorios_todas_filiais` usa "Todas" só em painel e relatórios. "Todas" inclui filiais desativadas com contas ou histórico (`FIL-06`). Está em `filiais.md`, citando a `USR-07` corrigida pelo produto (branch t-063-usr-07, T-067). O ajuste no `EscopoDeFilial` foi para a T-011, como o orquestrador pôs no quadro.

*Conferência da T-058 em `plataforma.md`:* está **de acordo** com a `PLT-08` nova (5 senhas ou 3 códigos, 15 minutos, nem o certo entra durante o bloqueio).
- O 401 para quem não manda código não revela qual dos três campos errou, como o contrato já pedia.
- O limite por IP usa `comum.rede.ip_do_cliente` (ADR 0018).
- O throttle do DRF com o cache que já existe não é dependência nova de infraestrutura, então não precisa de ADR.

Ajustes que fiz:
- `docs/api/README.md` ganhou a linha do 429 `muitas_requisicoes` (formato `tentar_de_novo_em_segundos` e `Retry-After`), separada do 429 de bloqueio por regra (`tentar_de_novo_em`).
- `plataforma.md` passou a citar o `sair` nos 30 por minuto (o código já faz assim) e o limite do proxy (S-17) como do devops.
- `contas.md` (`/api/auth/entrar/`) diz que a T-011 usa os mesmos limites e o mesmo 429.

**Onde:** `docs/api/financeiro.md`, `painel.md`, `veiculos.md`, `filiais.md`, `plataforma.md`, `contas.md`, `README.md`; `tarefas/em-andamento.md` (T-063).

**Check:** só documentação; nenhum arquivo de `backend/` ou `frontend/` mudou, então não rodei os checks de código.

**O que ficou de fora:**
- Os resíduos 1 a 4 da T-058 são da segurança.
- O financeiro no `EscopoDeFilial` vai na T-011.

**Próximo passo para quem recebe:**
- **Backend (T-011):** financeiro com `todas` e `pode_escolher_todas` em `/filiais/minhas/`; `relatorios_todas_filiais` só em painel e relatórios; 429 `muitas_requisicoes` no `entrar` da empresa. **(T-017):** caixa de 07 out = 111190 e os números da `FIN-15` acima.
- **Frontend:** em `falso-painel.ts`, o caixa passa a 111190 recebidos e 106390 de saldo, e o entra hoje a 262580 em "6 parcelas".
- **QA:** os números dos contratos batem com a carteira de outubro e com o caixa de 07 out das regras.
