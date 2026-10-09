"""Clientes PF e PJ, CNH, documentos, bloqueio e consentimento (CLI, AUD-04, AUD-05, ADR 0014).

Modelo em `docs/decisoes/modelo-de-dados.md`, item 11. Muda só por `clientes.services`; o
status, só por `comum.estados.transicionar` (ADR 0009). CPF, CNPJ e CNH ficam cifrados, com
hash de busca por empresa; o claro só aparece na representação completa (AUD-04).
"""

from typing import TYPE_CHECKING, Any, ClassVar

from django.db import models
from django.db.models.functions import Lower

from comum import arquivos
from comum.auditoria import Categoria as CategoriaAuditoria
from comum.campos import CampoCifrado, CampoHashBusca
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase, ModeloComCifra


class TipoCliente(models.TextChoices):
    PF = "pf", "Pessoa física"
    PJ = "pj", "Pessoa jurídica"


class StatusCliente(models.TextChoices):
    INCOMPLETO = "incompleto", "Cadastro incompleto"
    ATIVO = "ativo", "Ativo"
    BLOQUEADO = "bloqueado", "Bloqueado"
    INATIVO = "inativo", "Inativo"


class MotivoBloqueio(models.TextChoices):
    ATRASO = "atraso", "Atraso"  # CLI-05: só este desbloqueia sozinho
    MANUAL = "manual", "Manual"


class CategoriaCnh(models.TextChoices):
    A = "A", "A"
    B = "B", "B"
    C = "C", "C"
    D = "D", "D"
    E = "E", "E"
    AB = "AB", "AB"
    AC = "AC", "AC"
    AD = "AD", "AD"
    AE = "AE", "AE"


S = StatusCliente
# CLI-03 decide entre `incompleto` e `ativo`; CLI-05, o bloqueio; CLI-09, a inativação.
TRANSICOES_CLIENTE: dict[str, set[str]] = {
    S.INCOMPLETO: {S.ATIVO, S.BLOQUEADO, S.INATIVO},
    S.ATIVO: {S.INCOMPLETO, S.BLOQUEADO, S.INATIVO},
    S.BLOQUEADO: {S.ATIVO, S.INCOMPLETO},
    S.INATIVO: {S.ATIVO, S.INCOMPLETO},
}


