"""Relógio do domínio: o único lugar onde serviços e selectors leem "agora" e "hoje".

Os testes congelam a data de referência (07 out 2026) trocando `agora` por monkeypatch, sem
dependência nova. Datas sem hora (vencimento, teste grátis) são o dia em America/Sao_Paulo.

No desenvolvimento, `GIRO_DATA_REFERENCIA` (ADR 0021) fixa o dia e mantém a hora real de São
Paulo: o que depende da hora (bloqueio do login, expiração de tokens) continua andando. Em
produção, homologação e testes ela é sempre `None`.
"""

from datetime import date, datetime

from django.conf import settings
from django.utils import timezone


def data_de_referencia() -> date | None:
    data: date | None = getattr(settings, "GIRO_DATA_REFERENCIA", None)
    return data


def agora() -> datetime:
    real = timezone.now()
    data = data_de_referencia()
    if data is None:
        return real
    local = timezone.localtime(real)  # America/Sao_Paulo
    return local.replace(year=data.year, month=data.month, day=data.day)


def hoje() -> date:
    return timezone.localdate(agora())
