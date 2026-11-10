# Conferência no navegador · 10 nov 2026 (T-444, T-417, T-438, T-440, T-445, T-414)

Pedido do Orquestrador de 10 nov 2026. Conferido em 1440 e 390 px, com o Docker do projeto `giro` (giro-integracao: develop com o PR #505 mesclado só localmente), em `http://motorapida.localhost:3000`, com as contas de `docs/agentes/retomada.md`. Capturas em `tarefas/handoffs/anexos/conferencia-10-nov/`; as imagens lado a lado (referência à esquerda, app à direita) em `lado-a-lado/`, geradas por `npm run conferencia` (T-425).

## Como ler

- **O banco não está no dia 07 out.** Não há `GIRO_DATA_REFERENCIA` no `.env` do giro-integracao e o relógio do backend marca 10 nov 2026; além disso a base tem dados de outros testes (um lançamento "teste todas filiais" de R$ 1.000,00 no QXA-4B21, a Filial Maraponga, locações novas). Por isso vários números dos critérios (CA-417-07, CA-438-04) não batem por causa dos dados, não do código. Eu não mexi no relógio nem gravei nada: a stack é compartilhada.
- **Só olhei, não gravei.** Nada foi criado, salvo ou apagado no banco. Os critérios que dependem de gravar (CA-417-02, 04, 05, 10 a 13; CA-438-04 a 14 pelo salvar; CA-440-02 a 13, que pedem enviar a planilha; CA-414-01 a 09 e 12 a 14 em envio, troca e apagar) **não foram exercitados** e precisam da stack isolada com o seed de 07 out.
- A captura `Admin-Usuarios` não foi anexada: a lista dessa base tem o nome real de uma pessoa, e o repositório é público.

## Resumo por item

| Item | Resultado |
| --- | --- |
| 1 · T-444 (#497) | Passa, com uma dúvida de texto (D6). |
| 2 · T-417 (#492) | Seção e botão corretos por perfil; lançar não testado. Um erro de console para o vistoriador (D5). |
| 3 · T-438 (#501) | Passa na tela: tipo antes da categoria, lista só do tipo, esvazia ao trocar, mensagem no salvar, trava com a dica da locação. |
| 4 · T-440 (#503) | Só a tela inicial do passo conferida (sem enviar planilha). Sem divergência nela. |
| 5 · T-445 (#506) | Duas rotas do administrador caem em "sem acesso" (D1) e a edição do veículo está longe da tela (D4). |
| 6 · T-414 (#505) | Galeria e visualizador abrem; setas do teclado não funcionam ao abrir (D2); título sem hífen (D3); tamanho: ver abaixo. |

## Divergências

| # | Tela e tamanho | O que se esperava | O que aparece | Quem corrige |
| --- | --- | --- | --- | --- |
| D1 | `/admin/contratos` (Modelos de contrato) e `/admin/precos` (Tabelas de preço), 1440 e 390, Mariana (administradora) | O cartão "Modelos de contrato" e "Tabelas de preço" de Configurações abrem a tela (`Contratos-Modelos`, `Precos`). | O cartão leva a `/admin/contratos` e a página responde só "Seu perfil não tem acesso a esta página." (o mesmo em `/admin/precos`). O cartão de Configurações lista os dois, mas `rotaPermitida` em `frontend/src/lib/menu.ts` não tem a exceção dessas rotas: o menu da API não traz item para elas e a guarda barra. A tela de contratos não pôde ser conferida. | Frontend (`menu.ts`, como já é feito para `/admin/ramo` e `/admin/suporte`) |
| D2 | Visualizador de fotos da ficha (`/veiculos/44`), 1440 e 390 | Setas do teclado passam a foto (pedido do Orquestrador; CA-414-10). | Ao abrir, o foco fica no contêiner do diálogo e as setas (direita, direita, esquerda) não mudam nada: continua "Foto 1 de 3 · capa". Depois de clicar em "Próxima" (foco no botão), a seta direita funciona (2 para 3). Esc fecha. Quem abre e aperta a seta logo não vê efeito. | Frontend (ouvir a tecla no diálogo inteiro ou focar o primeiro botão ao abrir) |
| D3 | Título do visualizador, 1440 e 390 | "Galeria do veículo · QXA-4B21" (placa como no resto do sistema). | "Galeria do veículo · QXA4B21", sem o hífen. | Frontend |
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
