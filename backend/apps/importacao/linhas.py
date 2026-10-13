"""Cada linha da planilha: dos textos das células para o corpo do cadastro do app dono, e a
validação da linha (IMP-02).

A linha passa pelas mesmas validações do cadastro pela tela (`validar_novo` de veículos e de
clientes), mais o que só a planilha tem: célula em branco, número e data em texto, nome da
categoria e da filial, e a repetição dentro da própria planilha.

Em clientes, a mensagem nunca repete o valor da célula: os `erros` não são cifrados.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from apps.clientes import services as clientes
from apps.filiais.models import Filial
from apps.veiculos import services as veiculos
from apps.veiculos.models import Categoria
from comum.campos import buscar_por_hash
from comum.documentos import so_digitos

from .models import TipoImportacao
from .planilha import COLUNAS, normalizar_nome

Erro = dict[str, str]
# (campo, chave) → número da outra linha da planilha com a mesma chave, ou None.
Repetida = Callable[[str, str], int | None]

ROTULOS = {tipo: {c.nome: c.rotulo for c in colunas} for tipo, colunas in COLUNAS.items()}
OBRIGATORIAS_VEICULO = (
    "placa",
    "chassi",
    "marca",
    "modelo",
    "ano_fabricacao",
    "ano_modelo",
    "km",
    "categoria",
)
OBRIGATORIAS_CLIENTE = ("nome", "documento", "celular")
# Campo do erro do serviço → coluna da planilha.
COLUNA_DO_CAMPO = {
    "categoria_id": "categoria",
    "filial_id": "filial",
    "km_atual": "km",
    "valor_compra_centavos": "valor_compra",
    "endereco.cep": "cep",
    "endereco.uf": "uf",
    "referencia.telefone": "referencia_telefone",
    "responsavel.cpf": "responsavel_cpf",
    "cnh.categoria": "cnh_categoria",
}
_KM = re.compile(r"^(\d+|\d{1,3}(\.\d{3})+)$")
_ANO = re.compile(r"^\d{4}$")


def erro(campo: str, mensagem: str, codigo: str = "validacao") -> Erro:
    return {"campo": campo, "codigo": codigo, "mensagem": mensagem}


@dataclass
class Contexto:
    """Categorias e filiais ativas, lidas uma vez por importação."""

    categorias: list[Categoria]
    filiais: dict[str, Filial]
    filial_padrao_id: int | None

    @classmethod
    def carregar(cls, filial_padrao_id: int | None) -> "Contexto":
        return cls(
            categorias=list(Categoria.ativos.all()),
            filiais={normalizar_nome(f.nome): f for f in Filial.ativos.all()},
            filial_padrao_id=filial_padrao_id,
        )

    def categoria(self, nome: str, filial_id: int | None) -> Categoria | None:
        """A da filial da linha antes da que vale para a empresa toda."""
        procurado = normalizar_nome(nome)
        achadas = [
            c
            for c in self.categorias
            if normalizar_nome(c.nome) == procurado and c.filial_id in (None, filial_id)
        ]
        achadas.sort(key=lambda c: c.filial_id is None)
        return achadas[0] if achadas else None


@dataclass
class Resultado:
    erros: list[Erro] = field(default_factory=list)
    dados: dict[str, Any] = field(default_factory=dict)  # o corpo do cadastro
    chaves: dict[str, str] = field(default_factory=dict)  # placa, chassi ou documento (hash)

    @property
    def campos_com_erro(self) -> set[str]:
        return {e["campo"] for e in self.erros}


# --- Conversões ---


def data(texto: str) -> date | None:
    """`dd/mm/aaaa` ou `aaaa-mm-dd`. `ValueError` no resto."""
    for formato in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    raise ValueError(texto)


def centavos(texto: str) -> int:
    """`13900`, `13.900,00` ou `13900.00` → 1390000. `ValueError` no resto."""
    limpo = texto.replace("R$", "").replace(" ", "")
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
        limpo = limpo.replace(".", "")
    try:
        valor = Decimal(limpo)
    except InvalidOperation as erro_decimal:
        raise ValueError(texto) from erro_decimal
    if valor < 0 or not valor.is_finite():
        raise ValueError(texto)
    return int((valor * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# --- Veículos ---


def _veiculo(valores: dict[str, str], contexto: Contexto) -> Resultado:
    r = Resultado()
    rotulo = ROTULOS[TipoImportacao.VEICULOS]
    for coluna in OBRIGATORIAS_VEICULO:
        if not valores.get(coluna):
            r.erros.append(erro(coluna, f"{rotulo[coluna]} em branco"))
    dados: dict[str, Any] = {
        campo: valores.get(campo, "")
        for campo in ("placa", "chassi", "renavam", "marca", "modelo", "cor")
    }
    placa = veiculos.normalizar_placa(valores.get("placa", ""))
    chassi = veiculos.normalizar_chassi(valores.get("chassi", ""))
    if placa and not veiculos.PLACA.match(placa):
        mensagem = (
            f"Placa {valores['placa']} está incompleta"
            if len(placa) < 7
            else f"Placa {valores['placa']} fora do padrão ABC1234 ou ABC1D23"
        )
        r.erros.append(erro("placa", mensagem, "VEI-01"))
    if chassi and not veiculos.CHASSI.match(chassi):
        r.erros.append(
            erro("chassi", f"Chassi {valores['chassi']} precisa ter 17 letras e números", "VEI-01")
        )
    r.chaves = {"placa": placa[:10], "chassi": chassi[:20]}

    for coluna in ("ano_fabricacao", "ano_modelo"):
        texto = valores.get(coluna, "")
        if texto and not _ANO.match(texto):
            r.erros.append(erro(coluna, f"{rotulo[coluna]} precisa ser um número"))
        elif texto:
            dados[coluna] = int(texto)
    km = valores.get("km", "")
    if km and not _KM.match(km):
        r.erros.append(erro("km", "Km precisa ser um número"))
    elif km:
        dados["km_atual"] = int(km.replace(".", ""))

    filial_id = contexto.filial_padrao_id
    nome_filial = valores.get("filial", "")
    if nome_filial:
        filial = contexto.filiais.get(normalizar_nome(nome_filial))
        filial_id = filial.pk if filial else None
        if filial is None:
            r.erros.append(erro("filial", f"Filial {nome_filial} não existe ou está inativa"))
    elif filial_id is None:
        r.erros.append(erro("filial", "Filial em branco"))
    if filial_id is not None:
        dados["filial_id"] = filial_id
    nome_categoria = valores.get("categoria", "")
    if nome_categoria and filial_id is not None:
        categoria = contexto.categoria(nome_categoria, filial_id)
        if categoria is None:
            r.erros.append(
                erro("categoria", f"Categoria {nome_categoria} não existe ou está inativa")
            )
        else:
            dados["categoria_id"] = categoria.pk

    texto = valores.get("capacidade_tanque_litros", "")
    if texto:
        try:
            dados["capacidade_tanque_litros"] = Decimal(texto.replace(",", "."))
        except InvalidOperation:
            r.erros.append(erro("capacidade_tanque_litros", "Capacidade do tanque inválida"))
    texto = valores.get("valor_compra", "")
    if texto:
        try:
            dados["valor_compra_centavos"] = centavos(texto)
        except ValueError:
            r.erros.append(erro("valor_compra", "Valor de compra inválido"))
    texto = valores.get("data_compra", "")
    if texto:
        try:
            dados["data_compra"] = data(texto)
        except ValueError:
            r.erros.append(erro("data_compra", "Data de compra inválida"))
    r.dados = dados
    return r


def _mensagem_do_veiculo(e: Erro, valores: dict[str, str]) -> str:
    if e["campo"] in ("placa", "chassi"):  # o formato já foi conferido: é repetição na empresa
        if e["campo"] == "placa":
            return f"Placa {valores['placa']} já cadastrada"
        return f"Chassi {valores['chassi']} já cadastrado"
    return e["mensagem"]


# --- Clientes ---


def _cliente(valores: dict[str, str]) -> Resultado:
    r = Resultado()
    rotulo = ROTULOS[TipoImportacao.CLIENTES]
    for coluna in OBRIGATORIAS_CLIENTE:
        if not valores.get(coluna):
            r.erros.append(erro(coluna, f"{rotulo[coluna]} em branco"))
    digitos = so_digitos(valores.get("documento", ""))
    tipo = valores.get("tipo", "").strip().lower()
    if tipo and tipo not in ("pf", "pj"):
        r.erros.append(erro("tipo", "Tipo precisa ser pf ou pj"))
    if tipo not in ("pf", "pj"):
        tipo = "pj" if len(digitos) == 14 else "pf"
    dados: dict[str, Any] = {"tipo": tipo}
    for campo in ("nome", "documento", "celular", "email", "profissao"):
        if valores.get(campo):
            dados[campo] = valores[campo]

    def em_data(coluna: str) -> date | None:
        texto = valores.get(coluna, "")
        if not texto:
            return None
        try:
            return data(texto)
        except ValueError:
            r.erros.append(erro(coluna, f"{rotulo[coluna]} inválida"))
            return None

    nascimento = em_data("nascimento")
    if nascimento:
        dados["nascimento"] = nascimento
    grupos: dict[str, dict[str, Any]] = {
        "cnh": {
            "numero": valores.get("cnh_numero", ""),
            "categoria": valores.get("cnh_categoria", "").upper(),
            "validade": em_data("cnh_validade"),
            "primeira_habilitacao": em_data("cnh_primeira_habilitacao"),
        },
        "endereco": {
            campo: valores.get(campo, "")
            for campo in ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
        },
        "referencia": {
            "nome": valores.get("referencia_nome", ""),
            "parentesco": valores.get("referencia_parentesco", ""),
            "telefone": valores.get("referencia_telefone", ""),
        },
        "responsavel": {
            "nome": valores.get("responsavel_nome", ""),
            "cpf": valores.get("responsavel_cpf", ""),
        },
    }
    for grupo, campos in grupos.items():
        presentes = {chave: valor for chave, valor in campos.items() if valor}
        if presentes:
            dados[grupo] = presentes
    r.dados = dados
    r.chaves = {"documento": buscar_por_hash(digitos) if digitos else ""}
    return r


def _rotulo_do_documento(dados: dict[str, Any]) -> str:
    return "CNPJ" if dados.get("tipo") == "pj" else "CPF"


# --- Validação da linha ---


def converter(tipo: str, valores: dict[str, str], contexto: Contexto) -> Resultado:
    """Só a conversão (sem a validação do app dono): para gravar uma linha já pronta."""
    return _veiculo(valores, contexto) if tipo == TipoImportacao.VEICULOS else _cliente(valores)


def validar(
    tipo: str,
    valores: dict[str, str],
    contexto: Contexto,
    repetida: Repetida,
    longas: list[str] | None = None,
) -> Resultado:
    """IMP-02: os erros da linha, uma mensagem por problema. A repetição dentro da planilha
    vem de `repetida` (a primeira ocorrência fica pronta, as seguintes com erro)."""
    r = converter(tipo, valores, contexto)
    r.erros = [erro(c, "Célula com mais de 1.000 caracteres") for c in longas or []] + r.erros
    if tipo == TipoImportacao.VEICULOS:
        dono = veiculos.validar_novo(r.dados)
    else:
        dono = clientes.validar_novo(r.dados)
    rotulos = ROTULOS[tipo]
    for e in dono:
        coluna = COLUNA_DO_CAMPO.get(e["campo"], e["campo"])
        if coluna in r.campos_com_erro or (coluna == "categoria" and "filial" in r.campos_com_erro):
            continue  # sem a filial, a categoria não tem como ser conferida
        mensagem = e["mensagem"]
        if mensagem == "Campo obrigatório.":
            mensagem = f"{rotulos.get(coluna, coluna)} em branco"
        elif tipo == TipoImportacao.VEICULOS:
            mensagem = _mensagem_do_veiculo(e, valores)
        elif e["codigo"] == "CLI-01" and e["mensagem"].startswith("Já existe"):
            mensagem = f"{_rotulo_do_documento(r.dados)} já cadastrado"  # sem dizer de quem é
        r.erros.append(erro(coluna, mensagem.rstrip("."), e["codigo"]))

    for campo, chave in r.chaves.items():
        if not chave or campo in r.campos_com_erro:
            continue
        outra = repetida(campo, chave)
        if outra is None:
            continue
        if campo == "placa":
            mensagem, codigo = f"Placa repetida na linha {outra}", "VEI-01"
        elif campo == "chassi":
            mensagem, codigo = f"Chassi repetido na linha {outra}", "VEI-01"
        else:
            mensagem = f"{_rotulo_do_documento(r.dados)} já cadastrado (linha {outra})"
            codigo = "CLI-01"
        r.erros.append(erro(campo, mensagem, codigo))
    return r


def erros_do_cadastro(tipo: str, problema: Any, valores: dict[str, str]) -> list[Erro]:
    """O erro de negócio que o serviço do app dono levantou ao gravar, como erros da linha
    (alguém cadastrou a mesma placa pela tela no meio do caminho, por exemplo)."""
    campos = getattr(problema, "campos", None)
    if isinstance(campos, dict):
        return [
            erro(COLUNA_DO_CAMPO.get(str(campo), str(campo)), str(mensagem).rstrip("."))
            for campo, mensagens in campos.items()
            for mensagem in mensagens
        ]
    detalhes = getattr(problema, "detalhes", None) or {}
    campo = str(detalhes.get("campo") or ("documento" if problema.codigo == "CLI-01" else ""))
    mensagem = str(problema.mensagem)
    if tipo == TipoImportacao.VEICULOS and campo in ("placa", "chassi") and valores.get(campo):
        mensagem = _mensagem_do_veiculo(erro(campo, mensagem), valores)
    return [erro(campo, mensagem.rstrip("."), problema.codigo)]
