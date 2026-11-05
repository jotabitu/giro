"""Situação de um CNPJ antes de criar a empresa (`PLT-16`, `AUD-08`).

Um módulo só para a checagem, usado por `criar_empresa` (as duas portas: Django Admin e compra
pública) e pela compra pública, sem importar `services` nem `selectors` (evita ciclo). Reexportado
em `selectors.situacao_do_cnpj`, nome citado no contrato `compra.md`.
"""

from dataclasses import dataclass

from django_tenants.utils import get_public_schema_name, schema_context

from .models import Empresa, FaturaAssinatura, SituacaoCnpj, StatusFatura

MENSAGEM_EM_USO = "Este CNPJ já tem uma assinatura no Giro. Para voltar, fale com a equipe Giro."
MENSAGEM_FATURA_EM_ATRASO = (
    "Há uma fatura em aberto da assinatura anterior. "
    "Fale com a equipe Giro para pagar antes de assinar de novo."
)
AVISO_JA_FOI_CLIENTE = "Este CNPJ já usou o teste grátis. A 1ª fatura vence hoje."


@dataclass(frozen=True)
class Situacao:
    situacao: str
    # A empresa apagada mais recente com o mesmo CNPJ (`ja_foi_cliente` e `fatura_em_atraso`).
    empresa_anterior: Empresa | None = None


def situacao_do_cnpj(cnpj: str) -> Situacao:
    """Só dígitos na entrada.

    - `em_uso`: há empresa não apagada com o CNPJ, em qualquer estado (a `cancelada` com os dados
      ainda guardados volta pela reativação, `PLT-06`).
    - `fatura_em_atraso`: só há empresas apagadas, e uma delas deixou fatura `atrasada`.
    - `ja_foi_cliente`: só há empresas apagadas, sem fatura atrasada: compra sem teste.
    - `nova`: nenhuma linha com o CNPJ (ou o CNPJ já saiu da linha apagada, `AUD-08`).
    """
    with schema_context(get_public_schema_name()):
        linhas = Empresa.objects.filter(cnpj=cnpj)
        if linhas.filter(apagada_em__isnull=True).exists():
            return Situacao(SituacaoCnpj.EM_USO)
        anterior = linhas.order_by("-apagada_em", "-id").first()
        if anterior is None:
            return Situacao(SituacaoCnpj.NOVA)
        atrasada = FaturaAssinatura.objects.filter(
            empresa__in=linhas, status=StatusFatura.ATRASADA
        ).exists()
        if atrasada:
            return Situacao(SituacaoCnpj.FATURA_EM_ATRASO, anterior)
        return Situacao(SituacaoCnpj.JA_FOI_CLIENTE, anterior)
