# T-388 · Prévia do modelo de contrato sem HTML do cliente · segurança → orquestrador, backend, frontend

**O que foi feito:** conferi no backend o caminho da prévia (`POST /api/contratos/modelos/{id}/previa/`) que a tela da T-363 (PR #407) põe na página por `dangerouslySetInnerHTML`. Conferi também a tela `/assinar`. Relatório: `docs/seguranca/2026-10-26-t388-previa-contrato.md`. Nenhum código mudou.
**Resultado:** nenhum HTML do cliente chega à tela, e o PR #407 pode seguir.
- O texto é limpo com `nh3` ao salvar, sem atributos, então um marcador nunca fica em atributo nem em nome de tag.
- Cada valor é escapado com `html.escape` ao preencher.
- A tabela de parcelas é montada pelo sistema, com valores escapados.
- A `/assinar` só abre o PDF por link.
- A CSP sem `unsafe-inline` é uma terceira camada.

**Testes rodados:**
- Sonda fora do repositório, com 5 cargas (`<script>`, `onerror`, `onload`, marcador dentro do valor, entidade), pelo serviço e pela API com locação real. O `HTMLParser` só achou tags da lista e nenhum atributo: 2 passed.
- `test_t090_contratos.py` e `test_t263_gerar_contrato.py`: 23 passed.

**Ambiente:** o `giro-backend-pg` não subia depois que o Docker reiniciou, porque a porta 55432 do host caiu na faixa reservada do Windows (55350–55449, `netsh int ipv4 show excludedportrange protocol=tcp`). Testei num Postgres descartável meu (`--rm`, sem porta no host), já desligado. No fim, o `giro-backend-pg` já estava recriado por outra pessoa, e o antigo ficou como `giro-backend-pg-antigo`. Para a porta não voltar a cair na reserva: `net stop winnat` e `net start winnat`, como administrador, ou trocar a porta do host para fora das faixas.

**Achado:** B-01, baixa, defesa em profundidade. **Tarefa sugerida para o backend (sem número):**
- **O quê:** `services.previa` limpa de novo a saída com `sanitizacao.limpar`, para não depender de todo texto gravado já estar limpo.
- **Pronto quando:** `test_s_09_previa_limpa_texto_gravado_sem_sanitizar` passa, com o texto gravado por `update()` contendo `<img onerror>` e a prévia pela API sem `<img` nem `onerror`; e `test_modelos_api_lista_marcadores_prontos_e_previa` continua passando.
- **Prioridade:** sem urgência.

**Próximo passo:** o orquestrador decide se numera o B-01. Para o frontend, nada a mudar.
