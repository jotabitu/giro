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

## Implementado (T-109, devolução e acerto)

- `models.py`: `Devolucao` (uma por locação, `rascunho` → `concluida`, `REGRA_TRANSICAO = "transicao_devolucao"`), com a caução, o saldo (positivo devolve, negativo cobra), a forma de devolver, o preço do litro congelado ao encerrar, `devolvida_em` (LOC-11) e o recibo em PDF (armazenamento privado). Filho `ItemAcerto`: `tipo`, `natureza` (`cobranca` ou `credito`), `modo` (`calculado` ou `informado`), `avaria` e `conta_id` (a parcela em aberto).
- `acerto.py`: contas puras. Combustível = capacidade do tanque × (nível da saída − nível da chegada) × preço do litro da filial + R$ 10,00 uma vez, só quando falta (`DEV-01`); sem tanque, sem preço ou sem a saída, o item vira `informado`. O texto e o botão do resultado (`devolver`, `cobrar`, `zerado`).
- `services.py`:
  - `iniciar_devolucao` (locação `ativa` ou `devolucao_atrasada`; a existente volta, `DEV-05`) cria a chegada por `criar(locacao, "devolucao", ...)`;
  - `recalcular`, chamado a cada leitura e mudança enquanto o acerto é rascunho: combustível, atraso (`locacoes.services.calcular_atraso` na conclusão da chegada), km excedente (0, km livre), parcelas vencidas e não pagas, multa e crédito do encerramento antecipado aprovado (`LOC-12`, `LOC-13`) e um item por avaria nova da chegada. O valor informado pela pessoa fica;
  - `incluir_item` (avaria ou multa de trânsito), `editar_item` e `remover_item` (409 `item_calculado` nos calculados; 409 `acerto_concluido` depois de encerrar) e `definir_forma`;
  - `encerrar_devolucao`, numa transação: 422 `vistoria_pendente` sem a chegada concluída; cobranças pagas com a caução por `financeiro.services.pagar_com_caucao`; saldo positivo vira `Reembolso` (`devolver_ao_cliente`), negativo vira conta `acerto` em 3 dias (`DEV-02`); `locacoes.services.encerrar` (`encerrada` ou `cancelada`); km e veículo `disponivel` ou `em_manutencao` com "vai para oficina" (`DEV-04`); publica `vistorias.devolucao_encerrada` (com `avarias_para_oficina`, para o app `manutencao` abrir a OS) e agenda o recibo;
  - recibo: `url_do_recibo` (gera o PDF se faltar), `reenviar_recibo`.
- `recibo.py`: o HTML do recibo com a marca da locadora e as fotos da chegada (endereços internos `giro-imagem:<id>` em `contratos.pdf`).
- `tasks.py`: `vistorias_enviar_recibo` (idempotente; o reenvio força) manda o link de 15 minutos por WhatsApp.
- Rotas: `POST /api/locacoes/{id}/devolucao/`, `GET /api/devolucoes/{id}/`, `PATCH .../acerto/`, `POST .../acerto/itens/`, `PATCH` e `DELETE .../acerto/itens/{item_id}/`, `POST .../encerrar/`, `GET .../recibo/` e `POST .../recibo/reenviar/`. Abrir e ver: quem faz vistoria (o vistoriador sem valores); acerto, encerrar e recibo: administrador, gerente e vendedor.
