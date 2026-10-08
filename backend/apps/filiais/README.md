# app `filiais`

**Schema:** empresa
**Escopo:** Filiais, matriz, horário de funcionamento.
**Regras:** PLT-03 (limite) (ver `docs/regras-de-negocio.md`)
**Telas:** Filiais, Filial, Onboarding-Filial (ver `docs/telas/README.md`)

## Estrutura esperada

```
filiais/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/filiais.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-012)

- `models.py`: `Filial` (nome único sem diferenciar maiúsculas, uma matriz só por restrição no banco), `FeriadoFilial`, `UsuarioFilial`.
- `services.py`: `criar_filial` (primeira é matriz; quem criou fica ligado; `exigir_limite` e `atualizar_uso` na mesma transação; marca o passo `filial` da implantação), `editar_filial`, `tornar_matriz` (trava as filiais para nunca haver duas matrizes), `desativar` (FIL-06, todos os impedimentos de uma vez), `reativar` (PLT-03), `confirmar_feriados`, `remover_feriado`, `definir_filiais_do_usuario`.
- `calendario.py`: feriados nacionais de lei (com a Sexta-feira Santa pela Páscoa), validação e resumo do horário, cálculo de aberta e próxima abertura.
- `selectors.py`: `filiais_do_usuario`, `resumo_das_filiais` (`[{id, nome}]` para o `eu` de contas, registrada em `comum.permissoes`, T-011), `filial_da_requisicao`, `esta_aberta`, `proxima_abertura` (interface para os outros apps), representação e lista.
- `api/`: `/api/filiais/` (lista com `plano` e `indicadores`, criação), `/minhas/`, `/{id}/`, `tornar-matriz`, `desativar`, `reativar`, feriados e sugestões; `/api/enderecos/cep/{cep}/` (`integracoes/cep`, `GIRO_PROVEDOR_CEP` = `falso` ou `viacep`).

## Para os outros apps

- Filtrar pelo escopo de filial (`USR-07`): só com `selectors.filtrar_por_filial(queryset, request, campo="filial")`. Ninguém lê `filial_da_requisicao` e filtra por conta própria (teste de arquitetura em `tests/test_permissoes_das_rotas.py`). "Todas" é `TodasAsFiliais`, com ids das ativas e das desativadas, e nunca `None`. Pessoa sem filial recebe 403 `USR-07`.
- Na T-011, quem tem `relatorios_todas_filiais` só pode receber "todas" em painel e relatórios. A view marca isso (por exemplo, um atributo que `EscopoDeFilial` lê), para "todas" não valer em qualquer módulo.
- Permissões de view: `comum.permissoes.com_padrao(exige_perfil(...))`, nunca a lista à mão (F-01 da T-064).

- Operação que impede desativar (FIL-06): no `ready()`, `comum.leituras.registrar_contador("filiais.Filial", "veiculos" | "locacoes" | "caixas", contar)`, com `contar(filial_id) -> int`.
- Indicadores da lista: `comum.leituras.registrar_anotacao("filiais.Filial", "indicadores", anotar, montar)`, devolvendo `veiculos`, `locacoes_ativas` ou `ocupacao_pct`.
- Vínculo das pessoas: `contas` publica `contas.filiais_do_usuario_definidas` (`usuario_id`, `filiais_ids`); `filiais` assina e grava.

## Eventos assinados

| Evento | O que faz |
| --- | --- |
| `contas.filiais_do_usuario_definidas` | troca as filiais da pessoa (`UsuarioFilial`) |
