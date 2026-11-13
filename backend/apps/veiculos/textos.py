"""Textos prontos da auditoria para as ações de `veiculos` (`auditoria.md`, T-201).

Registrados no `ready()` por `comum.auditoria.registrar_formatador`.
"""

from datetime import date
from typing import Any

from django.utils import timezone

from comum.auditoria import Texto
from comum.dinheiro import formatar_reais
from comum.documentos import placa_com_hifen

from .models import Categoria, Veiculo

# Na ordem do texto: diária, semanal, (quinzenal,) mensal e caução.
PERIODOS = (
    ("diaria_centavos", "diária"),
    ("semanal_centavos", "semanal"),
    ("mensal_centavos", "mensal"),
    ("caucao_centavos", "caução"),
)
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def tabela_de_preco(evento: Any, _: dict[str, Any]) -> Texto:
    """ "Mudou a tabela de preço", "Street 150–160 · semanal R$ 299,40 → R$ 329,00"; sem preço
    anterior, "Definiu a tabela de preço" com os valores. Preço futuro: "a partir de 15 out"."""
    antes, depois = evento.antes or {}, evento.depois or {}
    nome = (
        Categoria.objects.filter(pk=evento.objeto_id).values_list("nome", flat=True).first() or ""
    )
    if antes:
        resumo = "Mudou a tabela de preço"
        trechos = [
            f"{rotulo} {formatar_reais(antes[campo])} → {formatar_reais(depois[campo])}"
            for campo, rotulo in PERIODOS
            if campo in antes and campo in depois
        ]
    else:
        resumo = "Definiu a tabela de preço"
        trechos = [
            f"{rotulo} {formatar_reais(depois[campo])}"
            for campo, rotulo in PERIODOS
            if isinstance(depois.get(campo), int)
        ]
    vigente = depois.get("vigente_desde")
    if vigente and date.fromisoformat(vigente) > timezone.localdate(evento.ocorrido_em):
        dia = date.fromisoformat(vigente)
        trechos.append(f"a partir de {dia.day:02d} {MESES[dia.month - 1]}")
    return Texto(resumo, " · ".join([nome, *trechos]) if nome else " · ".join(trechos))


# --- Galeria do veículo (VEI-10, T-460) ---

RESUMOS_DA_GALERIA = {
    "veiculo.foto_enviar": "Enviou uma foto do veículo",
    "veiculo.foto_trocar": "Trocou uma foto do veículo",
    "veiculo.foto_capa": "Mudou a capa do veículo",
    "veiculo.foto_apagar": "Apagou uma foto do veículo",
}


def _placa(evento: Any, apoio: dict[str, Any]) -> str:
    """O código gravado no evento; nos eventos de antes da T-460 (sem código), a placa atual do
    veículo, lida uma vez por veículo na página."""
    if evento.objeto_codigo:
        return str(evento.objeto_codigo)
    placas: dict[int, str] = apoio.setdefault("placas_de_veiculos", {})
    if evento.objeto_id is None:
        return ""
    if evento.objeto_id not in placas:
        placa = Veiculo.objects.filter(pk=evento.objeto_id).values_list("placa", flat=True).first()
        placas[evento.objeto_id] = placa_com_hifen(placa) if placa else ""
    return placas[evento.objeto_id]


def _detalhe_da_galeria(acao: str, depois: dict[str, Any]) -> list[str]:
    """Só o nome do arquivo, o número da foto e a capa: nunca a imagem nem dado pessoal (AUD-01).
    Evento antigo sem um dos campos fica sem aquele trecho."""
    numero = depois.get("numero")
    foto = f"foto {numero}" if isinstance(numero, int) else ""
    if acao == "veiculo.foto_capa":
        return [f"a {foto} virou a capa" if foto else ""]
    if acao == "veiculo.foto_apagar":
        era_capa = depois.get("era_capa")
        if era_capa is None:
            capa = ""
        elif not era_capa:
            capa = "não era a capa"
        elif depois.get("nova_capa_id"):
            capa = "era a capa; a mais antiga virou a capa"
        else:
            capa = "era a capa"
        return [foto, capa]
    capa_agora = depois.get("capa")
    if capa_agora is None:
        capa = ""
    elif acao == "veiculo.foto_enviar":
        capa = "virou a capa" if capa_agora else "não é a capa"
    else:
        capa = "é a capa" if capa_agora else "não é a capa"
    return [str(depois.get("arquivo") or ""), foto, capa]


def foto_da_galeria(evento: Any, apoio: dict[str, Any]) -> Texto:
    """ "Enviou uma foto do veículo TBC-5H22", "moto.png · foto 1 · virou a capa". Trocar, capa e
    apagar seguem o mesmo jeito (docs/api/auditoria.md)."""
    placa = _placa(evento, apoio)
    resumo = RESUMOS_DA_GALERIA[evento.acao]
    trechos = _detalhe_da_galeria(evento.acao, evento.depois or {})
    return Texto(f"{resumo} {placa}" if placa else resumo, " · ".join(t for t in trechos if t))


# --- Cadastrar e editar o veículo (VEI-01, T-464) ---

RESUMOS_DO_CADASTRO = {
    "veiculo.cadastrar": "Cadastrou o veículo",
    "veiculo.editar": "Editou o veículo",
}


def cadastro_do_veiculo(evento: Any, apoio: dict[str, Any]) -> Texto:
    """ "Cadastrou o veículo PNB-7C04", "Editou o veículo PNB-7C04", com a placa do código; nos
    eventos de antes da T-464 (sem código), a placa atual do veículo, como nas fotos."""
    placa = _placa(evento, apoio)
    resumo = RESUMOS_DO_CADASTRO[evento.acao]
    return Texto(f"{resumo} {placa}" if placa else resumo, evento.motivo or "")


# --- Veículo vendido (VEN-11, T-420) ---


def vendido(evento: Any, apoio: dict[str, Any]) -> Texto:
    """ "Vendeu o veículo SAK-1D39", com o motivo ("Quitação da LOC-2877"); a placa como nas
    fotos (o código ou, sem ele, a placa atual)."""
    placa = _placa(evento, apoio)
    resumo = "Vendeu o veículo"
    return Texto(f"{resumo} {placa}" if placa else resumo, evento.motivo or "")
