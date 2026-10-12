# T-128 · Contrato das rotas do painel e da marca da empresa · arquiteto → orquestrador, backend, frontend, design-system, seguranca

**O que foi feito:**
- **Painel** (`docs/api/painel.md`, seção nova "Rotas, perfis e o que entra no MVP"): o contrato de números da T-047 continua o mesmo. Acrescentei o app dono (`relatorios`, rotas em `config/urls.py`, sem depender de `relatorios` em `GIRO_MODULOS_ATIVOS`), os perfis (todos, com a variante do `eu`; suporte como "só ver", escopo do administrador), a filial só por `filtrar_por_filial`, os erros e a regra do MVP: **um número sai quando a fonte dele já existe no backend; senão, `null`**. A tabela diz bloco por bloco o que sai hoje. Fica `null` até a T-017 só o que depende de caixa (`caixa_hoje`, `caixas_do_dia`); fica `null` até existir a despesa: `despesas`, `contas_a_pagar`, `sai_hoje`. Manutenção, vendas e conciliação seguem `null` (fase 2). Contadores e menu saem da mesma função de navegação, então item escondido não tem contador. Cache dos contadores caiu de 5 min para 60 s, o intervalo da consulta do frontend.
- **Marca** (`docs/api/empresas.md`, novo): `GET /api/marca/` pública, pelo subdomínio, a mesma antes e depois do login (o `eu` não ganha marca). Devolve `nome_exibicao`, `iniciais`, `logo` (url e dimensões), `cor`, `cor_sobre`, `cor_suave`, `cor_suave_escuro`, `personalizada` e `versao`. Sem marca configurada: 200 com o nome da compra, iniciais, sem logo e cores padrão (nunca 404). O cache tem `ETag`/304, `max-age=300` e cache por schema no backend. O logo sai por `GET /api/marca/logo/?v=`, servido pela própria API (o storage continua privado), com cache longo na versão atual e `nosniff`, CSP `sandbox` e `Content-Disposition` (2ª barreira da S-12). Host sem empresa: 404 do urlconf, e o frontend mantém "Sua locadora" (como já faz).
- **Dados:** `ConfiguracaoEmpresa` ganha `nome_exibicao`, `logo` (+ largura e altura), `cor_marca` e `meta_ocupacao_pct`. Cor sobre a marca e cores suaves passam a ser **calculadas na leitura**, não guardadas (`modelo-de-dados.md` ajustado).
- **Locações** (`docs/api/locacoes.md`): a linha da lista ganha `veiculo.tipo` e `pagamento.pago_centavos` (sem caução; LOC-2836 = 65800), para a ficha do cliente.
- **Quadro:** T-129 (backend) criada no backlog; T-128 em `feito.md`.

