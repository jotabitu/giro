# Filiais

**Dono:** arquiteto · **Versão:** 07 out 2026 (T-030) · **App:** `filiais` (schema da empresa) · **Regras:** PLT-03, USR-07, LOC-11 (horário) · **Telas:** Filiais, Filial, Onboarding-Filial

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
  "horario": {
    "seg": [ { "abre": "08:00", "fecha": "18:00" } ], "ter": [ ... ], "qua": [ ... ], "qui": [ ... ], "sex": [ ... ],
    "sab": [ { "abre": "08:00", "fecha": "12:00" } ],
    "dom": []
  },
  "horario_resumo": "seg a sex 8h–18h · sáb 8h–12h",
  "endereco_resumo": "Av. Bezerra de Menezes, 1200 · Fortaleza, CE",
  "gerentes": [ { "id": 2, "nome": "Rodrigo Pinheiro" } ],
  "criado_em": "2026-10-07T13:00:00Z"
}
```

- `horario`: chaves `seg` a `dom`, cada dia com 0, 1 ou 2 intervalos (para quem fecha no almoço); lista vazia = fechado. Horas em `HH:MM`, no fuso `America/Sao_Paulo`. `fecha` > `abre`; intervalos do mesmo dia não se sobrepõem. É a base de `LOC-11` (devolução fora do horário).
- `horario_resumo` e `endereco_resumo` são montados pela API.
- `gerentes`: usuários ativos com perfil `gerente` ligados à filial (`UsuarioFilial`). Só leitura aqui; muda em Usuários.
- `cnpj`, inscrições e contato são opcionais.

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
- Indicadores por filial (veículos, locações ativas, usuários, ocupação) **não** vêm aqui: `filiais` está acima de `veiculos` e `locacoes` na ordem dos apps (ADR 0011). Eles virão de `GET /api/relatorios/filiais/` (contrato de relatórios, quando veículos e locações existirem). Até lá a tela mostra só os dados cadastrais.

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
Regras: PLT-03.

## PATCH /api/filiais/{id}/
Perfil: administrador. Corpo: qualquer subconjunto do `POST`, menos `matriz` (use `tornar-matriz`). `endereco`, `contato` e `horario` são trocados inteiros quando enviados.
200: representação da filial. Erros iguais aos do `POST` (sem `PLT-03`).
Mudar o horário vale para as devoluções a partir de agora; o que já foi calculado não muda.

## POST /api/filiais/{id}/tornar-matriz/
Perfil: administrador. Corpo vazio. 200: representação. A antiga matriz deixa de ser matriz. Filial inativa → 422 `{ "codigo": "filial_inativa" }`.

## POST /api/filiais/{id}/desativar/
Perfil: administrador. Corpo: `{ motivo }`.
200: representação com `ativo: false`.
422 `{ "codigo": "filial_matriz", "mensagem": "Escolha outra matriz antes de desativar esta filial" }`.
422 `{ "codigo": "ultima_filial", "mensagem": "A empresa precisa de ao menos uma filial ativa" }`.
422 (**proposta**, aguarda o produto) quando a filial ainda tem operação: `filial_com_veiculos` (veículos que não estão `vendido` nem `baixado`), `filial_com_locacoes` (locações abertas), `filial_com_caixa_aberto`. Mecanismo: o serviço publica `filiais.desativacao_solicitada` e os apps de baixo vetam levantando `ErroDeRegra` na mesma transação (ADR 0011); `filiais` não importa nenhum deles.
Efeitos: a filial some do seletor de todos; `UsoEmpresa.filiais` diminui (`atualizar_uso`); os vínculos `UsuarioFilial` ficam guardados. Nada é apagado.

## POST /api/filiais/{id}/reativar/
Perfil: administrador. Corpo: `{ motivo }`. 200. 422 `PLT-03` se o plano já estiver no limite.

## GET /api/enderecos/cep/{cep}/
Perfis: todos (usado também no cadastro de cliente, `CLI-01`).
200: `{ "cep": "60325000", "logradouro": "Av. Bezerra de Menezes", "bairro": "São Gerardo", "cidade": "Fortaleza", "uf": "CE" }`.
404 `{ "codigo": "cep_nao_encontrado", "mensagem": "Não achamos esse CEP. Preencha o endereço à mão." }`.
Implementado em `backend/integracoes/cep/` atrás de uma interface, com implementação falsa em desenvolvimento e testes; o provedor real é escolhido pelo backend e registrado no PR. Resposta guardada em cache por 30 dias.

---

## Interface interna para os outros apps

| Função | Uso |
| --- | --- |
| `filiais.selectors.filiais_do_usuario(usuario)` | ids das filiais ativas da pessoa (todas, para administrador). Base de `comum.permissoes` (`USR-07`). |
| `filiais.selectors.filial_da_requisicao(request)` | filial escolhida pelo `X-Filial` (ou `None` para "todas"). |
| `filiais.selectors.esta_aberta(filial, momento) -> bool` e `proxima_abertura(filial, momento)` | `LOC-11`. |
| `filiais.services.vincular_usuario(usuario, filiais)` | chamado por `contas` no convite e na edição de usuário. |

## Fora deste contrato (em `[divergência]` no backlog)

A tela `Filial` mostra campos que as regras não têm. Ficam de fora até o produto decidir: gerente responsável como campo próprio (aqui é derivado dos usuários), vagas no pátio, tabela de preço padrão da filial, conta de recebimento, centro de custo, "emite notas fiscais com o CNPJ desta filial", "aceita devolução de veículos de outras filiais", "compartilha a frota com as outras filiais", status "Rascunho" e o horário de feriados.
