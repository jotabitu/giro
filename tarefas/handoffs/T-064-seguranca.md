# T-064 · Revisão de segurança da T-058 e da T-012 · seguranca → orquestrador, backend, arquiteto, devops, produto

**O que foi feito:** conferi as correções de P-01 a P-04 (T-058) contra o relatório da T-057 e revisei o código da T-012 (escopo por `X-Filial`, `tornar-matriz`, desativação, limites do plano, CEP) contra a `USR-07`, a `FIL-01`, a `FIL-06`, a `PLT-03` e as ADRs. Rodei `test_t058_seguranca.py` e `test_t012_filiais.py` num Postgres descartável: 39 passaram, inclusive os dois de concorrência. Confirmei F-01 e F-02 com um teste temporário, que não foi commitado. O container já foi removido.

**Onde:** `docs/seguranca/2026-10-09-t058-t012.md`.

**Resultado:**
- **T-058:** P-01 a P-04 estão fechados. Os resíduos do handoff da T-058 são baixos e aceitos. Recomendo, sem prazo, a trava no model `Usuario` e o aviso ao dono quando uma conta da equipe for bloqueada.
- **T-012:** nenhum alto. Ficaram 2 médios e 3 baixos:
  - **F-01 (média, confirmado):** `SO_ADMINISTRADOR` substitui as permissões padrão e perde `EmpresaOperando` e `EscopoDeFilial`. Com a empresa suspensa, o administrador cria filial (201) e também edita, desativa, reativa e mexe em feriados.
  - **F-02 (média, confirmado, latente):** `filial_da_requisicao` devolve `None` tanto para "todas" quanto para pessoa sem filial nenhuma. Quando a T-013 filtrar por ela, quem não tem filial vai ver todas.
  - **F-03 (baixa):** a troca de filiais da pessoa não é auditada, apaga o vínculo e aceita filial inativa.
  - **F-04 (baixa):** sem IP, todo mundo divide a mesma chave do limite por IP (risco de derrubar o login de todos); em IPv6 a contagem é por endereço inteiro.
  - **F-05 (baixa):** a busca de CEP não tem limite.

**O que ficou de fora:** os indicadores e contadores de operação reais (T-013, T-015, T-017), o publicador do evento de filiais da pessoa (T-011) e o logo da empresa (S-12).

**Próximo passo para quem recebe:**
- **Orquestrador:** F-01 e F-02 numa tarefa de backend antes da T-013, com o arquiteto revisando o contrato de "Interface interna" das filiais para o F-02. F-03 vai para a T-011. F-04 e F-05 podem ir junto do F-01.
- **DevOps:** conferir que o `REMOTE_ADDR` chega com o IP do proxy em cada ambiente (F-04).
- **Produto:** aviso ao dono quando uma conta da equipe é bloqueada (resíduo do P-03).
- O PR #40 pode ser considerado fechado do lado da segurança.
