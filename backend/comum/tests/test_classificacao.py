"""Classificação dos campos na auditoria (ADR 0014, item 3)."""

import json
from datetime import date
from types import SimpleNamespace

import pytest
from django.db import models

from apps.auditoria.models import EventoAuditoria
from apps.contas.models import Usuario
from comum import classificacao
from comum.auditoria import Categoria, auditar
from comum.classificacao import (
    OMITIDO,
    mascarar_cnh,
    mascarar_documento,
    mascarar_email,
    mascarar_ip,
    mascarar_nascimento,
    mascarar_nome,
    mascarar_telefone,
)
from tests.app_exemplo.models import Pessoa


def test_mascaras_da_adr_0014():
    assert mascarar_documento("123.218.330-45") == "***.218.330-**"
    assert mascarar_documento("12.345.678/0001-90") == "12345678000190"
    assert mascarar_cnh("01234561234") == "*******1234"
    assert mascarar_nome("Larissa Souza") == "L. S."
    assert mascarar_nascimento(date(1994, 3, 12)) == "1994"
    assert mascarar_telefone("(85) 98765-1234") == "(85) *****-1234"
    assert mascarar_telefone("+55 85 98765-1234") == "(85) *****-1234"
    assert mascarar_email("larissa@gmail.com") == "l***@g***.com"
    assert mascarar_ip("200.150.10.77") == "200.150.10.0/24"


def test_aud_06_auditoria_de_pessoa_nao_guarda_nome_nem_documento_completos(empresa_a):
    pessoa = Pessoa(
        nome="Larissa Souza",
        celular="(85) 98765-1234",
        email="larissa@gmail.com",
        nascimento=date(1994, 3, 12),
        endereco="Rua das Flores, 120",
        cidade="Fortaleza",
        uf="CE",
    )
    with auditar(pessoa, "pessoa.criar", Categoria.OPERACAO):
        pessoa.definir_documento("123.218.330-45")
        pessoa.definir_cnh_numero("01234561234")
        pessoa.save()

    evento = EventoAuditoria.objects.get(acao="pessoa.criar")
    texto = json.dumps(evento.depois)
    for proibido in ("Larissa", "Souza", "12321833045", "218.330", "98765", "larissa@", "Flores"):
        assert proibido not in texto
    assert evento.depois["documento"] == OMITIDO
    assert evento.depois["documento_hash"] == OMITIDO
    assert evento.depois["cnh_numero"] == OMITIDO
    assert evento.depois["nome"] == "L. S."
    assert evento.depois["celular"] == "(85) *****-1234"
    assert evento.depois["email"] == "l***@g***.com"
    assert evento.depois["nascimento"] == "1994"
    assert evento.depois["endereco"] == "***"
    assert evento.depois["cidade"] == "Fortaleza"
    assert evento.depois["uf"] == "CE"


def test_aud_01_troca_de_documento_cifrado_gera_evento_sem_valor(empresa_a):
    pessoa = Pessoa(nome="Larissa Souza")
    pessoa.definir_documento("123.218.330-45")
    pessoa.save()
    with auditar(pessoa, "pessoa.editar", Categoria.OPERACAO):
        pessoa.definir_documento("999.218.330-11")
        pessoa.save()
    evento = EventoAuditoria.objects.get(acao="pessoa.editar")
    assert evento.antes == {}
    assert evento.depois == {"documento": OMITIDO, "documento_hash": OMITIDO}


def test_aud_01_troca_de_senha_nao_grava_hash(empresa_a):
    usuario = Usuario.objects.create_user("carla@a.com", "senha-antiga-123", nome="Carla", perfil="gerente")
    with auditar(usuario, "usuario.trocar_senha", Categoria.SEGURANCA):
        usuario.set_password("senha-nova-456")
        usuario.save()
    evento = EventoAuditoria.objects.get(acao="usuario.trocar_senha")
    assert evento.antes == {}
    assert evento.depois == {"password": OMITIDO}
    assert usuario.password not in json.dumps(evento.depois)


def test_email_do_funcionario_vai_inteiro(empresa_a):
    usuario = Usuario.objects.create_user("carla@a.com", "x", nome="Carla", perfil="gerente")
    with auditar(usuario, "usuario.editar", Categoria.CONFIGURACOES):
        usuario.email = "carla.menezes@a.com"
        usuario.save()
    evento = EventoAuditoria.objects.get(acao="usuario.editar")
    assert evento.depois == {"email": "carla.menezes@a.com"}


def _falso(nome: str, campos: list[str], declarado: dict) -> type:
    """Classe com `_meta` mínimo; não registra model no Django."""
    lista = []
    for campo_nome in campos:
        campo = models.CharField(max_length=20)
        campo.set_attributes_from_name(campo_nome)
        lista.append(campo)
    return type(nome, (), {"_meta": SimpleNamespace(concrete_fields=lista), "CAMPOS_AUDITORIA": declarado})


def test_classificacao_recusa_campo_inexistente_e_mascara_desconhecida():
    errado = _falso("Errado", ["celular"], {"mascarar": ["nao_existe"]})
    with pytest.raises(ValueError, match="inexistente"):
        classificacao.classificacao(errado)  # type: ignore[arg-type]

    mascara = _falso("Mascara", ["celular"], {"mascarar": {"celular": "borrar"}})
    with pytest.raises(ValueError, match="desconhecida"):
        classificacao.classificacao(mascara)  # type: ignore[arg-type]


def test_campo_sensivel_sem_classificacao_e_apontado():
    falso = _falso("SemClassificar", ["celular", "tipo", "nome_contato"], {})
    assert classificacao.campos_sensiveis_sem_classificacao(falso) == ["celular"]  # type: ignore[arg-type]


def test_mascarar_em_lista_deduz_o_tipo_pelo_nome():
    falso = _falso("Lista", ["responsavel_cpf", "telefone_fixo"], {"mascarar": ["responsavel_cpf", "telefone_fixo"]})
    regras = classificacao.classificacao(falso)  # type: ignore[arg-type]
    assert regras.mascarar == {"responsavel_cpf": "documento", "telefone_fixo": "telefone"}
