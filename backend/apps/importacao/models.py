"""Importação de veículos e clientes por planilha (IMP-02, IMP-03; ADR 0017).

Arquivo e linhas são dados temporários, não registro de negócio: saem 30 dias depois do envio
(`apagar_em`, tarefa `importacao_limpar`). O que fica são os cadastros criados e a auditoria.
As linhas de clientes guardam os dados cifrados (ADR 0014).
"""

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models

from comum.auditoria import Categoria as CategoriaAuditoria
from comum.campos import CampoCifrado
from comum.estados import MaquinaDeEstados
from comum.models import ModeloBase, ModeloComCifra


class TipoImportacao(models.TextChoices):
    VEICULOS = "veiculos", "Veículos"
    CLIENTES = "clientes", "Clientes"


class StatusImportacao(models.TextChoices):
    VALIDANDO = "validando", "Validando"
    VALIDADA = "validada", "Validada"
    IMPORTANDO = "importando", "Importando"
    CONCLUIDA = "concluida", "Concluída"
    FALHOU = "falhou", "Falhou"
    CANCELADA = "cancelada", "Cancelada"


class StatusLinha(models.TextChoices):
    PRONTA = "pronta", "Pronta"
    COM_ERRO = "com_erro", "Com erro"
    IMPORTADA = "importada", "Importada"
    ACIMA_DO_LIMITE = "acima_do_limite", "Acima do limite"
    IGNORADA = "ignorada", "Ignorada"


S = StatusImportacao
CONTAGENS = ("linhas", "prontas", "com_erro", "importadas", "acima_do_limite")


class Importacao(MaquinaDeEstados, ModeloBase):
    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        S.VALIDANDO: {S.VALIDADA, S.FALHOU},
        S.VALIDADA: {S.IMPORTANDO, S.CANCELADA},
        # Se a gravação falhar no meio (tempo esgotado), tudo é desfeito e ela volta.
        S.IMPORTANDO: {S.CONCLUIDA, S.VALIDADA},
        S.CONCLUIDA: {S.IMPORTANDO},
    }
    REGRA_TRANSICAO = "transicao_importacao"
    CATEGORIA_AUDITORIA = CategoriaAuditoria.CONFIGURACOES
    CAMPOS_AUDITORIA: ClassVar[dict[str, Any]] = {
        # O nome do arquivo de clientes pode trazer dado pessoal: fora da auditoria (ADR 0014).
        "omitir": ["arquivo_caminho", "arquivo_nome"],
        "mascarar": {"enviada_por_nome": "nome"},
    }

    tipo = models.CharField(max_length=10, choices=TipoImportacao.choices)
    status = models.CharField(max_length=12, choices=S.choices, default=S.VALIDANDO)
    # O nome original só aparece na tela; no storage o nome é aleatório (AUD-05).
    arquivo_nome = models.CharField(max_length=255)
    arquivo_caminho = models.CharField(max_length=300, blank=True, default="")
    filial_padrao = models.ForeignKey(
        "filiais.Filial", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    linhas = models.PositiveIntegerField(default=0)
    prontas = models.PositiveIntegerField(default=0)
    com_erro = models.PositiveIntegerField(default=0)
    importadas = models.PositiveIntegerField(default=0)
    acima_do_limite = models.PositiveIntegerField(default=0)
    aviso = models.JSONField(null=True, blank=True)
    enviada_por_id = models.BigIntegerField(null=True, blank=True)
    enviada_por_nome = models.CharField(max_length=150, blank=True, default="")
    enviada_em = models.DateTimeField()
    concluida_em = models.DateTimeField(null=True, blank=True)
    apagar_em = models.DateField()

    class Meta:
        indexes = [models.Index(fields=["tipo", "status"], name="importacao_tipo_status_idx")]

    def __str__(self) -> str:
        return f"Importação {self.pk} ({self.tipo})"


class LinhaImportacao(ModeloComCifra, ModeloBase):
    """Uma linha da planilha. `dados` (veículos) ou `dados_cifrados` (clientes, JSON cifrado)."""

    CAMPOS_AUDITORIA: ClassVar[dict[str, Any]] = {
        "omitir": ["dados", "chave_documento"],
        "inteiro": ["chave_placa", "chave_chassi"],  # do veículo, não dado pessoal
    }

    importacao = models.ForeignKey(Importacao, on_delete=models.CASCADE, related_name="itens")
    numero = models.PositiveIntegerField()  # a linha na planilha (o cabeçalho é a 1)
    status = models.CharField(max_length=15, choices=StatusLinha.choices)
    dados = models.JSONField(default=dict, blank=True)
    dados_cifrados = CampoCifrado()
    erros = models.JSONField(default=list, blank=True)
    # Para achar a repetição dentro da planilha. O documento vai pelo hash (ADR 0014).
    chave_placa = models.CharField(max_length=10, blank=True, default="")
    chave_chassi = models.CharField(max_length=20, blank=True, default="")
    chave_documento = models.CharField(max_length=64, blank=True, default="")
    objeto_tipo = models.CharField(max_length=10, blank=True, default="")
    objeto_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["importacao", "numero"], name="linha_importacao_unica")
        ]
        indexes = [models.Index(fields=["importacao", "status"], name="linha_importacao_status")]

    if TYPE_CHECKING:  # criados por CampoCifrado.contribute_to_class

        def dados_cifrados_claro(self) -> str: ...
        def definir_dados_cifrados(self, valor: str | None) -> None: ...

    def __str__(self) -> str:
        return f"Linha {self.numero}"
