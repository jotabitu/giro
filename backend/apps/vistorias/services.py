"""Regras da vistoria (VIS-01 a VIS-04, VEI-01, VEI-02, VEI-03, CLI-02, CLI-03, CLI-05).

O único lugar que muda uma vistoria. A saída concluída chama
`locacoes.services.registrar_vistoria_saida`, que pode ativar a locação (ADR 0011: `vistorias`
fica acima de `locacoes`).
"""

from dataclasses import dataclass, field
from typing import Any

from django.db import IntegrityError, transaction

from apps.clientes import selectors as clientes_selectors
from apps.locacoes import services as locacoes
from apps.locacoes.models import Locacao, StatusLocacao
from apps.veiculos import services as veiculos
from apps.veiculos.models import Origem, Veiculo
from comum import arquivos, estados, relogio
from comum.auditoria import Categoria, auditar, registrar_evento, retrato
from comum.erros import Conflito, ErroDeRegra, ErroDeValidacao, TransicaoInvalida

from .models import (
    POSICOES_OBRIGATORIAS,
    Avaria,
    FotoVistoria,
    PosicaoFoto,
    StatusVistoria,
    TipoVistoria,
    Vistoria,
)

S = StatusVistoria

# VIS-02: a lista padrão do ramo, na ordem da tela. Motos e carros usam a mesma por enquanto.
ITENS_PADRAO: dict[str, list[tuple[str, str]]] = {
    tipo: [
        ("pneus_freios", "Pneus e freios"),
        ("luzes_buzina", "Luzes e buzina"),
        ("retrovisores", "Retrovisores"),
        ("documento_chave", "Documento e chave"),
        ("acessorios", "Acessórios entregues"),
    ]
    for tipo in ("moto", "carro")
}
ROTULO_POSICAO = dict(PosicaoFoto.choices)


@dataclass
class Pendencia:
    """Um motivo para não concluir; `detalhes` sobem para os detalhes do 422."""

    codigo: str
    mensagem: str
    curta: str  # o nome em `pendencias` da representação
    detalhes: dict[str, Any] = field(default_factory=dict)

    def como_dict(self) -> dict[str, Any]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, **self.detalhes}


def _quem(usuario: Any) -> int | None:
    return getattr(usuario, "pk", None)


def _travar(vistoria: Vistoria) -> Vistoria:
    travada: Vistoria = Vistoria.objects.select_for_update().get(pk=vistoria.pk)
    return travada


def _recarregar(vistoria: Vistoria) -> None:
    vistoria.refresh_from_db()
    vistoria._status_salvo = vistoria.status


def _origem(vistoria: Vistoria, locacao: Locacao) -> veiculos.OrigemDaMudanca:
    return veiculos.OrigemDaMudanca(Origem.VISTORIA, vistoria.pk, locacao.codigo)


def concluida_nao_se_edita() -> Conflito:
    return Conflito(
        "vistoria_concluida",
        "A vistoria concluída não se edita. Para corrigir, use Corrigir vistoria.",
    )


def _exigir_rascunho(vistoria: Vistoria) -> None:
    if vistoria.status != S.RASCUNHO:
        raise concluida_nao_se_edita()


# --- Criar (VIS-02) ---


def itens_iniciais(locacao: Locacao, veiculo: Veiculo) -> list[dict[str, Any]]:
    """A lista do ramo e os extras da locação como itens ("Capacete extra")."""
    padrao = ITENS_PADRAO[veiculo.categoria.tipo_veiculo]
    extras = [(f"extra_{e.pk}", e.nome) for e in locacao.extras.order_by("id")]
    return [
        {"codigo": codigo, "rotulo": rotulo, "ok": None, "observacao": None}
        for codigo, rotulo in [*padrao, *extras]
    ]


def _rascunho(locacao: Locacao, veiculo: Veiculo, tipo: str) -> Vistoria | None:
    return Vistoria.objects.filter(
        locacao=locacao, veiculo=veiculo, tipo=tipo, status=S.RASCUNHO
    ).first()


def _vigente(locacao: Locacao, veiculo: Veiculo, tipo: str) -> Vistoria | None:
    return Vistoria.objects.filter(
        locacao=locacao, veiculo=veiculo, tipo=tipo, status=S.CONCLUIDA, vigente=True
    ).first()


