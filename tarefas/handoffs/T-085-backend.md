# T-085 · AUT-06 gera tarefa urgente para veículo reservado ou em manutenção · backend → orquestrador, qa

**O que foi feito (`VEI-03`, `AUT-06`, `FIL-02`, regra da T-084):**
- No dia em que vence o CRLV ou o seguro, a `aut_06_vencimento_de_documentos` trata o veículo `reservado` e o `em_manutencao` como o `alugado`: o status não muda, e os gerentes da filial recebem uma tarefa urgente.
- A tarefa diz a placa e o documento, por exemplo "CRLV da RHT9F02 venceu com o veículo reservado. Regularize o documento.".
- O `tipo` da notificação passou a ser `documento_vencido_<status>`: `documento_vencido_alugado`, `documento_vencido_reservado` ou `documento_vencido_em_manutencao`.
- Continua idempotente, pela mesma `chave` por documento. IPVA e rastreador só recebem o alerta de 30 dias, sem tarefa urgente.
- A recusa da retirada (CA-016-21) não entrou: fica para a T-016.

**Onde:**
- `backend/apps/veiculos/services.py` (`EM_USO_NO_VENCIMENTO` e `aplicar_vencimento_de_documentos`) e o `README.md`.
- `docs/api/veiculos.md` (a linha da `AUT-06` em "Eventos e interface interna").
- Teste: `test_vei_03_aut_06_ca_013_28_reservado_ou_em_manutencao_no_vencimento`.

**Check:**
- Ruff, `ruff format --check`, mypy e `makemigrations --check` limpos.
- Pytest: `400 passed, 17 xfailed`. Antes eram 399 e 17, na main sem a T-083.
- O OpenAPI foi regerado com `--validate`, sem aviso e sem mudança.
- Rodei no Postgres descartável, com `--rm` e `POSTGRES_HOST`.

**Ponto em aberto que já está nas regras:** a manutenção concluída com CRLV ou seguro vencido ("Pontos em aberto", padrão A) entra com o app `manutencao`.

**Próximo passo para quem recebe:**
- **QA:** o CA-013-28 está coberto.
- **Backend (T-016):** a vistoria de saída recusa a retirada com CRLV ou seguro vencido. Use `veiculos.services.documentos_vencidos_que_bloqueiam(veiculo, hoje)`.
