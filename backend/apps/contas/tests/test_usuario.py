"""Usuário nos dois schemas (ADR 0008, item 1)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.contas.models import Usuario


def test_superusuario_do_public_e_dono_da_plataforma(publico):
    usuario = Usuario.objects.create_superuser("dono@giro.com", "senha-forte-123", nome="Dono")
    assert usuario.funcao_plataforma == "dono"
    assert usuario.perfil == ""


def test_superusuario_da_empresa_e_administrador(empresa_a):
    usuario = Usuario.objects.create_superuser("adm@a.com", "senha-forte-123", nome="Adm")
    assert usuario.perfil == "administrador"
    assert usuario.funcao_plataforma == ""


def test_usuario_da_empresa_nao_recebe_funcao_da_plataforma(empresa_a):
    with pytest.raises(ValidationError):
        Usuario.objects.create_user("x@a.com", "x", nome="X", funcao_plataforma="suporte")


def test_usuario_do_public_nao_recebe_perfil_de_locadora(publico):
    with pytest.raises(ValidationError):
        Usuario.objects.create_user("x@giro.com", "x", nome="X", perfil="gerente")


def test_banco_exige_exatamente_um_dos_dois(empresa_a):
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.create(email="sem@a.com", nome="Sem")
    with pytest.raises(IntegrityError), transaction.atomic():
        Usuario.objects.create(
            email="dois@a.com", nome="Dois", perfil="gerente", funcao_plataforma="dono"
        )


def test_senha_guardada_com_hash_e_email_minusculo(empresa_a):
    usuario = Usuario.objects.create_user(
        "Carla@A.com", "senha-forte-123", nome="Carla", perfil="gerente"
    )
    assert usuario.email == "carla@a.com"
    assert usuario.check_password("senha-forte-123")
    assert "senha-forte-123" not in usuario.password


@pytest.mark.parametrize(
    ("status", "ativo"), [("ativo", True), ("convite_pendente", False), ("desativado", False)]
)
def test_usr_04_is_active_segue_o_status(empresa_a, status, ativo):
    usuario = Usuario(email="x@a.com", nome="X", perfil="vendedor", status=status)
    assert usuario.is_active is ativo


def test_usr_04_status_so_muda_pela_maquina(empresa_a):
    from comum.estados import MudancaDeStatusForaDaMaquina, transicionar

    usuario = Usuario.objects.create_user("x@a.com", "senha-forte-123", nome="X", perfil="gerente")
    with pytest.raises(MudancaDeStatusForaDaMaquina):
        Usuario.objects.filter(pk=usuario.pk).update(status="desativado")
    transicionar(usuario, "desativado")
    usuario.refresh_from_db()
    assert usuario.status == "desativado"
