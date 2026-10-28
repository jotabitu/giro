"""Regras das filiais (FIL-01, FIL-03, FIL-06, PLT-03, USR-07). Único lugar que grava filial.

O limite do plano é conferido e somado na mesma transação do cadastro (`exigir_limite` e
`atualizar_uso`, contrato da plataforma). A operação que impede desativar vem dos contadores
que `veiculos`, `locacoes` e `financeiro` registram em `comum.leituras` (ADR 0015).
"""

from collections.abc import Iterable
from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.functions import Lower

from apps.plataforma.services import (
    atualizar_uso,
    copiar_endereco_da_matriz,
    exigir_limite,
    registrar_passo_implantacao,
)
from comum import leituras
from comum.auditoria import Categoria, auditar, registrar_evento, retrato
from comum.documentos import UFS, cnpj_valido, so_digitos
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao

from .calendario import validar_horario
from .models import FeriadoFilial, Filial, UsuarioFilial

ALVO = "filiais.Filial"
# Grupos de operação que impedem desativar (FIL-06); cada app registra o seu contador.
OPERACAO = ("veiculos", "locacoes", "caixas")

CAMPOS_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
CAMPOS_CONTATO = ("telefone", "whatsapp", "email")
CAMPOS_SIMPLES = (
    "nome",
    "cnpj",
    "inscricao_estadual",
    "inscricao_municipal",
    "preco_litro_centavos",
)


NOME_CURTO_MAXIMO = 30


def _validar(dados: dict[str, Any]) -> dict[str, Any]:
    """Normaliza e confere os campos (400 `validacao` com todos os erros de uma vez)."""
    erros: dict[str, list[str]] = {}
    limpos: dict[str, Any] = {}
    if "nome" in dados:
        limpos["nome"] = str(dados["nome"]).strip()
        if not limpos["nome"]:
            erros["nome"] = ["Informe o nome da filial."]
    if "cnpj" in dados:
        cnpj = so_digitos(dados["cnpj"] or "")
        limpos["cnpj"] = cnpj
        if cnpj and not cnpj_valido(cnpj):
            erros["cnpj"] = ["CNPJ inválido"]
    for campo in ("inscricao_estadual", "inscricao_municipal"):
        if campo in dados:
            limpos[campo] = (dados[campo] or "").strip()
    if "nome_curto" in dados:
        limpos["nome_curto"] = (dados["nome_curto"] or "").strip()  # FIL-01
        if len(limpos["nome_curto"]) > NOME_CURTO_MAXIMO:
            erros["nome_curto"] = ["Use até 30 caracteres."]
    if "preco_litro_centavos" in dados:
        limpos["preco_litro_centavos"] = dados["preco_litro_centavos"]
        if limpos["preco_litro_centavos"] is not None and limpos["preco_litro_centavos"] <= 0:
            erros["preco_litro_centavos"] = ["Informe um preço maior que zero."]  # DEV-01
    if "endereco" in dados:
        endereco = dados["endereco"] or {}
        cep = so_digitos(endereco.get("cep") or "")
        if len(cep) != 8:
            erros["endereco.cep"] = ["Informe o CEP com 8 dígitos."]
        uf = (endereco.get("uf") or "").strip().upper()
        if uf not in UFS:
            erros["endereco.uf"] = ["UF inválida."]
        for campo in ("logradouro", "numero", "bairro", "cidade"):
            if not (endereco.get(campo) or "").strip():
                erros[f"endereco.{campo}"] = ["Campo obrigatório."]
        limpos.update(
            cep=cep,
            uf=uf,
            logradouro=(endereco.get("logradouro") or "").strip(),
            numero=(endereco.get("numero") or "").strip(),
            complemento=(endereco.get("complemento") or "").strip(),
            bairro=(endereco.get("bairro") or "").strip(),
            cidade=(endereco.get("cidade") or "").strip(),
        )
    if "contato" in dados:
        contato = dados["contato"] or {}
        limpos.update(
            telefone=so_digitos(contato.get("telefone") or ""),
            whatsapp=so_digitos(contato.get("whatsapp") or ""),
            email=(contato.get("email") or "").strip().lower(),
        )
    if "horario" in dados:
        mensagens = validar_horario(dados["horario"])
        if mensagens:
            erros["horario"] = mensagens
        limpos["horario"] = dados["horario"]
    if erros:
        raise ErroDeValidacao(erros)
    return limpos


def _conferir_nome(nome: str, exceto: int | None = None) -> None:
    existentes = Filial.objects.annotate(nome_minusculo=Lower("nome")).filter(
        nome_minusculo=nome.lower()
    )
    if exceto is not None:
        existentes = existentes.exclude(pk=exceto)
    if existentes.exists():
        raise Conflito("filial_nome_em_uso", "Já existe uma filial com esse nome")


