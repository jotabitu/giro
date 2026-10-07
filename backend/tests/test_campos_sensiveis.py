"""Teste de arquitetura da ADR 0014, item 3: todo campo com nome sensível está classificado."""

from django.apps import apps

from comum.campos import CampoCifrado, CampoHashBusca
from comum.classificacao import campos_sensiveis_sem_classificacao, classificacao
from comum.models import ModeloComCifra

PACOTES_DO_GIRO = ("apps.", "comum.", "tests.")


def _models_do_giro():
    return [m for m in apps.get_models() if m.__module__.startswith(PACOTES_DO_GIRO)]


def test_ha_models_para_conferir():
    assert len(_models_do_giro()) >= 5


def test_todo_campo_sensivel_esta_classificado():
    faltando = {
        m._meta.label: campos for m in _models_do_giro() if (campos := campos_sensiveis_sem_classificacao(m))
    }
    assert not faltando, f"Classifique em CAMPOS_AUDITORIA: {faltando}"


def test_classificacao_de_todos_os_models_e_valida():
    for modelo in _models_do_giro():
        classificacao(modelo)


def test_campo_cifrado_so_em_modelo_com_cifra():
    errados = [
        f"{m._meta.label}.{c.name}"
        for m in _models_do_giro()
        for c in m._meta.concrete_fields
        if isinstance(c, CampoCifrado) and not issubclass(m, ModeloComCifra)
    ]
    assert not errados


def test_hash_de_busca_aponta_para_campo_cifrado_do_mesmo_model():
    errados = []
    for modelo in _models_do_giro():
        cifrados = {c.name for c in modelo._meta.concrete_fields if isinstance(c, CampoCifrado)}
        for campo in modelo._meta.concrete_fields:
            if isinstance(campo, CampoHashBusca) and campo.de not in cifrados:
                errados.append(f"{modelo._meta.label}.{campo.name} → {campo.de}")
    assert not errados
