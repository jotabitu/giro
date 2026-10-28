"""T-369 · Pedido do titular pela equipe Giro (AUD-06, M-03 da T-355).

Os comandos `exportar_titular` e `anonimizar_titular` atendem o titular até a tela da fase 2:
só o Dono da plataforma, com motivo, e sempre com o evento na auditoria da empresa e na da
plataforma.
"""

import io
import json
import os
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django_tenants.utils import schema_context
from PIL import Image

from apps.auditoria.models import EventoAuditoria
from apps.clientes import selectors, services
from apps.clientes.models import Cliente, DocumentoCliente
from apps.contas.models import Usuario
from comum import arquivos
from comum.campos import buscar_por_hash

CPF = "52998224725"
CNH = "01234567890"
MOTIVO = "Chamado 4521: pedido do titular"


def _jpg() -> SimpleUploadedFile:
    saida = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(saida, format="JPEG")
    return SimpleUploadedFile("cnh.jpg", saida.getvalue(), content_type="image/jpeg")


@pytest.fixture
def equipe(empresa_a):
    with schema_context("public"):
        dono = Usuario.objects.create_user(
            "dono@giro.test",
            "senha-longa-2026",
            nome="Ana Dono",
            funcao_plataforma="dono",
            status="ativo",
        )
        suporte = Usuario.objects.create_user(
            "suporte@giro.test",
            "senha-longa-2026",
            nome="Beto Suporte",
            funcao_plataforma="suporte",
            status="ativo",
        )
    return {"dono": dono, "suporte": suporte}


@pytest.fixture
def lucas(empresa_a):
    cliente = services.cadastrar(
        {
            "tipo": "pf",
            "nome": "Lucas Ferreira",
            "documento": CPF,
            "celular": "85988887777",
            "email": "lucas@exemplo.test",
            "nascimento": "1998-02-14",
            "endereco": {
                "cep": "60000000",
                "logradouro": "Rua A",
                "numero": "10",
                "bairro": "Centro",
                "cidade": "Fortaleza",
                "uf": "CE",
            },
            "referencia": {"nome": "Maria", "parentesco": "mãe", "telefone": "85977776666"},
            "cnh": {"numero": CNH, "categoria": "A", "validade": "2030-01-10"},
        }
    )
    services.enviar_documento(cliente, "cnh_frente", _jpg())
    return cliente


def _exportar(empresa, cliente, saida: Path, dono: str = "dono@giro.test") -> None:
    call_command(
        "exportar_titular",
        empresa.schema_name,
        str(cliente.pk),
        "--dono",
        dono,
        "--motivo",
        MOTIVO,
        "--saida",
        str(saida),
    )


def _anonimizar(empresa, cliente, confirmacao: str = "Lucas Ferreira", dono="dono@giro.test"):
    call_command(
        "anonimizar_titular",
        empresa.schema_name,
        str(cliente.pk),
        "--dono",
        dono,
        "--motivo",
        MOTIVO,
        "--confirmacao",
        confirmacao,
    )


def _eventos_da_plataforma(acao: str):
    with schema_context("public"):
        return list(EventoAuditoria.objects.filter(acao=acao).values("motivo", "depois"))


def test_aud_06_exportar_titular_entrega_os_dados_completos_e_audita(
    empresa_a, equipe, lucas, tmp_path
):
    saida = tmp_path / "lucas.zip"
    _exportar(empresa_a, lucas, saida)

    with zipfile.ZipFile(saida) as zipado:
        dados = json.loads(zipado.read("dados.json"))
        assert dados["cliente"]["nome"] == "Lucas Ferreira"
        assert dados["cliente"]["documento"] == CPF  # decifrado para o titular
        assert dados["cliente"]["cnh_numero"] == CNH
        assert "documento_hash" not in dados["cliente"]
        (documento,) = dados["documentos"]
        assert documento["tipo"] == "cnh_frente"
        assert zipado.read(documento["arquivo"])[:2] == b"\xff\xd8"  # o JPEG
        assert {"locacoes", "contratos", "contas_receber", "reembolsos"} <= dados.keys()
    if os.name != "nt":
        assert saida.stat().st_mode & 0o777 == 0o600

    evento = EventoAuditoria.objects.get(acao="cliente.exportar_titular")
    assert (evento.ator_tipo, evento.ator_nome) == ("suporte", "Equipe Giro: Ana Dono")
    assert (evento.motivo, evento.regra, evento.objeto_id) == (MOTIVO, "AUD-06", lucas.pk)
    assert _eventos_da_plataforma("empresa.exportar_titular") == [
        {"motivo": MOTIVO, "depois": {"cliente_id": lucas.pk}}
    ]
    # Não sobrescreve um arquivo que já existe.
    with pytest.raises(CommandError, match="já existe"):
        _exportar(empresa_a, lucas, saida)


