"""Seed parcial da Moto Rápida (T-127): o que não depende do financeiro da T-017.

Cria, pelos serviços de domínio e de forma idempotente (cada passo confere o que já existe):
empresa com subdomínio, Filial Centro, uma pessoa por perfil, as 4 categorias com os preços, as
86 motos e carros, os clientes e as 42 locações abertas de 07 out 2026 (LOC-2836 pela confirmação
de verdade). Fica para a T-019: contas a pagar, caixa, baixas, vendas e comissões.
"""

from dataclasses import dataclass
from typing import Any

from django.db import transaction
from django_tenants.utils import tenant_context

from apps.clientes import services as clientes_services
from apps.clientes.models import Cliente
from apps.contas import services as contas_services
from apps.contas.dois_fatores import confirmar_autenticador, novo_autenticador
from apps.contas.models import Autenticador, Convite, Perfil, StatusUsuario, Usuario
from apps.contratos import prontos
from apps.contratos import services as contratos_services
from apps.contratos.models import ModeloContrato
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.locacoes.models import Locacao
from apps.plataforma.models import Empresa, Plano
from apps.plataforma.services import Administrador, criar_empresa
from apps.veiculos.models import Veiculo

from . import carteira, frota
from .relogio import RelogioDoSeed

SUBDOMINIO = "motorapida"
CNPJ = "12.345.678/0001-95"
SENHA_DEV = "giro-dev-2026"
# Semente fixa do autenticador (hex de 20 bytes): `seed_moto_rapida --codigo <e-mail>` mostra o
# código de agora. Só para desenvolvimento.
CHAVE_2FA = "67" * 20
INICIO = "2026-10-07 07:00"
PERFIS_COM_2FA = {Perfil.ADMINISTRADOR, Perfil.FINANCEIRO}

# nome → (e-mail, perfil). A Mariana nasce com a empresa; as outras são convidadas por ela.
PESSOAS = {
    "Mariana Costa": ("mariana@motorapida.com.br", Perfil.ADMINISTRADOR),
    "Rodrigo Pinheiro": ("rodrigo@motorapida.com.br", Perfil.GERENTE),
    "Bruna Alves": ("bruna@motorapida.com.br", Perfil.VENDEDOR),
    "João Silva": ("joao@motorapida.com.br", Perfil.VISTORIADOR),
    "Lúcia Freitas": ("lucia@motorapida.com.br", Perfil.FINANCEIRO),
}
CENTRO: dict[str, Any] = {
    "nome": "Filial Centro",
    "matriz": False,
    "cnpj": CNPJ,
    "endereco": {
        "cep": "60325-000",
        "logradouro": "Av. Bezerra de Menezes",
        "numero": "1200",
        "complemento": None,
        "bairro": "São Gerardo",
        "cidade": "Fortaleza",
        "uf": "CE",
    },
    "contato": {"telefone": "8532123344", "whatsapp": None, "email": "centro@motorapida.com.br"},
    "horario": {
        **{
            dia: [{"abre": "08:00", "fecha": "18:00"}]
            for dia in ("seg", "ter", "qua", "qui", "sex")
        },
        "sab": [{"abre": "08:00", "fecha": "12:00"}],
        "dom": [],
    },
}


@dataclass
class Resultado:
    empresa: Empresa
    criado: list[str]
    existente: list[str]


def _autenticador_fixo(usuario: Usuario) -> None:
    dispositivo = novo_autenticador(usuario)
    dispositivo.definir_chave(CHAVE_2FA)
    dispositivo.save()
    confirmar_autenticador(dispositivo)


def _ativar(usuario: Usuario) -> None:
    """Convite aceito com a senha de desenvolvimento e, nos perfis que exigem, 2 etapas
    confirmadas (USR-01, USR-02). O token em claro só existe na criação: o seed gera outro."""
    convite = Convite.objects.filter(usuario=usuario, aceito_em__isnull=True).latest("criado_em")
    token = contas_services.renovar_token(convite)
    contas_services.aceitar_convite(token, SENHA_DEV, usuario.nome)
    if usuario.perfil in PERFIS_COM_2FA:
        _autenticador_fixo(usuario)
    contas_services.ativar_depois_do_2fa(usuario)
    usuario.refresh_from_db()


