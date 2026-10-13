"""Regras da importação por planilha (IMP-02, IMP-03, IMP-05; docs/api/importacao.md).

Único lugar que grava em `Importacao` e `LinhaImportacao`. O status da importação muda só por
`comum.estados.transicionar`, com auditoria. Cada cadastro passa pelo serviço do app dono
(`veiculos.services.cadastrar`, `clientes.services.cadastrar`), que audita em nome de quem pediu
a importação (o administrador ou o "Suporte Giro", nunca o Sistema).
"""

import json
import os
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Count

from apps.clientes import services as clientes
from apps.contas import selectors as contas
from apps.filiais.models import Filial
from apps.notificacoes.services import avisar
from apps.plataforma.services import registrar_passo_implantacao, vagas_no_plano
from apps.veiculos import services as veiculos
from apps.veiculos.models import Origem
from comum import arquivos, estados, relogio
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.auditoria import TipoAtor, ator_atual, registrar_evento, retrato
from comum.erros import (
    Conflito,
    ErroDeNegocio,
    ErroDeRegra,
    ErroDeValidacao,
    LimiteDoPlano,
    NaoEncontrado,
)
from comum.tarefas import ator_para_fila, schema_atual

from . import linhas, planilha
from .models import (
    CONTAGENS,
    Importacao,
    LinhaImportacao,
    StatusImportacao,
    StatusLinha,
    TipoImportacao,
)
from .selectors import valores

S = StatusImportacao
L = StatusLinha
DIAS_PARA_APAGAR = 30
EM_ANDAMENTO = (S.VALIDANDO, S.IMPORTANDO)
ABERTAS = (S.VALIDADA, S.CONCLUIDA)  # aceitam correção, ignorar e importar
A_GRAVAR = (L.PRONTA, L.ACIMA_DO_LIMITE)  # mudando de plano, as de fora entram de novo
CORRIGIVEIS = (L.PRONTA, L.COM_ERRO)
TIPO_DO_CONTEUDO = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "csv": "text/csv",
}
SUPORTE_GIRO = "Suporte Giro"


# --- Dados da linha (cifrados em clientes, ADR 0014) ---


def _guardar(linha: LinhaImportacao, tipo: str, dados: dict[str, str]) -> None:
    if tipo == TipoImportacao.CLIENTES:
        linha.definir_dados_cifrados(json.dumps(dados, ensure_ascii=False, sort_keys=True))
        linha.dados = {}
    else:
        linha.dados = dados


def _aplicar(linha: LinhaImportacao, resultado: linhas.Resultado) -> None:
    linha.erros = resultado.erros
    linha.status = L.COM_ERRO if resultado.erros else L.PRONTA
    linha.chave_placa = resultado.chaves.get("placa", "")
    linha.chave_chassi = resultado.chaves.get("chassi", "")
    linha.chave_documento = resultado.chaves.get("documento", "")


def _contar(importacao: Importacao) -> None:
    por_status = dict(importacao.itens.values_list("status").annotate(n=Count("id")).order_by())
    importacao.linhas = sum(por_status.values())
    importacao.prontas = por_status.get(L.PRONTA, 0)
    importacao.com_erro = por_status.get(L.COM_ERRO, 0)
    importacao.importadas = por_status.get(L.IMPORTADA, 0)
    importacao.acima_do_limite = por_status.get(L.ACIMA_DO_LIMITE, 0)


def _salvar_contagens(importacao: Importacao) -> None:
    _contar(importacao)
    importacao.save(update_fields=[*CONTAGENS, "atualizado_em"])


def _travar(importacao: Importacao) -> Importacao:
    travada: Importacao = Importacao.objects.select_for_update().get(pk=importacao.pk)
    return travada


def _apagar_arquivo(importacao: Importacao) -> None:
    if importacao.arquivo_caminho:
        arquivos.apagar_temporario(importacao.arquivo_caminho)
        importacao.arquivo_caminho = ""
        importacao.save(update_fields=["arquivo_caminho", "atualizado_em"])


# --- Envio ---


def _filial_padrao(tipo: str, filial_id: int | None, tem_coluna: bool) -> Filial | None:
    """A filial da coluna vazia. Obrigatória com mais de uma filial e sem a coluna."""
    if tipo != TipoImportacao.VEICULOS:
        return None
    if filial_id is not None:
        escolhida: Filial | None = Filial.ativos.filter(pk=filial_id).first()
        if escolhida is None:
            raise ErroDeValidacao({"filial_id": ["Escolha uma filial ativa."]})
        return escolhida
    ativas: list[Filial] = list(Filial.ativos.order_by("id")[:2])
    if len(ativas) == 1:
        return ativas[0]
    if tem_coluna:
        return None
    if not ativas:
        raise ErroDeValidacao({"filial_id": ["Cadastre a filial antes de importar veículos."]})
    raise ErroDeValidacao({"filial_id": ["Escolha a filial dos veículos."]})


