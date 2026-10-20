# T-203 · Telas resolvidas · frontend → qa (T-204), orquestrador

**O que foi feito:**
- **Filial e seletor (`FIL-01`, `DEV-01`, `FIL-03`, `PLT-03`, CA-FIL-01 a 06):**
  - Seletor da `CascaDoApp`, lista de filiais da pessoa (`usuarios.ts`, `falso-usuarios.ts`) e resumo de Configurações (`falso-configuracoes.ts`) exibem `nome_curto` direto da API, sem cortar o prefixo `"Filial "` no cliente.
  - Em `FormularioDaFilial.tsx` e `lib/filiais.ts`: campo "Nome curto no seletor" (`nome_curto`, até 30 caracteres), campo "Preço do litro do combustível" (`preco_litro_centavos`) dentro do bloco "Operação" visível e editável apenas para o administrador (`eu.pode.administracao`), campo "Telefone" visível também no celular, horário por dia com suporte a até 2 intervalos (`"2º intervalo"`, `"Remover"`, dica `"Cada dia aceita até 2 intervalos, para quem fecha no almoço."` e resumo compacto no celular) e aviso de limite do plano com `"Para abrir outra, mude de plano."`.
- **Usuários (`USR-01` a `USR-04`, `FIL-01`):**
  - Textos neutros em `lib/usuarios.ts` (`"Hoje a pessoa vê só ..."`, `"Escolha as filiais da pessoa"`) e `filiaisDoUsuario` usando `f.nome_curto`.
  - Em `PainelDoUsuario.tsx`, texto de bloqueio atualizado para `"A pessoa sai do sistema na hora. O histórico do que fez continua guardado."`.
- **Aprovações (`APR-12`, `APR-01` a `APR-11`, CA-APR-01 a 11):**
  - `ListaAprovacoes.tsx` exibe os 4 indicadores de `GET /api/aprovacoes/` (`indicadores.esperando`, `indicadores.aprovadas`, `indicadores.recusadas` e `indicadores.descontos` com `titulo`, `quantidade`/`valor_centavos` e `contexto` vindos da API) e as contagens nas abas (`pendente`, `aprovado`, `recusado`).
  - Aba `"Meus pedidos"` consulta `?minhas=true` (sem `status` fixo), sem contador no chip, mostra pedidos em qualquer status e exibe `"Cancelar pedido"` quando `pode_cancelar` é `true`.
  - Cartões renderizam as células (`p.resumo.celulas`, com `destaque: "perigo" | "info" | "mono" | null`) e a `p.resumo.nota` vindas prontas da API; sem frase de 4 horas úteis (CA-APR-09) e sem link `"Ver proposta"` até a tela de venda existir (CA-APR-10).
- **Auditoria (`AUD-02`, `AUD-03`):**
  - `tomDoEvento` (`lib/auditoria.ts`) e o destaque de linha (`ListaAuditoria.tsx`) leem `e.tom` (`null | "info" | "alerta" | "perigo"`) direto da API, sem inferir por `categoria`, `acao`, `regra` ou `suporte` no cliente.
- **Importar (`IMP-05`):**
  - `CaixaDeImportacao.tsx` invalida também a query `["implantacao"]` ao concluir ou desfazer importação, mantendo o andamento dos passos sincronizado na `CascaDoAssistente`.

**Onde:**
- `frontend/src/lib/api/tipos.ts`, `frontend/src/lib/api/tipos-financeiro.ts`
- `frontend/src/components/casca/CascaDoApp.tsx`
- `frontend/src/lib/filiais.ts`, `frontend/src/components/admin/FormularioDaFilial.tsx`
- `frontend/src/lib/usuarios.ts`, `frontend/src/components/admin/PainelDoUsuario.tsx`
- `frontend/src/components/aprovacoes/ListaAprovacoes.tsx`
- `frontend/src/lib/auditoria.ts`, `frontend/src/components/admin/ListaAuditoria.tsx`
- `frontend/src/components/implantacao/CaixaDeImportacao.tsx`
- Falsos e testes em `frontend/src/testes/falsos/` e `frontend/src/components/` / `frontend/src/lib/`

**Contrato:** `GET /api/eu/`, `GET/POST/PATCH /api/filiais/`, `GET /api/aprovacoes/`, `POST /api/aprovacoes/{id}/cancelar/`, `GET /api/auditoria/`, `GET /api/implantacao/` (entregues na T-201 / T-202).

**Regras cobertas:** `FIL-01`, `DEV-01`, `FIL-03`, `PLT-03`, `USR-01` a `USR-04`, `APR-01` a `APR-12`, `AUD-02`, `AUD-03`, `IMP-05` (CA-FIL-01 a 06, CA-APR-01 a 11).

**Verificações:**
- `npm run typecheck` limpo
- `npm run lint` limpo
- 174 testes Vitest nas suítes afetadas (`Filiais.test.tsx`, `Aprovacoes.test.tsx`, `Auditoria.test.tsx`, `Usuarios.test.tsx`, `Configuracoes.test.tsx`, `Importar.test.tsx`, `filial.test.ts`, `filial-perfis.test.ts`, `aprovacoes.test.ts`, `FaixaDataSimulada.test.tsx`, `GuardaDeRota.test.tsx`, `Financeiro.test.tsx`, `Despesas.test.tsx`) passando
- `npm run build` limpo

**O que não foi conferido:**
- Conferência visual no navegador com backend real rodando (validado via testes de componente Testing Library e build de produção).

**Próximo passo para quem recebe:**
- **qa (T-204):** rodar os testes ponta a ponta / aceitação com os critérios CA-FIL-01 a 06 e CA-APR-01 a 11.
- **orquestrador:** revisar e abrir PR da branch `t-203-telas-resolvidas`.