def _empresa(relogio: RelogioDoSeed, criado: list[str], existente: list[str]) -> Empresa:
    empresa = Empresa.objects.filter(subdominio=SUBDOMINIO).first()
    if empresa is not None:
        existente.append("empresa")
        return empresa  # type: ignore[no-any-return]
    relogio.em(INICIO)
    nome, (email, _) = next(iter(PESSOAS.items()))
    empresa = criar_empresa(
        razao_social="Moto Rápida Locações Ltda",
        nome_exibicao="Moto Rápida",
        cnpj=CNPJ,
        subdominio=SUBDOMINIO,
        plano=Plano.objects.get(nome="Profissional"),
        administrador=Administrador(nome=nome, email=email),
        cidade="Fortaleza",
        uf="CE",
    )
    criado.append("empresa")
    return empresa


def _pessoas(mariana: Usuario, centro: Filial, criado: list[str]) -> dict[str, Usuario]:
    pessoas = {"Mariana Costa": mariana}
    for nome, (email, perfil) in list(PESSOAS.items())[1:]:
        usuario = Usuario.objects.filter(email=email).first()
        if usuario is None:
            usuario = contas_services.convidar(
                email=email, perfil=perfil, filiais=[centro.pk], nome=nome, por=mariana
            )
            _ativar(usuario)
            criado.append(nome)
        pessoas[nome] = usuario
    return pessoas


def semear() -> Resultado:
    criado: list[str] = []
    existente: list[str] = []
    with RelogioDoSeed(INICIO) as relogio:
        empresa = _empresa(relogio, criado, existente)
        with tenant_context(empresa):
            with transaction.atomic():
                mariana = Usuario.objects.get(email=PESSOAS["Mariana Costa"][0])
                if mariana.status != StatusUsuario.ATIVO:
                    _ativar(mariana)
                    criado.append("Mariana Costa")
                centro = Filial.objects.filter(nome=CENTRO["nome"]).first()
                if centro is None:
                    centro = filiais_services.criar_filial(CENTRO, mariana)
                    criado.append("filial")
                pessoas = _pessoas(mariana, centro, criado)
            if not Veiculo.objects.exists():
                with transaction.atomic():
                    base = frota.montar_frota(centro, empresa, relogio)
                    criado.append("frota")
                    relogio.em("2026-10-07 10:00")
                    if not Locacao.objects.exists():
                        _publicar_modelo_de_contrato()
                        carteira.carregar(base, pessoas["Bruna Alves"], relogio)
                        _bloquear_rafael()
                        criado.append("locações")
            else:
                existente.append("frota")
    return Resultado(empresa, criado, existente)


def _bloquear_rafael() -> None:
    """Caso "Bloqueio" (CLI-05): Rafael Sousa, conta de 12 set, 25 dias de atraso em 07 out."""
    from datetime import date

    rafael = Cliente.objects.get(nome="Rafael Sousa")
    clientes_services.bloquear_por_atraso(rafael.pk, 25, date(2026, 9, 12))


def codigo_de_2fa(email: str) -> str:
    """Código TOTP de agora do autenticador do seed (relógio de verdade)."""
    empresa = Empresa.objects.get(subdominio=SUBDOMINIO)
    with tenant_context(empresa):
        dispositivo = Autenticador.objects.get(user__email=email.strip().lower(), confirmed=True)
        return f"{dispositivo.totp().token():0{dispositivo.DIGITOS}d}"


def _publicar_modelo_de_contrato() -> None:
    """A locação só se confirma com modelo de contrato publicado (IMP-04)."""
    if not ModeloContrato.objects.filter(publicado=True, finalidade="locacao").exists():
        modelo = contratos_services.criar_de_pronto(None, prontos.PRONTOS[0].chave)
        contratos_services.publicar_modelo(modelo)
