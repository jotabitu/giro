# T-437 · o que faltou da conferência de 11 nov (CA-437-13, 06 e 11)

Pedido do Orquestrador. giro-integracao, 1440 px (390 px no CA-437-06), uma sessão da Mariana. Capturas em `tarefas/handoffs/anexos/conferencia-11-nov/`. O CA-437-08 (150 veículos) ficou de fora, como combinado.

| CA | Resultado |
| --- | --- |
| 437-13 · auditoria | **O evento existe; o que falta é conteúdo, não ordem.** Detalhe abaixo. |
| 437-06 · sem fotos | Passa. |
| 437-11 · sair no meio | Passa; as fotos que não subiram se perdem sem aviso. Detalhe abaixo. |

## CA-437-13 · auditoria

A lista aberta sem filtro mostrava só os eventos mais novos (login, convite, usuário), por isso a conferência anterior não os viu. A tela só filtra por categoria (Tudo, Financeiro, Operação, Configurações, Segurança, Suporte), pessoa e período; não filtra por veículo nem por tipo de evento. Com "Operação" os eventos aparecem em 5 páginas: "Cadastrou o veículo" e "Veículo: foto enviar" (na ordem do envio), "Veículo: foto capa" e "Veículo: foto apagar" (da T-414).

Li a resposta da API (`GET /api/auditoria/eventos/?categoria=operacao&periodo=7d`) que a tela usa. Um evento de foto do cadastro vem assim:

`acao: "veiculo.foto_enviar"`, `resumo: "Veículo: foto enviar"`, `detalhe: ""`, `ator: Mariana Costa`, `regra: "VEI-10"`, `objeto: { tipo: "veiculo", id: 95, codigo: null, filial: "Filial Centro" }`, sem imagem.

O que bate com o CA-437-13: o evento é gravado, é da Mariana, leva `VEI-10`, não leva a imagem, e há um por foto (3 para a TBC-5H22 e o "Cadastrou o veículo" antes).

O que **não** bate e não dá para confirmar pela tela nem pela lista da API:

1. **`capa: true` da `moto.png`**: o `detalhe` vem vazio, então o campo não aparece. Não sei se o backend guarda `capa` no evento (a lista não o devolve).
2. **Qual veículo**: `objeto.codigo` vem `null` (só o `id`), então na tela a linha não diz TBC-5H22; o usuário não consegue ligar o evento ao veículo.
3. **Texto**: "Veículo: foto enviar" é o nome da ação com a primeira palavra trocada, diferente dos outros eventos ("Convidou teste", "Cadastrou o veículo").

**Quem corrige:** Backend (devolver `codigo` do veículo no `objeto`, preencher o `detalhe` com a capa e dar um `resumo` em português). Não é só lista ou ordem da tela. O Frontend não precisa mudar nada até a API devolver o texto.

## CA-437-06 · cadastro sem fotos

Veículo TBC-5H25 (id 96), sem escolher foto: só `POST /api/veiculos/` (nenhum `.../fotos/`), abre a ficha e ela mostra "0 de 20 fotos", "Nenhuma foto do veículo." e o link "Adicionar fotos". Nos dois tamanhos (1440 e 390) a ficha abre sem erro.

## CA-437-11 · sair no meio do envio

Veículo TBC-5H26 (id 97), 3 fotos escolhidas (`moto-1.jpg`, `moto-2.jpg`, `moto.png`, a 1ª capa), com a 2ª resposta segurada por 8 s no navegador para dar tempo de sair. Na tela "Enviando fotos · 2 de 3", a Mariana vai para outra página (`/inicio`):

- O veículo foi criado, com **1 foto**: a 1ª, que é a capa ("1 de 20 fotos"; o editar mostra "Foto 1 de 1" com capa).
- A 2ª requisição ficou em voo e foi cancelada pelo navegador ao sair; ela e a 3ª **não chegam ao servidor**. Mesmo esperando 12 s, a ficha continua com 1.
- **Nenhum aviso ao sair**: o navegador não mostrou pergunta de confirmação e a tela não alertou que faltam fotos. As fotos escolhidas ficam só na página e se perdem ao sair; quem quiser as outras duas precisa enviar pelo editar (CA-414-01).
- Isso é o que a regra descreve (o veículo existe com a 1ª foto, que é a capa). O que não está descrito é o aviso ao sair; se o dono quiser, é um pedido de Produto e de Frontend.

## O que fica no banco

TBC-5H25 (id 96, sem fotos) e TBC-5H26 (id 97, com 1 foto) ficam no banco: veículo não se apaga. Somados aos 92 a 95 da rodada anterior, a frota de teste tem 6 veículos a mais (93 no total). Se o Orquestrador quiser o seed de volta, `make seed` na stack.
