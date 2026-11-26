"""T-517: ressalvas baixas da Segurança no link público da proposta (#650) e no Excluir (#679).

- PLT-12 de verdade na página pública da proposta: sem o recurso, 404 (o recibo fica no
  `test_t411_copiar_link`, com o cenário da devolução).
- S-15: pedir desconto muda os valores, então anula o link e solta o PDF, como o editar.
- VEN-13/AUD-06: trocar o cliente da venda apaga os PDFs de antes (têm o nome do cliente de antes).
- `comum.tasks.arquivos_apagar`: a remoção dos arquivos depois do commit, com nova tentativa.
"""

from typing import Any

import pytest
from celery.exceptions import Retry
from django.core.cache import cache

from apps.clientes import services as clientes_services
from apps.vendas.models import Venda
from apps.vendas.services import pasta_da_venda
from comum import arquivos
from comum import tasks as tarefas_comuns

from .test_t015_locacoes import cenario  # noqa: F401
from .test_t411_copiar_link import _ramo
from .test_t502_fase_1c import VENDAS, _abrir, _copiar, _enviada, _token
from .test_t502_fluxo_de_venda import _post


@pytest.fixture(autouse=True)
def _paginas_publicas_ligadas(settings):
    settings.GIRO_PROPOSTA_PUBLICA = True
    settings.GIRO_RECIBO_PUBLICO = True
    cache.clear()


def _paula() -> Any:
    return clientes_services.cadastrar(
        {
            "tipo": "pf",
            "nome": "Paula Souza",
            "documento": "52998224725",
            "celular": "85988880000",
            "email": "paula@exemplo.test",
        }
    )


# --- PLT-12 nas páginas públicas (Segurança no #650, item 2) ---


def test_plt_12_proposta_publica_sem_o_recurso_de_vendas_404(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    assert _abrir(token).status_code == 200
    _ramo("aluga")  # a empresa deixa de vender: sai `vendas_comissoes`
    recusa = _abrir(token)
    assert recusa.status_code == 404
    assert "PLT-12" not in recusa.content.decode()  # não diz o motivo
    _ramo("ambos")
    assert _abrir(token).status_code == 200


# --- S-15: pedir desconto anula o link (Segurança no #650, a) ---


def test_s_15_pedir_desconto_anula_o_link_e_solta_o_pdf(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    token = _token(_copiar(cenario, venda["id"]).json()["link"])
    assert _abrir(token).status_code == 200
    pedido = _post(cenario, venda["id"], "pedir-aprovacao", desconto_pct="8.00")
    assert pedido.status_code == 200, pedido.json()
    salva = Venda.objects.get(pk=venda["id"])
    assert salva.status == "aguardando_aprovacao"
    assert (salva.token_proposta_hash, salva.token_proposta_expira_em) == (None, None)
    assert not salva.proposta_pdf
    assert _abrir(token).status_code == 404


# --- VEN-13/AUD-06: trocar o cliente apaga os PDFs de antes (Segurança no #650, b) ---


def test_ven_13_trocar_o_cliente_apaga_os_pdfs_do_cliente_anterior(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """Os PDFs com o nome de Paula saem do armazenamento quando a venda passa para Carlos: a
    anonimização de Paula procura pelas vendas dela e não acharia esta."""
    paula = _paula()
    venda = _enviada(cenario, django_capture_on_commit_callbacks, cliente_id=paula.pk)
    primeiro = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    _copiar(cenario, venda["id"])
    do_link = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    assert primeiro.startswith(pasta_da_venda(venda["id"]))
    assert arquivos.provedor().existe(primeiro) and arquivos.provedor().existe(do_link)

    with django_capture_on_commit_callbacks(execute=True):
        editada = cenario.moto.api("Bruna").patch(
            f"{VENDAS}{venda['id']}/", {"cliente_id": cenario.cliente("Carlos").pk}, format="json"
        )
    assert editada.status_code == 200, editada.json()
    assert not arquivos.provedor().existe(primeiro)
    assert not arquivos.provedor().existe(do_link)


def test_ven_13_editar_com_o_mesmo_cliente_guarda_o_pdf(
    cenario,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    """ADR 0009: com o mesmo cliente, o PDF de antes fica guardado; só a venda deixa de apontar
    para ele."""
    venda = _enviada(cenario, django_capture_on_commit_callbacks)
    pdf = Venda.objects.get(pk=venda["id"]).proposta_pdf.name
    with django_capture_on_commit_callbacks(execute=True):
        editada = cenario.moto.api("Bruna").patch(
            f"{VENDAS}{venda['id']}/", {"desconto_pct": "4.00"}, format="json"
        )
    assert editada.status_code == 200, editada.json()
    assert not Venda.objects.get(pk=venda["id"]).proposta_pdf
    assert arquivos.provedor().existe(pdf)


# --- A remoção depois do commit (Segurança no #679, B3) ---


def test_aud_06_remocao_tenta_de_novo_quando_o_armazenamento_falha(monkeypatch):
    provedor = arquivos.provedor()
    provedor.salvar("empresa_a/clientes/documento/1/cnh.pdf", b"x", "application/pdf")
    original = provedor.apagar
    falhas: list[str] = []

    def apagar(caminho: str) -> None:
        if not falhas:
            falhas.append(caminho)
            raise OSError("armazenamento fora do ar")
        original(caminho)

    monkeypatch.setattr(type(provedor), "apagar", lambda self, caminho: apagar(caminho))
    caminho = "empresa_a/clientes/documento/1/cnh.pdf"
    argumentos: tuple[str, list[str], list[str]] = ("empresa_a", [caminho], [])
    # A falha agenda a nova tentativa (`Retry`): no worker, 60 s depois, até 12 vezes, com espera
    # crescente até 1 hora.
    with pytest.raises(Retry):
        tarefas_comuns.arquivos_apagar.apply(args=argumentos)
    assert falhas and provedor.existe(caminho)
    assert tarefas_comuns.arquivos_apagar.apply(args=argumentos).get() == 1  # a nova tentativa
    assert not provedor.existe("empresa_a/clientes/documento/1/cnh.pdf")


@pytest.mark.parametrize(
    ("caminhos", "pastas"),
    [
        (["empresa_b/clientes/documento/1/cnh.pdf"], []),  # outra empresa
        (["empresa_a/../empresa_b/x.pdf"], []),
        ([], ["empresa_a/"]),  # o prefixo inteiro é só da AUD-08
        ([], ["empresa_a/vendas/"]),
    ],
)
def test_aud_06_remocao_so_dentro_da_empresa(caminhos, pastas):
    """Recusa sem nova tentativa (`dont_autoretry_for`)."""
    with pytest.raises(ValueError):
        tarefas_comuns.arquivos_apagar.apply(args=("empresa_a", caminhos, pastas))


def test_aud_06_remocao_nao_derruba_a_resposta(monkeypatch, caplog):
    """Se nem agendar der certo, o erro vai ao log e quem pediu segue."""

    def falha(*_: Any, **__: Any) -> None:
        raise ConnectionError("fila fora do ar")

    monkeypatch.setattr(tarefas_comuns.arquivos_apagar, "delay", falha)
    tarefas_comuns._agendar("empresa_a", ["empresa_a/clientes/documento/1/cnh.pdf"], [])
    assert "Remoção de arquivos não agendada" in caplog.text
