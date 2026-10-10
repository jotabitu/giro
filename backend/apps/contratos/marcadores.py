"""Marcadores do modelo de contrato: lista fechada, troca por texto já escapado (S-09).

O texto da locadora nunca passa por motor de template: `{{grupo.campo}}` é procurado por
expressão regular e trocado pelo valor que a origem do contrato manda, escapado. Marcador fora
da lista é recusado ao salvar e ao publicar (`marcador_invalido`).
"""

import html
import re
from dataclasses import dataclass

from comum.erros import ErroDeValidacao


@dataclass(frozen=True)
class Marcador:
    chave: str
    rotulo: str
    exemplo: str


MARCADORES: tuple[Marcador, ...] = (
    Marcador("empresa.nome", "Nome da locadora", "Moto Rápida"),
    Marcador("empresa.razao_social", "Razão social da locadora", "Moto Rápida Locações Ltda"),
    Marcador("empresa.cnpj", "CNPJ da locadora", "12.345.678/0001-90"),
    Marcador("empresa.endereco", "Endereço da locadora", "Av. Bezerra de Menezes, 1200"),
    Marcador("empresa.cidade", "Cidade da locadora", "Fortaleza/CE"),
    Marcador("filial.nome", "Nome da filial", "Filial Centro"),
    Marcador("filial.cnpj", "CNPJ da filial", "12.345.678/0001-90"),
    Marcador("filial.endereco", "Endereço da filial", "Av. Bezerra de Menezes, 1200, Centro"),
    Marcador("filial.telefone", "Telefone da filial", "(85) 3333-1200"),
    Marcador("cliente.nome", "Nome do cliente", "Lucas Ferreira"),
    Marcador("cliente.cpf", "CPF ou CNPJ do cliente", "123.456.789-09"),
    Marcador("cliente.nascimento", "Nascimento do cliente", "14/03/1995"),
    Marcador("cliente.endereco", "Endereço do cliente", "Rua das Flores, 45, Fortaleza/CE"),
    Marcador("cliente.celular", "Celular do cliente", "(85) 98877-1203"),
    Marcador("cliente.email", "E-mail do cliente", "lucas@exemplo.com.br"),
    Marcador("cliente.cnh_numero", "Número da CNH", "01234567890"),
    Marcador("cliente.cnh_categoria", "Categoria da CNH", "A"),
    Marcador("cliente.cnh_validade", "Validade da CNH", "20/05/2029"),
    Marcador("cliente.responsavel_nome", "Responsável (empresa)", "Ana Souza"),
    Marcador("cliente.responsavel_cpf", "CPF do responsável", "987.654.321-00"),
    Marcador("veiculo.marca", "Marca do veículo", "Honda"),
    Marcador("veiculo.modelo", "Modelo do veículo", "CG 160 Start"),
    Marcador("veiculo.placa", "Placa", "SAK1D39"),
    Marcador("veiculo.chassi", "Chassi", "9C2KC2200RR012345"),
    Marcador("veiculo.renavam", "Renavam", "01234567890"),
    Marcador("veiculo.ano", "Ano", "2024/2024"),
    Marcador("veiculo.cor", "Cor", "Vermelha"),
    Marcador("veiculo.km_saida", "Km na saída", "18.402"),
    Marcador("locacao.codigo", "Código da locação", "LOC-2856"),
    Marcador("locacao.inicio", "Início", "07/10/2026 12:30"),
    Marcador("locacao.fim_previsto", "Devolução prevista", "14/10/2026 12:30"),
    Marcador("locacao.periodicidade", "Periodicidade", "semanal"),
    Marcador("locacao.plano", "Plano", "Tabela"),
    Marcador("locacao.valor", "Valor por período", "R$ 329,00"),
    Marcador("locacao.caucao", "Caução", "R$ 300,00"),
    Marcador("locacao.diaria_atraso", "Diária de atraso", "R$ 54,90"),
    Marcador("locacao.extras", "Extras", "Capacete extra (1)"),
    Marcador("locacao.forma_pagamento", "Forma de pagamento", "Pix"),
    Marcador("locacao.parcelas", "Tabela de vencimentos", "1ª parcela: 07/10/2026, R$ 329,00"),
    Marcador("locacao.tolerancia_atraso", "Tolerância de atraso", "60 minutos"),
    Marcador("cobranca.multa_atraso_pct", "Multa por atraso", "2,00%"),
    Marcador("cobranca.juros_mes_pct", "Juros por mês", "1,00%"),
    Marcador("contrato.data", "Data do contrato", "07/10/2026"),
    Marcador("contrato.cidade_assinatura", "Cidade da assinatura", "Fortaleza/CE"),
)
CHAVES = frozenset(m.chave for m in MARCADORES)
EXEMPLOS = {m.chave: m.exemplo for m in MARCADORES}

# FIN-03: o contrato só permite cobrar juros e multa se o modelo usa os dois.
CLAUSULA_JUROS = frozenset({"cobranca.multa_atraso_pct", "cobranca.juros_mes_pct"})

# Valores que já vêm em HTML montado pelo sistema (a tabela de vencimentos), não pelo usuário.
EM_HTML = frozenset({"locacao.parcelas"})

_MARCADOR = re.compile(r"\{\{\s*([^{}]*?)\s*\}\}")


class MarcadorInvalido(ErroDeValidacao):
    """400 `marcador_invalido` (S-09), com a lista em `campos.texto`."""

    def __init__(self, invalidos: list[str]) -> None:
        mensagens = [f"Campo desconhecido: {{{{{chave}}}}}" for chave in invalidos]
        super().__init__({"texto": mensagens})
        self.codigo = "marcador_invalido"
        self.mensagem = mensagens[0]


def usados(texto: str) -> list[str]:
    """Os marcadores do texto, sem repetir, na ordem em que aparecem."""
    vistos: dict[str, None] = {}
    for achado in _MARCADOR.finditer(texto):
        vistos.setdefault(achado.group(1), None)
    return list(vistos)


def conferir(texto: str) -> list[str]:
    """Levanta `MarcadorInvalido` se houver marcador fora da lista. Devolve os usados."""
    lista = usados(texto)
    invalidos = [chave for chave in lista if chave not in CHAVES]
    if invalidos:
        raise MarcadorInvalido(invalidos)
    return lista


def tem_clausula_juros(texto: str) -> bool:
    return set(usados(texto)) >= CLAUSULA_JUROS


def substituir(texto: str, valores: dict[str, str]) -> str:
    """Troca cada marcador pelo valor escapado. Sem valor, fica vazio. Só a tabela de
    vencimentos (montada pelo sistema) entra como HTML."""

    def trocar(achado: re.Match[str]) -> str:
        chave = achado.group(1)
        valor = valores.get(chave, "")
        return valor if chave in EM_HTML else html.escape(valor)

    return _MARCADOR.sub(trocar, texto)
