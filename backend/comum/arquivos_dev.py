"""Serve, só no desenvolvimento, os arquivos do armazenamento "falso" (T-210).

A URL assinada do provedor falso aponta para `/api/arquivos-dev/<caminho>` na mesma origem da
tela, para a foto abrir no navegador sem a CSP bloqueá-la. Confere a assinatura e a validade
como o S3 faria. A rota só existe com `GIRO_ARQUIVOS_FALSOS_BASE` relativa (`dev.py`).
"""

import hmac
from urllib.parse import unquote

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseForbidden

from comum import arquivos, relogio


def servir(request: HttpRequest, caminho: str) -> HttpResponse:
    expira = request.GET.get("expira", "")
    nonce = request.GET.get("nonce", "")
    assinatura = request.GET.get("assinatura", "")
    baixar = request.GET.get("baixar", "")
    esperada = arquivos.assinar(unquote(caminho), expira, nonce, baixar)
    if not hmac.compare_digest(assinatura, esperada):
        return HttpResponseForbidden("Assinatura inválida.")
    if not expira.isdigit() or int(expira) < int(relogio.agora().timestamp()):
        return HttpResponseForbidden("Link vencido.")
    guardado = arquivos.ler_falso(unquote(caminho))
    if guardado is None:
        raise Http404
    conteudo, tipo = guardado
    resposta = HttpResponse(conteudo, content_type=tipo)
    resposta["Cache-Control"] = "private, no-store"
    resposta["X-Content-Type-Options"] = "nosniff"
    if baixar:
        # O nome já entrou na assinatura; o formato é conferido de novo (ADR 0036, item 4).
        try:
            resposta["Content-Disposition"] = arquivos.disposicao_de_download(baixar)
        except ValueError:
            return HttpResponseForbidden("Nome de arquivo inválido.")
    return resposta
