"""Consultas e representações de clientes (docs/api/clientes.md).

A API decide `situacao`, `acao_principal`, pendências, análise e impedimentos; a tela só mostra.
Os blocos de outros apps (`locacao_atual`, `financeiro`, `venda_aberta`...) chegam pelo registro
de `comum.leituras` (ADR 0015) e vêm `null` enquanto o fornecedor não existe.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.db.models import Q, QuerySet

from comum import arquivos, leituras, relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import registrar_evento
from comum.campos import buscar_por_hash
from comum.classificacao import mascarar_documento
from comum.documentos import cnpj_valido, cpf_valido, so_digitos

from .models import (
    Cliente,
    DocumentoCliente,
    StatusCliente,
    TipoCliente,
    TipoDocumentoCliente,
)

S = StatusCliente
ALVO = "clientes.Cliente"
BLOCOS = ("locacao_atual", "ultima_locacao", "financeiro", "venda_aberta")
PERFIS_DE_CADASTRO = frozenset({"administrador", "gerente", "vendedor"})
DIAS_DE_TOLERANCIA_DA_CNH = 30  # CLI-02
TIPOS_DE_DOCUMENTO = [t.value for t in TipoDocumentoCliente]
# Contador registrado por `financeiro` (ADR 0015): contas do cliente com 15 dias ou mais de
# atraso. Sem o fornecedor, vale 0 (CLI-05).
CONTADOR_ATRASO_PARA_BLOQUEIO = "contas_atrasadas_15_dias"
CONTADORES_DE_PENDENCIA = ("locacao_aberta", "venda_aberta", "em_aberto_centavos")


def pode_ver_completo(usuario: Any) -> bool:
    """AUD-04: quem cadastra vê o completo. AUD-09: o suporte Giro nunca, em nenhum modo."""
    if getattr(usuario, "e_suporte", False):
        return False
    return getattr(usuario, "perfil", None) in PERFIS_DE_CADASTRO


# --- Cadastro (CLI-02, CLI-03) ---


def _tem_cnh(cliente: Cliente) -> bool:
    return bool(cliente.cnh_numero and cliente.cnh_categoria and cliente.cnh_validade)


def _tem_endereco(cliente: Cliente) -> bool:
    obrigatorios = ("cep", "logradouro", "numero", "bairro", "cidade", "uf")
    return all(getattr(cliente, campo) for campo in obrigatorios)


def _tem_referencia(cliente: Cliente) -> bool:
    return bool(cliente.referencia_nome and cliente.referencia_telefone)


def _tem_responsavel(cliente: Cliente) -> bool:
    return bool(
        cliente.responsavel_nome and cliente.responsavel_cpf and cliente.responsavel_celular
    )


def documentos_ativos(cliente: Cliente) -> dict[str, DocumentoCliente]:
    return {d.tipo: d for d in DocumentoCliente.ativos.filter(cliente=cliente)}


def pendencias(cliente: Cliente, enviados: set[str] | None = None) -> list[str]:
    """CLI-03: o que falta para sair de `incompleto`."""
    if enviados is None:
        enviados = set(documentos_ativos(cliente)) if cliente.pk else set()
    faltando = [tipo for tipo in TIPOS_DE_DOCUMENTO if tipo not in enviados]
    if cliente.consentimento_em is None:
        faltando.append("consentimento")
    if not _tem_cnh(cliente):
        faltando.append("cnh")
    if not _tem_endereco(cliente):
        faltando.append("endereco")
    if not _tem_referencia(cliente):
        faltando.append("referencia")
    if cliente.tipo == TipoCliente.PF and cliente.nascimento is None:
        faltando.append("nascimento")
    if cliente.tipo == TipoCliente.PJ and not _tem_responsavel(cliente):
        faltando.append("responsavel")
    return faltando


def situacao_da_cnh(validade: date | None, hoje: date) -> str | None:
    """CLI-02: `valida` até o dia da validade; `vencida` até 30 dias depois (não impede);
    `vencida_impede` com mais de 30 dias."""
    if validade is None:
        return None
    if validade >= hoje:
        return "valida"
    if (hoje - validade).days <= DIAS_DE_TOLERANCIA_DA_CNH:
        return "vencida"
    return "vencida_impede"


# Categorias que dirigem moto (A) e carro (B). C, D e E incluem a B (CTB, art. 143).
CATEGORIA_POR_TIPO = {
    "moto": frozenset({"A", "AB", "AC", "AD", "AE"}),
    "carro": frozenset({"B", "C", "D", "E", "AB", "AC", "AD", "AE"}),
}
EXIGIDA_POR_TIPO = {"moto": "A", "carro": "B"}


@dataclass(frozen=True)
class Impedimento:
    codigo: str
    mensagem: str

    def como_dict(self) -> dict[str, str]:
        return {"codigo": self.codigo, "mensagem": self.mensagem}


INATIVO = Impedimento("cliente_inativo", "O cliente está inativo.")
BLOQUEADO = Impedimento("CLI-05", "O cliente está bloqueado.")


def impedimentos_para_nova_locacao(cliente: Cliente) -> list[dict[str, str]]:
    """CLI-05 e CLI-09: bloqueado ou inativo não faz nova locação."""
    if cliente.status == S.BLOQUEADO:
        return [BLOQUEADO.como_dict()]
    if cliente.status == S.INATIVO:
        return [INATIVO.como_dict()]
    return []


def impedimentos_para_venda(cliente: Cliente) -> list[dict[str, str]]:
    """CLI-05 e CLI-09: bloqueado ou inativo não compra."""
    return impedimentos_para_nova_locacao(cliente)


def impedimentos_para_retirada(
    cliente: Cliente, tipo_veiculo: str, data: date
) -> list[dict[str, str]]:
    """Usado por locações e vistorias antes da retirada. Vazia = pode retirar."""
    impedimentos = [Impedimento(**i) for i in impedimentos_para_nova_locacao(cliente)]
    if cliente.status == S.INCOMPLETO:
        impedimentos.append(
            Impedimento("CLI-03", "Complete o cadastro do cliente antes da retirada.")
        )
    exigida = EXIGIDA_POR_TIPO[tipo_veiculo]
    if cliente.cnh_categoria not in CATEGORIA_POR_TIPO[tipo_veiculo]:
        impedimentos.append(
            Impedimento("CLI-02", f"A CNH do cliente não tem a categoria {exigida}.")
        )
    elif situacao_da_cnh(cliente.cnh_validade, data) == "vencida_impede":
        impedimentos.append(
            Impedimento("CLI-02", "A CNH do cliente está vencida há mais de 30 dias.")
        )
    return [i.como_dict() for i in impedimentos]


def contas_com_atraso_para_bloqueio(cliente_id: int) -> int:
    return leituras.contar(ALVO, cliente_id, [CONTADOR_ATRASO_PARA_BLOQUEIO])[
        CONTADOR_ATRASO_PARA_BLOQUEIO
    ]


def pendencias_para_inativar(cliente: Cliente) -> dict[str, Any]:
    """CLI-09: locação aberta, venda aberta ou valor em aberto (contadores de `locacoes`,
    `vendas` e `financeiro`; sem o fornecedor, nada)."""
    contagem = leituras.contar(ALVO, cliente.pk, CONTADORES_DE_PENDENCIA)
    return {
        "locacao_aberta": contagem["locacao_aberta"] > 0,
        "em_aberto_centavos": contagem["em_aberto_centavos"],
        "venda_aberta": contagem["venda_aberta"] > 0,
    }


# --- Análise do cadastro (CLI-04) ---


def _item(codigo: str, situacao: str, rotulo: str) -> dict[str, str]:
    return {"codigo": codigo, "situacao": situacao, "rotulo": rotulo}


def _item_documento(tipo: str, documento: str) -> dict[str, str]:
    nome = "CPF" if tipo == TipoCliente.PF else "CNPJ"
    if not documento:
        return _item("cpf", "pendente", f"{nome} não informado")
    valido = cpf_valido(documento) if tipo == TipoCliente.PF else cnpj_valido(documento)
    if valido:
        return _item("cpf", "ok", f"{nome} válido")
    return _item("cpf", "problema", f"{nome} inválido")


def _item_cnh(categoria: str, validade: date | None, tem_numero: bool) -> dict[str, str]:
    if not (categoria and validade and tem_numero):
        return _item("cnh", "pendente", "CNH não informada")
    situacao = situacao_da_cnh(validade, relogio.hoje())
    if situacao == "valida":
        return _item("cnh", "ok", f"CNH categoria {categoria}, válida")
    if situacao == "vencida":
        return _item("cnh", "pendente", f"CNH categoria {categoria}, vencida")
    return _item("cnh", "problema", "CNH vencida há mais de 30 dias")


def _item_lista_de_bloqueio(hashes: list[str]) -> dict[str, str]:
    """O documento, ou o CPF do responsável na PJ, pertence a cliente bloqueado da empresa."""
    if hashes and Cliente.objects.filter(status=S.BLOQUEADO, documento_hash__in=hashes).exists():
        return _item("lista_bloqueio", "problema", "Consta na lista de bloqueio")
    return _item("lista_bloqueio", "ok", "Fora da lista de bloqueio")


def _item_historico(cliente: Cliente | None) -> dict[str, str]:
    """Fornecido por `financeiro` (bloco `historico`, ADR 0015)."""
    historico = leituras.blocos(ALVO, cliente).get("historico") if cliente is not None else None
    if historico is None:
        return _item("historico", "pendente", "Sem histórico")
    return _item("historico", historico["situacao"], historico["rotulo"])


def _item_documentos(faltando: int) -> dict[str, str]:
    if faltando == 0:
        return _item("documentos", "ok", "Documentos enviados")
    if faltando == 1:
        return _item("documentos", "pendente", "Falta 1 documento")
    return _item("documentos", "pendente", f"Faltam {faltando} documentos")


def analise(cliente: Cliente, enviados: set[str] | None = None) -> dict[str, Any]:
    if enviados is None:
        enviados = set(documentos_ativos(cliente))
    documento = cliente.documento_claro()
    hashes = [h for h in (cliente.documento_hash, cliente.responsavel_cpf_hash) if h]
    return {
        "itens": [
            _item_documento(cliente.tipo, documento),
            _item_cnh(cliente.cnh_categoria, cliente.cnh_validade, bool(cliente.cnh_numero)),
            _item_lista_de_bloqueio(hashes),
            _item_historico(cliente),
            _item_documentos(len([t for t in TIPOS_DE_DOCUMENTO if t not in enviados])),
        ]
    }


def analise_de_dados(dados: dict[str, Any]) -> dict[str, Any]:
    """`POST /analisar/`: o mesmo corpo do cadastro, sem gravar nada (sem documentos ainda)."""
    tipo = dados["tipo"]
    documento = so_digitos(dados.get("documento") or "")
    cnh = dados.get("cnh") or {}
    hashes = [buscar_por_hash(documento)] if documento else []
    cpf_responsavel = so_digitos((dados.get("responsavel") or {}).get("cpf") or "")
    if tipo == TipoCliente.PJ and cpf_responsavel:
        hashes.append(buscar_por_hash(cpf_responsavel))
    return {
        "itens": [
            _item_documento(tipo, documento),
            _item_cnh(cnh.get("categoria") or "", cnh.get("validade"), bool(cnh.get("numero"))),
            _item_lista_de_bloqueio(hashes),
            _item_historico(None),
            _item_documentos(len(TIPOS_DE_DOCUMENTO)),
        ]
    }


# --- Situação e ação principal (CLI-06, CLI-07) ---


def situacao(cliente: Cliente, blocos: dict[str, Any]) -> dict[str, str]:
    locacao = blocos.get("locacao_atual")
    financeiro = blocos.get("financeiro") or {}
    if cliente.status == S.BLOQUEADO:
        return {"codigo": "bloqueado", "rotulo": "Bloqueado", "tom": "perigo"}
    if locacao and locacao.get("alerta") == "Cancelando":
        return {"codigo": "cancelando", "rotulo": "Cancelando", "tom": "alerta"}
    if financeiro.get("em_aberto_centavos", 0) > 0:
        return {"codigo": "parcela_atrasada", "rotulo": "Parcela atrasada", "tom": "perigo"}
    if cliente.status == S.INCOMPLETO:
        return {"codigo": "incompleto", "rotulo": "Cadastro incompleto", "tom": "alerta"}
    if cliente.status == S.INATIVO:
        return {"codigo": "inativo", "rotulo": "Inativo", "tom": "neutro"}
    if locacao:
        return {"codigo": "em_dia", "rotulo": "Em dia", "tom": "sucesso"}
    return {"codigo": "sem_locacao", "rotulo": "Sem locação", "tom": "neutro"}


def acao_principal(cliente: Cliente, blocos: dict[str, Any]) -> dict[str, Any] | None:
    """CLI-07, na ordem: em aberto, incompleto, venda aberta, com locação, nova locação.
    Bloqueado sem valor em aberto não ganha Nova locação."""
    financeiro = blocos.get("financeiro") or {}
    venda = blocos.get("venda_aberta")
    locacao = blocos.get("locacao_atual")
    if financeiro.get("em_aberto_centavos", 0) > 0:
        conta = financeiro.get("conta_mais_antiga_id")
        alvo = {"tipo": "conta", "id": conta} if conta else None
        return {"codigo": "cobrar", "rotulo": "Cobrar", "alvo": alvo}
    if cliente.status == S.INCOMPLETO:
        return {
            "codigo": "completar_cadastro",
            "rotulo": "Completar cadastro",
            "alvo": {"tipo": "cliente", "id": cliente.pk},
        }
    if venda:
        return {
            "codigo": "ver_proposta",
            "rotulo": "Ver proposta",
            "alvo": {"tipo": "venda", "id": venda["id"]},
        }
    if locacao:
        return {
            "codigo": "ver_locacao",
            "rotulo": "Ver locação",
            "alvo": {"tipo": "locacao", "id": locacao["id"]},
        }
    if cliente.status == S.ATIVO:
        return {
            "codigo": "nova_locacao",
            "rotulo": "Nova locação",
            "alvo": {"tipo": "cliente", "id": cliente.pk},
        }
    return None


# --- Representações (AUD-04, AUD-05, AUD-09) ---


def documento_mascarado(cliente: Cliente) -> str:
    """CPF `***.218.330-**`; CNPJ inteiro (não é dado pessoal)."""
    documento = cliente.documento_claro()
    return mascarar_documento(documento) if documento else ""


def blocos_de(cliente: Cliente) -> dict[str, Any]:
    recebidos = leituras.blocos(ALVO, cliente)
    return {bloco: recebidos.get(bloco) for bloco in BLOCOS}


def resumida(cliente: Cliente) -> dict[str, Any]:
    blocos = blocos_de(cliente)
    return {
        "id": cliente.pk,
        "tipo": cliente.tipo,
        "nome": cliente.nome,
        "documento_mascarado": documento_mascarado(cliente),
        "celular": cliente.celular,
        "status": cliente.status,
        "situacao": situacao(cliente, blocos),
        "cliente_desde": cliente.cliente_desde,
        **blocos,
        "acao_principal": acao_principal(cliente, blocos),
    }


def _idade(nascimento: date | None, hoje: date) -> int | None:
    if nascimento is None:
        return None
    return (
        hoje.year - nascimento.year - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
    )


def _ou_nulo(grupo: dict[str, Any]) -> dict[str, Any] | None:
    return grupo if any(v not in (None, "") for v in grupo.values()) else None


def _documentos(cliente: Cliente, ativos: dict[str, DocumentoCliente]) -> list[dict[str, Any]]:
    """AUD-05: URL assinada de 15 minutos, nova a cada leitura, e cada geração auditada."""
    lista = []
    for tipo in TIPOS_DE_DOCUMENTO:
        documento = ativos.get(tipo)
        item: dict[str, Any] = {
            "tipo": tipo,
            "enviado_em": documento.criado_em if documento else None,
            "url": None,
            "url_expira_em": None,
        }
        if documento is not None and documento.arquivo:
            assinada = arquivos.url_assinada(documento.arquivo.name)
            item["url"], item["url_expira_em"] = assinada.url, assinada.expira_em
            registrar_evento(
                "documento_cliente.ver",
                CategoriaAuditoria.OPERACAO,
                objeto=documento,
                regra="AUD-05",
            )
        lista.append(item)
    return lista


def completa(cliente: Cliente) -> dict[str, Any]:
    """Só para quem cadastra (AUD-04), e nunca para o suporte (AUD-09)."""
    hoje = relogio.hoje()
    ativos = documentos_ativos(cliente)
    enviados = set(ativos)
    cnh = _ou_nulo(
        {
            "numero": cliente.cnh_numero_claro(),
            "categoria": cliente.cnh_categoria,
            "validade": cliente.cnh_validade,
            "primeira_habilitacao": cliente.cnh_primeira_habilitacao,
        }
    )
    if cnh is not None:
        cnh["situacao"] = situacao_da_cnh(cliente.cnh_validade, hoje)
    responsavel = None
    if cliente.tipo == TipoCliente.PJ:
        responsavel = _ou_nulo(
            {
                "nome": cliente.responsavel_nome,
                "cpf": cliente.responsavel_cpf_claro(),
                "celular": cliente.responsavel_celular,
            }
        )
    bloqueio = None
    if cliente.status == S.BLOQUEADO:
        bloqueio = {
            "motivo": cliente.bloqueio_motivo,
            "desde": cliente.bloqueio_desde,
            "descricao": cliente.bloqueio_descricao,
            "desbloqueia_sozinho": cliente.bloqueio_motivo == "atraso",
        }
    return {
        **resumida(cliente),
        "documento": cliente.documento_claro(),
        "nascimento": cliente.nascimento,
        "idade": _idade(cliente.nascimento, hoje),
        "email": cliente.email,
        "profissao": cliente.profissao,
        "cnh": cnh,
        "responsavel": responsavel,
        "endereco": _ou_nulo(
            {
                "cep": cliente.cep,
                "logradouro": cliente.logradouro,
                "numero": cliente.numero,
                "complemento": cliente.complemento or None,
                "bairro": cliente.bairro,
                "cidade": cliente.cidade,
                "uf": cliente.uf,
            }
        ),
        "referencia": _ou_nulo(
            {
                "nome": cliente.referencia_nome,
                "parentesco": cliente.referencia_parentesco,
                "telefone": cliente.referencia_telefone,
            }
        ),
        "consentimento_em": cliente.consentimento_em,
        "bloqueio": bloqueio,
        "documentos": _documentos(cliente, ativos),
        "pendencias": pendencias(cliente, enviados),
        "analise": analise(cliente, enviados),
    }


def representacao(cliente: Cliente, usuario: Any) -> tuple[dict[str, Any], bool]:
    """`(dados, completa?)` conforme quem pede."""
    if pode_ver_completo(usuario):
        return completa(cliente), True
    return resumida(cliente), False


# --- Lista (CLI-06) ---

SITUACOES_DA_LISTA = ("com_locacao", "em_aberto", "bloqueados", "incompletos", "inativos")
ORDENS = {"-criado_em": "-criado_em", "nome": "nome", "-total_pago": "-criado_em"}


def filtrar(
    qs: QuerySet[Cliente], *, situacao: str | None, tipo: str | None, busca: str | None
) -> QuerySet[Cliente]:
    if tipo in (TipoCliente.PF, TipoCliente.PJ):
        qs = qs.filter(tipo=tipo)
    if situacao == "bloqueados":
        qs = qs.filter(status=S.BLOQUEADO)
    elif situacao == "incompletos":
        qs = qs.filter(status=S.INCOMPLETO)
    elif situacao == "inativos":
        qs = qs.filter(status=S.INATIVO)
    elif situacao in ("com_locacao", "em_aberto"):
        filtro = leituras.filtro(ALVO, situacao)
        qs = filtro(qs.exclude(status=S.INATIVO)) if filtro else qs.none()
    else:
        qs = qs.exclude(status=S.INATIVO)  # CLI-09: o inativo sai da lista padrão
    return buscar(qs, busca)


def buscar(qs: QuerySet[Cliente], busca: str | None) -> QuerySet[Cliente]:
    """Só dígitos com 11 ou 14: CPF ou CNPJ exato pelo hash (ADR 0014); busca parcial de
    documento não existe. Com texto: nome ou celular."""
    termo = (busca or "").strip()
    if not termo:
        return qs
    if termo.isdigit() and len(termo) in (11, 14):
        return qs.filter(documento_hash=buscar_por_hash(termo))
    filtro = Q(nome__icontains=termo)
    if termo.isdigit():
        filtro |= Q(celular__contains=termo)
    return qs.filter(filtro)


def contagens(qs: QuerySet[Cliente]) -> dict[str, int | None]:
    sem_inativos = qs.exclude(status=S.INATIVO)
    resultado: dict[str, int | None] = {
        "todos": sem_inativos.count(),
        "com_locacao": None,
        "em_aberto": None,
        "bloqueados": qs.filter(status=S.BLOQUEADO).count(),
        "incompletos": qs.filter(status=S.INCOMPLETO).count(),
        "inativos": qs.filter(status=S.INATIVO).count(),
    }
    for nome in ("com_locacao", "em_aberto"):
        filtro = leituras.filtro(ALVO, nome)
        if filtro is not None:
            resultado[nome] = filtro(sem_inativos).count()
    return resultado


def indicadores(qs: QuerySet[Cliente], contagem: dict[str, int | None]) -> dict[str, Any]:
    hoje = relogio.hoje()
    fim = hoje.replace(day=1) - timedelta(days=1)
    novos = qs.filter(cliente_desde__gte=fim.replace(day=1), cliente_desde__lte=fim).count()
    com_locacao, todos = contagem["com_locacao"], contagem["todos"]
    pct = None
    if com_locacao is not None and todos:
        pct = str((Decimal(com_locacao * 100) / todos).quantize(Decimal("0.01"), ROUND_HALF_UP))
    return {
        "novos_no_mes_anterior": novos,
        "com_locacao_pct": pct,
        "em_aberto_total_centavos": None,
    }


def total_ativos() -> int:
    """Clientes fora de `inativo`: o indicador da implantação no painel."""
    return int(Cliente.objects.exclude(status=S.INATIVO).count())
