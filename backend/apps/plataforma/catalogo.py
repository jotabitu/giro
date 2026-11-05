"""Catálogo de planos (PLT-11): os textos de cada plano, num lugar só.

Usado na `Admin-Assinatura` (Mudar de plano, Comparar planos e o cartão do plano acima, a
`oferta`) e, quando existirem, na `Compra-Planos` e na `Plat-Planos`. Cada plano só promete o que
existe no sistema ou o que a equipe Giro faz à mão: nada de NF-e da locadora, domínio próprio,
portal do cliente, API e integrações, nem contrato digital como extra do Completo (CA-ASS-20).
Quando o produto mudar a `PLT-11`, muda só este arquivo. Funções puras, sem banco.
"""

from dataclasses import dataclass

TITULO_DA_OFERTA = "Precisa de mais veículos ou filiais?"
# O selo "Mais escolhido" da `Compra-Planos` (`compra.md`, `destaque`).
PLANO_EM_DESTAQUE = "Profissional"


@dataclass(frozen=True)
class TextosDoPlano:
    # "O que inclui", na ordem da tabela da PLT-11 (Comparar planos).
    inclui: tuple[str, ...]
    # O que este plano tem e o plano de baixo não: os itens do cartão do plano acima.
    a_mais: tuple[str, ...]
    # A frase curta da `Compra-Planos`, abaixo do nome.
    descricao: str = ""


CATALOGO: dict[str, TextosDoPlano] = {
    "Essencial": TextosDoPlano(
        inclui=(
            "Locação, vistoria e contas a receber",
            "Contrato digital, assinado pelo cliente no celular",
            "Sua marca e seu endereço de acesso",
        ),
        a_mais=(),
        descricao="Para quem está começando a frota.",
    ),
    # PLT-11, catálogo da fase 1 (T-356): só o que já existe. Vendas, manutenção, comissões,
    # conciliação e relatórios entram no texto quando existirem.
    "Profissional": TextosDoPlano(
        inclui=(
            "Tudo do Essencial, mais despesas",
            "Pix e boleto automáticos e cobrança pelo WhatsApp",
        ),
        a_mais=(
            "Despesas",
            "Pix e boleto automáticos e cobrança pelo WhatsApp",
            "Até 150 veículos, 3 filiais e 10 usuários",
        ),
        descricao="Para locadoras com equipe e mais de uma loja.",
    ),
    "Completo": TextosDoPlano(
        inclui=(
            "Tudo do Profissional",
            "Veículos, filiais e usuários sem limite",
            "Implantação acompanhada por chamada",
            "Suporte prioritário",
        ),
        a_mais=(
            "Veículos, filiais e usuários sem limite",
            "Implantação acompanhada por chamada",
            "Suporte prioritário",
        ),
        descricao="Para redes e operações maiores.",
    ),
}

SEM_TEXTOS = TextosDoPlano(inclui=(), a_mais=())


def textos(nome_do_plano: str) -> TextosDoPlano:
    """Os textos do plano; um plano fora do catálogo (criado pela equipe) não promete nada."""
    return CATALOGO.get(nome_do_plano, SEM_TEXTOS)
