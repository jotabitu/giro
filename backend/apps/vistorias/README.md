# app `vistorias`

**Schema:** empresa
**Escopo:** Vistoria de saída e de devolução, fotos, avarias, acerto da devolução e da caução.
**Regras:** VIS, DEV (ver `docs/regras-de-negocio.md`)
**Telas:** Vistoria, Devolucao, Vistoriador (ver `docs/telas/README.md`)

## Estrutura esperada

```
vistorias/
├── models.py       dados
├── services.py     regras e mudanças de status (único lugar que muda status)
├── selectors.py    consultas
├── api/            serializers.py, views.py, urls.py (finos)
├── tasks.py        tarefas Celery deste domínio
├── admin.py
└── tests/          test_<regra>_*.py
```

Contrato da API: `docs/api/vistorias.md` (escrito pelo arquiteto antes da implementação).

## Implementado (T-016, parte 1)

- `models.py`:
  - `Vistoria`, uma máquina de estados (`rascunho` → `concluida`, `REGRA_TRANSICAO = "transicao_vistoria"`), presa à locação e ao veículo. A correção (`VIS-04`) é uma vistoria nova com `substitui` e `motivo_correcao`; concluída, a anterior fica com `vigente=False` e guardada. Restrições: uma vigente e um rascunho por `(locacao, veiculo, tipo)`;
  - `FotoVistoria` (ativável): arquivo privado em `comum.arquivos`, reprocessado sem metadados (sem GPS). A nova foto de posição fixa deixa a anterior inativa;
  - `Avaria`: na saída, sempre `preexistente` e sem valor; na chegada, com `valor_centavos` (não do vistoriador) e `vai_para_oficina`. Fica aberta até `resolvida_em`. `ordem_servico_id` sem FK enquanto o app `manutencao` não existe.
- `services.py`:
  - `criar` e `iniciar_saida` (só `aguardando_retirada`), com a lista do ramo e os extras da locação como itens (`VIS-02`). O rascunho existente volta;
  - `editar`, `enviar_foto`, `registrar_avaria` e `remover_avaria`, só em rascunho (409 `vistoria_concluida` depois);
  - `concluir`: 422 com **todas** as pendências em `detalhes.pendencias` (`VIS-01`, `VIS-02`, `VIS-03`, `km_nao_informado`, `VEI-01` com o link de Corrigir km e, só na saída nova, `CLI-03`, `CLI-02`, `CLI-05` e `VEI-03` com `detalhes.documentos`). Conclui, atualiza o km (`VEI-02`) e, na saída, chama `locacoes.services.registrar_vistoria_saida`;
  - `corrigir` (`VIS-04`): copia os dados, as fotos (o mesmo arquivo) e as avarias.
- `selectors.py`: `representacao`, `avarias_abertas`, `avaria_aberta`, `agenda` (`VIS-05`) e `sem_valores` (o vistoriador não recebe `_centavos` nem `acerto`; aplicado depois do serializer, nas views).
- Rotas: `POST /api/locacoes/{id}/vistorias/`, `GET` e `PATCH /api/vistorias/{id}/`, `.../fotos/`, `.../avarias/` (e `DELETE .../avarias/{avaria_id}/`), `.../concluir/`, `.../corrigir/`, `GET /api/vistorias/agenda/` e `GET /api/vistorias/avarias/`.
- A devolução e o acerto (`DEV-01` a `DEV-06`) ficam com a parte 2.
