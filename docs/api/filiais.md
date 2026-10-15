# Filiais

**Dono:** arquiteto · **Versão:** 15 out 2026 (T-201, T-213; T-030) · **App:** `filiais` (schema da empresa) · **Regras:** FIL-01 a FIL-06, DEV-01, PLT-03, PLT-15, USR-07, LOC-11 · **Telas:** Filiais, Filial, Onboarding-Filial, seletor de filial · **Critérios:** `docs/qa/criterios/filiais.md` (CA-FIL-01 a 06)

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (item 6).

> **O que mudou na T-201 (decisões do dono de 14 out 2026, regras na T-190).** (1) A filial ganha o `nome_curto` (`FIL-01`), opcional; a API manda o nome pronto para o seletor e as listas curtas (`nome_curto` já com o nome no lugar quando vazio), e o frontend para de cortar "Filial " do nome. (2) O preço do litro (`DEV-01`) fica no bloco Operação da tela `Filial`, editado só pelo administrador, com antes e depois na auditoria. (3) O horário por dia com até 2 intervalos já era o formato deste contrato; só a tela muda (T-200). Ver "O que muda para as tarefas" no fim.

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver as próprias filiais (seletor) | todas, e "Todas as filiais" | as suas | as suas | as suas | todas, e "Todas as filiais" |
| Ver o detalhe de uma filial do seu escopo | sim | sim | sim | sim | sim |
| Administrar filiais (listar todas, criar, editar, desativar) | sim | — | — | — | — |

"Administração (marca, filiais, usuários, ...)" é só do administrador na tabela de perfis: as ações de administrar (lista, criar, editar, matriz, desativar, reativar, feriados) respondem 403 aos demais perfis. Fora do escopo da pessoa, a filial responde 404.

O financeiro vê painel, relatórios e contas de todas as filiais (tabela de perfis, `USR-08`, `financeiro.md` e `painel.md`); por isso o escopo dele é igual ao do administrador, sem depender das filiais ligadas a ele (`USR-07`: "Administrador e financeiro veem todas as filiais ativas, sem depender das filiais ligadas a eles, e podem escolher 'Todas as filiais'"; confirmado pelo produto na T-063, texto da regra corrigido na T-067).

## Representação da filial

```json
{
  "id": 1,
  "nome": "Filial Centro",
  "nome_curto": "Centro",
  "matriz": true,
  "ativo": true,
  "cnpj": "12345678000195",
  "inscricao_estadual": null,
  "inscricao_municipal": null,
  "endereco": { "cep": "60325000", "logradouro": "Av. Bezerra de Menezes", "numero": "1200", "complemento": null,
                "bairro": "São Gerardo", "cidade": "Fortaleza", "uf": "CE" },
  "contato": { "telefone": "8532123344", "whatsapp": "85998124410", "email": "centro@motorapida.com.br" },
  "preco_litro_centavos": 550,
  "horario": {
    "seg": [ { "abre": "08:00", "fecha": "18:00" } ], "ter": [ ... ], "qua": [ ... ], "qui": [ ... ], "sex": [ ... ],
    "sab": [ { "abre": "08:00", "fecha": "12:00" } ],
    "dom": []
  },
  "horario_resumo": "seg a sex 8h–18h · sáb 8h–12h",
  "endereco_resumo": "Av. Bezerra de Menezes, 1200 · Fortaleza, CE",
  "gerentes": [ { "id": 2, "nome": "Rodrigo Pinheiro" } ],
  "feriados_proximos": [ { "data": "2026-10-12", "nome": "Nossa Senhora Aparecida" } ],
  "feriados_ano_seguinte_pendentes": false,
  "criado_em": "2026-10-07T13:00:00Z"
}
```

