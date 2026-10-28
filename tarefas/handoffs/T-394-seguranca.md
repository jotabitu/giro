# T-394 · Prévia do contrato limpa depois de preencher (B-01 da T-388) · segurança → orquestrador

Feita pela segurança no lugar do Backend.

**O que foi feito:**
- `apps/contratos/services.py`: `previa` devolve agora `sanitizacao.limpar(marcadores.substituir(...))`.
- A prévia deixa de depender de todo texto gravado ter passado por `_texto_limpo`. Um texto que entre no banco por migração, seed ou script de suporte sai limpo na tela da T-363, que põe o HTML na página (S-09).
- O texto que já estava limpo sai igual. A tabela de parcelas usa só tags da lista e também não muda.

**Testes:**
- `test_s_09_previa_limpa_texto_gravado_sem_sanitizar`, em `tests/aceitacao/test_t090_contratos.py`: grava o texto por `update()`, com `<img src=x onerror=alert(1)>`. A prévia pela API sai sem `<img` e sem `onerror`, igual a `<p>Lucas Ferreira</p>`.
- `test_modelos_api_lista_marcadores_prontos_e_previa` continua passando.
- `test_t090_contratos.py`, `test_t263_gerar_contrato.py` e `apps/contratos`: 24 passed.
- ruff, ruff format e mypy: sem erro.

**Fora desta tarefa:** a mesma limpeza em `versao_texto_html` na geração do contrato, que só vai ao PDF (opcional no relatório da T-388), não foi feita.

**Próximo passo:** o orquestrador revisa e abre o PR.
