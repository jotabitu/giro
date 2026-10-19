"""Mudanças na configuração da empresa, sempre auditadas."""

from django.db import transaction

from apps.plataforma import selectors as plataforma_selectors
from apps.plataforma import services as plataforma_services
from comum import modulos
from comum.auditoria import Categoria, auditar
from comum.erros import ErroDeRegra

from .models import ConfiguracaoEmpresa

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
