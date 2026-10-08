"""Django Admin da plataforma (ADR 0013, item 4): leitura, e "Criar empresa" pelo serviço.

No MVP a empresa piloto nasce aqui. O formulário chama `services.criar_empresa`, que valida,
cria o schema, convida o administrador e audita; nada é gravado direto pelo Admin.
"""

from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest

from comum.erros import ErroDeNegocio, ErroDeValidacao

from .models import Empresa, Plano, UsoEmpresa
from .services import Administrador, criar_empresa, validar_criacao


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


@admin.register(Empresa)
class EmpresaAdmin(SoLeitura):
    list_display = ["nome_exibicao", "subdominio", "plano", "status", "teste_fim"]
    list_filter = ["status", "plano"]
    search_fields = ["nome_exibicao", "subdominio", "cnpj"]
    add_form = CriarEmpresaForm

    def get_form(
        self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any
    ) -> Any:
        if obj is None:
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, change, **kwargs)

    def has_add_permission(self, request: HttpRequest) -> bool:
        return bool(getattr(request.user, "funcao_plataforma", "") == "dono")

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