def test_aud_06_anonimizar_titular_apaga_dados_e_arquivos_e_audita(empresa_a, equipe, lucas):
    caminho = DocumentoCliente.objects.get(cliente=lucas).arquivo.name
    assert arquivos.provedor().existe(caminho)

    _anonimizar(empresa_a, lucas)

    cliente = Cliente.objects.get(pk=lucas.pk)
    assert cliente.anonimizado_em is not None
    assert cliente.nome == "Cliente anonimizado"
    assert (cliente.documento_claro(), cliente.cnh_numero_claro()) == ("", "")
    assert (cliente.celular, cliente.email, cliente.nascimento) == ("", "", None)
    assert (cliente.logradouro, cliente.cidade, cliente.referencia_nome) == ("", "", "")
    assert not Cliente.objects.filter(documento_hash=buscar_por_hash(CPF)).exists()
    assert cliente.status == "incompleto"  # sem CPF nem documento (CLI-03)
    documento = DocumentoCliente.objects.get(cliente=lucas)
    assert (documento.ativo, documento.arquivo.name or None) == (False, None)
    assert not arquivos.provedor().existe(caminho)

    evento = EventoAuditoria.objects.get(acao="cliente.anonimizar_titular")
    assert (evento.ator_tipo, evento.motivo, evento.regra) == ("suporte", MOTIVO, "AUD-06")
    assert "Lucas" not in json.dumps(evento.antes) and CPF not in json.dumps(evento.antes)
    assert EventoAuditoria.objects.filter(acao="documento_cliente.anonimizar_titular").exists()
    assert _eventos_da_plataforma("empresa.anonimizar_titular") == [
        {"motivo": MOTIVO, "depois": {"cliente_id": lucas.pk}}
    ]
    # O CPF fica livre para um cadastro novo, e não se anonimiza duas vezes.
    services.cadastrar(
        {"tipo": "pf", "nome": "Lucas Ferreira", "documento": CPF, "celular": "85988887777"}
    )
    with pytest.raises(CommandError, match="já foi anonimizado"):
        _anonimizar(empresa_a, lucas, confirmacao="Cliente anonimizado")


def test_aud_06_titular_so_pelo_dono_com_motivo_e_confirmacao(empresa_a, equipe, lucas, tmp_path):
    with pytest.raises(CommandError, match="Só o Dono"):
        _anonimizar(empresa_a, lucas, dono="suporte@giro.test")  # AUD-09
    with pytest.raises(CommandError, match="Só o Dono"):
        _exportar(empresa_a, lucas, tmp_path / "x.zip", dono="ninguem@giro.test")
    with pytest.raises(CommandError, match="nome do cliente"):
        _anonimizar(empresa_a, lucas, confirmacao="Lucas")
    with pytest.raises(CommandError):
        call_command(
            "anonimizar_titular",
            empresa_a.schema_name,
            str(lucas.pk),
            "--dono",
            "dono@giro.test",
            "--motivo",
            " ",
            "--confirmacao",
            "Lucas Ferreira",
        )
    assert Cliente.objects.get(pk=lucas.pk).anonimizado_em is None
    assert not (tmp_path / "x.zip").exists()
    assert not EventoAuditoria.objects.filter(acao__endswith="_titular").exists()


def test_aud_06_anonimizar_recusa_cliente_com_pendencia(empresa_a, equipe, lucas, monkeypatch):
    monkeypatch.setattr(
        selectors,
        "pendencias_para_inativar",
        lambda cliente: {"locacao_aberta": True, "em_aberto_centavos": 0, "venda_aberta": False},
    )
    with pytest.raises(CommandError, match="locação, venda ou valor em aberto"):
        _anonimizar(empresa_a, lucas)
    assert Cliente.objects.get(pk=lucas.pk).nome == "Lucas Ferreira"
    assert DocumentoCliente.objects.get(cliente=lucas).arquivo


def test_aud_06_titular_recusa_empresa_apagada_e_cliente_de_outra(empresa_a, equipe, lucas):
    from apps.plataforma.models import Empresa

    with schema_context("public"):
        empresa_b = Empresa.objects.get(schema_name="empresa_b")
        Empresa.objects.filter(pk=empresa_b.pk).update(apagada_em="2026-10-01T00:00:00Z")
    with pytest.raises(CommandError, match="apagados"):
        _anonimizar(empresa_b, lucas)
    with schema_context("public"):
        Empresa.objects.filter(pk=empresa_b.pk).update(apagada_em=None)
    # O id do cliente da A não existe na B: nada cruza empresas.
    with pytest.raises(CommandError, match="não encontrado"):
        _anonimizar(empresa_b, lucas)
    assert Cliente.objects.get(pk=lucas.pk).anonimizado_em is None
