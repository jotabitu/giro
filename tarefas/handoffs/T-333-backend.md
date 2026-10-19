# T-333 · WeasyPrint 70 · backend → devops, qa

**O que foi feito:** `weasyprint` sobe de `>=66,<70` (instalada a 69.0) para `>=70,<71` (70.0), que corrige a PYSEC-2026-3940 e a PYSEC-2026-4311 levantadas pelo `pip-audit` na T-328. Nenhuma mudança de código: `apps/contratos/pdf.py` (`HTML(...).write_pdf()`, `URLFetcherResponse` no `url_fetcher`) segue igual na 70.

**Onde:** `backend/requirements.txt`.

**Conferência:**
- `pip-audit -r requirements.txt`: "No known vulnerabilities found".
- PDFs iguais: o mesmo contrato (60 cláusulas, logo SVG, página de registro da assinatura e uma imagem como as fotos do recibo) gerado pela 69.0 e pela 70.0 tem as mesmas 4 páginas, os mesmos tamanhos, o mesmo texto extraído pelo pypdf e as mesmas imagens por página. Os bytes mudam (versão e data no metadado do PDF), como já mudavam entre gerações.
- Testes: `test_t090_contratos.py`, `test_t263_gerar_contrato.py`, `test_t016_vistorias.py` (recibo), `test_t148_decisoes_t017.py`, `test_t185b_forma_faturas.py` e `comum/tests/test_arquivos.py`, 128 passando com a 70 num contêiner descartável.

**Para o devops:** reconstruir a imagem do backend (a `giro-backend:latest` de teste ainda tem a 69.0). A 70 avisa no log: "Using fontTools instead of HarfBuzz-Subset ... Please install HarfBuzz-Subset >= 4.1.0". Funciona sem ele, mas vale pôr `libharfbuzz-subset0` em `infra/docker/backend.Dockerfile` (e no passo "Dependências do sistema (WeasyPrint)" do `ci.yml`) na mesma reconstrução.

**O que ficou de fora:** nada.
