# T-253 · Tela da troca do ramo em Configurações · design-system → frontend, arquiteto, produto

**O que foi feito:** referência desktop e celular da troca do ramo (`PLT-12`), a partir do `Onboarding-Ramo` e dos contratos `GET` e `PUT /api/ramo/` (`docs/api/empresas.md`).

**Onde:**
- `docs/telas/html/Admin-Ramo-Desktop.dc.html` e `Admin-Ramo-Mobile.dc.html`.
- Cartão "O que a empresa faz" nos hubs `Config-Desktop` e `Config-Mobile`.
- Linha no índice (`docs/telas/README.md`, Administração e relatórios), rota `(empresa)/admin/ramo` como proposta.

**O que a tela mostra, e de onde vem:**
- Atividades "Locação" e "Venda de veículos" (`atividades`), e tipos Motos e Carros (`trabalha_com`; os dois marcados é `ambos`). Pelo menos um de cada grupo fica marcado.
- Aviso "Vendas faz parte do plano Profissional." junto do botão de venda quando `aviso` vem preenchido (Essencial). No Essencial, Locação fica travada, porque `atividades_aceitas` é `aluga` e `ambos`: venda pode ser marcada junto, "só vende" não existe.
- "Módulos que vamos ligar": a lista `modulos` da combinação marcada (nomes do `Recurso.label`, não os do passo 7 antigo). Profissional, aluga e vende: 9; só aluga ou só vende: 8; Essencial: 3.
- Recusa 422 `PLT-12` em bloco crítico, com o `abertos_texto` e um atalho para o que está aberto: "Para deixar de alugar, resolva o que está aberto: 51 locações abertas." (seed de 07 out) e "Para deixar de vender, resolva o que está aberto: 1 venda aberta e 1 comissão a pagar." (CA-ASS-50). "Nada mudou" e o botão "Manter o ramo atual" voltam a seleção ao que está salvo.
- Sucesso: "Ramo salvo. O menu muda agora, e nada foi apagado." (`PLT-12`, ADR 0024 item 6).
- Salvar fica desligado sem mudança. Só o administrador chega à tela (a Administração já é dele).
- A tela não decide nada: lista de combinações aceitas, recusa e textos são da API. Os três "estados de exemplo" no alto (Profissional, Profissional com venda aberta, Essencial) existem só na referência para mostrar os casos; o frontend não os leva.

**Checagens:** as duas telas foram renderizadas em Chromium (1440 e 390 px) nos três estados, com cliques em Salvar e na troca de plano; links resolvem; sem emoji nem exclamação; tokens e componentes do design system, sem token novo. Os arquivos usam o formato `x-dc` do canvas, como as outras telas: em navegador puro os `{{...}}` aparecem crus (mesmo limite do `Onboarding-Ramo`).

**Regras cobertas:** PLT-12, IMP (passo 7); critérios CA-ASS-50, 51 e 52 (CA-ASS-52, downgrade de quem só vende, é da tela de assinatura, não desta).

**Divergências (em `tarefas/backlog.md`):** (1) o hub precisa de um cartão `ramo` em `GET /api/configuracoes/`; (2) "comissão não paga" no CA-ASS-50 contra "comissão a pagar" da API; (3) 51 locações abertas no seed contra "1" do CA-ASS-50; (4) o `Onboarding-Ramo` está atrás desta tela.

**O que ficou de fora:** o `Onboarding-Ramo` não foi alterado (precisa de tarefa própria, item 4 acima). "Como você aluga" (modalidades) e "CNH exigida" não entraram: não são do contrato de ramo.

**Próximo passo para quem recebe:** frontend, ligar a tela em `GET`/`PUT /api/ramo/` com os componentes do design system, tratando 422 `PLT-12` (`detalhes.motivo` `plano` ou `abertos`); arquiteto, o cartão `ramo` em `configuracoes`; produto, confirmar o texto do CA-ASS-50.
