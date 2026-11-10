"""Fotos do QXA-4B21 (VEI-10, T-414; linha "Fotos do QXA-4B21" dos dados de teste).

- Galeria: em 12 mar 2025 a Mariana envia, pelo serviço, lateral, frente e painel, nesta ordem, e
  escolhe a frente como capa. Resultado: 3 ativas, a frente com `numero` 1.
- Vistoria: a saída concluída da LOC-2841 (a que `seed/financeiro._saida` cria) ganha 12 fotos,
  as 5 posições fixas e 7 de avaria, tiradas em 23 set. Sem `Avaria`: o bloco `avarias` e os
  números do seed não mudam.

As imagens são fictícias, geradas na hora com o Pillow (nada binário no git). Idempotente: cada
parte só roda se o QXA-4B21 (ou a vistoria) ainda não tem foto. Os outros 85 veículos ficam sem
galeria, e as outras vistorias, sem fotos.
"""

import io
from datetime import datetime, timedelta

from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont

from apps.contas.models import Usuario
from apps.veiculos import services as veiculos_services
from apps.veiculos.models import FotoVeiculo, Veiculo
from apps.vistorias.models import POSICOES_OBRIGATORIAS, FotoVistoria, PosicaoFoto, Vistoria

from .ator import como
from .frota import EMAIL_DA_ADMINISTRADORA
from .relogio import FUSO, RelogioDoSeed

PLACA = "QXA4B21"
GALERIA = ("Lateral", "Frente", "Painel")
CAPA = "Frente"
AVARIAS_NA_VISTORIA = 7
TIRADAS_EM = datetime(2026, 9, 23, 9, 2, tzinfo=FUSO)


def imagem_ficticia(rotulo: str, nome: str) -> "ContentFile[bytes]":  # genérico só no stub
    """JPG 1600×1200, fundo neutro, com "QXA-4B21 · <rótulo> · foto fictícia"."""
    imagem = Image.new("RGB", (1600, 1200), (214, 217, 222))
    desenho = ImageDraw.Draw(imagem)
    texto = f"QXA-4B21 · {rotulo} · foto fictícia"
    try:
        fonte: ImageFont.FreeTypeFont | ImageFont.ImageFont = ImageFont.load_default(size=72)
    except (OSError, TypeError):  # Pillow sem FreeType: a fonte pequena de sempre
        fonte = ImageFont.load_default()
    esquerda, topo, direita, base = desenho.textbbox((0, 0), texto, font=fonte)
    posicao = ((1600 - (direita - esquerda)) / 2, (1200 - (base - topo)) / 2)
    desenho.text(posicao, texto, fill=(60, 64, 72), font=fonte)
    saida = io.BytesIO()
    imagem.save(saida, format="JPEG", quality=85)
    return ContentFile(saida.getvalue(), name=nome)


def _galeria(qxa: Veiculo, relogio: RelogioDoSeed) -> bool:
    if FotoVeiculo.objects.filter(veiculo=qxa).exists():
        return False
    mariana = Usuario.objects.get(email=EMAIL_DA_ADMINISTRADORA)
    enviadas = {}
    antes = relogio.agora  # o relógio volta ao ponto em que estava
    try:
        with como(mariana):
            for minuto, rotulo in enumerate(GALERIA):
                relogio.em(f"2025-03-12 10:0{minuto}")
                arquivo = imagem_ficticia(rotulo, f"{rotulo.lower()}.jpg")
                enviadas[rotulo] = veiculos_services.enviar_foto(qxa, arquivo)
            relogio.em("2025-03-12 10:05")
            veiculos_services.usar_como_capa(qxa, enviadas[CAPA].pk)
    finally:
        relogio.em(antes.astimezone(FUSO).replace(tzinfo=None).isoformat(sep=" "))
    return True


def _vistoria(qxa: Veiculo) -> bool:
    saida = (
        Vistoria.objects.filter(
            veiculo=qxa, tipo="saida", status="concluida", locacao__codigo="LOC-2841"
        )
        .order_by("-concluida_em")
        .first()
    )
    if saida is None or FotoVistoria.objects.filter(vistoria=saida).exists():
        return False
    posicoes = [*POSICOES_OBRIGATORIAS, *[PosicaoFoto.AVARIA] * AVARIAS_NA_VISTORIA]
    avaria = 0
    for indice, posicao in enumerate(posicoes):
        if posicao == PosicaoFoto.AVARIA:
            avaria += 1
            rotulo = f"Avaria {avaria}"
        else:
            rotulo = PosicaoFoto(posicao).label
        # Criada direto, como a vistoria do seed já é: a vistoria está concluída.
        foto = FotoVistoria.objects.create(
            vistoria=saida,
            posicao=posicao,
            tirada_em=TIRADAS_EM + timedelta(seconds=30 * indice),
            por_id=saida.responsavel_id,
        )
        foto.arquivo.save(f"{posicao}.jpg", imagem_ficticia(rotulo, f"{posicao}.jpg"), save=True)
    return True


def garantir_fotos_do_qxa(relogio: RelogioDoSeed) -> bool:
    """A galeria e as fotos da vistoria do QXA-4B21. O relógio volta ao ponto em que estava."""
    qxa = Veiculo.objects.filter(placa=PLACA).first()
    if qxa is None:
        return False
    galeria = _galeria(qxa, relogio)
    vistoria = _vistoria(qxa)
    return galeria or vistoria
