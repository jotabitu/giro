# T-036 · Contratos da API de contas, veículos e clientes · arquiteto → backend, frontend, orquestrador

**O que foi feito:**
- `docs/api/contas.md`: login em etapas (`pronto`, `verificar_2fa`, `configurar_2fa`), 2 etapas (configurar, ativar, desativar, códigos de recuperação), renovar e sair por cookie, `eu` com a tabela `pode` calculada por perfil e permissões extras, senha (trocar, esqueci, redefinir), sessões (ADR 0014), convite e primeiro acesso, usuários da Administração (convidar, reenviar, cancelar, editar, desativar, reativar, redefinir 2 etapas, sessões de outros), modo suporte e controle do suporte pelo administrador.
- `docs/api/veiculos.md`: frota com contagens e blocos de outros apps, ficha com ocupação (`VEI-06`), cadastro e unicidade de placa e chassi (`VEI-01`), ações de status pela tabela de transições, transferência (`VEI-04`), km e correção (`APR-06`), documentos com URL assinada (`VEI-03`, `AUD-05`), categorias, histórico de preços (`LOC-15`) e extras (`LOC-02`).
- `docs/api/clientes.md`: lista com `situacao` e `acao_principal` decididas pela API (`CLI-06`, `CLI-07`), cadastro PF e PJ com pendências (`CLI-03`), CPF cifrado com busca pelo hash (`CLI-01`, ADR 0014), documentos, análise do cadastro (`CLI-04`), bloqueio manual e automático (`CLI-05`, `APR-05`), inativação, LGPD do titular (fase 2) e `impedimentos_para_retirada` para locações (`CLI-02`, `CLI-03`, `CLI-05`).
- ADR 0015: leituras compostas entre apps por registro de anotações (locação atual na Frota, financeiro na lista de clientes, indicadores de Filiais), sem quebrar a ordem da ADR 0011. `filiais.md` ajustado.
- Ajustes pedidos pelo produto: convite sempre por e-mail e também por WhatsApp quando há celular; sem "manter conectado".

**Onde:** `docs/api/contas.md`, `docs/api/veiculos.md`, `docs/api/clientes.md`, `docs/api/filiais.md`, `docs/decisoes/0015-leituras-compostas-entre-apps.md`, `docs/decisoes/modelo-de-dados.md`, `tarefas/backlog.md`.

**Regras cobertas:** USR-01 a USR-07, PLT-03, PLT-07, VEI-01 a VEI-07, LOC-01, LOC-02, LOC-15, APR-05, APR-06, CLI-01 a CLI-08, AUD-04, AUD-05, AUD-06.

**O que ficou de fora:**
- Importação por planilha (T-027) e planos especiais (contrato de locações, T-015).
- Marca e "Regras de cobrança" (`ConfiguracaoEmpresa`): contrato de empresas, ainda não escrito.
- Dúvidas para o produto no backlog, todas com proposta e sem bloquear: prioridade do botão em `CLI-07`, desbloqueio manual (`CLI-05` × `APR-05` × `APR-09`), quando o cliente fica `inativo`, "manter conectado" (com o dono). Divergências de tela para T-028: reserva `RES-0412` na Frota e diárias que não batem com a tabela.

**Próximo passo para quem recebe:**
- Backend: T-011 por `contas.md`, T-013 por `veiculos.md`, T-014 por `clientes.md`. Os blocos da ADR 0015 vêm `null` até os apps fornecedores existirem; o mecanismo de registro (`comum/leituras.py`) entra junto com a primeira lista que o usa.
- Frontend: T-020 e T-021 podem montar telas com dados falsos a partir destes contratos.
- Orquestrador: próximos contratos para a fase 1 são `empresas.md` (marca e configurações), `locacoes.md` + `contratos.md` (T-015, com S-09), `vistorias.md` (T-016) e `financeiro.md` (T-017).
