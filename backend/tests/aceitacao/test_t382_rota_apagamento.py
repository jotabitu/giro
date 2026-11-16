"""T-382 · A tarefa do apagamento da empresa cancelada vai para a fila própria, lida só pelo worker
que recebe a `DATABASE_URL_MIGRACAO` (M-01 da T-355, T-352, ADR 0025). Desde a ADR 0040 (T-477) a
fila se chama `banco` e leva também a criação da empresa. AUD-08."""

from config.celery import app
from config.settings import base


def _fila(tarefa: str) -> str:
    return str(app.amqp.router.route({}, tarefa)["queue"].name)


def test_aud_08_apagar_empresas_vai_para_a_fila_banco() -> None:
    assert _fila("aud_08_apagar_empresas") == "banco"


def test_aud_08_outras_tarefas_ficam_na_fila_padrao() -> None:
    padrao = str(app.conf.task_default_queue)
    assert padrao == "celery"
    # Só as tarefas da fila `banco` mudam: o aviso de 7 dias e as demais seguem na padrão.
    assert _fila("aud_08_avisar_apagamento") == padrao
    assert _fila("plataforma_gerar_faturas") == padrao


def test_aud_08_agenda_nao_fixa_fila_por_fora_da_rota() -> None:
    """O Beat usa o nome da tarefa e a rota decide a fila; `queue` na agenda mudaria o destino."""
    entrada = base.CELERY_BEAT_SCHEDULE["aud_08_apagar_empresas"]
    assert entrada["task"] == "aud_08_apagar_empresas"
    assert "options" not in entrada
    assert base.CELERY_TASK_ROUTES["aud_08_apagar_empresas"] == {"queue": "banco"}
    assert all(rota == {"queue": "banco"} for rota in base.CELERY_TASK_ROUTES.values())