class Cliente(ModeloComCifra, MaquinaDeEstados, ModeloBase):
    tipo = models.CharField(max_length=2, choices=TipoCliente.choices)
    nome = models.CharField(max_length=150)  # nome ou razão social
    documento = CampoCifrado()  # CPF ou CNPJ, só dígitos (ADR 0014)
    documento_hash = CampoHashBusca(de="documento", unique=True)  # CLI-01
    nascimento = models.DateField(null=True, blank=True)  # PF
    celular = models.CharField(max_length=13)
    email = models.EmailField(blank=True, default="")
    profissao = models.CharField(max_length=80, blank=True, default="")
    # CNH do PF ou do condutor responsável na PJ (CLI-02).
    cnh_numero = CampoCifrado()
    cnh_hash = CampoHashBusca(de="cnh_numero", db_index=True)
    cnh_categoria = models.CharField(
        max_length=3, choices=CategoriaCnh.choices, blank=True, default=""
    )
    cnh_validade = models.DateField(null=True, blank=True, db_index=True)
    cnh_primeira_habilitacao = models.DateField(null=True, blank=True)
    # PJ: o condutor responsável.
    responsavel_nome = models.CharField(max_length=150, blank=True, default="")
    responsavel_cpf = CampoCifrado()
    responsavel_cpf_hash = CampoHashBusca(de="responsavel_cpf", db_index=True)
    responsavel_celular = models.CharField(max_length=13, blank=True, default="")
    cep = models.CharField(max_length=8, blank=True, default="")
    logradouro = models.CharField(max_length=150, blank=True, default="")
    numero = models.CharField(max_length=20, blank=True, default="")
    complemento = models.CharField(max_length=80, blank=True, default="")
    bairro = models.CharField(max_length=80, blank=True, default="")
    cidade = models.CharField(max_length=80, blank=True, default="")
    uf = models.CharField(max_length=2, blank=True, default="")
    referencia_nome = models.CharField(max_length=150, blank=True, default="")
    referencia_parentesco = models.CharField(max_length=40, blank=True, default="")
    referencia_telefone = models.CharField(max_length=13, blank=True, default="")
    status = models.CharField(max_length=10, choices=StatusCliente.choices, default=S.INCOMPLETO)
    bloqueio_motivo = models.CharField(
        max_length=6, choices=MotivoBloqueio.choices, blank=True, default=""
    )
    bloqueio_desde = models.DateTimeField(null=True, blank=True)
    bloqueio_descricao = models.CharField(max_length=200, blank=True, default="")
    consentimento_em = models.DateTimeField(null=True, blank=True)  # LGPD
    anonimizado_em = models.DateTimeField(null=True, blank=True)  # AUD-06
    cliente_desde = models.DateField()  # CLI-06

    TRANSICOES: ClassVar[dict[str, set[str]]] = TRANSICOES_CLIENTE
    REGRA_TRANSICAO: ClassVar[str] = "transicao_cliente"
    CATEGORIA_AUDITORIA: ClassVar[str] = CategoriaAuditoria.OPERACAO

    # ADR 0014, item 3: cifrados e hashes omitidos sozinhos; o resto pessoal, mascarado. Cidade,
    # UF e parentesco vão inteiros (endereço do cliente aparece só com cidade e UF).
    CAMPOS_AUDITORIA: ClassVar[dict[str, Any]] = {
        "mascarar": {
            "nome": "nome",
            "nascimento": "nascimento",
            "celular": "telefone",
            "email": "email",
            "responsavel_nome": "nome",
            "responsavel_celular": "telefone",
            "cep": "endereco",
            "logradouro": "endereco",
            "numero": "endereco",
            "complemento": "endereco",
            "bairro": "endereco",
            "referencia_nome": "nome",
            "referencia_telefone": "telefone",
        },
        # Categoria e datas da CNH não identificam a pessoa; o número fica cifrado e omitido.
        "inteiro": ["cnh_categoria", "cnh_validade", "cnh_primeira_habilitacao"],
    }

    class Meta:
        verbose_name = "cliente"
        ordering = ["-criado_em", "-id"]
        indexes = [
            models.Index(fields=["status"], name="cliente_status"),
            models.Index(Lower("nome"), name="cliente_nome_lower"),
        ]
        constraints = [
            # CLI-05: bloqueado sempre com motivo; fora do bloqueio, sem motivo.
            models.CheckConstraint(
                condition=(
                    models.Q(status="bloqueado") & ~models.Q(bloqueio_motivo="")
                    | ~models.Q(status="bloqueado") & models.Q(bloqueio_motivo="")
                ),
                name="cliente_bloqueio_com_motivo",
            ),
        ]

    if TYPE_CHECKING:  # criados por CampoCifrado.contribute_to_class

        def documento_claro(self) -> str: ...
        def definir_documento(self, valor: str | None) -> None: ...
        def cnh_numero_claro(self) -> str: ...
        def definir_cnh_numero(self, valor: str | None) -> None: ...
        def responsavel_cpf_claro(self) -> str: ...
        def definir_responsavel_cpf(self, valor: str | None) -> None: ...

    def __str__(self) -> str:
        return f"Cliente {self.pk}"


class TipoDocumentoCliente(models.TextChoices):
    CNH_FRENTE = "cnh_frente", "CNH (frente)"
    CNH_VERSO = "cnh_verso", "CNH (verso)"
    SELFIE_DOCUMENTO = "selfie_documento", "Selfie com o documento"
    COMPROVANTE_RESIDENCIA = "comprovante_residencia", "Comprovante de residência"


class DocumentoCliente(ModeloBase, ModeloAtivavel):
    """CLI-03. Reenviar = novo documento, e o anterior fica `ativo=False` (guardado)."""

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="documentos")
    tipo = models.CharField(max_length=22, choices=TipoDocumentoCliente.choices)
    # Armazenamento privado com URL assinada de 15 minutos (AUD-05, ADR 0009).
    arquivo = models.FileField(
        storage=arquivos.armazenamento_privado,
        upload_to=arquivos.caminho_privado,
        max_length=200,
        null=True,
        blank=True,
    )
    por = models.ForeignKey(
        "contas.Usuario", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "documento do cliente"
        verbose_name_plural = "documentos do cliente"
        ordering = ["tipo", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["cliente", "tipo"],
                condition=models.Q(ativo=True),
                name="documento_cliente_um_ativo_por_tipo",
            )
        ]

    def __str__(self) -> str:
        return f"{self.cliente_id}: {self.tipo}"
