"""Planos, empresas (tenants), faturas da assinatura e o resumo de uso no public (PLT-01,
PLT-03, PLT-13, PLT-14, IMP-05).

Modelo em `docs/decisoes/modelo-de-dados.md` (itens 1 a 3 e apoio). Empresa nasce só por
`plataforma.services.criar_empresa`; status muda só por `comum.estados.transicionar`.
"""

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django_tenants.models import DomainMixin, TenantMixin

from comum import cripto
from comum.auditoria import Categoria
from comum.campos import CampoCifrado, CentavosField
from comum.estados import MaquinaDeEstados
from comum.models import ModeloAtivavel, ModeloBase, ModeloComCifra

DIAS_DE_TESTE = 14  # PLT-01
CAMPOS_DO_ENDERECO = ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")
CAMPOS_ENDERECO_DA_NOTA = tuple(f"endereco_{campo}" for campo in CAMPOS_DO_ENDERECO)
# Dados da empresa que o apagamento limpa (AUD-08): só `{"alterado": true}` na auditoria do public.
DADOS_APAGADOS_DA_EMPRESA = (
    "razao_social",
    "nome_exibicao",
    *CAMPOS_ENDERECO_DA_NOTA,
    "email_cobranca",
    "responsavel_nome",
    "responsavel_email",
    "responsavel_telefone",
)


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

    # Nome de coisa, não de pessoa (R-02 da T-050): vai inteiro para a auditoria.
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {"inteiro": ["nome"]}

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

    # Coluna "Saída" da tabela de estados ("Plataforma e assinatura") e as transições do
    # contrato (`assinatura.md`; a em teste com forma e sem pagar vira inadimplente em D+1).
    # Pausar e cancelar nascem de ação do administrador e entram com a T-195.
    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        "em_teste": {"ativa", "inadimplente", "suspensa"},
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
    # Faturas, boleto, régua e NFS-e da assinatura (PLT-02, PLT-15). Nasce = responsavel_email.
    email_cobranca = models.EmailField(blank=True, default="")
    # Endereço da nota da assinatura (PLT-15): copiado uma vez da matriz
    # (`copiar_endereco_da_matriz`), depois independente da filial. Vazios até lá; não voltam.
    endereco_cep = models.CharField(max_length=8, blank=True, default="")
    endereco_logradouro = models.CharField(max_length=150, blank=True, default="")
    endereco_numero = models.CharField(max_length=20, blank=True, default="")
    endereco_complemento = models.CharField(max_length=80, blank=True, default="")
    endereco_bairro = models.CharField(max_length=80, blank=True, default="")
    endereco_cidade = models.CharField(max_length=80, blank=True, default="")
    endereco_uf = models.CharField(max_length=2, blank=True, default="")
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
    # Mudança de ciclo pela equipe, na próxima fatura (PLT-04).
    ciclo_proximo = models.CharField(max_length=10, choices=Ciclo.choices, blank=True, default="")
    # PLT-01: dia de `teste_fim + 1`. Em mês sem esse dia, vence no último (`calendario`).
    dia_vencimento = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(31)]
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
    # nome e o e-mail do `Usuario` (ADR 0014, item 3), no schema da empresa. No public, que fica
    # 5 anos e o apagamento não alcança, os dados que o apagamento limpa vão como
    # `{"alterado": true}` (AUD-08, T-236; `auditoria.md`, "Dados da empresa no `public`").
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": [
            "nome_exibicao",
            "responsavel_nome",
            "responsavel_email",
            "responsavel_telefone",
            "email_cobranca",
            *CAMPOS_ENDERECO_DA_NOTA,
        ],
        "omitir_no_public": list(DADOS_APAGADOS_DA_EMPRESA),
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

    @property
    def endereco(self) -> dict[str, str | None] | None:
        """O endereço da nota no formato do endereço da filial (complemento vazio = `None`);
        `None` antes do passo 6."""
        if not self.endereco_cep:
            return None
        return {campo: getattr(self, f"endereco_{campo}") or None for campo in CAMPOS_DO_ENDERECO}


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


