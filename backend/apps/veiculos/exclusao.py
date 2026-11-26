"""Excluir o veículo sem histórico (VEI-22, T-515): a conferência do histórico e os textos.

O histórico vem dos apps de baixo pelo registro de contadores (ADR 0015): cada um registra, no
`ready()`, `historico_<tipo>` no alvo `veiculos.Veiculo`, sem `recurso=`: o histórico conta mesmo
com o módulo desligado no plano (PLT-12). Contador sem fornecedor vale 0 (a ordem de serviço,
que ainda não existe). A transferência entre filiais é deste app.

Lido por `services.excluir` (a recusa 409 `VEI-22`) e pela ficha (`acoes.excluir`), para a tela
mostrar sem calcular.
"""

from typing import Any

from comum import leituras
from comum.documentos import placa_com_hifen

from .models import TipoVeiculo, TransferenciaVeiculo, Veiculo

ALVO = "veiculos.Veiculo"
# Na ordem e com os nomes da frase da recusa (VEI-22).
HISTORICO = (
    ("locacao", "locação"),
    ("troca", "troca de veículo"),
    ("venda", "venda"),
    ("vistoria", "vistoria"),
    ("ordem_servico", "ordem de serviço"),
    ("despesa", "despesa"),
    ("movimentacao", "movimentação"),
    ("transferencia", "transferência"),
)
NOME_DO_TIPO = dict(HISTORICO)
EXCLUEM = frozenset({"administrador", "gerente"})  # tabela de perfis; o gerente, na sua filial


def contador(tipo: str) -> str:
    return f"historico_{tipo}"


def historico(veiculo: Veiculo) -> list[str]:
    """Os tipos de histórico achados, na ordem da frase. Vazio: o veículo pode ser excluído."""
    contagem = leituras.contar(ALVO, veiculo.pk, [contador(tipo) for tipo, _ in HISTORICO])
    return [tipo for tipo, _ in HISTORICO if contagem[contador(tipo)] > 0]


def juntar(nomes: list[str]) -> str:
    """ "locação", "locação e vistoria", "vistoria, despesa e transferência"."""
    if len(nomes) <= 1:
        return "".join(nomes)
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def motivo(achados: list[str]) -> str:
    nomes = juntar([NOME_DO_TIPO[tipo] for tipo in achados])
    return f"Este veículo já tem {nomes}. Ele fica guardado e não pode ser excluído."


def _e_moto(veiculo: Veiculo) -> bool:
    return bool(veiculo.categoria.tipo_veiculo == TipoVeiculo.MOTO)


def caminho(veiculo: Veiculo, perfil: str) -> str:
    """O que a locadora pode fazer no lugar (o aviso da ficha)."""
    quem = "a moto" if _e_moto(veiculo) else "o carro"
    baixa = (
        "faça a baixa (perda total, roubo ou sucata)."
        if perfil == "administrador"
        else "peça a baixa ao administrador (perda total, roubo ou sucata)."
    )
    return f"Para tirar {quem} da frota, coloque à venda ou {baixa}"


def acao(veiculo: Veiculo, usuario: Any) -> dict[str, Any] | None:
    """`acoes.excluir` da ficha. `None` para quem não exclui (o botão não aparece): os perfis
    fora da tabela e o suporte Giro (PLT-07). O botão aparece com ou sem histórico (padrão A); com
    histórico, `permitido` é `false` e a tela abre o aviso com `motivo` e `caminho`."""
    perfil = getattr(usuario, "perfil", "")
    if perfil not in EXCLUEM or getattr(usuario, "e_suporte", False):
        return None
    achados = historico(veiculo)
    placa = placa_com_hifen(veiculo.placa)
    if achados:
        return {
            "permitido": False,
            "titulo": "Este veículo não pode ser excluído",
            "texto": None,
            "motivo": motivo(achados),
            "caminho": caminho(veiculo, perfil),
            "historico": achados,
        }
    quem = "A moto" if _e_moto(veiculo) else "O carro"
    return {
        "permitido": True,
        "titulo": f"Excluir a {placa}?",
        "texto": (
            f"Use só para um cadastro feito por engano. {quem} sai da frota e de todas as listas,"
            " com as fotos, os documentos e os preços. A placa e o chassi ficam livres para um"
            " novo cadastro. Não dá para desfazer."
        ),
        "motivo": None,
        "caminho": None,
        "historico": [],
    }


def contar_transferencias(veiculo_id: int) -> int:
    return int(TransferenciaVeiculo.objects.filter(veiculo_id=veiculo_id).count())


def registrar() -> None:
    leituras.registrar_contador(ALVO, contador("transferencia"), contar_transferencias)
