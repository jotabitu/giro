"""Planos, empresas (tenants) e o resumo de uso no public (PLT-01, PLT-03, IMP-05).

Modelo em `docs/decisoes/modelo-de-dados.md` (itens 1 e 2 e apoio). Empresa nasce só por
`plataforma.services.criar_empresa`; status muda só por `comum.estados.transicionar`.
"""

from datetime import date, timedelta
from typing import ClassVar

from django.conf import settings
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin

from comum.auditoria import Categoria
from comum.campos import CentavosField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase

DIAS_DE_TESTE = 14  # PLT-01


class Recurso(models.TextChoices):
    LOCACOES_VISTORIA = "locacoes_vistoria", "Locação e vistoria"
    CONTAS_RECEBER = "contas_receber", "Contas a receber"
    CONTRATO_DIGITAL = "contrato_digital", "Contrato digital"
    VENDAS_COMISSOES = "vendas_comissoes", "Vendas e comissões"
    MANUTENCAO_DESPESAS = "manutencao_despesas", "Manutenção e despesas"
    RELATORIOS = "relatorios", "Relatórios"
    DOMINIO_PROPRIO = "dominio_proprio", "Domínio próprio"
    API_INTEGRACOES = "api_integracoes", "API e integrações"
    SUPORTE_PRIORITARIO = "suporte_prioritario", "Suporte prioritário"


class Item(models.TextChoices):
    """Itens com limite no plano (PLT-03)."""

    VEICULOS = "veiculos", "veículos"
    FILIAIS = "filiais", "filiais"
    USUARIOS = "usuarios", "usuários"


class Plano(ModeloBase, ModeloAtivavel):
    nome = models.CharField(max_length=40, unique=True)
    preco_mensal_centavos = CentavosField()
    meses_cobrados_no_anual = models.PositiveSmallIntegerField(default=10)
    # Nulo = sem limite (Completo).
    limite_veiculos = models.PositiveIntegerField(null=True, blank=True)
    limite_filiais = models.PositiveIntegerField(null=True, blank=True)
    limite_usuarios = models.PositiveIntegerField(null=True, blank=True)
    recursos = models.JSONField(default=list, blank=True)
    ordem = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "plano"
        ordering = ["ordem", "id"]

    def __str__(self) -> str:
        return self.nome

    @property
    def preco_anual_centavos(self) -> int:
        """Anual = `meses_cobrados_no_anual` mensalidades (Decisões de 07 out 2026)."""
        return int(self.preco_mensal_centavos) * int(self.meses_cobrados_no_anual)

    def limite(self, item: str) -> int | None:
        valor: int | None = getattr(self, f"limite_{item}")
        return valor


class Empresa(TenantMixin, MaquinaDeEstados, ModeloBase):  # type: ignore[django-manager-missing]
    class Status(models.TextChoices):
        EM_TESTE = "em_teste", "Em teste"
        ATIVA = "ativa", "Ativa"
        INADIMPLENTE = "inadimplente", "Inadimplente"
        SUSPENSA = "suspensa", "Suspensa"
        PAUSADA = "pausada", "Pausada"
        CANCELADA = "cancelada", "Cancelada"

    class Ciclo(models.TextChoices):
        MENSAL = "mensal", "Mensal"
        ANUAL = "anual", "Anual"

    class EtapaImplantacao(models.TextChoices):
        """Funil da IMP-05."""

        CONTA = "conta", "Conta"
        MARCA = "marca", "Marca"
        FILIAL = "filial", "Filial"
        PRECOS = "precos", "Preços"
        DADOS = "dados", "Dados"
        PRIMEIRA_LOCACAO = "primeira_locacao", "1ª locação"
        CONCLUIDA = "concluida", "Concluída"

    # Coluna "Saída" da tabela de estados ("Plataforma e assinatura"). Pausar e cancelar
    # nascem de ação do administrador e entram com essas ações (fase 2).
    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "em_teste": {"ativa", "suspensa"},
        "ativa": {"inadimplente"},
        "inadimplente": {"ativa", "suspensa"},
        "suspensa": {"ativa"},
        "pausada": {"ativa"},
        "cancelada": set(),
    }
    REGRA_TRANSICAO = "transicao_empresa"
    CATEGORIA_AUDITORIA = Categoria.CONFIGURACOES

    razao_social = models.CharField(max_length=150, blank=True, default="")
    nome_exibicao = models.CharField(max_length=80)
    cidade = models.CharField(max_length=80, blank=True, default="")
    uf = models.CharField(max_length=2, blank=True, default="")
    responsavel_nome = models.CharField(max_length=150, blank=True, default="")
    responsavel_email = models.EmailField(blank=True, default="")
    responsavel_telefone = models.CharField(max_length=13, blank=True, default="")
    # Só dígitos. Nulo só na linha do public e nas empresas de teste da fundação.
    cnpj = models.CharField(max_length=14, unique=True, null=True, blank=True)
    subdominio = models.CharField(max_length=63, unique=True, null=True, blank=True)
    plano = models.ForeignKey(
        Plano, on_delete=models.PROTECT, null=True, blank=True, related_name="empresas"
    )
    ciclo = models.CharField(max_length=10, choices=Ciclo.choices, default=Ciclo.MENSAL)
    preco_contratado_centavos = CentavosField(default=0)  # PLT-05
    plano_proximo = models.ForeignKey(
        Plano, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.EM_TESTE)
    teste_inicio = models.DateField(null=True, blank=True)
    teste_fim = models.DateField(null=True, blank=True)
    pausada_ate = models.DateField(null=True, blank=True)
    cancelada_em = models.DateTimeField(null=True, blank=True)
    acesso_ate = models.DateField(null=True, blank=True)
    apagar_em = models.DateField(null=True, blank=True)
    motivo_cancelamento = models.TextField(blank=True, default="")
    suporte_bloqueado = models.BooleanField(default=False)  # PLT-07
    etapa_implantacao = models.CharField(
        max_length=20, choices=EtapaImplantacao.choices, default=EtapaImplantacao.CONTA
    )
    etapa_implantacao_desde = models.DateTimeField(null=True, blank=True)

    auto_create_schema = True
    auto_drop_schema = False

    # O responsável é funcionário da locadora (o administrador): vai inteiro, como o
    # nome e o e-mail do `Usuario` (ADR 0014, item 3).
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": ["responsavel_email", "responsavel_telefone"],
    }

    class Meta:
        verbose_name = "empresa"
        indexes = [
            models.Index(fields=["status"], name="empresa_status_idx"),
            models.Index(
                fields=["etapa_implantacao", "etapa_implantacao_desde"], name="empresa_etapa_idx"
            ),
        ]

    def __str__(self) -> str:
        return self.nome_exibicao

    @property
    def primeira_cobranca(self) -> date | None:
        """PLT-01: a 1ª fatura vence no dia seguinte ao fim do teste."""
        return self.teste_fim + timedelta(days=1) if self.teste_fim else None


