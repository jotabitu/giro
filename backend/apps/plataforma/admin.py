"""Django Admin da plataforma (ADR 0013, item 4): leitura, "Criar empresa" e "Reativar" pelo
serviço.

No MVP a empresa piloto nasce aqui, e a equipe vê as faturas de todas as empresas até a
`Plat-Cobranca` (`plataforma.md`, "Faturas de todas as empresas"; PLT-14), só leitura. O
formulário chama `services.criar_empresa`, que valida, cria o schema, convida o administrador e
audita; a ação "Reativar" chama `services.reativar_empresa` (PLT-06, T-365), com o motivo. Nada é
gravado direto pelo Admin.
"""

from typing import Any

from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.db.models import Q
from django.http import HttpRequest

from comum.erros import ErroDeNegocio, ErroDeValidacao

from .models import Empresa, FaturaAssinatura, Plano, StatusFatura, UsoEmpresa
from .services import POR_EQUIPE, Administrador, criar_empresa, reativar_empresa, validar_criacao


class CriarEmpresaForm(forms.ModelForm):  # type: ignore[type-arg]
    administrador_nome = forms.CharField(label="Nome do administrador")
    administrador_email = forms.EmailField(label="E-mail do administrador")
    administrador_celular = forms.CharField(label="Celular do administrador", required=False)

    class Meta:
        model = Empresa
        fields = ["razao_social", "nome_exibicao", "cnpj", "subdominio", "cidade", "uf", "plano"]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for campo in ("razao_social", "cnpj", "subdominio", "plano"):
            self.fields[campo].required = True

    def _post_clean(self) -> None:
        # Sem a validação do model (exigiria o schema): quem valida é o serviço.
        pass

    def clean(self) -> dict[str, Any]:
        dados = super().clean() or {}
        if self.errors:
            return dados
        try:
            validar_criacao(
                dados.get("subdominio") or "",
                dados.get("cnpj") or "",
                Administrador(
                    dados.get("administrador_nome", ""), dados.get("administrador_email", "")
                ),
            )
        except ErroDeValidacao as erro:
            for campo, mensagens in erro.campos.items():
                self.add_error(campo.replace("administrador.", "administrador_"), mensagens)
        except ErroDeNegocio as erro:
            self.add_error("subdominio" if "subdominio" in erro.codigo else "cnpj", erro.mensagem)
        return dados


class SoLeitura(admin.ModelAdmin):  # type: ignore[type-arg]
    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(Plano)
class PlanoAdmin(SoLeitura):
    list_display = ["nome", "preco_mensal_centavos", "limite_veiculos", "ativo"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class AcaoComMotivo(ActionForm):
    motivo = forms.CharField(label="Motivo", required=False, max_length=300)


def _so_o_dono(request: HttpRequest) -> bool:
    return bool(getattr(request.user, "funcao_plataforma", "") == "dono")


@admin.register(Empresa)
class EmpresaAdmin(SoLeitura):
    list_display = ["nome_exibicao", "subdominio", "plano", "status", "teste_fim", "apagar_em"]
    list_filter = ["status", "plano"]
    search_fields = ["nome_exibicao", "subdominio", "cnpj"]
    add_form = CriarEmpresaForm
    action_form = AcaoComMotivo
    actions = ["reativar"]

    def get_form(
        self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any
    ) -> Any:
        if obj is None:
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, change, **kwargs)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return _so_o_dono(request)

    def has_reativar_permission(self, request: HttpRequest) -> bool:
        return _so_o_dono(request)

    @admin.action(description="Reativar a empresa cancelada", permissions=["reativar"])
    def reativar(self, request: HttpRequest, queryset: Any) -> None:
        """PLT-06: cada empresa pelo serviço, que trava, confere e audita com o usuário da
        equipe. A recusa (fatura em atraso, apagamento começado) aparece na mensagem."""
        motivo = str(request.POST.get("motivo", "")).strip()
        if not motivo:
            self.message_user(request, "Informe o motivo para reativar.", messages.ERROR)
            return
        for empresa in queryset.order_by("pk"):
            try:
                reativar_empresa(empresa, POR_EQUIPE, motivo)
            except ErroDeNegocio as erro:
                self.message_user(request, f"{empresa}: {erro.mensagem}", messages.ERROR)
            else:
                self.message_user(request, f"{empresa} reativada.", messages.SUCCESS)

    def save_model(self, request: HttpRequest, obj: Empresa, form: Any, change: bool) -> None:
        dados = form.cleaned_data
        criada = criar_empresa(
            razao_social=dados["razao_social"],
            nome_exibicao=dados["nome_exibicao"],
            cnpj=dados["cnpj"],
            subdominio=dados["subdominio"],
            plano=dados["plano"],
            cidade=dados.get("cidade", ""),
            uf=dados.get("uf", ""),
            administrador=Administrador(
                nome=dados["administrador_nome"],
                email=dados["administrador_email"],
                celular=dados.get("administrador_celular", ""),
            ),
        )
        # O Admin segue com o objeto criado pelo serviço (mensagem e redirecionamento).
        obj.__dict__.update(criada.__dict__)
        obj._state = criada._state

    def save_related(self, request: HttpRequest, form: Any, formsets: Any, change: bool) -> None:
        return None


@admin.register(UsoEmpresa)
class UsoEmpresaAdmin(SoLeitura):
    list_display = ["empresa", "veiculos", "filiais", "usuarios", "ultimo_acesso_em"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False


class NotaPendente(admin.SimpleListFilter):
    """Faturas pagas sem nota pedida ou com a nota em erro (PLT-15)."""

    title = "nota pendente"
    parameter_name = "nota_pendente"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [("sim", "Sim")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() != "sim":
            return queryset
        return queryset.filter(status=StatusFatura.PAGA).filter(
            Q(nota_situacao="") | Q(nota_situacao="erro")
        )


@admin.register(FaturaAssinatura)
class FaturaAssinaturaAdmin(SoLeitura):
    """Sem incluir, editar nem apagar: a baixa vem só do webhook, e fatura paga não se edita."""

    list_display = [
        "codigo",
        "empresa",
        "razao_social",
        "cnpj",
        "tipo",
        "periodo_inicio",
        "periodo_fim",
        "valor_centavos",
        "vencimento",
        "status",
        "forma",
        "pago_em",
        "tentativas_cartao",
        "nota_situacao",
        "tomador_razao_social",
        "tomador_cnpj",
    ]
    list_filter = ["status", "tipo", "vencimento", "forma", NotaPendente]
    search_fields = ["codigo", "empresa__razao_social", "empresa__cnpj"]
    list_select_related = ["empresa", "plano"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    @admin.display(description="razão social")
    def razao_social(self, obj: FaturaAssinatura) -> str:
        return str(obj.empresa.razao_social)

    @admin.display(description="CNPJ")
    def cnpj(self, obj: FaturaAssinatura) -> str:
        return str(obj.empresa.cnpj or "")
