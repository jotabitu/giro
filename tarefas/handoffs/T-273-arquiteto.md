# T-273 · ADR 0026 pela revisão da segurança · arquiteto → backend, devops, orquestrador

**O que foi feito:** a ADR 0026 passou de proposta a aceita com os achados da revisão da segurança (`docs/seguranca/2026-10-16-t247-leitura-pdf.md`, PR #265).
**Onde:** `docs/decisoes/0026-leitura-de-documentos-em-pdf.md`, `docs/decisoes/README.md`, `docs/api/veiculos.md`, `docs/api/clientes.md`.
**Na ADR:**
- M-01 (item 4): o filho recebe só `PATH` e `LANG`, com `close_fds`, `stderr=DEVNULL` e `start_new_session`. Nenhuma chave no processo.
- M-02 (item 4): sem `preexec_fn`. O `trabalhador.py` aplica a si mesmo `RLIMIT_CPU` 5 s, `RLIMIT_AS` 512 MB, `RLIMIT_FSIZE` 0, `RLIMIT_NOFILE` baixo e `RLIMIT_CORE` 0, antes de importar o `pypdf`. O pai mata o grupo nos 8 s.
- M-04 (item 3): sai o `>=5.1,<7`. A versão mínima é a mais nova sem aviso no `pip-audit` quando o backend começar, e sobe a cada aviso. O CI falha o PR com aviso no `pypdf`.
- B-01 (item 4): o filho é chamado como `sys.executable -I <caminho absoluto de trabalhador.py> <tipo>`, sem `-m` e sem tirar o `-I`. O trabalhador põe só o próprio diretório no `sys.path`.
- B-04 (item 8): o resumo usa `HMAC(GIRO_PEPPER_HMAC, "leitura-documento")` como chave e leva o SHA-256 do arquivo junto. O comprovante leva o `schema` e o usuário, e o salvar trata o de outra empresa ou de outra pessoa como ausente.
- Também atualizados pela revisão: a rede fechada não é condição do MVP (item 5), o Sentry sem variáveis locais no projeto inteiro (item 9, M-03 com o devops), o suporte confirmado (item 10), o semáforo e as recusas no limite (item 6), e o B-06 no salvar. Os testes estão em Consequências.
**Nos contratos:**
- `veiculos.md`: suporte só em "ver e editar"; 503 `leitura_ocupada`; recusas contam no 429; comprovante de outra empresa ou pessoa vira ausente; arquivo conferido de novo e `Content-Type` fixo.
- `clientes.md`: suporte com 403 nos dois modos (confirmado), os mesmos 503 e 429, o comprovante e o B-05 (`cnh_digital` no `AUD-06`).
**O que ficou de fora:** o código (T-265, backend), o M-03 no Sentry (T-270, devops) e as senhas do Postgres e do Redis (T-274, devops). A ADR cita a ADR 0027 (Gunicorn `gthread`), que está na branch da T-264, ainda não mesclada.
**Próximo passo para quem recebe:** o backend segue os itens 3, 4, 6, 8 e 9 e os testes de Consequências na T-265.