**Onde:** `docs/api/painel.md`, `docs/api/empresas.md`, `docs/api/locacoes.md`, `docs/api/contas.md` (aponta para a rota de marca), `docs/decisoes/modelo-de-dados.md`, `tarefas/backlog.md`, `tarefas/feito.md`. A branch traz o merge da `origin/quadro-t127-t128` (PR #134), para o backlog não conflitar.

**Decisões que tomei (técnicas, sem regra nova):**
1. Uma rota de marca só, pública, em vez de marca no `eu` mais rota pública: uma fonte, um cache.
2. O logo vai pela API, não por URL assinada: o `AUD-05` (15 min) é para documento pessoal. O logo é público por natureza e aparece em e-mail.
3. O painel ilustrativo do `Login-Desktop` ("Alugados agora 42 de 86", "Ocupação 71%") é desenho fixo do frontend. Nenhuma rota pública devolve número da operação. O `modelo-de-dados` dizia que a `meta_ocupacao_pct` é "exibida no login"; no MVP ela só aparece no início.
4. Os blocos financeiros que já têm fonte (`receita_locacao`, `em_atraso`, `entra_hoje`, parcelas do vendedor) saem antes do menu do financeiro existir, porque `ContaReceber` já é real desde a T-015.

**Fichas (itens 3 e 4 do handoff da T-126): MVP ou depois**

| Item | Decisão | O que fazer |
| --- | --- | --- |
| Manutenções do veículo | **Depois** (fase 2, app `manutencao`) | O contrato já aponta para `GET /api/manutencao/ordens/?veiculo=`, que nasce com o app. Até lá o bloco `manutencao` do veículo vem `null`. O frontend **esconde** a seção Manutenções da ficha enquanto `manutencoes` não estiver no menu do `eu`. Lista vazia passaria a ideia de "nenhuma manutenção". |
| "N no total" das locações do veículo | MVP como está | O tamanho da lista (até 100) basta no MVP. |
| Linha do tempo do cliente (`historico`) | **Depois** | Não há contrato, e o MVP não precisa dela. O frontend esconde a seção (não mostra vazia). A linha do tempo da locação (`GET /api/locacoes/{id}/historico/`) continua sendo o lugar do histórico no MVP. |
| Resumo pago por cliente | **MVP, já contratado** | `financeiro.total_pago_centavos`, `em_aberto_centavos` e `a_devolver_centavos` na representação do cliente (`clientes.md`) são fornecidos por `financeiro` (ADR 0015) e chegam com a T-017. Até lá vêm `null`. O frontend deve **parar de somar** o detalhe de cada locação (é cálculo na tela) e mostrar o bloco da API. |
| Pago e tipo do veículo por locação na ficha do cliente | **MVP, T-129** | `pagamento.pago_centavos` e `veiculo.tipo` na linha de `GET /api/locacoes/?cliente=`. Com eles a ficha não precisa abrir o detalhe de cada locação. |
| `pago_detalhe` ("2 semanas + caução") | **Não entra** | Texto inventado pela camada falsa. Some da tela. |
| Documentos sem `rotulo`, IPVA e rastreador | Como está | O frontend monta o rótulo pelo `tipo` (enum fechado). IPVA e rastreador não são tipos de documento (`veiculos.md`). |

**Pendente / para quem recebe:**
- **Design-system:** confirme a fórmula de `cor_suave_escuro` para cores além da padrão. O `wl-theme.css` só traz `#2B3510` para `#C8F04A`, e não deduzi uma conta que reproduza o valor exato. Responda na T-129 antes do backend começar a parte da marca. O resto da T-129 (painel, `cor_sobre`, `cor_suave`) pode começar já.
- **Backend (T-129):** implemente a partir dos dois contratos; o "Pronto quando" está no backlog. Para a T-017: ao entregar o caixa, ligue `caixa_hoje` e `caixas_do_dia` no selector de `relatorios`, com o teste do seed (Filial Centro, recebido 111190). Ponha `financeiro` em `GIRO_MODULOS_ATIVOS` para o contador `receber` aparecer.
- **Frontend:** depois da T-129, troque a marca padrão pelo `GET /api/marca/` no login, convite, primeiro acesso, esqueci a senha, entrada do suporte e na casca; o logo vai sempre em `<img>`. Na ficha do veículo, esconda Manutenções; na do cliente, a linha do tempo. Use `financeiro.total_pago_centavos` do cliente e `pago_centavos` e `veiculo.tipo` da linha de locação; tire `pago_detalhe`.
- **Orquestrador:** a edição da marca (`Admin-Marca` e `Onboarding-Marca`: upload com a sanitização da S-12, cor, nome, invalidação do cache) ainda não tem tarefa; a nota da T-012 no backlog continua valendo. Ao criá-la: a tela aceita "PNG ou SVG, até 2 MB" e o modelo dizia só SVG. O contrato de leitura serve os dois formatos, e a tarefa de edição decide o upload com a Segurança.
- **Segurança:** confira os cabeçalhos do `GET /api/marca/logo/` e o limite por IP das duas rotas públicas (120 por minuto).