def criar(locacao: Locacao, tipo: str, usuario: Any) -> tuple[Vistoria, bool]:
    """A vistoria em `rascunho` do veículo atual, com a lista pronta. Se já existe rascunho do
    mesmo tipo, devolve ele (`criada = False`): quem vistoria continua de onde parou."""
    veiculo = Veiculo.objects.select_related("categoria").get(pk=locacao.veiculo_id)
    existente = _rascunho(locacao, veiculo, tipo)
    if existente is not None:
        return existente, False
    if _vigente(locacao, veiculo, tipo) is not None:
        raise Conflito(
            "vistoria_concluida",
            "Esta vistoria já foi concluída. Para corrigir, use Corrigir vistoria.",
        )
    try:
        with transaction.atomic():
            vistoria = Vistoria.objects.create(
                locacao=locacao,
                veiculo=veiculo,
                tipo=tipo,
                itens=itens_iniciais(locacao, veiculo),
                responsavel_id=_quem(usuario),
            )
            registrar_evento(
                f"vistoria.iniciar_{tipo}",
                Categoria.OPERACAO,
                objeto=vistoria,
                depois=retrato(vistoria),
            )
    except IntegrityError:  # outra pessoa abriu o rascunho ao mesmo tempo
        concorrente = _rascunho(locacao, veiculo, tipo)
        if concorrente is None:
            raise
        return concorrente, False
    return vistoria, True


def iniciar_saida(locacao: Locacao, usuario: Any) -> tuple[Vistoria, bool]:
    """Saída só para locação `aguardando_retirada`. A troca de veículo (LOC-09) chega na T-092."""
    if locacao.status != StatusLocacao.AGUARDANDO_RETIRADA:
        raise TransicaoInvalida(
            "transicao_locacao",
            "A vistoria de saída é só para locação aguardando retirada.",
            {"status": locacao.status},
        )
    return criar(locacao, TipoVistoria.SAIDA, usuario)


# --- Preencher ("Salvar e continuar depois" é só este passo, DEV-05) ---


def _itens_respondidos(atuais: list[dict[str, Any]], respostas: list[dict[str, Any]]) -> list[Any]:
    por_codigo = {item["codigo"]: dict(item) for item in atuais}
    desconhecidos = [r["codigo"] for r in respostas if r["codigo"] not in por_codigo]
    if desconhecidos:
        raise ErroDeValidacao({"itens": [f"Item desconhecido: {', '.join(desconhecidos)}."]})
    for resposta in respostas:
        item = por_codigo[resposta["codigo"]]
        item["ok"] = resposta.get("ok")
        if "observacao" in resposta:
            item["observacao"] = (resposta["observacao"] or "").strip() or None
    return [por_codigo[item["codigo"]] for item in atuais]


def editar(vistoria: Vistoria, dados: dict[str, Any], usuario: Any) -> Vistoria:
    """`{km?, combustivel?, itens?, observacoes?}`, só em rascunho (VIS-04)."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        if "km" in dados:
            travada.km = dados["km"]
        if "combustivel" in dados:
            travada.combustivel = dados["combustivel"] or ""
        if "itens" in dados:
            travada.itens = _itens_respondidos(travada.itens, dados["itens"])
        if "observacoes" in dados:
            travada.observacoes = (dados["observacoes"] or "").strip()
        travada.responsavel_id = _quem(usuario)
        travada.save()
    _recarregar(vistoria)
    return vistoria


def enviar_foto(vistoria: Vistoria, posicao: str, arquivo: Any, usuario: Any) -> FotoVistoria:
    """JPG ou PNG até 10 MB, reprocessada sem metadados (sem GPS, AUD-05). A nova foto de posição
    fixa deixa a anterior inativa e guardada; as de avaria se somam."""
    formato = arquivos.validar(arquivo)
    if formato.extensao == "pdf":
        raise ErroDeValidacao({"arquivo": ["Envie uma foto JPG ou PNG."]})
    limpo = arquivos.sem_metadados(arquivo, formato)
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        if posicao != PosicaoFoto.AVARIA:
            for anterior in FotoVistoria.ativos.select_for_update().filter(
                vistoria=travada, posicao=posicao
            ):
                anterior.ativo = False
                anterior.save(update_fields=["ativo", "atualizado_em"])
        foto = FotoVistoria.objects.create(
            vistoria=travada, posicao=posicao, tirada_em=relogio.agora(), por_id=_quem(usuario)
        )
        foto.arquivo.save(limpo.name, limpo, save=True)
    return foto


def registrar_avaria(vistoria: Vistoria, dados: dict[str, Any], usuario: Any) -> Avaria:
    """Na saída, a avaria é preexistente: só registro, sem valor nem oficina (VIS-01). Na chegada,
    `valor_centavos` vem só de quem vê o acerto (o vistoriador não informa valores)."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        saida = travada.tipo == TipoVistoria.SAIDA
        erros: dict[str, list[str]] = {}
        valor = dados.get("valor_centavos")
        if valor is not None and getattr(usuario, "perfil", "") == "vistoriador":
            erros["valor_centavos"] = ["O vistoriador não informa valores."]
        elif valor is not None and saida:
            erros["valor_centavos"] = ["Na saída, a avaria só é registrada, sem valor."]
        if saida and dados.get("vai_para_oficina"):
            erros["vai_para_oficina"] = ["Na saída, a avaria só é registrada."]
        foto = FotoVistoria.ativos.filter(vistoria=travada, pk=dados.get("foto_id")).first()
        if foto is None:
            erros["foto_id"] = ["Tire a foto da avaria nesta vistoria."]
        if erros:
            raise ErroDeValidacao(erros)
        avaria = Avaria.objects.create(
            vistoria=travada,
            veiculo_id=travada.veiculo_id,
            descricao=dados["descricao"].strip(),
            preexistente=saida,
            valor_centavos=valor,
            vai_para_oficina=bool(dados.get("vai_para_oficina")),
            foto=foto,
        )
    return avaria