- `horario`: chaves `seg` a `dom`, cada dia com 0, 1 ou 2 intervalos (para quem fecha no almoço); lista vazia = fechado. Horas em `HH:MM`, no fuso `America/Sao_Paulo`. `fecha` > `abre`; intervalos do mesmo dia não se sobrepõem. É a base de `LOC-11` (devolução fora do horário).
- `horario_resumo` e `endereco_resumo` são montados pela API.
- `gerentes`: usuários ativos com perfil `gerente` ligados à filial (`UsuarioFilial`, `FIL-02`). Só leitura aqui; muda em Usuários. Avisos "para o gerente" vão a todos eles.
- `feriados_proximos`: os 3 próximos feriados da filial (`FIL-03`). `feriados_ano_seguinte_pendentes` fica `true` a partir de 1º de novembro enquanto o administrador não confirmou nenhum feriado do ano seguinte; a tela mostra o aviso e leva às sugestões.
- Não existe status "rascunho": a filial só é salva com os obrigatórios e é ativa ou inativa (`FIL-01`).
- `cnpj`, inscrições e contato são opcionais.
- `nome_curto` (`FIL-01`): opcional, até 30 caracteres, sem espaço nas pontas; vazio sai `null`. Aqui vem o valor guardado (para o formulário da tela `Filial`); nas listas curtas a API já manda o nome a mostrar (abaixo). Não precisa ser único (a `FIL-01` só pede o `nome` único).
- `preco_litro_centavos`: preço da bomba usado no acerto da devolução (`DEV-01`); opcional, inteiro maior que 0 (400 `{ "preco_litro_centavos": ["Informe um preço maior que zero."] }`), editado no `PATCH`, só pelo administrador (os demais perfis: 403, CA-FIL-03). A tela `Filial` mostra o campo no bloco Operação, só para o administrador. Sem ele, o combustível do acerto é informado à mão (CA-FIL-05). O acerto lê o preço da filial na hora do cálculo: mudar o preço vale para o próximo acerto, e acerto já encerrado não muda (CA-FIL-03, CA-FIL-04).

### Nome a mostrar (`FIL-01`)

Onde a regra pede o nome curto, a API manda o texto pronto, nunca os dois para a tela escolher: `nome_curto or nome`. Moto Rápida: "Centro"; "Filial Messejana" sem nome curto: "Filial Messejana" (CA-FIL-02). O frontend não corta nem monta texto do nome (CA-FIL-01).

| Onde | Campo | Contrato |
| --- | --- | --- |
| Seletor de filial (`GET /api/filiais/minhas/`) | `nome_curto` de cada item | este |
| Filiais da pessoa em `Admin-Usuarios` (lista, detalhe e `eu`) | `filiais[].nome_curto` | `contas.md` |
| Resumo do cartão Filiais na `Configurações` | dentro do `resumo` ("1 filial · Centro, Fortaleza") | `configuracoes.md` |

As outras telas (a `Filial`, a lista `Filiais`, listas e relatórios com a filial) continuam com o `nome` ("Filial Centro").

---

## GET /api/filiais/minhas/
Perfis: todos.
Para o seletor de filial do topo do menu (`USR-07`). Sem paginação.
200:
```json
{
  "pode_escolher_todas": true,
  "resultados": [ { "id": 1, "nome": "Filial Centro", "nome_curto": "Centro", "matriz": true, "cidade": "Fortaleza", "uf": "CE" } ]
}
```
- O seletor mostra `nome_curto`, que já vem com o nome quando a filial não tem nome curto ("Filial Messejana", CA-FIL-02). `nome` continua vindo, para o título da tela ou o aviso que precise do nome inteiro.
- Só filiais ativas e ligadas à pessoa. Administrador e financeiro recebem todas as ativas e `pode_escolher_todas: true` ("Todas as filiais").
- O seletor lista só filiais ativas, mas `X-Filial: todas` inclui os dados das filiais desativadas que ainda têm contas em aberto ou histórico: elas mantêm a filial de origem para relatório e DRE (`FIL-06`). Ou seja, "todas" não filtra por filial, em vez de filtrar pelas ativas.
- A filial escolhida vai nas próximas requisições pelo cabeçalho `X-Filial: <id>` (ou `X-Filial: todas`, só para quem pode: administrador e financeiro em qualquer endpoint; quem tem a permissão extra `relatorios_todas_filiais` (`USR-03`) só nos endpoints de painel e relatórios, e nos demais recebe 403 `USR-07`). Sem o cabeçalho, a API usa a matriz, se a pessoa tiver acesso a ela, ou a primeira filial da pessoa. Filial fora do escopo no cabeçalho → 403 `{ "codigo": "USR-07", "mensagem": "Você não tem acesso a esta filial" }`. A regra vale para todos os módulos com filial e é aplicada por `comum.permissoes`.