class Dominio(DomainMixin):
    class Meta:
        verbose_name = "domínio"

    def __str__(self) -> str:
        return str(self.domain)


class UsoEmpresa(ModeloBase):
    """Resumo no public do uso de cada empresa (PLT-03, IMP-05).

    Mantido por `plataforma.services.atualizar_uso` e corrigido pela tarefa noturna
    `plataforma_recalcular_uso`. A lista da plataforma lê daqui, sem entrar em cada schema.
    """

    empresa = models.OneToOneField(Empresa, on_delete=models.PROTECT, related_name="uso")
    veiculos = models.PositiveIntegerField(default=0)
    filiais = models.PositiveIntegerField(default=0)
    usuarios = models.PositiveIntegerField(default=0)
    locacoes_total = models.PositiveIntegerField(default=0)
    ultimo_acesso_em = models.DateTimeField(null=True, blank=True)
    # {passo: "AAAA-MM-DD"}
    passos_implantacao = models.JSONField(default=dict, blank=True)
    # {item: "AAAA-MM"}: mês em que o aviso de 90% já saiu (uma vez por item e por mês).
    aviso_90_enviado = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "uso da empresa"
        verbose_name_plural = "uso das empresas"

    def __str__(self) -> str:
        return f"Uso da empresa {self.empresa_id}"


# --- Acesso de suporte (PLT-07; ADR 0013, item 2) ---


class PermissaoSuporte(models.TextChoices):
    VER = "ver", "Só ver"
    VER_EDITAR = "ver_editar", "Ver e editar"


class StatusAcessoSuporte(models.TextChoices):
    ATIVO = "ativo", "Ativo"
    ENCERRADO = "encerrado", "Encerrado"  # o prazo acabou ou o suporte saiu
    REVOGADO = "revogado", "Revogado"  # o administrador da empresa bloqueou ou revogou


DURACOES_DO_SUPORTE = (15, 30, 60)  # minutos (PLT-07)


class AcessoSuporte(MaquinaDeEstados, ModeloBase):
    """Entrada da equipe da plataforma numa empresa, com motivo, prazo e permissão (PLT-07).

    O token de suporte leva o `id`; a autenticação confere esta linha a cada requisição.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="acessos_suporte"
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="acessos_suporte")
    motivo = models.TextField()
    permissao = models.CharField(max_length=10, choices=PermissaoSuporte.choices)
    inicio = models.DateTimeField()
    fim = models.DateTimeField()
    encerrado_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=StatusAcessoSuporte.choices, default=StatusAcessoSuporte.ATIVO
    )

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "ativo": {"encerrado", "revogado"},
        "encerrado": set(),
        "revogado": set(),
    }
    REGRA_TRANSICAO = "transicao_acesso_suporte"
    CATEGORIA_AUDITORIA = Categoria.SUPORTE

    class Meta:
        verbose_name = "acesso de suporte"
        verbose_name_plural = "acessos de suporte"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fim__gt=models.F("inicio")), name="acesso_suporte_fim_depois"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "fim"], name="acesso_suporte_status_fim"),
            models.Index(fields=["empresa", "-inicio"], name="acesso_suporte_empresa"),
        ]

    def __str__(self) -> str:
        return f"Acesso de suporte {self.pk}"