class StatusContaPagamento(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    APROVADA = "aprovada", "Aprovada"
    RECUSADA = "recusada", "Recusada"


class ContaPagamento(MaquinaDeEstados, ModeloComCifra, ModeloBase):
    """A subconta da empresa no parceiro de pagamentos (ADR 0007, `FIL-04`). O webhook chega no
    `public`, acha a empresa pelo hash do token e só então entra no schema dela (S-14).

    A chave da API da subconta (T-029) fica cifrada com a chave dos segredos (ADR 0014, S-05) e só
    é decifrada dentro de `integracoes/pagamentos`, por `integracoes.pagamentos.referencia`."""

    empresa = models.OneToOneField(
        Empresa, on_delete=models.PROTECT, related_name="conta_pagamento"
    )
    provedor = models.CharField(max_length=10, default="asaas")
    conta_externa_id = models.CharField(max_length=60, unique=True)
    carteira_id = models.CharField(max_length=60, blank=True, default="")
    chave_api_cifrada = CampoCifrado(tipo=cripto.SEGREDOS)
    webhook_token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=10, choices=StatusContaPagamento.choices, default=StatusContaPagamento.PENDENTE
    )

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        StatusContaPagamento.PENDENTE: {
            StatusContaPagamento.APROVADA,
            StatusContaPagamento.RECUSADA,
        },
        StatusContaPagamento.APROVADA: set(),
        StatusContaPagamento.RECUSADA: set(),
    }
    REGRA_TRANSICAO = "FIN-04"
    CATEGORIA_AUDITORIA = Categoria.CONFIGURACOES
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "omitir": ["webhook_token_hash", "chave_api_cifrada"]
    }

    if TYPE_CHECKING:  # criados por CampoCifrado.contribute_to_class

        def chave_api_cifrada_claro(self) -> str: ...

        def definir_chave_api_cifrada(self, valor: str | None) -> None: ...

    class Meta:
        verbose_name = "conta de pagamento"
        verbose_name_plural = "contas de pagamento"

    def empresa_id_da_cifra(self) -> int:
        # No public: a cifra amarra a chave à empresa da subconta, não à da conexão.
        return int(self.empresa_id)

    def __str__(self) -> str:
        return f"{self.provedor} {self.conta_externa_id}"


# --- Faturas da assinatura (PLT-01, PLT-02, PLT-13, PLT-14, PLT-15; T-184) ---


class TipoFatura(models.TextChoices):
    MENSALIDADE = "mensalidade", "Mensalidade"
    DIFERENCA_PLANO = "diferenca_plano", "Diferença de plano"  # upgrade no meio do período


class StatusFatura(models.TextChoices):
    ABERTA = "aberta", "Aberta"
    PAGA = "paga", "Paga"
    ATRASADA = "atrasada", "Atrasada"
    CANCELADA = "cancelada", "Cancelada"


class FormaPagaFatura(models.TextChoices):
    """Como a fatura foi paga."""

    PIX = "pix", "Pix"
    BOLETO = "boleto", "Boleto"
    CARTAO = "cartao", "Cartão"


class SituacaoNota(models.TextChoices):
    PROCESSANDO = "processando", "Processando"
    EMITIDA = "emitida", "Emitida"
    ERRO = "erro", "Erro"


class MotivoCancelamentoFatura(models.TextChoices):
    CANCELAMENTO_ASSINATURA = "cancelamento_assinatura", "Cancelamento da assinatura"
    PAUSA = "pausa", "Pausa"


PREFIXO_FATURA = "FAT"
CAMPOS_DA_COBRANCA = (
    "cobranca_pix_copia_e_cola",
    "cobranca_linha_digitavel",
    "cobranca_boleto_url",
    "cobranca_url_pagina",
    "recibo_url",
)
TENTATIVAS_DO_CARTAO = 2  # PLT-02: a cobrança no vencimento e uma tentativa a mais