## GET /api/filiais/
Perfil: administrador.
Query: `?ativo=true|false` (padrão: todas), `?busca=` (nome, cidade). Ordem fixa por `nome` (único na empresa, sem diferenciar maiúsculas), que é a chave do cursor; não há `?ordem=`.
200:
```json
{
  "plano": { "usado": 1, "limite": 3, "aviso": false, "bloqueado": false, "nome_plano": "Profissional" },
  "resultados": [ { ...representação da filial... } ],
  "proximo": null, "anterior": null
}
```
- `plano` é o item `filiais` de `GET /api/assinatura/` (contrato da plataforma). A tela mostra "1 de 3 filiais do plano Profissional" e "Seu plano permite mais 2 filiais" a partir dele; com `bloqueado: true` o botão "Nova filial" leva para a mudança de plano.
- Indicadores por filial vêm no bloco `indicadores` de cada item, por anotação de leitura (ADR 0015): `{ "veiculos": 86, "locacoes_ativas": 42, "usuarios": 5, "ocupacao_pct": "71.00" }`. `veiculos` e `ocupacao_pct` (`VEI-06`, últimos 90 dias) são fornecidos pelo app `veiculos`, `locacoes_ativas` por `locacoes` e `usuarios` por `filiais`. Enquanto o app fornecedor não existe, o campo vem `null`.

## GET /api/filiais/{id}/
Perfis: todos, para filial do seu escopo (assim gerente e demais veem `horario` e `feriados_proximos`). Fora do escopo: 404. 200: representação da filial.
Campos opcionais de texto (CNPJ, inscrições, contato, complemento) vazios saem `null`.

## POST /api/filiais/
Perfil: administrador.
Corpo:
```json
{ "nome": "Filial Caucaia", "nome_curto": "Caucaia", "matriz": false, "cnpj": "12345678000276",
  "endereco": { "cep": "61600000", "logradouro": "...", "numero": "...", "complemento": null, "bairro": "...", "cidade": "Caucaia", "uf": "CE" },
  "contato": { "telefone": null, "whatsapp": null, "email": null },
  "horario": { "seg": [ { "abre": "08:00", "fecha": "18:00" } ], "...": [] } }
```
Obrigatórios: `nome`, `endereco` (todos os campos menos `complemento`), `horario` (as 7 chaves). Opcionais: `nome_curto` (400 `{ "nome_curto": ["Use até 30 caracteres."] }` acima disso; texto vazio ou só espaços vira `null`), `preco_litro_centavos`, CNPJ, inscrições e contato.
201: representação da filial.
400 `validacao`: CNPJ com dígito errado, CEP sem 8 dígitos, UF fora da lista, horário inválido.
409 `{ "codigo": "filial_nome_em_uso", "mensagem": "Já existe uma filial com esse nome" }`.
422 `PLT-03`: limite do plano (mensagem e `detalhes` no contrato da plataforma, `exigir_limite("filiais")`).
Efeitos: se `matriz: true`, a matriz anterior deixa de ser matriz na mesma transação. A primeira filial da empresa é sempre matriz, mesmo que venha `false`. O administrador que criou a filial é ligado a ela. No assistente (Onboarding-Filial) marca o passo `filial` da implantação. Quando a filial nasce matriz, chama `plataforma.services.copiar_endereco_da_matriz(endereco)` na mesma transação: a empresa sem endereço da nota fiscal da assinatura recebe o desta filial, uma vez só (`PLT-15`, `assinatura.md`, "De onde vem o endereço"). Editar a filial, `tornar-matriz` e criar outra matriz depois não mudam o endereço da nota (CA-ASS-48). A tela do passo 6 avisa: "Este endereço também vai na nota fiscal da sua assinatura. Você muda só a nota em Administração › Assinatura."
Na criação, nenhum feriado entra: a filial nasce sem feriados, e os nacionais aparecem como sugestão em `GET /api/filiais/{id}/feriados/sugestoes/` até o administrador confirmar (`FIL-03`, CA-012-08). Nada vale antes da confirmação.
Regras: FIL-01, FIL-03, PLT-03, PLT-15.

## PATCH /api/filiais/{id}/
Perfil: administrador. Corpo: qualquer subconjunto do `POST`, menos `matriz` (use `tornar-matriz`). `endereco`, `contato` e `horario` são trocados inteiros quando enviados.
200: representação da filial. Erros iguais aos do `POST` (sem `PLT-03`).
Mudar o horário vale para as devoluções a partir de agora; o que já foi calculado não muda.
Auditoria: o `PATCH` grava `filial.editar` (categoria `configuracoes`) com `antes` e `depois` só dos campos mudados. Ex.: preço do litro de R$ 5,50 para R$ 5,90 → `"antes": { "preco_litro_centavos": 550 }`, `"depois": { "preco_litro_centavos": 590 }` (CA-FIL-03); o texto pronto é "Mudou o preço do litro" com o detalhe "Filial Centro · R$ 5,50 → R$ 5,90". Endereço e contato da filial não são dado pessoal e saem inteiros.

