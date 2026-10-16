# T-315 · Movimentações (T-288 parte 1)

**Data:** 16 out 2026 · **Agente:** segurança · **Regras:** MOV-02 a MOV-06, PLT-07, AUD-01, AUD-05, FIN-06, USR-07, USR-09
**Base:** branch `t-288-movimentacoes-backend` (PR #324): `apps/movimentacoes/{services,selectors}.py` e `api/views.py`, `apps/financeiro` (`NotaDespesaView`, `anexar_nota`), `apps/veiculos/services.py` (`baixar` e o evento `veiculos.veiculo_baixado`), `comum/arquivos.py`, `comum/autenticacao.py` (`conferir_rota_do_suporte`); handoff `tarefas/handoffs/T-288-backend.md`.
**Método:** leitura do código e testes novos em `backend/tests/aceitacao/test_t315_seguranca_movimentacoes.py` (7 passam, 2 `xfail` estritos com os achados). A branch desta revisão tem o merge da `t-288-movimentacoes-backend`: o teste depende do código do PR #324 e só pode entrar depois dele.

## Resumo

A pergunta do backend está respondida: **confirmo** que o suporte em "só ver" lê o quadro, a lista, `pessoas/`, `recebedores/` e os locais, e não lê o detalhe. É o que a ADR 0013 (item 2) pede: a geração de URL assinada de foto fica fora do "só ver". As fotos, a nota, as listas de pessoas e o isolamento estão certos. Há um achado médio (M-01: o suporte em "ver e editar" recebe 500 ao criar uma movimentação) e três baixos.

| Ponto | Situação | Onde está provado |
| --- | --- | --- |
| Suporte "só ver" no detalhe | 403 `PLT-07`: `MovimentacaoView` não tem `suporte_somente_leitura` | `test_plt_07_suporte_so_ver_nao_le_o_detalhe` |
| Suporte "só ver" no quadro, na lista, em `pessoas/`, `recebedores/` e locais | 200, sem nenhuma URL assinada nem `fotos_chegada` (a `linha` não traz fotos) | `test_plt_07_suporte_so_ver_le_quadro_e_lista_sem_url`; lista de rotas em `test_plt_07_lista_de_rotas_que_o_suporte_le` |
| Suporte "só ver" enviando foto | 403 `PLT-07` | `test_plt_07_suporte_so_ver_nao_le_o_detalhe` |
| Suporte "ver e editar" | **500** ao criar | M-01 |
| `pessoas/` e `recebedores/` sem contato | só `id`, `nome`, `perfil`, `perfil_rotulo` e `eu`: sem e-mail, telefone ou CPF | `test_mov_02_pessoas_e_recebedores_sem_contato` |
| `pessoas/` só das filiais com acesso | `exigir_gestao(usuario, filial)`: gerente de outra filial, vendedor, vistoriador e financeiro recebem 403 | o mesmo teste e `test_mov_02_ca_246_11_quem_pode` (T-288) |
| `recebedores/` | só quem registra a chegada (quem leva, o gerente da saída, o administrador); a filial é sempre o destino da própria movimentação, sem `?filial=`. Quem leva vê os nomes da filial de destino, que é o mínimo para escolher quem recebe | o mesmo teste (a Bruna, que não leva, recebe 403) |
| Fotos: tipo | pelo conteúdo (`comum.arquivos.validar`), não pela extensão; PDF recusado na foto; texto com extensão `.jpg` recusado | `test_aud_05_foto_da_chegada_recusa_o_que_nao_e_imagem` |
| Fotos: tamanho | 10 MB (`TAMANHO_MAXIMO`); a reconstrução da imagem barra a bomba de descompressão (`DecompressionBombError`) | leitura de `comum/arquivos.py` |
| Fotos: metadados | a imagem é reconstruída pixel a pixel, sem EXIF nem GPS | `test_aud_05_foto_da_chegada_sem_metadados_e_com_nome_aleatorio` |
| Fotos: nome e lugar | `<schema>/movimentacoes/<model>/<id>/<uuid>.jpg` no armazenamento privado; o nome original não fica; URL de 15 minutos | o mesmo teste |
| Fotos: quem envia | quem registra a chegada; o financeiro e o vendedor que não leva recebem 403, e nada é gravado | `test_mov_02_so_quem_registra_a_chegada_envia_foto` |
| Fotos depois da chegada | não mudam: o envio exige `em_transito` sem paradas pendentes | leitura de `enviar_foto` |
| Nota da parada (na saída) | `arquivos.validar(nota, "nota")`: imagem ou PDF pelo conteúdo, até 10 MB, caminho aleatório e privado | leitura; `test_mov_04_fin_06_ca_246_14_parada_sem_nota` (T-288) |
| Nota depois (`despesas/{id}/nota/`) | administrador, gerente, vendedor e financeiro (`despesas_lancar = todas`), a despesa filtrada pela filial (`filtrar_por_filial`), 409 `nota_existente` se já houver: a nota nunca é trocada; evento `despesa.anexar_nota` | leitura; o mesmo teste da T-288 |
| Baixa que cancela | só quem baixa (o vistoriador recebe 403 e a movimentação segue); o cancelamento entra na mesma transação, com o evento `movimentacao.cancelar`, o motivo "Veículo baixado: roubo", a regra `MOV-03` e o **ator de quem baixou** | `test_mov_03_baixa_cancela_com_o_ator_da_baixa`; `test_mov_03_falha_no_assinante_desfaz_a_baixa` (T-288) |
| Isolamento entre empresas | dado só no schema da empresa; o caminho do arquivo começa pelo schema; o token de uma empresa é recusado no host de outra (ADR 0013, item 1) | `test_mov_isolamento_entre_empresas` (T-288); o mesmo teste das fotos confere o schema no caminho |
| Valores | o vistoriador recebe tudo sem `_centavos` (`sem_valores`); o vendedor que leva vê o custo das paradas que ele mesmo pagou, como diz o contrato | leitura; testes da T-288 |

## Achados

### M-01 · O suporte em "ver e editar" recebe 500 ao criar uma movimentação · média

**Onde:** `movimentacoes/services.py`, `criar` (`criada_por=usuario`) e `enviar_foto` (`foto.por = usuario`); o modelo exige um `contas.Usuario` em `criada_por`, e o suporte é um `AtorSuporte`, sem `pk` (ADR 0013, item 2).
**Problema:** o suporte com "ver e editar" age como administrador e passa por `exigir_gestao`. Ao criar, o Django recusa o `AtorSuporte` no campo e a rota responde 500 com o traceback no log. Não abre acesso nem grava nada (a transação desfaz), mas:
- o suporte, que deveria ajudar a empresa, fica sem saber o que aconteceu, e cada tentativa vira um erro 500 no Sentry;
- a regra não diz se o suporte pode criar movimentação. Se puder, o registro precisa dizer que foi o suporte (o `ator` da auditoria já diz; `criada_por` não tem como).
- `registra_chegada` compara `levado_por_id` com `getattr(usuario, "pk", None)`: com o suporte, `None`. Hoje não abre nada, porque `levado_por` é obrigatório, mas fica frágil se o campo virar opcional.

**Reprodução:** `test_plt_07_suporte_ver_e_editar_cria_sem_erro` (`xfail` estrito): token de suporte "ver e editar", `POST /api/movimentacoes/` com o corpo do CA-246-01, e a resposta é 500 (`ValueError: Cannot assign "AtorSuporte(...)": "Movimentacao.criada_por" must be a "Usuario" instance.`).
**Sugestão (tarefa no handoff):** a mais simples é `suporte_proibido` nas rotas de escrita das movimentações (criar, editar, iniciar, cancelar, paradas, fotos, chegada): 403 `PLT-07`. Uma movimentação tem quem leva, e o suporte não leva veículo. Se o produto quiser que o suporte crie, o caminho é `criada_por` opcional, com o suporte no evento. A escolha é do produto; o padrão que proponho é proibir.
**Fora desta revisão:** o mesmo padrão (`*_por=usuario` num campo que exige `contas.Usuario`) aparece em `financeiro/services.py` (`lancada_por`, `aberto_por`, `fechado_por`, `feito_por`). Não testei essas rotas com o suporte. Fica a sugestão de uma tarefa de varredura (abaixo, no handoff).

### B-01 · Trocar a foto da chegada não deixa rastro · baixa

**Onde:** `enviar_foto`.
**Problema:** a foto nova da mesma posição substitui a anterior (contrato), grava `por` e não gera evento. A foto anterior fica no armazenamento, sem referência. A vistoria rápida é a prova do estado do veículo na chegada (`MOV-05`). Hoje não há como saber, pela auditoria, que a frente foi trocada nem por quem, e o evento `movimentacao.concluir` não guarda quais fotos valeram. O envio de foto da vistoria (`vistorias/services.py`) segue o mesmo padrão, então não é um desvio deste PR.
**Reprodução:** `test_aud_01_foto_da_chegada_trocada_fica_na_auditoria` (`xfail` estrito): duas fotos da frente, nenhum evento.
**Sugestão:** um evento `movimentacao.foto_chegada` (posição, id da foto, `substituiu: true/false`, sem URL), ou os ids das 4 fotos no `depois` de `movimentacao.concluir`. Pode ir junto da M-01.

### B-02 · A imagem é processada antes de conferir quem envia · baixa

**Onde:** `enviar_foto` chama `arquivos.validar` e `arquivos.sem_metadados` (decodifica e reconstrói a imagem) antes de `_travada_para_chegada`, que confere a permissão.
**Problema:** qualquer pessoa autenticada da empresa (o financeiro, por exemplo) faz o servidor decodificar imagens de até 10 MB antes de receber o 403. Com o limite de tamanho e a proteção contra bomba de descompressão, o custo é limitado; é só ordem.
**Sugestão:** `exigir_chegada(movimentacao, usuario)` antes de validar o arquivo (também em `sair_parada`, com a nota).

### B-03 · A nota da despesa guarda os metadados · baixa

**Onde:** `sair_parada` e `anexar_nota` validam a nota e a gravam como veio.
**Problema:** a nota fotografada pelo celular guarda o EXIF (aparelho, às vezes GPS de onde a pessoa estava). É o mesmo comportamento das outras notas de despesa (`FIN-06`), não deste PR. Risco baixo: a nota é vista por quem lança e aprova despesas.
**Sugestão:** quando a nota for imagem, passar por `arquivos.sem_metadados`, como as fotos. Uma linha em `comum`, valendo para todas as notas.

## Respostas aos pontos do handoff

- **Suporte no detalhe:** confirmado, fica fora do "só ver". Com "ver e editar", o suporte lê o detalhe e as fotos (a ADR 0013 só proíbe a URL assinada no "só ver"), e o acesso fica na auditoria da entrada do suporte (`PLT-07`).
- **Editar a agendada apaga as paradas:** sem efeito de segurança. As paradas da agendada não andaram, não têm despesa nem foto, e o `movimentacao.editar` guarda o antes e o depois da movimentação (as paradas não entram no retrato). Se o produto quiser o rastro das paradas antigas, é com ele.
- **Auditoria da baixa sem `detalhes.origem`:** suficiente. O motivo "Veículo baixado: …" e o ator de quem baixou, no mesmo instante do evento `veiculo.baixar`, ligam um ao outro.