class FaturaAssinatura(MaquinaDeEstados, ModeloBase):
    """Cobrança do Giro à empresa, no public. Nasce só por `plataforma.services`; a baixa vem só
    do webhook da conta principal, que consulta o parceiro antes (PLT-14). Paga não se edita.

    `codigo` (`FAT-0001`) é sequencial por empresa (sequência `FAT-<empresa_id>` no public)."""

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="faturas")
    numero = models.PositiveIntegerField(editable=False)
    codigo = models.CharField(max_length=20, editable=False)
    tipo = models.CharField(max_length=20, choices=TipoFatura.choices)
    competencia = models.DateField()  # dia 1 do mês do início do período
    periodo_inicio = models.DateField()
    periodo_fim = models.DateField()
    plano = models.ForeignKey(Plano, on_delete=models.PROTECT, related_name="+")
    # O ciclo cobrado: a descrição do anual é outra (PLT-14).
    ciclo = models.CharField(max_length=10, choices=Empresa.Ciclo.choices)
    valor_centavos = CentavosField()
    vencimento = models.DateField()
    status = models.CharField(
        max_length=10, choices=StatusFatura.choices, default=StatusFatura.ABERTA
    )
    forma = models.CharField(max_length=10, choices=FormaPagaFatura.choices, blank=True, default="")
    cobranca_emitida_em = models.DateTimeField(null=True, blank=True)
    pago_em = models.DateTimeField(null=True, blank=True)
    cobranca_externa_id = models.CharField(max_length=60, unique=True, null=True, blank=True)
    # A cobrança viva no parceiro, para o "Pagar" e o detalhe (T-185): uma por fatura.
    cobranca_tipo = models.CharField(
        max_length=12, blank=True, default=""
    )  # pix, boleto, cartao_link
    cobranca_pix_copia_e_cola = models.TextField(blank=True, default="")
    cobranca_linha_digitavel = models.CharField(max_length=60, blank=True, default="")
    cobranca_boleto_url = models.CharField(max_length=500, blank=True, default="")
    cobranca_url_pagina = models.CharField(max_length=500, blank=True, default="")
    # Comprovante do parceiro, gravado na baixa (PLT-14). O Giro não gera PDF de recibo no MVP.
    recibo_url = models.CharField(max_length=500, blank=True, default="")
    tentativas_cartao = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(TENTATIVAS_DO_CARTAO)]
    )
    cartao_recusado_em = models.DateTimeField(null=True, blank=True)
    # NFS-e da assinatura (PLT-15; a emissão é da T-197).
    nota_situacao = models.CharField(
        max_length=12, choices=SituacaoNota.choices, blank=True, default=""
    )
    nota_numero = models.CharField(max_length=30, blank=True, default="")
    nota_externa_id = models.CharField(max_length=60, blank=True, default="")
    nota_url = models.URLField(max_length=500, blank=True, default="")
    nota_pedida_em = models.DateTimeField(null=True, blank=True)
    # Tomador como foi na nota, ou na baixa sem nota (PLT-14, T-236): gravado uma vez por
    # `services.gravar_tomador` e imutável depois.
    tomador_razao_social = models.CharField(max_length=150, blank=True, default="")
    tomador_cnpj = models.CharField(max_length=14, blank=True, default="")
    tomador_endereco = models.JSONField(null=True, blank=True)
    tomador_gravado_em = models.DateTimeField(null=True, blank=True)
    # Só na fatura `atrasada` de empresa apagada, até a baixa (AUD-08, T-195).
    email_cobranca = models.EmailField(blank=True, default="")
    # Cancelar e pausar (PLT-06, T-195).
    motivo_cancelamento = models.CharField(
        max_length=30, choices=MotivoCancelamentoFatura.choices, blank=True, default=""
    )
    cancelada_em = models.DateTimeField(null=True, blank=True)
    substituida_por = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        StatusFatura.ABERTA: {StatusFatura.PAGA, StatusFatura.ATRASADA, StatusFatura.CANCELADA},
        StatusFatura.ATRASADA: {StatusFatura.PAGA, StatusFatura.CANCELADA},
        StatusFatura.PAGA: set(),
        StatusFatura.CANCELADA: set(),
    }
    REGRA_TRANSICAO = "PLT-14"
    CATEGORIA_AUDITORIA = Categoria.FINANCEIRO
    # O tomador e o e-mail podem identificar uma pessoa (MEI, T-230): os eventos da fatura, no
    # public, não levam os valores (assinatura.md, "Tomador da fatura").
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "inteiro": ["codigo"],
        # Os dados para pagar e o recibo só saem na resposta ao administrador (T-189, item 8).
        "omitir": [
            "tomador_razao_social",
            "tomador_cnpj",
            "tomador_endereco",
            "email_cobranca",
            *CAMPOS_DA_COBRANCA,
        ],
    }

    class Meta:
        verbose_name = "fatura da assinatura"
        verbose_name_plural = "faturas da assinatura"
        ordering = ["-vencimento", "-numero"]
        constraints = [
            models.UniqueConstraint(fields=["empresa", "numero"], name="fatura_numero_unico"),
            models.UniqueConstraint(fields=["empresa", "codigo"], name="fatura_codigo_unico"),
            # Uma mensalidade viva por período (PLT-01); a cancelada abre espaço para outra.
            models.UniqueConstraint(
                fields=["empresa", "competencia"],
                condition=models.Q(tipo="mensalidade") & ~models.Q(status="cancelada"),
                name="fatura_mensalidade_unica",
            ),
            models.CheckConstraint(
                condition=models.Q(tentativas_cartao__lte=TENTATIVAS_DO_CARTAO),
                name="fatura_tentativas_cartao",
            ),
            models.CheckConstraint(
                condition=models.Q(periodo_fim__gte=models.F("periodo_inicio")),
                name="fatura_periodo",
            ),
        ]
        indexes = [models.Index(fields=["status", "vencimento"], name="fatura_status_vencimento")]

    def __str__(self) -> str:
        return f"{self.codigo} · empresa {self.empresa_id}"

    @property
    def descricao(self) -> str:
        """ "Plano Profissional · 22 out a 21 nov" (PLT-14)."""
        from .calendario import descricao_da_fatura

        return descricao_da_fatura(
            self.tipo, self.plano.nome, self.ciclo, self.periodo_inicio, self.periodo_fim
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self._state.adding and not self.codigo:
            from comum.codigos import formatar_codigo, proximo_numero

            # O número sai na mesma transação da fatura, no public: rollback devolve o número.
            with transaction.atomic():
                self.numero = proximo_numero(f"{PREFIXO_FATURA}-{self.empresa_id}")
                self.codigo = formatar_codigo(PREFIXO_FATURA, self.numero)
                super().save(*args, **kwargs)
            return
        super().save(*args, **kwargs)


class FormaAssinatura(models.TextChoices):
    CARTAO = "cartao", "Cartão de crédito"
    PIX_AUTOMATICO = "pix_automatico", "Pix automático"
    BOLETO = "boleto", "Boleto"


class StatusFormaPagamento(models.TextChoices):
    PENDENTE = "pendente", "Pendente"  # Pix aguardando autorização, cartão ainda não guardado
    ATIVA = "ativa", "Ativa"
    RECUSADA = "recusada", "Recusada"


class FormaPagamentoAssinatura(MaquinaDeEstados, ModeloComCifra, ModeloBase):
    """Forma de pagamento da assinatura e o pagador da empresa na conta principal (PLT-13).

    O número do cartão nunca passa pelo Giro (ADR 0023): fica só o token do parceiro, cifrado com
    a chave dos segredos e decifrado só em `integracoes/pagamentos`, mais a bandeira e o final. O
    token nunca sai na API, na auditoria nem no log."""

    empresa = models.OneToOneField(
        Empresa, on_delete=models.PROTECT, related_name="forma_pagamento"
    )
    forma = models.CharField(max_length=20, choices=FormaAssinatura.choices, blank=True, default="")
    status = models.CharField(
        max_length=10, choices=StatusFormaPagamento.choices, default=StatusFormaPagamento.PENDENTE
    )
    cliente_externo_id = models.CharField(max_length=60, blank=True, default="")
    autorizacao_externa_id = models.CharField(max_length=60, blank=True, default="")
    cartao_token_cifrado = CampoCifrado(tipo=cripto.SEGREDOS)
    cartao_bandeira = models.CharField(max_length=20, blank=True, default="")
    cartao_final = models.CharField(max_length=4, blank=True, default="")

    TRANSICOES: ClassVar[dict[str, set[str]]] = {
        StatusFormaPagamento.PENDENTE: {StatusFormaPagamento.ATIVA, StatusFormaPagamento.RECUSADA},
        StatusFormaPagamento.ATIVA: {StatusFormaPagamento.PENDENTE, StatusFormaPagamento.RECUSADA},
        StatusFormaPagamento.RECUSADA: {StatusFormaPagamento.PENDENTE, StatusFormaPagamento.ATIVA},
    }
    REGRA_TRANSICAO = "PLT-13"
    CATEGORIA_AUDITORIA = Categoria.FINANCEIRO
    CAMPOS_AUDITORIA: ClassVar[dict[str, list[str]]] = {
        "omitir": ["cartao_token_cifrado", "cliente_externo_id", "autorizacao_externa_id"]
    }

    if TYPE_CHECKING:  # criados por CampoCifrado.contribute_to_class

        def cartao_token_cifrado_claro(self) -> str: ...

        def definir_cartao_token_cifrado(self, valor: str | None) -> None: ...

    class Meta:
        verbose_name = "forma de pagamento da assinatura"
        verbose_name_plural = "formas de pagamento da assinatura"

    def empresa_id_da_cifra(self) -> int:
        # No public: a cifra amarra o token à empresa dona dele, não à da conexão.
        return int(self.empresa_id)

    def __str__(self) -> str:
        return f"Forma de pagamento da empresa {self.empresa_id}"
