# T-258 · Timeout do servidor para a leitura de PDF e cofre do deploy · devops → orquestrador, backend, segurança

Branch `t-258-timeout-leitura-pdf`, **empilhada sobre a `origin/t-247-adr-leitura-pdf`** (PR #250). Mesclar o #250 antes.

**O que foi feito:**
- `infra/docker/gunicorn.conf.py` (novo): `gthread`, 2 workers e 4 threads por padrão (variáveis `GUNICORN_*`), `timeout` de 30 s (3,75 vezes os 8 s da leitura), reciclagem de worker. Carregado e conferido com `gunicorn --check-config`.
- `infra/proxy/giro.conf.template`: rota própria para `/api/veiculos/leitura-crlv/` e `/api/clientes/leitura-cnh/` (corpo de 3 MB, 20 s de leitura e envio, 20 requisições por minuto por IP com rajada de 5). O resto de `/api/` fica como estava (60 s, 12 MB).
- `infra/README.md`: seções "Servidor da aplicação e leitura de PDF" e "Cofre do deploy depois da T-157" (o que preencher em cada ambiente).
- `infra/deploy/*.env.example`: comentário do que preencher no cofre (as quatro variáveis da T-157 já estavam lá) e as três `GUNICORN_*`.
- Quadro: seção da T-258 no backlog e linha em `em-andamento.md`.

**Verificação:** `nginx -t` passa (1,27). Com um servidor de mentira atrás do proxy: corpo de 2,8 MB passa na rota de leitura; 4 MB dá 413 nela e na da CNH-e; 4 MB passa em `/api/veiculos/`; 13 MB dá 413; passada a rajada, 429. Só configuração e documento, nenhum teste de backend para rodar.

**Descoberta:** o Gunicorn não existe no repositório (nem em `requirements.txt`, nem no Dockerfile, que roda `runserver`). A T-258 entregou a configuração; a imagem de produção fica para o deploy. O `timeout` do Gunicorn é global e, no `gthread`, não corta requisição lenta: o corte por rota é do proxy. Está explicado no README.

**O que ficou de fora:**
- Adicionar `gunicorn` ao `requirements.txt` e à imagem: dependência de infraestrutura, pede ADR de deploy (e motivo no PR).
- **Memória e workers são estimativa.** O parser da leitura ainda não existe; só medi o worker de desenvolvimento parado (cerca de 140 MiB). Números de 2 GiB (homologação) e 4 GiB (produção) assumem 2 a 5 leituras simultâneas. Rever com o RSS de pico do filho num CRLV-e e numa CNH-e fictícios.
- Rede fechada para o processo filho (pergunta 1 da segurança na ADR 0026): espera a resposta.
- O `nginx` continua suposição até a ADR de deploy.

**Pedidos ao backend:**
1. Limitar leituras simultâneas por processo (semáforo de 2, 429 ou 503 quando cheio): fecha o teto de memória, que sem isso é workers vezes threads vezes 512 MB.
2. Travar no `prod.py` os `S3_*` em branco (hoje o processo sobe e o erro só aparece na primeira foto); `GIRO_ARMAZENAMENTO=s3` já é conferido.

**Próximo passo para quem recebe:** orquestrador abre o PR (depois do #250); segurança confere se 20 s e 3 MB na borda servem; backend lê os dois pedidos acima.
