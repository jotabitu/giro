# T-173 · Contrato da tela de Configurações · arquiteto → orquestrador, produto, backend, frontend

**O que foi feito:** conferi o que `Config-Desktop` e `Config-Mobile` mostram contra os contratos que já existem, escrevi o contrato do que faltava (a leitura que monta a tela) e propus as tarefas de backend e frontend no backlog, sem número.

**Onde:**
- `docs/api/configuracoes.md` (novo): `GET /api/configuracoes/`, só administrador (token de suporte sem `auditoria` e `exportar`, `PLT-07`).
  - `cartoes`: `chave`, `titulo` e `resumo` prontos, na ordem da tela ("1 filial · Filial Centro, Fortaleza", "5 de 10 usuários · 2 convites", "4 categorias · 2 planos especiais", "5 modelos · 1 rascunho", "Profissional · teste até 21 out"). Regras de texto, plural e casos-limite na tabela "Cartões".
  - Cartão só vem quando o app da tela de destino está em `GIRO_MODULOS_ATIVOS`, pela mesma tabela do menu (`USR-05`). `integracoes` e `notificacoes` não vêm no MVP.
  - `implantacao`: `null` depois da 1ª locação (`IMP-01`); antes, "Implantação concluída em 6 de 10 passos" e "Faltam contrato, recebimentos, importar dados e a 1ª locação." pelos passos de `plataforma` (`IMP-05`). `acao` vem `null` até o assistente ter contrato; quando falta só a 1ª locação, leva a `nova_locacao`.
  - Tabela de fontes (selectors existentes e os 5 novos), rotas dos cartões e os casos do seed para teste.
- `docs/telas/README.md`: seção "Rotas dos cartões de Configurações" (`chave` → rota).
- `tarefas/backlog.md`: na T-173, a nota do contrato pronto, a `[decisão]` do texto do Exportar, a nota do que ficou sem contrato, e as duas tarefas propostas (`T-???` backend e frontend).

**Regras cobertas:** USR-05, USR-08, PLT-03, PLT-07, IMP-01, IMP-04, IMP-05; ADRs 0005 e 0011.

## Decisões

| # | Ponto | Decisão |
| --- | --- | --- |
| 1 | App dono do resumo | `relatorios`, como o painel: o resumo lê de oito apps, e pela ADR 0011 só o nível 13 lê de todos (`empresas` é nível 4). Sem ADR nova. |
| 2 | Cartão de área sem tela | Não vem (igual ao menu, `USR-05`), em vez de cartão desabilitado ou com número de exemplo. |
| 3 | Texto dos resumos | Pela API, inclusive plural e data; o frontend só liga `chave` → rota e ícone. |
| 4 | Filial no resumo | Empresa inteira, ignora `X-Filial`. |
| 5 | Cache | Nenhum: contagens pequenas, e o número tem que mudar ao voltar de Filiais ou Usuários. Teto de 10 queries. |
| 6 | "Continuar implantação" | Sem botão até o assistente ter contrato; com só a 1ª locação faltando, o destino `nova_locacao` do painel. |

**O que ficou de fora:**
- **Produto:** `[decisão]` do texto do cartão Exportar ("Baixe tudo quando quiser" na tela; no MVP só a auditoria se exporta, T-151). O contrato usa "Baixe a auditoria em CSV" até a resposta.
- **Design-system (T-028):** a tela mostra "1 filial · Centro, Fortaleza"; a API usa o nome cadastrado, "Filial Centro".
- **Orquestrador:** sem contrato nem tarefa: as "Regras de cobrança" da `Precos` e do `Onboarding-Precos` (citadas em `veiculos.md` como de `empresas.md`, que não as tem; o assistente pede ainda franquia de km e km excedente, que as regras não têm), o "exigir 2 etapas para todos" (`exige_2fa_todos`, citado em `contas.md`, sem tela na empresa), as telas `Precos`, `Contratos-Modelos` e `Integracoes` (sem tarefa de frontend) e o contrato do assistente de implantação.
- O item `config` do menu depende de `empresas` em `GIRO_MODULOS_ATIVOS`, fora do padrão hoje; a tarefa do backend o acrescenta (liga também "Empresa e marca", da T-154).

**Próximo passo para quem recebe:**
- **Orquestrador:** numerar as duas tarefas propostas e abrir o PR desta branch.
- **Produto:** responder a `[decisão]` do Exportar.
- **Backend:** começar pela tarefa do resumo quando numerada; nada depende de decisão pendente (o texto do Exportar é uma constante).
- **Frontend:** a tela pode começar com a API mockada pelo contrato.
