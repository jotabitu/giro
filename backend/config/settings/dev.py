from datetime import date

from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *  # noqa: F403
from config.settings.base import env

DEBUG = True

# ADR 0021: data de referência do relógio do domínio (AAAA-MM-DD). Vazia ou ausente = desligada;
# fora do formato, o processo não sobe.
_data_de_referencia = env("GIRO_DATA_REFERENCIA", default="").strip()
try:
    GIRO_DATA_REFERENCIA = date.fromisoformat(_data_de_referencia) if _data_de_referencia else None
except ValueError as erro:
    raise ImproperlyConfigured(
        f"GIRO_DATA_REFERENCIA fora do formato AAAA-MM-DD: {_data_de_referencia!r}."
    ) from erro

# T-210: com o armazenamento "falso", as URLs das fotos apontam para a própria API (mesma origem).
GIRO_ARQUIVOS_FALSOS_BASE = "/api/arquivos-dev"

# T-218: pasta (volume do compose) onde o armazenamento "falso" guarda as fotos, para elas
# sobreviverem ao reinício do backend. Vazia ou ausente = memória, como nos testes.
GIRO_ARQUIVOS_FALSOS_DIRETORIO = env("GIRO_ARQUIVOS_FALSOS_DIRETORIO", default="").strip()
