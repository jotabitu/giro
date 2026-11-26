"""Excluir o cliente sem histórico (CLI-13, T-515): a conferência do histórico e os textos.

O histórico vem dos apps de baixo pelo registro de contadores (ADR 0015): cada um registra, no
`ready()`, `historico_<tipo>` no alvo `clientes.Cliente`, sem `recurso=`: o histórico conta mesmo
com o módulo desligado no plano (PLT-12). Contador sem fornecedor vale 0.

Lido por `services.excluir` (a recusa 409 `CLI-13`) e pela ficha (`acoes.excluir`), para a tela
mostrar sem calcular.
"""

from typing import Any

from comum import leituras

from .models import Cliente, StatusCliente, TipoCliente

ALVO = "clientes.Cliente"
# Na ordem e com os nomes da frase da recusa (CLI-13). Caução e reembolso contam como conta.
HISTORICO = (
    ("locacao", "locação"),
    ("venda", "venda"),
    ("conta", "conta"),
    ("contrato", "contrato"),
    ("aprovacao", "pedido de aprovação"),
)
NOME_DO_TIPO = dict(HISTORICO)
EXCLUEM = frozenset({"administrador", "gerente"})  # como na CLI-09; o vendedor pede ao gerente
BLOQUEADO = "Desbloqueie o cliente antes de excluir."


def contador(tipo: str) -> str:
    return f"historico_{tipo}"


def historico(cliente: Cliente) -> list[str]:
    """Os tipos de histórico achados, na ordem da frase. Vazio: o cliente pode ser excluído."""
    contagem = leituras.contar(ALVO, cliente.pk, [contador(tipo) for tipo, _ in HISTORICO])
    return [tipo for tipo, _ in HISTORICO if contagem[contador(tipo)] > 0]


def _juntar(nomes: list[str]) -> str:
    if len(nomes) <= 1:
        return "".join(nomes)
    return f"{', '.join(nomes[:-1])} e {nomes[-1]}"


def motivo(achados: list[str]) -> str:
    nomes = _juntar([NOME_DO_TIPO[tipo] for tipo in achados])
    return (
        f"Este cliente já tem {nomes} na empresa. O cadastro fica guardado e não pode ser excluído."
    )


def caminho(cliente: Cliente, perfil: str) -> str:
    """O que a locadora pode fazer no lugar (o aviso da ficha)."""
    if cliente.status == StatusCliente.INATIVO:
        texto = "O cadastro já está inativo."
    else:
        texto = "Para ele não fazer novas locações nem compras, inative o cadastro."
    if perfil == "administrador":
        # AUD-06: o pedido do titular é atendido pela equipe Giro até a tela da fase 2.
        texto += (
            " Se o cliente pediu para apagar os dados dele, peça à equipe Giro para anonimizar"
            " o cadastro."
        )
    return texto


def acao(cliente: Cliente, usuario: Any) -> dict[str, Any] | None:
    """`acoes.excluir` da ficha. `None` para quem não exclui (o botão não aparece): os perfis
    fora da tabela e o suporte Giro (PLT-07). O botão aparece com ou sem histórico (padrão A); com
    histórico, `permitido` é `false` e a tela abre o aviso com `motivo`, `caminho` e, quando
    `inativar` vem `true`, o botão "Inativar cliente" (CLI-09)."""
    perfil = getattr(usuario, "perfil", "")
    if perfil not in EXCLUEM or getattr(usuario, "e_suporte", False):
        return None
    achados = historico(cliente)
    if achados:
        return {
            "permitido": False,
            "titulo": "Este cliente não pode ser excluído",
            "texto": None,
            "motivo": motivo(achados),
            "caminho": caminho(cliente, perfil),
            "inativar": cliente.status != StatusCliente.INATIVO,
            "historico": achados,
        }
    if cliente.status == StatusCliente.BLOQUEADO:
        return {
            "permitido": False,
            "titulo": "Este cliente não pode ser excluído",
            "texto": None,
            "motivo": BLOQUEADO,
            "caminho": None,
            "inativar": False,
            "historico": [],
        }
    documento = "o CNPJ" if cliente.tipo == TipoCliente.PJ else "o CPF"
    return {
        "permitido": True,
        "titulo": f"Excluir o cadastro de {cliente.nome}?",
        "texto": (
            "Use só para um cadastro feito por engano. O cliente sai da lista, os dados pessoais"
            f" e os documentos enviados são apagados, e {documento} fica livre para um novo"
            " cadastro. Não dá para desfazer."
        ),
        "motivo": None,
        "caminho": None,
        "inativar": False,
        "historico": [],
    }
