"""Pedido do titular (AUD-06) atendido pela equipe Giro até a tela da fase 2 (T-369).

Os comandos `exportar_titular` e `anonimizar_titular` chamam estas funções. Só o Dono da
plataforma as usa: a exportação traz CPF e CNH completos, que o suporte nunca vê (AUD-09). Cada
pedido grava um evento na auditoria da empresa, com a equipe como ator (AUD-03), e outro na da
plataforma. A anonimização segue `clientes.md` ("LGPD do titular"): contratos e registros
financeiros ficam, ligados ao cadastro anonimizado.
"""

import io
import json
import logging
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from django.apps import apps
from django.db import models, transaction
from django_tenants.utils import get_public_schema_name, schema_context, tenant_context

from comum import arquivos, relogio
from comum.auditoria import Ator, Categoria, TipoAtor, auditar, registrar_evento, usar_ator
from comum.campos import CampoCifrado, CampoHashBusca, anonimizar_cifrado
from comum.erros import Conflito, ErroDeNegocio, ErroDeRegra, ErroDeValidacao, SemPermissao

from . import selectors, services
from .models import Cliente, DocumentoCliente

logger = logging.getLogger(__name__)

CIFRADOS = ("documento", "cnh_numero", "responsavel_cpf")
NOME_ANONIMO = "Cliente anonimizado"
# Nome, contato, endereço e referência (clientes.md). Categoria e datas da CNH não identificam
# a pessoa (ADR 0014, item 3) e ficam.
CAMPOS_APAGADOS = (
    "email",
    "profissao",
    "responsavel_nome",
    "responsavel_celular",
    "cep",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cidade",
    "uf",
    "referencia_nome",
    "referencia_parentesco",
    "referencia_telefone",
)
# O que o titular recebe além do cadastro: os registros ligados a ele, como estão.
LIGADOS = (
    ("locacoes", "locacoes.Locacao"),
    ("contratos", "contratos.Contrato"),
    ("contas_receber", "financeiro.ContaReceber"),
    ("reembolsos", "financeiro.Reembolso"),
)


@dataclass(frozen=True)
class Pedido:
    """Quem da equipe atende e por quê. `dono` é o usuário do `public`."""

    dono: Any
    motivo: str


def texto_do_erro(erro: ErroDeNegocio) -> str:
    """A mensagem para o terminal, com o campo quando é validação."""
    if isinstance(erro, ErroDeValidacao):
        return " ".join(" ".join(textos) for textos in erro.campos.values())
    return erro.mensagem


def conferir_pedido(email: str, motivo: str) -> Pedido:
    """Só o Dono ativo da plataforma, sempre com motivo."""
    from apps.contas.models import FuncaoPlataforma, StatusUsuario, Usuario

    texto = (motivo or "").strip()
    if not texto:
        raise ErroDeValidacao({"motivo": ["Informe o motivo (de preferência o chamado)."]})
    with schema_context(get_public_schema_name()):
        dono = Usuario.objects.filter(email=(email or "").strip().lower()).first()
    if (
        dono is None
        or dono.funcao_plataforma != FuncaoPlataforma.DONO
        or dono.status != StatusUsuario.ATIVO
    ):
        raise SemPermissao("permissao", "Só o Dono ativo da plataforma atende o titular.")
    return Pedido(dono=dono, motivo=texto)


def empresa_para_titular(schema: str) -> Any:
    from apps.plataforma.models import Empresa

    with schema_context(get_public_schema_name()):
        empresa = Empresa.objects.filter(schema_name=schema).first()
    if empresa is None or schema == get_public_schema_name():
        raise ErroDeValidacao({"schema": ["Empresa não encontrada."]})
    if empresa.apagada_em is not None:
        raise Conflito("empresa_apagada", "Os dados desta empresa já foram apagados (AUD-08).")
    return empresa


def _ator(pedido: Pedido) -> Ator:
    return Ator(tipo=TipoAtor.SUPORTE, nome=f"Equipe Giro: {pedido.dono.nome}", id=pedido.dono.pk)


def _registrar_na_plataforma(empresa: Any, acao: str, pedido: Pedido, cliente_id: int) -> None:
    with schema_context(get_public_schema_name()), usar_ator(_ator(pedido)):
        registrar_evento(
            acao,
            Categoria.SUPORTE,
            objeto=empresa,
            depois={"cliente_id": cliente_id},
            motivo=pedido.motivo,
            regra="AUD-06",
        )


# --- Exportar ---


def _valor(valor: Any) -> Any:
    if isinstance(valor, models.fields.files.FieldFile):
        return valor.name or None
    if isinstance(valor, int | float | str | bool) or valor is None:
        return valor
    return str(valor)  # datas, Decimal, UUID


def _linha(objeto: models.Model) -> dict[str, Any]:
    """Os campos do registro, sem cifrados nem hashes de busca."""
    return {
        campo.attname: _valor(getattr(objeto, campo.attname))
        for campo in objeto._meta.concrete_fields
        if not isinstance(campo, CampoCifrado | CampoHashBusca) and campo.name != "id_cifra"
    }


