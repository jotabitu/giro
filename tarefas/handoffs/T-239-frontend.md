# T-239 · Bug: locação não passa do passo 1 · frontend → orquestrador, qa

**Causa:** com "Todas as filiais" escolhida no menu (só administrador e quem tem `pode_escolher_todas`), o `X-Filial` vai como `todas` e `POST /api/locacoes/simular/` responde 400 `{"campos":{"filial":["Escolha a filial no cabeçalho X-Filial."]}}`. A `NovaLocacao` só mostrava erro de simulação sem campos, então o erro de `filial` sumia: o resumo ficava vazio, `pronto` ficava falso e os dois botões ("Continuar para vistoria" e "Salvar como reserva") ficavam desligados sem explicação. A API está correta (a locação nasce numa filial); a falha era só da tela.

**Como reproduzi:** seed, `mariana@motorapida.com.br` (administradora), menu da filial em "Todas as filiais", `/locacoes/nova?cliente=51`, escolher veículo e Semanal: simulação 400, resumo vazio, botões desligados. Com uma filial escolhida (Filial Centro) o mesmo passo 1 simula, os botões ficam ativos e o clique cria, confirma e abre a vistoria. Com `rodrigo` (gerente, que não escolhe "Todas") o fluxo já funcionava em diária, semanal, mensal, desconto, vencimento, forma de pagamento e devolução prevista.

**O que foi feito:** `frontend/src/components/locacoes/NovaLocacao.tsx`
- Em "Todas as filiais" a tela não chama a simulação e mostra no Resumo: "Escolha uma filial no menu para criar a locação." (mesmo padrão do caixa e da baixa); botões desligados.
- Se a API recusar por `filial`, a mensagem dela aparece no Resumo.
- Qualquer outro erro de campo da simulação que nenhum campo da tela mostra passa a aparecer no Resumo, para o botão nunca ficar desligado sem motivo.

**Testes:** `NovaLocacaoFilial.test.tsx` (uma filial: resumo e sem aviso; "Todas": aviso, sem "Calculando…", dois botões desligados). `tsc --noEmit`, `eslint` e os testes de `components/locacoes` passam.

**O que ficou de fora:**
- O teste que "clica nos dois botões" precisa de DOM interativo; o Vitest do projeto roda em `node` (sem jsdom nem testing-library) e não adicionei dependência. O clique nos botões continua coberto pelo E2E da locação (`criarLocacao`, com uma filial). Um E2E com "Todas as filiais" pede login do administrador com 2 etapas, que `e2e/suporte/tela.ts` ainda não tem: fica para o QA.
- Impedimentos da simulação (ex.: veículo já alugado) seguem aparecendo no Resumo; num celular ele fica abaixo dos campos, então a mensagem pode passar despercebida. Não mexi na ordem das seções.

**Ambiente (atenção):** ao reproduzir, o backend de `giro-integracao` estava com a migração `plataforma.0009_faturas_assinatura` pendente (login dava 500, `email_cobranca` inexistente); rodei `migrate_schemas --shared` nessa pilha. Meus cliques de teste criaram LOC-2866 e LOC-2867 (Vanessa, Biz 125) e uma vistoria de saída nesse banco; o E2E espera LOC-2866 como a próxima, então rode `make seed` (ou o reset do E2E) antes de usar a pilha de novo.

**Próximo passo para quem recebe:** QA repete o fluxo com o administrador em "Todas as filiais" e em uma filial.
