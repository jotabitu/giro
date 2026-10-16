"""Gunicorn de homologação e produção (T-258; ADR 0026).

Uso: gunicorn -c infra/docker/gunicorn.conf.py config.wsgi:application
O desenvolvimento segue no `runserver`. Tudo se ajusta por variável de ambiente.

Por que gthread: a leitura do CRLV-e e da CNH-e (ADR 0026) segura a requisição por até 8 s de
relógio, esperando o processo filho. Com workers síncronos, cada leitura prenderia um worker
inteiro. Com threads, o worker segue atendendo as outras rotas.

Sobre o timeout: no gthread o `timeout` não corta uma requisição lenta, só mata o worker que
parou de avisar o mestre (documentação do Gunicorn). O corte por requisição é do proxy
(`proxy_read_timeout` em infra/proxy/giro.conf.template: 20 s nas rotas de leitura, 60 s no
resto). Mesmo assim o valor fica acima de 8 s com folga, para que trocar a classe de worker
por `sync` não passe a matar a leitura.
"""

import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
worker_class = "gthread"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# 30 s é 3,75 vezes os 8 s da leitura (filho com 8 s, mais ler o corpo, validar e gravar).
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

# Recicla o worker de tempos em tempos, com jitter para não reiniciarem juntos.
max_requests = 1000
max_requests_jitter = 100

# O arquivo de controle do worker em memória evita travar o heartbeat em disco lento (contêiner).
worker_tmp_dir = "/dev/shm"

# Logs na saída padrão; o proxy já registra o acesso.
accesslog = None
errorlog = "-"
