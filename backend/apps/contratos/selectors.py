"""Leituras de contratos. Interface para os outros apps (`docs/api/contratos.md`)."""

from .models import Finalidade, ModeloContrato


def modelo_publicado(finalidade: str = Finalidade.LOCACAO) -> ModeloContrato | None:
    """`IMP-04`: o modelo publicado e não arquivado da finalidade, o mais recente."""
    return (
        ModeloContrato.objects.filter(finalidade=finalidade, publicado=True, arquivado=False)
        .order_by("-publicado_em", "-id")
        .first()
    )
