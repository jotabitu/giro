# Conferência no navegador · 10 nov 2026 (T-444, T-417, T-438, T-440, T-445, T-414)

Pedido do Orquestrador de 10 nov 2026. Conferido em 1440 e 390 px, com o Docker do projeto `giro` (giro-integracao: develop com o PR #505 mesclado só localmente), em `http://motorapida.localhost:3000`, com as contas de `docs/agentes/retomada.md`. Capturas em `tarefas/handoffs/anexos/conferencia-10-nov/`; as imagens lado a lado (referência à esquerda, app à direita) em `lado-a-lado/`, geradas por `npm run conferencia` (T-425).

## Como ler

- **O banco não está no dia 07 out.** Não há `GIRO_DATA_REFERENCIA` no `.env` do giro-integracao e o relógio do backend marca 10 nov 2026; além disso a base tem dados de outros testes (um lançamento "teste todas filiais" de R$ 1.000,00 no QXA-4B21, a Filial Maraponga, locações novas). Por isso vários números dos critérios (CA-417-07, CA-438-04) não batem por causa dos dados, não do código. Eu não mexi no relógio nem gravei nada: a stack é compartilhada.
- **Itens 1 a 5: só olhei, não gravei.** Nada foi criado, salvo ou apagado no banco por eles. (O item 6 gravou: ver a seção própria.) Os critérios que dependem de gravar (CA-417-02, 04, 05, 10 a 13; CA-438-04 a 14 pelo salvar; CA-440-02 a 13, que pedem enviar a planilha; CA-414-09) **não foram exercitados** e precisam da stack isolada com o seed de 07 out.
- A captura `Admin-Usuarios` não foi anexada: a lista dessa base tem o nome real de uma pessoa, e o repositório é público.

## Resumo por item

| Item | Resultado |
| --- | --- |
| 1 · T-444 (#497) | Passa, com uma dúvida de texto (D6). |
| 2 · T-417 (#492) | Seção e botão corretos por perfil; lançar não testado. Um erro de console para o vistoriador (D5). |
| 3 · T-438 (#501) | Passa na tela: tipo antes da categoria, lista só do tipo, esvazia ao trocar, mensagem no salvar, trava com a dica da locação. |
| 4 · T-440 (#503) | Só a tela inicial do passo conferida (sem enviar planilha). Sem divergência nela. |
| 5 · T-445 (#506) | Duas rotas do administrador caem em "sem acesso" (D1) e a edição do veículo está longe da tela (D4). |
| 6 · T-414 (#505) | Refeito no build corrigido: CA-414-01 a 08 e 10 a 14 passam (09 não exercitado); D2 e D3 corrigidos; D7 novo (foto acima de 10 MB). |

## Divergências

| # | Tela e tamanho | O que se esperava | O que aparece | Quem corrige |
| --- | --- | --- | --- | --- |
| D1 | `/admin/contratos` (Modelos de contrato) e `/admin/precos` (Tabelas de preço), 1440 e 390, Mariana (administradora) | O cartão "Modelos de contrato" e "Tabelas de preço" de Configurações abrem a tela (`Contratos-Modelos`, `Precos`). | O cartão leva a `/admin/contratos` e a página responde só "Seu perfil não tem acesso a esta página." (o mesmo em `/admin/precos`). O cartão de Configurações lista os dois, mas `rotaPermitida` em `frontend/src/lib/menu.ts` não tem a exceção dessas rotas: o menu da API não traz item para elas e a guarda barra. A tela de contratos não pôde ser conferida. | Frontend (`menu.ts`, como já é feito para `/admin/ramo` e `/admin/suporte`) |
| D2 (corrigido, ver item 6) | Visualizador de fotos da ficha (`/veiculos/44`), 1440 e 390 | Setas do teclado passam a foto (pedido do Orquestrador; CA-414-10). | Ao abrir, o foco fica no contêiner do diálogo e as setas (direita, direita, esquerda) não mudam nada: continua "Foto 1 de 3 · capa". Depois de clicar em "Próxima" (foco no botão), a seta direita funciona (2 para 3). Esc fecha. Quem abre e aperta a seta logo não vê efeito. | Frontend (ouvir a tecla no diálogo inteiro ou focar o primeiro botão ao abrir) |
| D3 (corrigido, ver item 6) | Título do visualizador, 1440 e 390 | "Galeria do veículo · QXA-4B21" (placa como no resto do sistema). | "Galeria do veículo · QXA4B21", sem o hífen. | Frontend |
| D4 | `/veiculos/<id>/editar`, 1440 (tela `Veiculo-Editar`) | Galeria de fotos no topo, com o cartão lateral de Permissões; Identificação com placa e chassi travados; "Uso na frota" com Finalidade e Plano de manutenção; Documentos em cartões com "Substituir"/"Renovar" e validade; Cancelar e Salvar alterações no cabeçalho. | A página é uma coluna só: "Preencher pelo documento" no topo, Dados do documento, Rastreador, Uso na frota (sem Finalidade e sem Plano de manutenção), Compra e valores, Galeria depois de Compra, e Documentos como lista de formulários (campo de data, arquivo, "Enviar") sem cartões. Também: o rótulo "Tipo" (CRLV) e o novo "Tipo de veículo" aparecem na mesma página e se confundem; a tela de referência ainda não tem o campo de tipo (T-438) nem o texto da trava. | Design-system (atualizar a tela com o tipo do veículo e a galeria) e Frontend (levar a página à tela, ou registrar no handoff o que fica diferente) |
| D5 | Ficha do veículo (`/veiculos/44` e `/veiculos/1`), 1440, João (vistoriador) | Sem erro de rede na ficha. | O navegador chama `GET /api/locacoes/?veiculo=44&ordem=-inicio&tamanho=100` e recebe 403, com erro no console. A tela não quebra. | Frontend (não chamar para quem não lê locações) |
| D6 | Ficha do PNB-7C04 (`/veiculos/45`), 1440 e 390 | "Atrasado desde 14 out" (devolução prevista 14 out). | O card "Agora" diz "Atrasado desde 30 set" (início do período) e a tabela Locações diz "Devolução atrasada 27 dias" (conta a partir de 14 out). Os dois textos se contradizem. Confirmar com o Produto qual data vale. | Frontend, depois da resposta do Produto |

Observações sem dono ainda:

- **T-444:** a ficha abre sem erro, com o alerta "Atrasado" no cabeçalho, no card "Agora" e na lista de locações, a 1440 e 390 px, sem rolagem lateral.
- **Tamanho do visualizador (T-414):** diálogo de 560 x 650 px a 1440 e 358 x 534 px a 390. A foto ocupa 512 x 384 px; funciona, mas é pequena para ver avaria numa tela larga. Decisão do design-system se um tamanho maior é melhor.
- **T-417, ficha:** na ficha do QXA-4B21 a seção mostra "teste todas filiais · 15 out · Rastreamento · R$ 1.000,00" (dado de outro teste) e o total R$ 1.048,00, e não R$ 48,00 do CA-417-07. Nos pneus do PMZ-3E17 aparece "A pagar", não "Aguardando aprovação" (CA-417-08): alguém já aprovou. Para Bruna e João a seção mostra o título "Despesas do veículo" só com o botão "Lançar despesa", sem lista, como o CA-417-12 pede. A 390 px o botão fica no fim da seção; a 1440, no topo.
- **T-438:** Tipo antes de Categoria, com Moto marcado e só as categorias de moto (Scooter premium, Street, Urbana); com Carro, só "Carro compacto"; trocar o tipo esvazia a categoria; "Escolha a categoria de preço." aparece no salvar sem gravar; voltar a Moto antes de salvar volta à categoria original; em veículo com locação o tipo fica travado com "Este veículo está na LOC-2841. Troque o tipo depois da devolução." A 1440 e a 390, sem rolagem lateral. A base tem a Filial Maraponga ativa, por isso o cadastro pede a filial. O SAK-1D39 não estava livre (está na LOC-2856), então o teste de trocar de tipo foi feito no PMZ-3E17 (em manutenção).
- **T-440:** `/implantacao/importar` mostra "Filial dos veículos" (a base tem 2 filiais, CA-440-04) e as duas caixas Veículos e Clientes; "Categoria de cada modelo" só aparece depois de enviar uma planilha, o que não foi feito. A tela de referência mostra o estado de uma filial só, com a conferência, e os estados "Mais de uma filial", "Corrigir aqui" e "Sem categoria ativa". Os ícones do passo 7 e da lista de passos diferem um pouco da referência (círculo verde-limão no passo atual); nada de texto.
- **T-445 (espaços que eram zero):** olhei Veiculo-Novo, Veiculo-Editar, Onboarding-Importar, Frota, Despesas e Filiais nos dois tamanhos: sem rolagem lateral, sem campo colado ao vizinho. Nada estranho nos espaços além do que está em D4. Os contratos ficaram sem conferência por causa do D1.

## O que falta para fechar

1. Rodar de novo na stack isolada com o seed de 07 out os critérios que gravam (lista acima), depois que o D1 e o D2 forem corrigidos.
2. Produto: resposta do D6.
3. Design-system: tela `Veiculo-Editar` com o tipo e a galeria (D4) e o tamanho do visualizador.

## Item 6 refeito: T-414 (#505, push 9d004579, frontend reiniciado), 1440 e 390 px

A primeira passada foi contra o build antigo (o volume do Windows não avisou o frontend da mudança). Refeita depois do `docker restart` feito pelo Orquestrador. Desta vez **gravei** no banco do giro-integracao, no QXA-4B21 (veículo 44) e no PNB-7C04 (veículo 45), com arquivos gerados por mim (`moto-1.jpg` a `moto-18.jpg`, `moto.png`, `moto-gps.jpg` com GPS nos metadados, `grande.jpg` de 11 MB, `moto.heic`, `documento.pdf`). No fim apaguei as fotos de teste: o QXA-4B21 voltou a 3 fotos e o PNB-7C04 a 0. **Mas o QXA-4B21 não voltou ao que era:** a "Frente" foi trocada por `moto-1.jpg` (CA-414-06) e o "Painel" foi apagado (CA-414-07), e as 3 de agora são fotos de teste. As fotos fictícias originais do seed estão inativas no banco. Quem precisar do seed de volta recria o veículo com `make seed`.

| CA | Resultado | Como foi |
| --- | --- | --- |
| 414-01 enviar | Passa | 3 fotos; enviadas `moto-1.jpg` e `moto.png`: 5, na ordem, capa continua a 1ª. |
| 414-02 recusados | Passa nos formatos, falha no tamanho (D7) | `moto.heic` e `documento.pdf`: "Envie uma foto JPG ou PNG de até 10 MB." As outras do envio entram. `grande.jpg`: ver D7. |
| 414-03 limite de 20 | Passa | Com 6 fotos, 16 arquivos: entraram 14, a galeria foi a 20 e `moto-17.jpg` e `moto-18.jpg` ficaram de fora com "O veículo já tem 20 fotos. Apague uma para enviar outra." |
| 414-04 sem GPS | Passa | `moto-gps.jpg` (com tag GPS 0x8825): a foto servida depois do envio não traz o bloco Exif nem a tag. |
| 414-05 capa | Passa | PNB-7C04 sem galeria: 2 fotos, a 1ª é capa; "Usar como capa" na 2ª a põe primeiro; apagar a capa deixa a outra como capa (1 de 1). |
| 414-06 trocar | Passa | Trocar a frente: a imagem muda, a galeria continua com o mesmo número e a capa é a mesma posição. |
| 414-07 apagar | Passa na tela | Confirmação "Apagar esta foto? Ela sai da galeria e da ficha. Não dá para desfazer pela tela." com "Voltar" e "Apagar a foto"; apagada, some. Auditoria e foto inativa no banco: não verifiquei. |
| 414-08 quem mexe | Passa na tela | Bruna, João e Lúcia: o editar responde "Seu perfil não tem acesso a esta página." e a ficha não mostra Adicionar fotos, Trocar, Apagar nem Usar como capa. O 403 da API para cada ação e o `PLT-07` do suporte não foram exercitados. |
| 414-09 vendido e baixado | Não exercitado | Não achei veículo vendido ou baixado para testar sem alterar outro dado. |
| 414-10 galeria na ficha | Passa | Rodrigo, Bruna e Lúcia veem a galeria; tocar abre o visualizador; 24 vezes a seta direita para na última foto da galeria ("Foto 20 de 20"), sem entrar nas fotos da vistoria. |
| 414-11 vistoria | Passa | Rodrigo, Bruna e João veem "Vistoria de saída · LOC-2841 · 23 set" com 12 fotos (32 miniaturas com as 20 da galeria); o visualizador da vistoria passa de uma em uma. Lúcia não vê a seção. |
| 414-12 baixar | Passa no nome, link de 15 min não testado | Galeria: "Baixar (QXA-4B21-galeria-1.jpg)" e o `download` do link bate com o nome; vistoria: "QXA-4B21-vistoria-saida-frente.jpg" e "…-traseira.jpg". O texto "Link válido por 15 minutos." aparece; não esperei os 15 minutos. |
| 414-13 sem fotos | Passa | PNB-7C04: "Nenhuma foto do veículo."; Rodrigo vê "Adicionar fotos", Bruna não. A seção da vistoria aparece porque esse veículo tem vistoria concluída. |
| 414-14 origens separadas | Passa pela leitura | Nenhuma foto da vistoria aparece na galeria. Uma vistoria nova não foi criada. |

### D2 e D3: corrigidos

- **D2:** ao abrir o visualizador, sem clicar, as setas passam a foto (1, 2, 3, depois 2, 1); depois de Tab (foco em "Próxima foto") também. Na primeira foto, a seta esquerda não faz nada. Esc fecha. 1440 e 390 px.
- **D3:** o título agora é "Galeria do veículo · QXA-4B21".
- Tamanho do visualizador (Dialogo médio): 560 x 722 px a 1440 e 358 x 618 px a 390, com 20 fotos. A foto fica pequena em tela larga; a decisão é do design-system.

### D7 (novo): foto acima de 10 MB demora 25 s e termina em erro genérico

- **Tela e tamanho:** editar do veículo, galeria, 1440 px (o mesmo vale a 390).
- **O que se esperava:** `grande.jpg` (11 MB) recusada na hora com "Envie uma foto JPG ou PNG de até 10 MB.", como o `moto.heic` (CA-414-02).
- **O que aparece:** "Enviando 1 de 3…" por cerca de 25 segundos e depois "grande.jpg: Não foi possível concluir agora. Tente de novo." O navegador recebe 500 em `POST /api/veiculos/44/fotos/`. O log do frontend diz: "Request body exceeded 10MB for /api/veiculos/44/fotos/. Only the first 10MB will be available" e "Failed to proxy ... socket hang up (ECONNRESET)": o proxy do Next corta o corpo em 10 MB e derruba a conexão. O backend nem responde 400.
- **Quem corrige:** Frontend, recusar acima de 10 MB antes de enviar (mensagem do CA-414-02) e/ou configurar o limite do proxy (`middlewareClientMaxBodySize` em `next.config`). Em homologação e produção o proxy é outro; o Devops confere o limite de corpo de lá.

### Efeito colateral dos testes

Os logins repetidos desta conferência passaram o limite de tentativas (429 por 24 minutos); o Orquestrador limpou as chaves `throttle_entrar` no Redis. A partir daí entrei uma vez por perfil.
