# Filiais

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-030) · **App:** `filiais` (schema da empresa) · **Regras:** FIL-01 a FIL-06, PLT-03, USR-07, LOC-11 · **Telas:** Filiais, Filial, Onboarding-Filial

Convenções gerais em `docs/api/README.md`. Modelo em `docs/decisoes/modelo-de-dados.md` (item 6).

## Quem pode

| Ação | Administrador | Gerente | Vendedor | Vistoriador | Financeiro |
| --- | --- | --- | --- | --- | --- |
| Ver as próprias filiais (seletor) | todas | as suas | as suas | as suas | as suas |
| Administrar filiais (listar todas, criar, editar, desativar) | sim | — | — | — | — |

"Administração (marca, filiais, usuários, ...)" é só do administrador na tabela de perfis. Fora do escopo da pessoa, a filial responde 404.

## Representação da filial

```json
{
  "id": 1,
  "nome": "Filial Centro",
  "matriz": true,
  "ativo": true,
  "cnpj": "12345678000110",
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
- `preco_litro_centavos`: preço da bomba usado no acerto da devolução (`DEV-01`); opcional, editado no `PATCH`. Sem ele, o combustível do acerto é informado à mão.

---

## GET /api/filiais/minhas/
Perfis: todos.
Para o seletor de filial do topo do menu (`USR-07`). Sem paginação.
200:
```json
{
  "pode_escolher_todas": true,
  "resultados": [ { "id": 1, "nome": "Filial Centro", "matriz": true, "cidade": "Fortaleza", "uf": "CE" } ]
}
```
- Só filiais ativas e ligadas à pessoa. Administrador recebe todas as ativas e `pode_escolher_todas: true` ("Todas as filiais").
- A filial escolhida vai nas próximas requisições pelo cabeçalho `X-Filial: <id>` (ou `X-Filial: todas`, só para quem pode). Sem o cabeçalho, a API usa a matriz, se a pessoa tiver acesso a ela, ou a primeira filial da pessoa. Filial fora do escopo no cabeçalho → 403 `{ "codigo": "USR-07", "mensagem": "Você não tem acesso a esta filial" }`. A regra vale para todos os módulos com filial e é aplicada por `comum.permissoes`.

## GET /api/filiais/
Perfil: administrador.
Query: `?ativo=true|false` (padrão: todas), `?busca=` (nome, cidade).
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
Perfil: administrador. 200: representação da filial.

## POST /api/filiais/
Perfil: administrador.
Corpo:
```json
{ "nome": "Filial Caucaia", "matriz": false, "cnpj": "12345678000200",
  "endereco": { "cep": "61600000", "logradouro": "...", "numero": "...", "complemento": null, "bairro": "...", "cidade": "Caucaia", "uf": "CE" },
  "contato": { "telefone": null, "whatsapp": null, "email": null },
  "horario": { "seg": [ { "abre": "08:00", "fecha": "18:00" } ], "...": [] } }
```
Obrigatórios: `nome`, `endereco` (todos os campos menos `complemento`), `horario` (as 7 chaves).
201: representação da filial.
400 `validacao`: CNPJ com dígito errado, CEP sem 8 dígitos, UF fora da lista, horário inválido.
409 `{ "codigo": "filial_nome_em_uso", "mensagem": "Já existe uma filial com esse nome" }`.
422 `PLT-03`: limite do plano (mensagem e `detalhes` no contrato da plataforma, `exigir_limite("filiais")`).
Efeitos: se `matriz: true`, a matriz anterior deixa de ser matriz na mesma transação. A primeira filial da empresa é sempre matriz, mesmo que venha `false`. O administrador que criou a filial é ligado a ela. No assistente (Onboarding-Filial) marca o passo `filial` da implantação.
Na criação, os feriados nacionais do ano corrente e do seguinte já entram confirmados; o administrador ajusta depois.
Regras: FIL-01, FIL-03, PLT-03.

## PATCH /api/filiais/{id}/
Perfil: administrador. Corpo: qualquer subconjunto do `POST`, menos `matriz` (use `tornar-matriz`). `endereco`, `contato` e `horario` são trocados inteiros quando enviados.
200: representação da filial. Erros iguais aos do `POST` (sem `PLT-03`).
Mudar o horário vale para as devoluções a partir de agora; o que já foi calculado não muda.

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
200: `{ "resultados": [ { "data": "2027-01-01", "nome": "Confraternização Universal", "ja_cadastrado": false } ] }`. Feriados nacionais de lei do ano, calculados pelo backend (datas fixas e Sexta-feira Santa, pela Páscoa), sem integração externa.

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
| `filiais.selectors.filial_da_requisicao(request)` | filial escolhida pelo `X-Filial` (ou `None` para "todas"). |
| `filiais.selectors.esta_aberta(filial, momento) -> bool` e `proxima_abertura(filial, momento)` | `LOC-11`; consideram horário e feriados ativos (`FIL-03`). |
| assinante de `contas.filiais_do_usuario_definidas` | grava `UsuarioFilial` no convite e na edição de usuário (ver `contas.md`); `contas` não chama `filiais` direto (ADR 0011). |

## O que a filial não tem (FIL-04, FIL-05)

Decidido pelo produto em 07 out 2026 (T-037). A tela `Filial` será corrigida na T-028.

- Sem tabela de preço padrão: o preço é da categoria, da empresa ou da filial (`veiculos.md`).
- Sem vagas no pátio e sem centro de custo: a própria filial é o centro de custo da DRE (`FIN-13`).
- Sem conta de recebimento por filial: o recebimento é da empresa, numa subconta só (`plataforma.ContaPagamento`). O sistema não emite nota fiscal.
- Sem frota compartilhada e sem devolução em outra filial: a devolução é na filial da locação, e usar o veículo de outra filial exige transferência antes (`VEI-04`).
