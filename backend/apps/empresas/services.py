"""Mudanças na configuração da empresa, sempre auditadas."""

import hashlib
import logging
import re
from typing import Any

from django.core.cache import cache
from django.db import transaction

from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma import services as plataforma_services
from comum import arquivos, modulos
from comum.auditoria import Categoria, auditar
from comum.conexao import schema_atual
from comum.erros import ErroDeRegra, ErroDeValidacao

from . import marca as cores_da_marca
from . import selectors
from .logo import LogoInvalido, limpar_logo
from .models import ConfiguracaoEmpresa

logger = logging.getLogger(__name__)

# PLT-12: o verbo da recusa por recurso que sai ("Para deixar de alugar, ...").
DEIXAR_DE = {"locacoes_vistoria": "alugar", "vendas_comissoes": "vender"}


def criar_configuracao_padrao() -> ConfiguracaoEmpresa:
    """Linha única com os padrões. Idempotente."""
    configuracao, _ = ConfiguracaoEmpresa.objects.get_or_create(unica=1)
    return configuracao


def definir_exige_2fa_todos(valor: bool) -> ConfiguracaoEmpresa:
    """USR-02: o administrador exige 2 etapas de todos.

    Ligar derruba, no próximo uso, os tokens sem `otp` de quem ainda não confirmou o código
    (ADR 0013, item 3): a autenticação lê este valor a cada requisição.
    """
    with transaction.atomic():
        criar_configuracao_padrao()
        configuracao = ConfiguracaoEmpresa.objects.select_for_update().get(unica=1)
        if configuracao.exige_2fa_todos == valor:
            return configuracao
        with auditar(configuracao, "empresa.exigir_2fa_todos", Categoria.SEGURANCA, regra="USR-02"):
            configuracao.exige_2fa_todos = valor
            configuracao.save(update_fields=["exige_2fa_todos", "atualizado_em"])
    return configuracao


def _juntar(textos: list[str]) -> str:
    if len(textos) <= 1:
        return "".join(textos)
    return f"{', '.join(textos[:-1])} e {textos[-1]}"


def mudar_ramo(atividade: str, trabalha_com: str, por: object) -> ConfiguracaoEmpresa:
    """PLT-12, ADR 0024, item 9: o único caminho para mudar o ramo (passo 7 e Configurações).

    Recusa a atividade que o plano não aceita e a troca que tira um módulo com algo aberto
    (422 `PLT-12`); nada é apagado. Mesmo ramo: sem evento, e o passo `ramo` é marcado.
    """
    plano = plataforma_selectors.empresa_atual().plano
    aceitas = plataforma_selectors.atividades_aceitas(plano)
    with transaction.atomic():
        criar_configuracao_padrao()
        configuracao = ConfiguracaoEmpresa.objects.select_for_update().get(unica=1)
        if atividade not in aceitas:
            raise ErroDeRegra(
                "PLT-12",
                f"O plano {plano.nome if plano else ''} não inclui vendas. "
                "Escolha locação, ou locação e venda.",
                {"motivo": "plano", "atividades_aceitas": list(aceitas)},
            )
        antes = plataforma_selectors.recursos_para(plano, configuracao.atividade)
        depois = plataforma_selectors.recursos_para(plano, atividade)
        saem = sorted(antes - depois)
        abertos = modulos.pendencias(saem)
        if abertos:
            recurso = modulos.RECURSO_DO_GRUPO[abertos[0]["grupo"]]
            texto = _juntar([grupo["texto"] for grupo in abertos])
            raise ErroDeRegra(
                "PLT-12",
                f"Para deixar de {DEIXAR_DE[recurso]}, resolva o que está aberto: {texto}.",
                {
                    "motivo": "abertos",
                    "recurso": recurso,
                    "abertos": abertos,
                    "abertos_texto": texto,
                },
            )
        if (configuracao.atividade, configuracao.trabalha_com) != (atividade, trabalha_com):
            with auditar(
                configuracao,
                "empresa.mudar_ramo",
                Categoria.CONFIGURACOES,
                regra="PLT-12",
                extras=lambda: {
                    "recursos": sorted(
                        plataforma_selectors.recursos_para(plano, configuracao.atividade)
                    )
                },
            ):
                configuracao.atividade = atividade
                configuracao.trabalha_com = trabalha_com
                configuracao.save(update_fields=["atividade", "trabalha_com", "atualizado_em"])
        plataforma_services.registrar_passo_implantacao("ramo")
    return configuracao


# --- Marca (`docs/api/empresas.md`, "Escrita da marca"; ADR 0022; T-153) ---

NOME_MAXIMO = 80
CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
MENSAGEM_NOME = "Use até 80 caracteres."
MENSAGEM_COR = "Use uma cor no formato #RRGGBB."
MENSAGEM_LOGO_E_REMOVER = "Envie um logo novo ou remova o atual, não os dois."
TIPOS_DO_LOGO = {"svg": "image/svg+xml", "png": "image/png"}


def _validar_nome_e_cor(
    nome_exibicao: str | None, cor: str | None
) -> tuple[str | None, str | None, dict[str, list[str]]]:
    """Nome sem espaços nas pontas nem caracteres de controle, até 80; cor `#RRGGBB` em
    maiúsculas. Vazio vale (volta ao padrão); `None` é "não veio"."""
    erros: dict[str, list[str]] = {}
    if nome_exibicao is not None:
        nome_exibicao = CONTROLE.sub("", nome_exibicao).strip()
        if len(nome_exibicao) > NOME_MAXIMO:
            erros["nome_exibicao"] = [MENSAGEM_NOME]
    if cor is not None:
        cor = cor.strip().upper()
        if cor and not cores_da_marca.FORMATO.match(cor):
            erros["cor"] = [MENSAGEM_COR]
    return nome_exibicao, cor, erros


