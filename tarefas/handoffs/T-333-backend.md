# T-333 · WeasyPrint 70 · backend → devops, qa

**O que foi feito:** `weasyprint` sobe de `>=66,<70` (instalada a 69.0) para `>=70,<71` (70.0), que corrige a PYSEC-2026-3940 e a PYSEC-2026-4311 levantadas pelo `pip-audit` na T-328.

**Correção depois da imagem nova (19 out 2026):** a 70 exige que o `url_fetcher` seja uma instância de `URLFetcher` (lê `_fail_on_errors` nele), e a função do `apps/contratos/pdf.py` quebrou o `test_s_09_pdf_nao_busca_url_externa`. `buscador()` passa a devolver uma subclasse de `URLFetcher` cujo `fetch` nunca chama o da classe-mãe: só entrega o logo da empresa e as imagens internas, recusa todo o resto com `UrlRecusada` antes de abrir conexão, e a recusa vira aviso sem parar o PDF (`fail_on_errors=False`), como antes. A S-09 não mudou: `http`, `https`, `file`, `data` e o endereço do logo sem logo seguem recusados, e o teste confere de novo pelo `HTML(...).write_pdf()`. O espião do teste também virou `URLFetcher`.

**Erro meu na primeira entrega:** o handoff dizia que 128 testes tinham passado com a 70. No contêiner daquela conferência, o `pip install -r requirements.txt` não rodou (um passo anterior falhou e o `&&` o pulou), então os testes rodaram na 69. A comparação dos PDFs foi refeita à parte e essa, sim, rodou nas duas versões.

**Onde:** `backend/requirements.txt`, `backend/apps/contratos/pdf.py`, `backend/tests/aceitacao/test_t090_contratos.py`.

**Conferência:**
- `pip-audit -r requirements.txt`: "No known vulnerabilities found".
- PDFs iguais: o mesmo contrato (60 cláusulas, logo SVG, página de registro da assinatura e uma imagem como as fotos do recibo) gerado pela 69.0 e pela 70.0 tem as mesmas 4 páginas, os mesmos tamanhos, o mesmo texto extraído pelo pypdf e as mesmas imagens por página. Os bytes mudam (versão e data no metadado do PDF), como já mudavam entre gerações.
- Testes na imagem nova (WeasyPrint 70.0 conferida com `pip show`): `test_t090_contratos.py`, `test_t091_locacao_fim.py`, `test_t263_gerar_contrato.py`, `test_t016_vistorias.py` (recibo) e `apps/contratos`, 100 passando. ruff, ruff format --check e mypy limpos.

**Para o devops:** imagem reconstruída com `libharfbuzz-subset0` na branch `t-333-harfbuzz-subset` (o aviso "Using fontTools instead of HarfBuzz-Subset" da 70).

**O que ficou de fora:** nada.