def _salvar(filial: Filial, **kwargs: Any) -> None:
    try:
        with transaction.atomic():
            filial.save(**kwargs)
    except IntegrityError as erro:  # nome repetido numa corrida
        raise Conflito("filial_nome_em_uso", "Já existe uma filial com esse nome") from erro


def criar_filial(dados: dict[str, Any], criada_por: Any) -> Filial:
    """POST /api/filiais/. A primeira é sempre a matriz; quem criou fica ligado a ela."""
    obrigatorios = {"nome", "endereco", "horario"}
    faltando = sorted(obrigatorios - dados.keys())
    if faltando:
        raise ErroDeValidacao({campo: ["Campo obrigatório."] for campo in faltando})
    limpos = _validar(dados)
    with transaction.atomic():
        _conferir_nome(limpos["nome"])
        exigir_limite("filiais")
        primeira = not Filial.objects.exists()
        matriz = primeira or bool(dados.get("matriz"))
        if matriz and not primeira:
            _travar_todas()
            _tirar_matriz()
        filial = Filial(**limpos, matriz=matriz)
        _salvar(filial)
        definir_filiais_do_usuario(
            criada_por.pk, set(_vinculos_ativos(criada_por.pk)) | {filial.pk}
        )
        registrar_evento(
            "filial.criar",
            Categoria.CONFIGURACOES,
            objeto=filial,
            depois=retrato(filial),
            regra="FIL-01",
        )
        atualizar_uso("filiais", 1)
        if matriz:
            registrar_passo_implantacao("filial")  # IMP-07: a matriz é a "Primeira filial"
            # PLT-15 (T-213): o endereço da nota da assinatura nasce da 1ª matriz, uma vez só.
            copiar_endereco_da_matriz(
                {campo: getattr(filial, campo) for campo in CAMPOS_ENDERECO}, filial.pk
            )
    return filial


def editar_filial(filial: Filial, dados: dict[str, Any]) -> Filial:
    """PATCH: `endereco`, `contato` e `horario` são trocados inteiros; `matriz` não muda aqui."""
    dados = {chave: valor for chave, valor in dados.items() if chave != "matriz"}
    limpos = _validar(dados)
    with transaction.atomic(), auditar(filial, "filial.editar", Categoria.CONFIGURACOES):
        if "nome" in limpos:
            _conferir_nome(limpos["nome"], exceto=filial.pk)
        for campo, valor in limpos.items():
            setattr(filial, campo, valor)
        _salvar(filial)
    return filial


def _travar_todas() -> list[Filial]:
    """Serializa trocas de matriz: quem chega depois espera e lê o estado novo."""
    return list(Filial.objects.select_for_update().order_by("pk"))


def _tirar_matriz() -> None:
    for antiga in Filial.objects.filter(matriz=True):
        with auditar(
            antiga, "filial.deixar_de_ser_matriz", Categoria.CONFIGURACOES, regra="FIL-01"
        ):
            antiga.matriz = False
            antiga.save(update_fields=["matriz", "atualizado_em"])


def tornar_matriz(filial: Filial) -> Filial:
    with transaction.atomic():
        _travar_todas()
        filial.refresh_from_db()
        if not filial.ativo:
            raise ErroDeRegra("filial_inativa", "Reative a filial antes de torná-la matriz.")
        if filial.matriz:
            return filial
        _tirar_matriz()
        with auditar(filial, "filial.tornar_matriz", Categoria.CONFIGURACOES, regra="FIL-01"):
            filial.matriz = True
            filial.save(update_fields=["matriz", "atualizado_em"])
    return filial


def impedimentos_para_desativar(filial: Filial) -> dict[str, Any]:
    outras_ativas = Filial.ativos.exclude(pk=filial.pk).exists()
    return {
        "matriz": filial.matriz,
        "ultima_filial": not outras_ativas,
        "operacao": leituras.contar(ALVO, filial.pk, OPERACAO),
    }


def desativar(filial: Filial, motivo: str) -> Filial:
    """FIL-06: recusa com todos os impedimentos de uma vez. Vínculos de usuários ficam."""
    if not motivo.strip():
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with transaction.atomic():
        filial = Filial.objects.select_for_update().get(pk=filial.pk)
        if not filial.ativo:
            return filial
        impedimentos = impedimentos_para_desativar(filial)
        if (
            impedimentos["matriz"]
            or impedimentos["ultima_filial"]
            or any(impedimentos["operacao"].values())
        ):
            raise ErroDeRegra("FIL-06", "Esta filial ainda não pode ser desativada", impedimentos)
        with auditar(
            filial, "filial.desativar", Categoria.CONFIGURACOES, motivo=motivo, regra="FIL-06"
        ):
            filial.ativo = False
            filial.save(update_fields=["ativo", "atualizado_em"])
        atualizar_uso("filiais", -1)
    return filial


