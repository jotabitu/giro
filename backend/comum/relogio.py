"""Relógio do domínio: o único lugar onde serviços e selectors leem "agora" e "hoje".

Os testes congelam a data de referência (07 out 2026) trocando `agora` por monkeypatch, sem
dependência nova. Datas sem hora (vencimento, teste grátis) são o dia em America/Sao_Paulo.
"""

from datetime import date, datetime

from django.utils import timezone


def agora() -> datetime:
    return timezone.now()


def hoje() -> date:
    return timezone.localdate(agora())
