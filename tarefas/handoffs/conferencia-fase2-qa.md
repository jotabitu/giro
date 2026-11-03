# Conferência no navegador das entregas da fase 2 (T-412, T-413, T-416, T-410) · qa → orquestrador

**Onde rodou:** stack isolada do QA (projeto `giro-qa`, portas 3100 e 8100, banco próprio), seed da Moto Rápida, relógio em 07 out 2026, develop em `65df9002` (com o PR #457 e a migração `financeiro.0009`; `acertar_reservas_t410` rodado: 26 contas acertadas na Moto Rápida). Playwright a 1440 e 390 px, sem corrigir código. Capturas em `tarefas/handoffs/anexos/conferencia-fase2/`.

## Resultado

| Tarefa | 1440 px | 390 px | Divergências |
| --- | --- | --- | --- |
| T-412 faixa suspensa/pausada | passa | **falha para quem não administra** | D1 |
| T-413 documentos do veículo | passa com ressalva | **falha** | D2, D3, D4 |
| T-416 Ver comprovante | passa | passa | D5 (menor) |
| T-410 reserva e impedimento | passa | passa | D6 (critério, não é código) |

## Divergências para devolver ao dono

- **D1 · T-412 (frontend), celular, perfil sem administração.** Suspensa ou pausada, com a vendedora Bruna a 390 px, a faixa fixa ocupa 520 px dos 844 (61 % da tela): o texto cai numa coluna de uma palavra por linha e "Fale com o administrador da empresa." fica ao lado (`t412-susp-vendedora-390-inicio.png`). O administrador a 390 px fica com 235 px, alto mas legível (`t412-susp-admin-390-inicio.png`). Para reproduzir: `docker compose -p giro-qa exec backend python manage.py shell`, levar a empresa a `suspensa` (`transicionar_empresa(e, "suspensa", regra="PLT-02")`), entrar como `bruna@motorapida.com.br` a 390 px em `/inicio`. A 1440 as duas faixas ficam bem (73 px o administrador, 47 px os outros). Sugestão: texto e aviso em coluna (empilhar) no celular e faixa menos alta.
- **D2 · T-413, ficha do veículo a 1440 px.** O cartão Documentos mostra o botão do histórico duplicado: "Esconder o histórico" e "Ver o histórico" juntos, cada um com estado próprio; o histórico lista o CRLV "Em uso" repetido (`t413-ficha-doc-1440.png`). Reproduzir: `/veiculos/20` com um CRLV enviado.
- **D3 · T-413, ficha do veículo a 390 px.** Não existe "Ver o histórico" (0 botões visíveis), embora o handoff diga "vale para desktop e celular" (`t413-ficha-doc-390.png`).
- **D4 · T-413, editar a 390 px.** O campo "Nova validade" e o botão "Substituir" passam da borda direita do cartão (terminam em ~758 px de 780, o cartão em ~700): estouram o preenchimento sem criar rolagem lateral (`t413-editar-pos-390.png`). Funcionalmente passa: enviar PDF mostra "CRLV atualizado. O anterior ficou no histórico." e a ficha passa a mostrar "Abrir". Sem validade, o erro "Informe a validade" aparece no campo. Não testei IPVA e rastreador (a pergunta ao backend sobre os tipos segue aberta).
- **D5 · T-416 (menor).** "Ver comprovante" e "Ver a nota" parecem texto solto, sem aparência de botão ou link (`t416-comprovante-390.png`). Funciona: link com URL assinada (`/api/arquivos-dev/...?expira=...&assinatura=...`), `target=_blank`, `rel="noopener noreferrer"`, alvo de 44 px no celular (36 px no desktop). A despesa paga do seed (Aluguel do ponto) não tem comprovante e não mostra o botão, como previsto.
- **D6 · critério `docs/qa/criterios/T-410.md`, CA-410-23.** Cita a "LOC-2866" e a CDL-0B10 "Reservado na LOC-2866"; o seed não tem a LOC-2866 (as aguardando retirada são LOC-2857 a LOC-2865, todas com o veículo `reservado`) e a CDL-0B10 está `disponivel`. É erro do exemplo no critério; para o produto trocar por LOC-2858 / BAD-1Y07. Sem divergência no código.

## O que passou na T-410

- Frota e ficha mostram "Reservado na LOC-2858" (BAD-1Y07), com "Ver LOC-2858" e "Reservado na LOC-2858 desde 04 nov"; sem erro de API nas duas larguras.
- Nova locação: o veículo reservado não aparece no seletor ("Só os veículos disponíveis aparecem aqui"). Início em 03 out (último dia 06 out, hoje 07 out) mostra "O início passou de 3 dias. Mude a data de início para confirmar." e "Continuar para vistoria" fica desabilitado; início em 05 out libera o botão (cliente sem bloqueio). Com o cliente bloqueado, a mensagem do bloqueio vem primeiro.
- `AUT-17` rodada com `GIRO_DATA_REFERENCIA=2026-11-07`: aviso da LOC-2858 ao gerente (sino e e-mail, texto igual ao CA-410-13), segunda execução não repete (0); cancelamento derrubou a LOC-2857 (último dia 06 nov) e liberou o veículo, e a LOC-2858 seguiu `aguardando_retirada`. O 409 `inicio_vencido` na confirmação não foi exercitado pela tela (o impedimento da simulação barra antes); fica para os testes de aceitação do backend.
- Efeito colateral no banco isolado: LOC-2857 ficou `cancelada`; o seed (`make seed`) não a restaura sozinho.

## Próximo

Frontend: D1 a D4 (e D5 se o design-system concordar). Produto: D6. T-425 (conferência automática da página com a tela de referência) segue em andamento, com o design-system.