def em_andamento(tipo: str) -> Conflito:
    return Conflito(
        "importacao_em_andamento",
        "Já há uma planilha deste tipo sendo conferida ou importada. Espere ela terminar.",
    )


def enviar(tipo: str, arquivo: Any, filial_id: int | None = None) -> Importacao:
    """POST /api/importacoes/: confere o arquivo e o cabeçalho na hora (400) e agenda a
    validação de cada linha. Nada é gravado nos cadastros."""
    nome = os.path.basename(str(arquivo.name or "planilha"))[:255]
    conteudo = arquivo.read(planilha.MAX_BYTES + 1)
    leitura = planilha.ler(nome, conteudo, tipo)
    filial = _filial_padrao(tipo, filial_id, "filial" in leitura.colunas)
    ator = ator_atual()
    agora = relogio.agora()
    with transaction.atomic():
        if Importacao.objects.filter(tipo=tipo, status__in=EM_ANDAMENTO).exists():
            raise em_andamento(tipo)
        importacao = Importacao.objects.create(
            tipo=tipo,
            arquivo_nome=nome,
            filial_padrao=filial,
            enviada_por_id=ator.id if ator.tipo == TipoAtor.USUARIO else None,
            enviada_por_nome=SUPORTE_GIRO if ator.tipo == TipoAtor.SUPORTE else ator.nome,
            enviada_em=agora,
            apagar_em=relogio.hoje() + timedelta(days=DIAS_PARA_APAGAR),
        )
        # Nome aleatório sob o prefixo do schema (AUD-05); o original fica só na tela.
        ext = planilha.extensao(nome)
        caminho = arquivos.caminho_privado(importacao, f"planilha.{ext}")
        arquivos.provedor().salvar(caminho, conteudo, TIPO_DO_CONTEUDO[ext])
        importacao.arquivo_caminho = caminho
        importacao.save(update_fields=["arquivo_caminho", "atualizado_em"])
        registrar_evento(
            "importacao.enviar",
            CategoriaAuditoria.CONFIGURACOES,
            objeto=importacao,
            depois=retrato(importacao),
            regra="IMP-02",
        )
        _agendar("importacao_validar", importacao)
    return importacao


def _agendar(nome: str, importacao: Importacao) -> None:
    from . import tasks

    tarefa = getattr(tasks, nome)
    schema = schema_atual()
    ator = ator_para_fila()
    transaction.on_commit(lambda: tarefa.delay(schema, importacao.pk, ator=ator))


# --- Validação (task importacao_validar) ---


def validar(importacao_id: int) -> None:
    """IMP-02: lê o arquivo e valida cada linha, sem gravar nos cadastros. Idempotente: só age
    em importação `validando`, e uma nova tentativa começa as linhas do zero."""
    importacao = Importacao.objects.filter(pk=importacao_id).first()
    if importacao is None or importacao.status != S.VALIDANDO:
        return
    try:
        conteudo = arquivos.provedor().ler(importacao.arquivo_caminho)
        leitura = planilha.ler(importacao.arquivo_nome, conteudo, importacao.tipo)
    except (ErroDeNegocio, KeyError, OSError) as problema:
        campos = getattr(problema, "campos", None) or {}
        mensagens = [m for lista in campos.values() for m in lista]
        importacao.aviso = {
            "codigo": "validacao",
            "mensagem": mensagens[0] if mensagens else "Não conseguimos ler a planilha.",
        }
        estados.transicionar(
            importacao, S.FALHOU, acao="importacao.falhar", regra="IMP-02", mais_campos=("aviso",)
        )
        _apagar_arquivo(importacao)
        return
    contexto = linhas.Contexto.carregar(importacao.filial_padrao_id)
    primeiras: dict[tuple[str, str], int] = {}

    def repetida(campo: str, chave: str) -> int | None:
        return primeiras.get((campo, chave))

    novas = []
    for lida in leitura.linhas:
        linha = LinhaImportacao(importacao=importacao, numero=lida.numero)
        _guardar(linha, importacao.tipo, lida.valores)
        resultado = linhas.validar(
            importacao.tipo, lida.valores, contexto, repetida, longas=lida.longas
        )
        _aplicar(linha, resultado)
        for campo, chave in resultado.chaves.items():
            if chave:
                primeiras.setdefault((campo, chave), lida.numero)
        novas.append(linha)
    with transaction.atomic():
        importacao.itens.all().delete()
        LinhaImportacao.objects.bulk_create(novas, batch_size=500)
        _contar(importacao)
        estados.transicionar(
            importacao, S.VALIDADA, acao="importacao.validar", regra="IMP-02", mais_campos=CONTAGENS
        )
    # O de clientes sai assim que as linhas cifradas estão gravadas.
    if importacao.tipo == TipoImportacao.CLIENTES:
        _apagar_arquivo(importacao)


