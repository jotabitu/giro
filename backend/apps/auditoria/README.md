# app `auditoria`

**Schema:** empresa + public
**Escopo:** Eventos imutáveis, consulta da auditoria, exportação de dados, anonimização LGPD, retenção após cancelamento.
**Regras:** AUD (ver `docs/regras-de-negocio.md`)
**Telas:** Admin-Auditoria, Plat-Auditoria, Admin-Exportar (ver `docs/telas/README.md`)

Contrato da API: `docs/api/auditoria.md`. Critérios: `docs/qa/criterios/T-018.md`.

## Estrutura

```
auditoria/
├── models.py       EventoAuditoria (imutável, ADR 0010 e 0016) e Exportacao (AUD-07)
├── banco.py        permissões dos papéis de banco (giro_app, giro_expurgo)
├── textos.py       `resumo` e `detalhe` prontos de cada ação
├── selectors.py    filtros da consulta, representação e pessoas do filtro
├── services.py     exportação: pedido, geração do CSV, expiração e download
├── tasks.py        auditoria_exportar
└── api/            serializers.py, views.py, urls.py (finos)
```

## Como funciona

- **Gravar:** sempre por `comum.auditoria` (`auditar`, `registrar_evento`) ou pela máquina de estados. `ocorrido_em` vem de `comum.relogio`.
- **Ler:** só o schema da conexão. Na empresa, `GET /api/auditoria/eventos/` (administrador; suporte 403 `PLT-07`); no public, `GET /api/plataforma/auditoria/eventos/` (view no app `plataforma`, só o dono).
- **Textos:** o app dono de uma ação pode registrar o formatador dela com `comum.auditoria.registrar_formatador(acao, funcao)`. Sem formatador, valem os de `textos.py` e, por fim, o genérico "<verbo> <objeto> <código>".
- **Dados de outros apps** sem importá-los (ADR 0011): `comum.auditoria.registrar_consulta` com `filiais` (filiais), `acessos_suporte` (plataforma) e `emails_de_usuarios` (contas).
- **Exportação:** por enquanto só `auditoria` em `csv` (ver a `[decisão]` da T-018 no backlog). O arquivo fica no storage privado; o link é `GET /api/exportacoes/{id}/baixar/` (302 para URL de 15 min); depois de 7 dias, 410 e o arquivo sai do storage.