def remover_avaria(vistoria: Vistoria, avaria_id: int) -> None:
    """Avaria nova de um rascunho ainda não é registro de negócio: sai de verdade."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        apagadas, _ = Avaria.objects.filter(vistoria=travada, pk=avaria_id).delete()
        if not apagadas:
            raise ErroDeValidacao({"avaria_id": ["Esta avaria não é desta vistoria."]})


# --- Concluir (VIS-01 a VIS-04, VEI-01 a VEI-03, CLI-02, CLI-03, CLI-05) ---


def _faltam_fotos(vistoria: Vistoria) -> list[str]:
    feitas = set(FotoVistoria.ativos.filter(vistoria=vistoria).values_list("posicao", flat=True))
    return [p for p in POSICOES_OBRIGATORIAS if p not in feitas]


def _lista(rotulos: list[str]) -> str:
    return rotulos[0] if len(rotulos) == 1 else f"{', '.join(rotulos[:-1])} e {rotulos[-1]}"


def pendencias_da_vistoria(vistoria: Vistoria, veiculo: Veiculo) -> list[Pendencia]:
    """O que falta preencher: fotos, itens, combustível e km."""
    pendencias = []
    faltam = _faltam_fotos(vistoria)
    if faltam:
        nomes = _lista([str(ROTULO_POSICAO[p]).lower() for p in faltam])
        pendencias.append(
            Pendencia("VIS-01", f"Faltam as fotos: {nomes}.", "fotos", {"faltam": faltam})
        )
    sem_resposta = [i["codigo"] for i in vistoria.itens if i.get("ok") is None]
    if sem_resposta:
        pendencias.append(
            Pendencia("VIS-02", "Responda todos os itens.", "itens", {"itens": sem_resposta})
        )
    if not vistoria.combustivel:
        pendencias.append(Pendencia("VIS-03", "Informe o nível do combustível.", "combustivel"))
    if vistoria.km is None:
        pendencias.append(Pendencia("km_nao_informado", "Informe o km do painel.", "km"))
    elif vistoria.km < veiculo.km_atual:
        erro = veiculos.km_menor(veiculo.km_atual)
        pendencias.append(
            Pendencia(
                erro.codigo,
                erro.mensagem,
                "km",
                {
                    "km_atual": veiculo.km_atual,
                    "corrigir_km": f"/api/veiculos/{veiculo.pk}/corrigir-km/",
                },
            )
        )
    return pendencias


def impedimentos_da_retirada(locacao: Locacao, veiculo: Veiculo) -> list[Pendencia]:
    """Só na saída: o cliente liberado (CLI-02, CLI-03, CLI-05) e o CRLV e o seguro em dia
    (VEI-03, decisão de 08 out 2026)."""
    hoje = locacoes.data_local(relogio.agora(), locacao.filial)
    pendencias = [
        Pendencia(i["codigo"], i["mensagem"], "cliente")
        for i in clientes_selectors.impedimentos_para_retirada(
            locacao.cliente, veiculo.categoria.tipo_veiculo, hoje
        )
    ]
    vencidos = veiculos.documentos_vencidos_que_bloqueiam(veiculo, hoje)
    if vencidos:
        erro = veiculos.documento_vencido(vencidos, antes="da retirada")
        pendencias.append(
            Pendencia(erro.codigo, erro.mensagem, "documentos", {"documentos": vencidos})
        )
    return pendencias


def nao_conclui(pendencias: list[Pendencia]) -> ErroDeRegra:
    """422 com todas as pendências; o código e a mensagem são os da primeira, e os detalhes de
    cada uma (ex.: `documentos` da VEI-03) sobem para os detalhes."""
    primeira = pendencias[0]
    mensagem = (
        primeira.mensagem
        if len(pendencias) == 1
        else f"Resolva as {len(pendencias)} pendências antes de concluir."
    )
    detalhes: dict[str, Any] = {}
    for pendencia in pendencias:
        detalhes.update(pendencia.detalhes)
    detalhes["pendencias"] = [p.como_dict() for p in pendencias]
    return ErroDeRegra(primeira.codigo, mensagem, detalhes)


def concluir(vistoria: Vistoria, usuario: Any) -> Vistoria:
    """Numa transação: confere tudo, conclui (não se edita mais, VIS-04), atualiza o km do
    veículo (VEI-02) e, na saída, chama a ativação da locação. A correção concluída passa a ser a
    vigente, e a anterior fica guardada."""
    with transaction.atomic():
        travada = _travar(vistoria)
        _exigir_rascunho(travada)
        locacao = Locacao.objects.select_related("cliente", "filial").get(pk=travada.locacao_id)
        veiculo = Veiculo.objects.select_related("categoria").get(pk=travada.veiculo_id)
        saida = travada.tipo == TipoVistoria.SAIDA
        pendencias = pendencias_da_vistoria(travada, veiculo)
        if saida and travada.substitui_id is None:
            pendencias += impedimentos_da_retirada(locacao, veiculo)
        if pendencias:
            raise nao_conclui(pendencias)

        agora = relogio.agora()
        if travada.substitui_id is not None:
            anterior = Vistoria.objects.select_for_update().get(pk=travada.substitui_id)
            with auditar(
                anterior,
                "vistoria.substituir",
                Categoria.OPERACAO,
                motivo=travada.motivo_correcao,
                regra="VIS-04",
            ):
                anterior.vigente = False
                anterior.save(update_fields=["vigente", "atualizado_em"])
        travada.concluida_em = agora
        travada.responsavel_id = _quem(usuario)
        estados.transicionar(
            travada,
            S.CONCLUIDA,
            acao=f"vistoria.concluir_{travada.tipo}",
            regra="VIS-04",
            mais_campos=("concluida_em", "responsavel"),
        )
        km = int(travada.km or 0)  # conferido nas pendências
        if km != veiculo.km_atual:
            veiculos.atualizar_km(veiculo, km, origem=_origem(travada, locacao))
        # A saída nova ativa a locação (fora de `aguardando_retirada`: 409). A correção só
        # acerta o km da saída enquanto a locação ainda aguarda a retirada.
        if saida and (
            travada.substitui_id is None or locacao.status == StatusLocacao.AGUARDANDO_RETIRADA
        ):
            locacoes.registrar_vistoria_saida(locacao, km=km, concluida_em=agora)
    _recarregar(vistoria)
    return vistoria


# --- Corrigir (VIS-04) ---


def corrigir(vistoria: Vistoria, motivo: str, usuario: Any) -> tuple[Vistoria, bool]:
    """Uma vistoria nova em `rascunho`, com os dados da concluída copiados e `substitui`
    apontando para ela. Se a correção já está aberta, devolve ela (`criada = False`)."""
    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo da correção."]})
    with transaction.atomic():
        travada = _travar(vistoria)
        if travada.status != S.CONCLUIDA or not travada.vigente:
            raise Conflito(
                "vistoria_nao_corrigivel", "Só a vistoria concluída e vigente pode ser corrigida."
            )
        aberta = Vistoria.objects.filter(substitui=travada, status=S.RASCUNHO).first()
        if aberta is not None:
            return aberta, False
        nova = Vistoria.objects.create(
            locacao_id=travada.locacao_id,
            veiculo_id=travada.veiculo_id,
            tipo=travada.tipo,
            km=travada.km,
            combustivel=travada.combustivel,
            itens=travada.itens,
            observacoes=travada.observacoes,
            responsavel_id=_quem(usuario),
            substitui=travada,
            motivo_correcao=texto,
        )
        fotos: dict[int, FotoVistoria] = {}
        for foto in FotoVistoria.ativos.filter(vistoria=travada):
            copia = FotoVistoria(
                vistoria=nova, posicao=foto.posicao, tirada_em=foto.tirada_em, por_id=foto.por_id
            )
            copia.arquivo.name = foto.arquivo.name  # o mesmo arquivo; nada é apagado
            copia.save()
            fotos[foto.pk] = copia
        for avaria in Avaria.objects.filter(vistoria=travada):
            Avaria.objects.create(
                vistoria=nova,
                veiculo_id=avaria.veiculo_id,
                descricao=avaria.descricao,
                preexistente=avaria.preexistente,
                valor_centavos=avaria.valor_centavos,
                vai_para_oficina=avaria.vai_para_oficina,
                foto=fotos.get(avaria.foto_id) if avaria.foto_id else None,
            )
        registrar_evento(
            "vistoria.corrigir",
            Categoria.OPERACAO,
            objeto=nova,
            depois=retrato(nova),
            motivo=texto,
            regra="VIS-04",
        )
    return nova, True
