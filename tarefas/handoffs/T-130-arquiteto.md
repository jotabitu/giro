# T-130 · Contrato da edição da marca (Admin-Marca) · arquiteto → orquestrador, seguranca, backend, frontend

**O que foi feito:** contrato da escrita da marca da empresa, ADR da sanitização do logo e as tarefas de backend e frontend propostas no backlog, sem número.

**Onde:**
- `docs/api/empresas.md`: seção "Escrita da marca (T-130)".
  - `POST /api/marca/simular/`: prévia das cores e das iniciais sem gravar (ADR 0005), para a tela não fazer conta de cor. Administrador, 120 por minuto por usuário.
  - `PATCH /api/marca/`: `nome_exibicao`, `cor`, `logo` (arquivo até 2 MB, formato pelo conteúdo) e `remover_logo`; devolve o corpo de `GET /api/marca/` com a `versao` nova. Administrador; suporte e empresa sem operação 403; 30 por hora por usuário. Mensagens de 400 fechadas no contrato.
  - Serviço `salvar_marca`: transação com `select_for_update`, evento `empresa.alterar_marca` (`configuracoes`), e no `on_commit` apaga a chave `marca:<schema>` e o arquivo antigo; marca o passo `marca` da implantação (`IMP-05`).
  - Tabela com as seis cores do `Onboarding-Marca` calculadas pela função da T-129 (contraste do texto sobre as suaves conferido: todas acima de 11:1).
  - O seed continua sem marca salva (padrão, como nas telas).
- `docs/decisoes/0022-sanitizacao-do-logo-da-empresa.md` (nova, no índice): SVG relido com `defusedxml` (dependência nova), conteúdo ativo **recusado** (script, `on*`, `foreignObject`, `image`, animação, `href` externo, `javascript:`, `data:`, `url()` externo), o resto por lista fechada de elementos, atributos e CSS, limites de 5.000 elementos e 32 níveis, tamanho pelo `viewBox`. O PNG fica desenhado (item 6) e espera a Segurança.
- `docs/decisoes/modelo-de-dados.md`: linha de `ConfiguracaoEmpresa` (logo pela ADR 0022; `cor_marca` vazio, não nulo, como já está no código).
- `tarefas/backlog.md`: na T-130, a nota do contrato pronto, a `[decisão]` do PNG para a Segurança e as duas tarefas propostas.

**Regras cobertas:** IMP-05 (passo marca), S-12; ADRs 0004, 0005, 0022.

## Decisões

| # | Ponto | Decisão |
| --- | --- | --- |
| 1 | Saída (a) ou (b) de `cores-da-marca.md` | **(b):** `#C8F04A` com as suaves fixas do `wl-theme.css` (`#EEF9CC`, `#2B3510`), fórmula para as outras cores. A diferença da (a) é invisível, o `wl-theme.css` é do design-system e a T-129 já faz assim. Nada muda no código. |
| 2 | Uma rota ou duas para salvar | Uma só, `PATCH /api/marca/`, multipart com o logo: a tela tem um "Salvar" só, e o evento e a `versao` mudam uma vez. |
| 3 | SVG com conteúdo ativo | Recusa com mensagem, não limpeza silenciosa. Metadados de programa de desenho saem sem erro. |
| 4 | Logo antigo | Apagado do storage depois do commit (não é registro de negócio). |

**O que ficou de fora:**
- **Segurança:** `[decisão]` do PNG no backlog, com recomendação do arquiteto (aceitar: Gmail e Outlook não mostram SVG em e-mail). Até lá, só SVG.
- **Produto / orquestrador:** "Pular por agora" do passo Marca. Este contrato só marca o passo ao salvar; o assistente de implantação ainda não tem contrato, e pular sem marcar deixa a empresa parada no passo Marca do funil (`IMP-05`, 3 dias → "precisam de ajuda"). Decidir quando o assistente for contratado.
- **Orquestrador:** os blocos "Dados da empresa" (razão social, CNPJ, endereço, telefone, e-mail financeiro, com "Editar") e "Endereço do sistema" (domínio próprio, plano Completo) da `Admin-Marca` não têm contrato nem tarefa.
- **Design-system (opcional):** o script de prévia das telas de referência mistura 82% de branco e não bate com a API; vale uma nota nas telas de que a prévia vem de `POST /api/marca/simular/`.

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar as duas tarefas propostas na T-130 e abrir o PR desta branch.
- **Seguranca:** responder a `[decisão]` do PNG e conferir as listas da ADR 0022.
- **Backend:** começar pela tarefa de escrita quando numerada; a parte do SVG não depende da decisão do PNG.