def simular_marca(nome_exibicao: str | None = None, cor: str | None = None) -> dict[str, Any]:
    """`POST /api/marca/simular/` (ADR 0005): as contas de `GET /api/marca/`, sem gravar.
    O que não vem usa o salvo; vazio simula a volta ao padrão."""
    nome_exibicao, cor, erros = _validar_nome_e_cor(nome_exibicao, cor)
    if erros:
        raise ErroDeValidacao(erros)
    salva = selectors.configuracao()
    if nome_exibicao is None:
        nome_exibicao = salva.nome_exibicao
    if cor is None:
        cor = salva.cor_marca
    nome = nome_exibicao or plataforma_selectors.empresa_atual().nome_exibicao
    return {
        "nome_exibicao": nome,
        "iniciais": cores_da_marca.iniciais(nome),
        **cores_da_marca.cores(cor),
    }


def _caminho_do_logo(conteudo: bytes, extensao: str) -> str:
    """Nome pelo resumo do conteúdo limpo: é o que aparece na auditoria, nunca o conteúdo."""
    resumo = hashlib.sha256(conteudo).hexdigest()[:16]
    return f"{schema_atual()}/empresas/marca/logo-{resumo}.{extensao}"


def _apagar_arquivo(caminho: str) -> None:
    """O logo não é registro de negócio (`empresas.md`): o arquivo trocado não fica guardado."""
    try:
        arquivos.provedor().apagar(caminho)
    except Exception:  # o storage fora do ar não desfaz a marca salva
        logger.exception("Não foi possível apagar o arquivo do logo %s", caminho)


def salvar_marca(
    *,
    nome_exibicao: str | None = None,
    cor: str | None = None,
    logo: bytes | None = None,
    remover_logo: bool = False,
    por: Any = None,
) -> ConfiguracaoEmpresa:
    """`PATCH /api/marca/`: nome, cor e logo, só o que vier (`None` é "não veio").

    O logo é limpo (ADR 0022) e gravado antes da transação; nela, a linha única é travada e a
    mudança vira o evento `empresa.alterar_marca`. Sem mudança, sem evento e sem versão nova.
    No `on_commit`, sai a chave `marca:<schema>` e o arquivo antigo; se a transação falhar, sai
    o novo. Marca o passo `marca` da implantação (IMP-05) em toda gravação aceita.
    """
    nome_exibicao, cor, erros = _validar_nome_e_cor(nome_exibicao, cor)
    if logo is not None and remover_logo:
        erros["remover_logo"] = [MENSAGEM_LOGO_E_REMOVER]
    if erros:
        raise ErroDeValidacao(erros)

    caminho_novo: str | None = None
    gravou_novo = False
    if logo is not None:
        try:
            limpo = limpar_logo(logo)
        except LogoInvalido as recusa:
            if recusa.suspeito:
                logger.warning(
                    "Logo recusado (S-12): schema=%s usuario=%s motivo=%s",
                    schema_atual(),
                    getattr(por, "pk", None),
                    recusa.mensagem,
                )
            raise ErroDeValidacao({"logo": [recusa.mensagem]}) from recusa
        caminho_novo = _caminho_do_logo(limpo.conteudo, limpo.extensao)
        provedor = arquivos.provedor()
        if not provedor.existe(caminho_novo):
            provedor.salvar(caminho_novo, limpo.conteudo, TIPOS_DO_LOGO[limpo.extensao])
            gravou_novo = True

    try:
        with transaction.atomic():
            criar_configuracao_padrao()
            configuracao = ConfiguracaoEmpresa.objects.select_for_update().get(unica=1)
            antigo = configuracao.logo.name or None
            novos: dict[str, Any] = {}
            if nome_exibicao is not None and nome_exibicao != configuracao.nome_exibicao:
                novos["nome_exibicao"] = nome_exibicao
            if cor is not None and cor != configuracao.cor_marca:
                novos["cor_marca"] = cor
            if caminho_novo is not None and caminho_novo != antigo:
                novos["logo"] = caminho_novo
                novos["logo_largura"], novos["logo_altura"] = limpo.largura, limpo.altura
            elif remover_logo and antigo:
                novos.update(logo=None, logo_largura=None, logo_altura=None)
            if novos:
                with auditar(configuracao, "empresa.alterar_marca", Categoria.CONFIGURACOES):
                    for campo, valor in novos.items():
                        setattr(configuracao, campo, valor)
                    configuracao.save(update_fields=[*novos, "atualizado_em"])
                # Já agora, para a resposta do PATCH ler a marca nova, e de novo no `on_commit`:
                # uma leitura no meio da transação pode ter guardado a antiga.
                chave = selectors.chave_da_marca()
                cache.delete(chave)
                trocou_logo = "logo" in novos and antigo is not None

                def depois() -> None:
                    cache.delete(chave)
                    if trocou_logo and antigo is not None:
                        _apagar_arquivo(antigo)

                transaction.on_commit(depois)
            plataforma_services.registrar_passo_implantacao("marca")
    except BaseException:
        if gravou_novo and caminho_novo is not None:
            _apagar_arquivo(caminho_novo)
        raise
    return configuracao
