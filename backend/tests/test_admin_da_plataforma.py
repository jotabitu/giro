"""Django Admin da plataforma (ADR 0029, T-277): só o `createsuperuser` dá `is_staff`.

O Admin lê o `public` inteiro e só deixa entrar quem tem `is_staff` (`contas.login_admin`).
Dar `is_staff` é ato do Dono pela linha de comando no servidor: nenhum serviço, nenhuma rota.
"""

import json
from pathlib import Path

from drf_spectacular.generators import SchemaGenerator

from apps.contas.models import Usuario

RAIZ = Path(__file__).resolve().parent.parent
PASTAS_DE_CODIGO = ("apps", "comum", "config")
# Quem cita `is_staff` fora de testes e migrações, e quantas vezes: o campo e o
# `create_superuser` (contas/models.py) e a porta do Admin, que só lê (contas/login_admin.py).
CITAM_IS_STAFF = {"apps/contas/models.py": 2, "apps/contas/login_admin.py": 1}


def test_t277_is_staff_so_pelo_createsuperuser():
    citacoes = {}
    for pasta in PASTAS_DE_CODIGO:
        for arquivo in sorted((RAIZ / pasta).rglob("*.py")):
            relativo = arquivo.relative_to(RAIZ).as_posix()
            if "/migrations/" in relativo:
                continue
            vezes = arquivo.read_text(encoding="utf-8").count("is_staff")
            if vezes:
                citacoes[relativo] = vezes
    assert citacoes == CITAM_IS_STAFF

    assert Usuario._meta.get_field("is_staff").default is False

    # Nenhuma rota da API lê ou grava `is_staff`.
    esquema = SchemaGenerator(urlconf="config.urls_openapi").get_schema(request=None, public=True)
    assert "is_staff" not in json.dumps(esquema)