def reativar(filial: Filial, motivo: str) -> Filial:
    """Volta a contar no plano: recusa com 422 `PLT-03` se o limite já foi atingido."""
    if not motivo.strip():
        raise ErroDeValidacao({"motivo": ["Informe o motivo."]})
    with transaction.atomic():
        filial = Filial.objects.select_for_update().get(pk=filial.pk)
        if filial.ativo:
            return filial
        exigir_limite("filiais")
        _conferir_nome(filial.nome, exceto=filial.pk)
        with auditar(
            filial, "filial.reativar", Categoria.CONFIGURACOES, motivo=motivo, regra="FIL-06"
        ):
            filial.ativo = True
            filial.save(update_fields=["ativo", "atualizado_em"])
        atualizar_uso("filiais", 1)
    return filial


# --- Feriados (FIL-03) ---


def confirmar_feriados(filial: Filial, feriados: Iterable[dict[str, Any]]) -> list[FeriadoFilial]:
    """Confirma sugestões e acrescenta locais. Data já cadastrada (ativa) é ignorada."""
    criados: list[FeriadoFilial] = []
    with transaction.atomic():
        ja = set(filial.feriados.filter(ativo=True).values_list("data", flat=True))
        for item in feriados:
            if item["data"] in ja:
                continue
            feriado = FeriadoFilial.objects.create(
                filial=filial, data=item["data"], nome=item["nome"].strip(), origem=item["origem"]
            )
            ja.add(feriado.data)
            criados.append(feriado)
        if criados:
            registrar_evento(
                "filial.confirmar_feriados",
                Categoria.CONFIGURACOES,
                objeto=filial,
                depois={"feriados": [f"{f.data.isoformat()} {f.nome}" for f in criados]},
                regra="FIL-03",
            )
    return criados


def remover_feriado(feriado: FeriadoFilial) -> FeriadoFilial:
    with auditar(feriado, "filial.remover_feriado", Categoria.CONFIGURACOES, regra="FIL-03"):
        feriado.ativo = False
        feriado.save(update_fields=["ativo", "atualizado_em"])
    return feriado


# --- Vínculo das pessoas (USR-07) ---


def _vinculos_ativos(usuario_id: int) -> list[int]:
    return list(
        UsuarioFilial.ativos.filter(usuario_id=usuario_id).values_list("filial_id", flat=True)
    )


def filial_invalida() -> ErroDeRegra:
    return ErroDeRegra("filial_invalida", "Escolha só filiais ativas")


def _nomes(ids: Iterable[int]) -> list[dict[str, Any]]:
    filiais = Filial.objects.filter(pk__in=list(ids)).order_by("nome")
    return [{"id": f.pk, "nome": f.nome} for f in filiais]


def definir_filiais_do_usuario(usuario_id: int, filiais_ids: Iterable[int]) -> None:
    """Troca as filiais da pessoa (USR-07). Chamado pelo evento
    `contas.filiais_do_usuario_definidas` e ao criar uma filial.

    Filial acrescentada inexistente ou inativa: 422 `filial_invalida`, e nada é gravado. O
    vínculo tirado é desativado, não apagado, e a troca vai para a auditoria com antes e depois
    (F-03).
    """
    novas = set(filiais_ids)
    with transaction.atomic():
        vinculos = {
            v.filial_id: v
            for v in UsuarioFilial.objects.select_for_update().filter(usuario_id=usuario_id)
        }
        atuais = {f for f, v in vinculos.items() if v.ativo}
        acrescentadas = novas - atuais
        if Filial.ativos.filter(pk__in=acrescentadas).count() != len(acrescentadas):
            raise filial_invalida()
        if atuais == novas:
            return
        UsuarioFilial.objects.filter(usuario_id=usuario_id, filial_id__in=atuais - novas).update(
            ativo=False
        )
        UsuarioFilial.objects.filter(
            usuario_id=usuario_id, filial_id__in=novas & set(vinculos), ativo=False
        ).update(ativo=True)
        UsuarioFilial.objects.bulk_create(
            [
                UsuarioFilial(usuario_id=usuario_id, filial_id=f)
                for f in sorted(novas - set(vinculos))
            ]
        )
        usuario = get_user_model().objects.get(pk=usuario_id)
        registrar_evento(
            "usuario.alterar_filiais",
            Categoria.SEGURANCA,
            objeto=usuario,
            antes={"filiais": _nomes(atuais)},
            depois={"filiais": _nomes(novas)},
            regra="USR-07",
        )