## POST /api/filiais/{id}/tornar-matriz/
Perfil: administrador. Corpo vazio. 200: representação. A antiga matriz deixa de ser matriz. Filial inativa → 422 `{ "codigo": "filial_inativa" }`.

## POST /api/filiais/{id}/desativar/
Perfil: administrador. Corpo: `{ motivo }`.
200: representação com `ativo: false`.
422 `FIL-06`, sempre com todos os impedimentos de uma vez:
```json
{ "codigo": "FIL-06", "mensagem": "Esta filial ainda não pode ser desativada",
  "detalhes": { "matriz": false, "ultima_filial": false,
                "operacao": { "veiculos": 3, "locacoes": 1, "caixas": 0 } } }
```
- `matriz`: escolha outra matriz antes (`tornar-matriz`). `ultima_filial`: a empresa precisa de ao menos uma ativa.
- `operacao.veiculos`: veículos fora de `vendido` e `baixado` (transfira antes, `VEI-04`); `operacao.locacoes`: locações em `rascunho`, `aguardando_retirada`, `ativa` ou `devolucao_atrasada`; `operacao.caixas`: caixa do dia `aberto` ou `aguardando_aprovacao`.
- Contas a receber em aberto e despesas a pagar **não** impedem: seguem na régua de cobrança e mantêm a filial de origem para relatório e DRE (`FIL-06`).
- Mecanismo: `veiculos`, `locacoes` e `financeiro` registram em `comum.leituras` um contador de operação por filial (ADR 0015); `filiais` soma todos e recusa com a lista completa, sem importar esses apps. Enquanto um app não existe, o contador dele vale 0.
Efeitos: a filial some do seletor de todos; `UsoEmpresa.filiais` diminui (`atualizar_uso`); os vínculos `UsuarioFilial` ficam guardados. Nada é apagado.

## POST /api/filiais/{id}/reativar/
Perfil: administrador. Corpo: `{ motivo }`. 200. 422 `PLT-03` se o plano já estiver no limite.

## Feriados (FIL-03)

Perfil: administrador (os demais veem os próximos na representação).

### GET /api/filiais/{id}/feriados/?ano=2026
200: `{ "resultados": [ { "id": 14, "data": "2026-10-12", "nome": "Nossa Senhora Aparecida", "origem": "nacional" } ] }`. `origem`: `nacional` (veio da sugestão) ou `local`.

### GET /api/filiais/{id}/feriados/sugestoes/?ano=2027
200: `{ "resultados": [ { "data": "2027-01-01", "nome": "Confraternização Universal", "ja_cadastrado": false } ] }`. Os 10 feriados nacionais de lei do ano, calculados pelo backend (datas fixas e Sexta-feira Santa, pela Páscoa), sem integração externa. Carnaval e Corpus Christi são ponto facultativo e não entram na sugestão: a filial que fecha nesses dias cadastra como feriado local.

### POST /api/filiais/{id}/feriados/
Corpo: `{ "feriados": [ { "data": "2027-01-01", "nome": "Confraternização Universal", "origem": "nacional" }, { "data": "2027-03-19", "nome": "São José", "origem": "local" } ] }`. Confirma sugestões e acrescenta locais numa chamada. 201 com a lista do ano. Data já cadastrada na filial é ignorada.

### POST /api/filiais/{id}/feriados/{feriado_id}/remover/
200. O feriado deixa de valer (`ativo = false`); devoluções já acertadas não mudam.

Feriado conta como dia fechado em `esta_aberta` e `proxima_abertura`: o atraso de `LOC-11` não corre nesses dias, e a devolução prevista para um feriado pode ser feita na abertura seguinte sem atraso.

## GET /api/enderecos/cep/{cep}/
Perfis: todos (usado também no cadastro de cliente, `CLI-01`).
200: `{ "cep": "60325000", "logradouro": "Av. Bezerra de Menezes", "bairro": "São Gerardo", "cidade": "Fortaleza", "uf": "CE" }`.
404 `{ "codigo": "cep_nao_encontrado", "mensagem": "Não achamos esse CEP. Preencha o endereço à mão." }`.
Implementado em `backend/integracoes/cep/` atrás de uma interface, com implementação falsa em desenvolvimento e testes; o provedor real é escolhido pelo backend e registrado no PR. Resposta guardada em cache por 30 dias.

---

## Interface interna para os outros apps