def _cadastro(cliente: Cliente) -> dict[str, Any]:
    dados = _linha(cliente)
    for nome in CIFRADOS:
        dados[nome] = getattr(cliente, f"{nome}_claro")()
    return dados


def _guardar(zipado: zipfile.ZipFile, pasta: str, registro_id: int, arquivo: Any) -> str | None:
    if not arquivo:
        return None
    destino = f"{pasta}/{registro_id}-{PurePosixPath(arquivo.name).name}"
    zipado.writestr(destino, arquivos.provedor().ler(arquivo.name))
    return destino


def exportar(empresa: Any, cliente_id: int, pedido: Pedido) -> bytes:
    """ZIP com `dados.json` (cadastro decifrado e registros ligados) e os arquivos do titular:
    documentos (também os substituídos) e PDFs dos contratos."""
    with tenant_context(empresa):
        cliente = Cliente.objects.get(pk=cliente_id)
        saida = io.BytesIO()
        with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as zipado:
            dados: dict[str, Any] = {
                "empresa": empresa.nome_exibicao,
                "gerado_em": relogio.agora().isoformat(),
                "cliente": _cadastro(cliente),
                "documentos": [],
            }
            for documento in DocumentoCliente.objects.filter(cliente=cliente).order_by("pk"):
                linha = _linha(documento)
                linha["arquivo"] = _guardar(zipado, "documentos", documento.pk, documento.arquivo)
                dados["documentos"].append(linha)
            for chave, rotulo in LIGADOS:
                modelo = apps.get_model(rotulo)
                linhas = []
                for registro in modelo.objects.filter(cliente=cliente).order_by("pk"):
                    linha = _linha(registro)
                    if rotulo == "contratos.Contrato":
                        linha.pop("versao_texto_html", None)  # o PDF vai inteiro
                        for campo in ("pdf", "pdf_assinado"):
                            linha[campo] = _guardar(
                                zipado, f"contratos/{campo}", registro.pk, getattr(registro, campo)
                            )
                    linhas.append(linha)
                dados[chave] = linhas
            zipado.writestr(
                "dados.json", json.dumps(dados, ensure_ascii=False, indent=2, sort_keys=True)
            )
        with usar_ator(_ator(pedido)):
            registrar_evento(
                "cliente.exportar_titular",
                Categoria.SUPORTE,
                objeto=cliente,
                motivo=pedido.motivo,
                regra="AUD-06",
            )
    _registrar_na_plataforma(empresa, "empresa.exportar_titular", pedido, cliente_id)
    return saida.getvalue()


# --- Anonimizar ---


def anonimizar(empresa: Any, cliente_id: int, pedido: Pedido, confirmacao: str) -> int:
    """Apaga os cifrados (hash aleatório), troca nome, contato, endereço e referência e grava
    `anonimizado_em`; os documentos ficam inativos e sem arquivo. Recusa com pendência (422
    `cliente_com_pendencia`) ou já anonimizado. Devolve quantos arquivos saíram."""
    with tenant_context(empresa):
        caminhos: list[str] = []
        with transaction.atomic(), usar_ator(_ator(pedido)):
            cliente = Cliente.objects.select_for_update().get(pk=cliente_id)
            if cliente.anonimizado_em is not None:
                raise Conflito("cliente_anonimizado", "Este cliente já foi anonimizado.")
            if confirmacao.strip() != cliente.nome:
                raise ErroDeValidacao({"confirmacao": ["Digite o nome do cliente como está."]})
            pendencia = selectors.pendencias_para_inativar(cliente)
            if any(pendencia.values()):
                raise ErroDeRegra(
                    "cliente_com_pendencia",
                    "O cliente tem locação, venda ou valor em aberto.",
                    pendencia,
                )
            with auditar(
                cliente,
                "cliente.anonimizar_titular",
                Categoria.SUPORTE,
                motivo=pedido.motivo,
                regra="AUD-06",
            ):
                for nome in CIFRADOS:
                    anonimizar_cifrado(cliente, nome)
                cliente.nome = NOME_ANONIMO
                cliente.celular = ""
                cliente.nascimento = None
                for nome in CAMPOS_APAGADOS:
                    setattr(cliente, nome, "")
                cliente.anonimizado_em = relogio.agora()
                cliente.save()
            for documento in DocumentoCliente.objects.select_for_update().filter(cliente=cliente):
                with auditar(
                    documento,
                    "documento_cliente.anonimizar_titular",
                    Categoria.SUPORTE,
                    regra="AUD-06",
                ):
                    if documento.arquivo:
                        caminhos.append(documento.arquivo.name)
                    documento.arquivo = None
                    documento.ativo = False
                    documento.save(update_fields=["arquivo", "ativo", "atualizado_em"])
            # Sem documento e sem CPF, o cadastro volta a `incompleto` (CLI-03).
            services.acertar_cadastro(cliente)
    _registrar_na_plataforma(empresa, "empresa.anonimizar_titular", pedido, cliente_id)
    # Depois do commit: se algo antes falhar, nenhum arquivo some sem o registro mudar.
    for caminho in caminhos:
        arquivos.provedor().apagar(caminho)
    return len(caminhos)
