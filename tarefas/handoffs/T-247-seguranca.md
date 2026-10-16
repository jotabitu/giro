# T-247 · Revisão da leitura do CRLV-e e da CNH-e por PDF · seguranca → orquestrador, arquiteto, backend, devops

**O que foi feito:** revisão da ADR 0026 e dos contratos do PR #250 (as duas rotas, mesmo com a CNH-e na fase 2) e da borda da T-258 (PR #256). Só documento: ainda não há código da leitura. Conferido na imagem do backend que `python -I -m <pacote>` não acha o pacote e que o `sentry-sdk` 2.72 captura as variáveis locais por padrão.
**Onde:** `docs/seguranca/2026-10-16-t247-leitura-pdf.md`.
**Regras cobertas:** VEI-08, CLI-11, CLI-01, CLI-03, PLT-07, AUD-04, AUD-05, AUD-06, AUD-09.
**Achados (nenhum alto):**
- M-01: o filho herda o ambiente com todas as chaves; passar `env` mínimo.
- M-02: `preexec_fn` não é seguro no Gunicorn `gthread`; o filho aplica os próprios limites antes de importar o `pypdf`.
- M-03 (devops): o Sentry leva as variáveis locais (o CPF lido); `include_local_variables=False`, junto com o B-01 da T-189.
- M-04: `pypdf>=5.1` admite versões com DoS corrigido; mínimo pelo `pip-audit`.
- B-01 a B-06: `-I` por caminho, endurecimento do filho, validação da saída no pai, chave própria do comprovante, `cnh_digital` no `AUD-06`, salvar confere de novo o arquivo.
**Respostas:** às 7 perguntas do arquiteto e às 6 do produto, no relatório. Rede fechada do filho: não é condição do MVP, desde que o filho não tenha chaves e o Postgres e o Redis tenham senha; com contêiner próprio no futuro, `network_mode: none`. Suporte: 403 `PLT-07` na CNH-e; CRLV-e só com "ver e editar". Borda da T-258: serve.
**Testes:** nenhum: não há código. Os testes que a tarefa do backend precisa estão em cada achado.
**O que ficou de fora:** a ADR continua "proposta" até o arquiteto pôr nela M-01, M-02, M-04, B-01 e B-04 (ela é do arquiteto; não editei). O catálogo de marcas e modelos não é de segurança.
**Próximo passo para quem recebe:** orquestrador numera as tarefas (arquiteto: ajuste da ADR; devops: Sentry e senhas; os do backend entram na tarefa do CRLV-e); arquiteto ajusta a ADR e marca "aceita".