| Função | Uso |
| --- | --- |
| `filiais.selectors.filiais_do_usuario(usuario)` | ids das filiais ativas da pessoa (todas, para administrador). Registrada em `comum.permissoes` no `AppConfig.ready()` (`USR-07`). |
| `filiais.selectors.filtrar_por_filial(queryset, request, campo="filial")` | **o único jeito de um módulo filtrar pelo escopo de filial** (T-068, F-02 da T-064). Com uma filial, filtra por ela. Com "todas", filtra por `campo__in` com todas as filiais da empresa, ativas e desativadas (a desativada ainda tem contas e histórico, `USR-07` e `FIL-06`). Pessoa sem filial ativa e sem `X-Filial` recebe 403 `{ "codigo": "USR-07", "mensagem": "Você não tem acesso a nenhuma filial" }`. |
| `filiais.selectors.filial_da_requisicao(request)` | usada por `filtrar_por_filial`; nenhum outro app a chama (teste de arquitetura em `tests/test_permissoes_das_rotas.py`). Devolve a `Filial` do `X-Filial` (só ativa do escopo) ou `TodasAsFiliais(ids)`, nunca `None`. Sem cabeçalho, devolve a matriz, se a pessoa tem acesso a ela, ou a primeira filial dela. Sem filial nenhuma, 403 `USR-07`. `/filiais/minhas/` e `/auth/eu/` não chamam a função: continuam respondendo, com a lista vazia. |
| `comum.permissoes.com_padrao(*extras)` | permissões de uma view: as padrão (`IsAuthenticated`, `EmpresaOperando`, `EscopoDeFilial`) mais as extras. Declarar a lista à mão derruba as padrão (F-01 da T-064). |
| `filiais.selectors.esta_aberta(filial, momento) -> bool` e `proxima_abertura(filial, momento)` | `LOC-11`; consideram horário e feriados ativos (`FIL-03`). |
| `filiais.selectors.resumo_das_filiais(usuario)` | `[{id, nome, nome_curto}]` para o `eu` e para Usuários (`contas.md`), registrada em `comum.permissoes` (`resumo_das_filiais`); `nome_curto` já com o nome quando vazio (T-201). |
| `filiais.selectors.resumo_das_filiais_ativas()` | o cartão Filiais da `Configurações` (`configuracoes.md`): `ativas`, `cidades` e, com uma só, `nome` (o nome a mostrar: `nome_curto or nome`, T-201) e `cidade`. |
| assinante de `contas.filiais_do_usuario_definidas` | grava `UsuarioFilial` no convite e na edição de usuário (ver `contas.md`); `contas` não chama `filiais` direto (ADR 0011). |

## O que a filial não tem (FIL-04, FIL-05)

Decidido pelo produto em 07 out 2026 (T-037). A tela `Filial` será corrigida na T-028.

- Sem tabela de preço padrão: o preço é da categoria, da empresa ou da filial (`veiculos.md`).
- Sem vagas no pátio e sem centro de custo: a própria filial é o centro de custo da DRE (`FIN-13`).
- Sem conta de recebimento por filial: o recebimento é da empresa, numa subconta só (`plataforma.ContaPagamento`). O sistema não emite nota fiscal.
- Sem frota compartilhada e sem devolução em outra filial: a devolução é na filial da locação, e usar o veículo de outra filial exige transferência antes (`VEI-04`).

## O que muda para as tarefas (T-201)

- **T-202 (backend):** campo `Filial.nome_curto` (texto 30, vazio = `""`, migração sem preencher nada); seed com "Centro" na Filial Centro; `POST` e `PATCH` aceitam e validam (`strip`, até 30, vazio → `""`); representação com `nome_curto` (`null` quando vazio); `minhas/`, `resumo_das_filiais` e `resumo_das_filiais_ativas` com o nome a mostrar; `preco_litro_centavos` maior que 0; formatador de `filial.editar` para o preço do litro. Testes: `test_fil_01_nome_curto` (seletor "Centro", Usuários "Centro", Configurações "1 filial · Centro, Fortaleza", sem nome curto vale o nome, CA-FIL-01 e 02); `test_dev_01_preco_litro_pelo_administrador` (gerente 403, evento com antes e depois, próximo acerto com R$ 5,90, CA-FIL-03).
- **T-203 (frontend):** seletor, filiais da pessoa em `Admin-Usuarios` e Configurações pelo campo que a API manda, sem cortar "Filial "; na tela `Filial`, o campo "Nome curto" e o preço do litro no bloco Operação, só para o administrador; o horário por dia com até 2 intervalos no formato `horario` deste contrato (CA-FIL-01 a 05).