# --- Correção e ignorar ---


def _linha_aberta(importacao: Importacao, numero: int, permitidos: tuple[str, ...]) -> Any:
    if importacao.status not in ABERTAS:
        raise Conflito(
            "importacao_fechada",
            "Esta importação não aceita mudanças agora.",
            {"status": importacao.status},
        )
    linha = importacao.itens.select_for_update().filter(numero=numero).first()
    if linha is None:
        raise NaoEncontrado("nao_encontrado", "Linha não encontrada.")
    if linha.status not in permitidos:
        raise Conflito(
            "linha_fechada", "Esta linha não pode mais ser mudada.", {"status": linha.status}
        )
    return linha


def _repetida_no_banco(linha: LinhaImportacao) -> linhas.Repetida:
    """Repetição com as outras linhas da importação, menos as ignoradas: vale a que veio antes
    na planilha ou a que já está pronta ou importada."""

    def repetida(campo: str, chave: str) -> int | None:
        outra = (
            LinhaImportacao.objects.filter(
                importacao_id=linha.importacao_id, **{f"chave_{campo}": chave}
            )
            .exclude(pk=linha.pk)
            .exclude(status=L.IGNORADA)
            .exclude(status=L.COM_ERRO, numero__gt=linha.numero)
            .order_by("numero")
            .values_list("numero", flat=True)
            .first()
        )
        return int(outra) if outra is not None else None

    return repetida


def corrigir(importacao: Importacao, numero: int, dados: dict[str, Any]) -> LinhaImportacao:
    """ "Corrigir aqui": junta os campos corrigidos e revalida a linha na hora."""
    conhecidas = {coluna.nome for coluna in planilha.COLUNAS[importacao.tipo]}
    with transaction.atomic():
        travada = _travar(importacao)
        linha = _linha_aberta(travada, numero, CORRIGIVEIS)
        atuais = valores(linha, travada.tipo)
        longas = []
        for coluna, valor in dados.items():
            if coluna not in conhecidas:
                continue  # coluna não reconhecida é descartada
            texto = planilha.texto(valor)
            if len(texto) > planilha.MAX_CELULA:
                longas.append(coluna)
                texto = texto[: planilha.MAX_CELULA]
            atuais[coluna] = texto
        atuais = {coluna: texto for coluna, texto in atuais.items() if texto}
        contexto = linhas.Contexto.carregar(travada.filial_padrao_id)
        resultado = linhas.validar(
            travada.tipo, atuais, contexto, _repetida_no_banco(linha), longas=longas
        )
        _guardar(linha, travada.tipo, atuais)
        _aplicar(linha, resultado)
        linha.save()
        _salvar_contagens(travada)
    importacao.refresh_from_db()
    return linha  # type: ignore[no-any-return]


def ignorar(importacao: Importacao, numero: int) -> LinhaImportacao:
    """Tira a linha da importação."""
    with transaction.atomic():
        travada = _travar(importacao)
        linha = _linha_aberta(travada, numero, (*CORRIGIVEIS, L.ACIMA_DO_LIMITE))
        linha.status = L.IGNORADA
        linha.save(update_fields=["status", "atualizado_em"])
        _salvar_contagens(travada)
    importacao.refresh_from_db()
    return linha  # type: ignore[no-any-return]


def cancelar(importacao: Importacao) -> Importacao:
    """Só `validada`; nada vai para os cadastros."""
    estados.transicionar(importacao, S.CANCELADA, acao="importacao.cancelar")
    return importacao


# --- Importar (task importacao_importar) ---


def nada_para_importar() -> ErroDeRegra:
    return ErroDeRegra("nada_para_importar", "Não há linha pronta para importar.")


def importar(importacao: Importacao) -> Importacao:
    """POST .../importar/: `importando`, e a task grava as linhas prontas."""
    with transaction.atomic():
        travada = _travar(importacao)
        if travada.status in ABERTAS and not travada.itens.filter(status__in=A_GRAVAR).exists():
            raise nada_para_importar()
        estados.transicionar(travada, S.IMPORTANDO, acao="importacao.importar", regra="IMP-03")
        _agendar("importacao_importar", travada)
    importacao.refresh_from_db()
    importacao._status_salvo = importacao.status
    return importacao


def _cadastrar(importacao: Importacao, dados: dict[str, Any]) -> Any:
    if importacao.tipo == TipoImportacao.VEICULOS:
        origem = veiculos.OrigemDaMudanca(Origem.IMPORTACAO, importacao.pk)
        return veiculos.cadastrar(dados, origem=origem)
    return clientes.cadastrar(dados)


