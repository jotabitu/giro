"""Cifra e hash de busca (ADR 0014, item 2)."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.forms import modelform_factory
from django.test import override_settings
from django.utils import timezone

from apps.auditoria.models import EventoAuditoria
from apps.plataforma.models import Empresa
from comum import cripto
from comum.auditoria import Categoria, auditar
from comum.campos import anonimizar_cifrado, buscar_por_hash
from comum.classificacao import OMITIDO
from tests.app_exemplo.models import Credencial, Pessoa

CPF = "123.218.330-45"
CHAVE_1 = "1:" + "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="
CHAVE_2 = "2:" + "MzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzMzM="


@pytest.fixture(autouse=True)
def _cache_de_chaves_limpo():
    cripto.limpar_cache_de_chaves()
    yield
    cripto.limpar_cache_de_chaves()


def _pessoa(**campos) -> Pessoa:
    pessoa = Pessoa(nome=campos.pop("nome", "Larissa Souza"), **campos)
    pessoa.definir_documento(CPF)
    return pessoa


def test_cifra_e_decifra_no_formato_com_id_da_chave(empresa_a):
    pessoa = _pessoa()
    assert pessoa.documento.startswith("v1:")
    assert CPF not in pessoa.documento
    pessoa.save()
    pessoa.refresh_from_db()
    assert pessoa.documento_claro() == CPF


def test_cifra_antes_do_primeiro_save(empresa_a):
    pessoa = _pessoa()
    assert pessoa.pk is None
    assert pessoa.documento_claro() == CPF


def test_cifrado_copiado_para_outra_linha_nao_decifra(empresa_a):
    origem = _pessoa()
    origem.save()
    destino = Pessoa(nome="Rafael Lima")
    destino.documento = origem.documento
    with pytest.raises(cripto.ErroDeCifra):
        destino.documento_claro()


def test_cifrado_copiado_para_outro_campo_nao_decifra(empresa_a):
    pessoa = _pessoa()
    pessoa.cnh_numero = pessoa.documento
    with pytest.raises(cripto.ErroDeCifra):
        pessoa.cnh_numero_claro()


def test_cifrado_copiado_para_outra_empresa_nao_decifra(empresa_a):
    origem = _pessoa()
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    copia = Pessoa(nome="Larissa Souza", id_cifra=origem.id_cifra, documento=origem.documento)
    with pytest.raises(cripto.ErroDeCifra):
        copia.documento_claro()


def test_cifrado_adulterado_nao_decifra(empresa_a):
    pessoa = _pessoa()
    prefixo, corpo = pessoa.documento.split(":", 1)
    trocado = "A" if corpo[20] != "A" else "B"
    pessoa.documento = f"{prefixo}:{corpo[:20]}{trocado}{corpo[21:]}"
    with pytest.raises(cripto.ErroDeCifra):
        pessoa.documento_claro()


@pytest.mark.parametrize("valor", ["v1:AAAA", "v1:" + "A" * 36, "v1:@@@@"])
def test_r05_cifrado_truncado_ou_invalido_e_erro_de_cifra(empresa_a, valor):
    """R-05 da T-050: nonce curto não vira ValueError genérico (erro 500)."""
    pessoa = _pessoa()
    pessoa.documento = valor
    with pytest.raises(cripto.ErroDeCifra):
        pessoa.documento_claro()


def test_r05_definir_o_mesmo_valor_nao_gera_alterado_falso(empresa_a):
    pessoa = _pessoa()
    pessoa.save()
    cifrado = pessoa.documento
    with auditar(pessoa, "pessoa.editar", Categoria.OPERACAO):
        pessoa.definir_documento(CPF)
        pessoa.save()
    assert pessoa.documento == cifrado
    evento = EventoAuditoria.objects.filter(acao="pessoa.editar").latest("id")
    assert "documento" not in evento.depois


def test_troca_de_chave_sem_migracao_em_massa(empresa_a):
    with override_settings(GIRO_CHAVE_DADOS_PESSOAIS=CHAVE_1):
        cripto.limpar_cache_de_chaves()
        antiga = _pessoa()
    with override_settings(GIRO_CHAVE_DADOS_PESSOAIS=f"{CHAVE_1},{CHAVE_2}"):
        cripto.limpar_cache_de_chaves()
        assert antiga.documento_claro() == CPF
        assert cripto.precisa_recifrar(antiga.documento, tipo=cripto.DADOS_PESSOAIS)
        nova = _pessoa()
        assert nova.documento.startswith("v2:")
    with override_settings(GIRO_CHAVE_DADOS_PESSOAIS=CHAVE_2):
        cripto.limpar_cache_de_chaves()
        with pytest.raises(cripto.ErroDeCifra):
            antiga.documento_claro()


def test_dados_pessoais_e_segredos_usam_chaves_separadas(empresa_a):
    credencial = Credencial(descricao="Asaas")
    credencial.definir_chave_api_cifrada("chave-secreta-asaas")
    pessoa = _pessoa()
    # Mesmo trocando o cifrado de campo, a chave errada não abre.
    with override_settings(GIRO_CHAVE_SEGREDOS=CHAVE_2):
        cripto.limpar_cache_de_chaves()
        with pytest.raises(cripto.ErroDeCifra):
            credencial.chave_api_cifrada_claro()
    cripto.limpar_cache_de_chaves()
    assert credencial.chave_api_cifrada_claro() == "chave-secreta-asaas"
    assert pessoa.documento_claro() == CPF


def test_sem_empresa_na_conexao_nao_cifra(publico):
    connection.tenant = None
    try:
        with pytest.raises(cripto.ErroDeCifra):
            Pessoa(nome="X").definir_documento(CPF)
    finally:
        connection.set_schema_to_public()


def test_hash_ignora_mascara_e_muda_por_empresa(empresa_a):
    assert cripto.hash_busca(CPF) == cripto.hash_busca("12321833045")
    assert len(cripto.hash_busca(CPF)) == 64
    assert cripto.hash_busca(CPF, empresa_id=1) != cripto.hash_busca(CPF, empresa_id=2)


def test_cli_01_cpf_unico_pelo_hash(empresa_a):
    _pessoa().save()
    repetida = Pessoa(nome="Outra")
    repetida.definir_documento("12321833045")
    with pytest.raises(IntegrityError), transaction.atomic():
        repetida.save()


def test_cli_01_mesmo_cpf_em_outra_empresa_pode(empresa_a):
    _pessoa().save()
    connection.set_tenant(Empresa.objects.get(schema_name="empresa_b"))
    _pessoa().save()
    assert Pessoa.objects.count() == 1


def test_busca_exata_pelo_hash(empresa_a):
    _pessoa().save()
    assert Pessoa.objects.filter(documento_hash=buscar_por_hash("123 218 330 45")).exists()


def test_aud_06_anonimizar_apaga_o_cifrado_e_troca_o_hash(empresa_a):
    pessoa = _pessoa()
    pessoa.save()
    hash_antigo = pessoa.documento_hash
    anonimizar_cifrado(pessoa, "documento")
    pessoa.anonimizado_em = timezone.now()
    pessoa.save()
    pessoa.refresh_from_db()
    assert pessoa.documento == ""
    assert pessoa.documento_claro() == ""
    assert pessoa.documento_hash != hash_antigo
    assert len(pessoa.documento_hash or "") == 64
    # O CPF fica livre para um novo cadastro.
    _pessoa(nome="Nova").save()


def test_claro_nunca_aparece_em_str_repr_e_formulario(empresa_a):
    pessoa = _pessoa()
    assert CPF not in str(pessoa) and CPF not in repr(pessoa)
    formulario = modelform_factory(Pessoa, fields="__all__")
    assert "documento" not in formulario.base_fields
    assert "documento_hash" not in formulario.base_fields


def test_conta_pagamento_chave_nao_aparece_em_formulario_e_auditoria(empresa_a):
    credencial = Credencial(descricao="Asaas")
    with auditar(credencial, "credencial.criar", Categoria.CONFIGURACOES):
        credencial.definir_chave_api_cifrada("chave-secreta-asaas")
        credencial.save()
    evento = EventoAuditoria.objects.get(acao="credencial.criar")
    assert evento.depois["chave_api_cifrada"] == OMITIDO
    assert "chave-secreta-asaas" not in str(evento.antes) + str(evento.depois)
    assert credencial.chave_api_cifrada not in str(evento.depois)
    formulario = modelform_factory(Credencial, fields="__all__")
    assert "chave_api_cifrada" not in formulario.base_fields
    assert "chave-secreta-asaas" not in repr(credencial)


def test_id_cifra_e_imutavel(empresa_a):
    import uuid

    pessoa = _pessoa()
    pessoa.save()
    pessoa.id_cifra = uuid.uuid4()
    with pytest.raises(ValueError, match="id_cifra"):
        pessoa.save()


def test_copiar_par_id_cifra_e_cifrado_para_outra_linha_e_recusado(empresa_a):
    origem = _pessoa()
    origem.save()
    copia = Pessoa(nome="Rafael Lima", id_cifra=origem.id_cifra, documento=origem.documento)
    with pytest.raises(IntegrityError), transaction.atomic():
        copia.save()