def _plural(n: int, um: str, varios: str) -> str:
    return f"{n} {um if n == 1 else varios}"


def _aviso_do_limite(gravadas: int, fora: int, plano: str) -> dict[str, str]:
    ficaram = "ficou" if fora == 1 else "ficaram"
    return {
        "codigo": "IMP-03",
        "mensagem": (
            f"Importamos {_plural(gravadas, 'veículo', 'veículos')}, o limite do plano {plano}. "
            f"{fora} {ficaram} de fora: mude de plano para importar o resto."
        ),
    }


def gravar(importacao_id: int) -> None:
    """IMP-03: grava as linhas prontas na ordem da planilha, cada uma no próprio savepoint, até
    o limite do plano (o `UsoEmpresa` fica travado do começo ao fim). Idempotente: só age em
    importação `importando`."""
    importacao = Importacao.objects.filter(pk=importacao_id).first()
    if importacao is None or importacao.status != S.IMPORTANDO:
        return
    tipo = importacao.tipo
    with transaction.atomic():
        importacao = _travar(importacao)
        vagas = vagas_no_plano("veiculos") if tipo == TipoImportacao.VEICULOS else None
        contexto = linhas.Contexto.carregar(importacao.filial_padrao_id)
        gravadas = fora = 0
        for linha in importacao.itens.filter(status__in=A_GRAVAR).order_by("numero"):
            texto = valores(linha, tipo)
            convertida = linhas.converter(tipo, texto, contexto)
            if vagas is not None and vagas.cabem is not None and gravadas >= vagas.cabem:
                linha.status, linha.erros = L.ACIMA_DO_LIMITE, []
            elif convertida.erros:  # categoria desativada no meio do caminho, por exemplo
                linha.status, linha.erros = L.COM_ERRO, convertida.erros
            else:
                try:
                    with transaction.atomic():
                        objeto = _cadastrar(importacao, convertida.dados)
                except LimiteDoPlano:
                    linha.status, linha.erros = L.ACIMA_DO_LIMITE, []
                except ErroDeNegocio as problema:
                    linha.status = L.COM_ERRO
                    linha.erros = linhas.erros_do_cadastro(tipo, problema, texto)
                else:
                    gravadas += 1
                    linha.status, linha.erros = L.IMPORTADA, []
                    linha.objeto_tipo = "veiculo" if tipo == TipoImportacao.VEICULOS else "cliente"
                    linha.objeto_id = objeto.pk
            fora += linha.status == L.ACIMA_DO_LIMITE
            linha.save(
                update_fields=["status", "erros", "objeto_tipo", "objeto_id", "atualizado_em"]
            )
        importacao.aviso = _aviso_do_limite(gravadas, fora, vagas.plano) if fora and vagas else None
        importacao.concluida_em = relogio.agora()
        _contar(importacao)
        estados.transicionar(
            importacao,
            S.CONCLUIDA,
            acao="importacao.concluir",
            regra="IMP-03",
            mais_campos=(*CONTAGENS, "aviso", "concluida_em"),
        )
        registrar_passo_implantacao("importar")  # IMP-05: etapa "Dados" do funil
        _avisar_conclusao(importacao, gravadas)


def interromper(importacao_id: int) -> None:
    """A gravação passou do tempo: nada ficou gravado e a importação volta para `validada`."""
    importacao = Importacao.objects.filter(pk=importacao_id, status=S.IMPORTANDO).first()
    if importacao is not None:
        estados.transicionar(
            importacao, S.VALIDADA, acao="importacao.interromper", motivo="Tempo esgotado"
        )


def _avisar_conclusao(importacao: Importacao, gravadas: int) -> None:
    ator = ator_atual()
    if ator.tipo == TipoAtor.USUARIO and ator.id is not None:
        destinatarios: list[int] = [ator.id]
    else:
        destinatarios = list(contas.administradores().values_list("id", flat=True))
    if importacao.tipo == TipoImportacao.VEICULOS:
        o_que = _plural(gravadas, "veículo importado", "veículos importados")
    else:
        o_que = _plural(gravadas, "cliente importado", "clientes importados")
    avisar(
        destinatarios,
        tipo="importacao_concluida",
        titulo=f"Importação concluída: {o_que}",
        link="/implantacao",
    )


# --- Limpeza (task importacao_limpar) ---


def limpar_vencidas() -> int:
    """Arquivo e linhas saem 30 dias depois do envio: não são registro de negócio."""
    vencidas = list(Importacao.objects.filter(apagar_em__lte=relogio.hoje()))
    for importacao in vencidas:
        if importacao.arquivo_caminho:
            arquivos.apagar_temporario(importacao.arquivo_caminho)
        importacao.delete()
    return len(vencidas)
