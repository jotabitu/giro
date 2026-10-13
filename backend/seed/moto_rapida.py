"""Seed parcial da Moto Rápida (T-127): o que não depende do financeiro da T-017.

Cria, pelos serviços de domínio e de forma idempotente (cada passo confere o que já existe):
empresa com subdomínio, Filial Centro, uma pessoa por perfil, as 4 categorias com os preços, as
86 motos e carros, os clientes e as 42 locações abertas de 07 out 2026 (LOC-2836 pela confirmação
de verdade). O financeiro de 07 out (caixa, despesas, caução) vem de `seed/financeiro.py` (T-019).
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import transaction
from django_tenants.utils import get_public_schema_name, schema_context, tenant_context

from apps.contas import services as contas_services
from apps.contas.dois_fatores import confirmar_autenticador, novo_autenticador
from apps.contas.models import (
    Autenticador,
    Convite,
    FuncaoPlataforma,
    Perfil,
    StatusUsuario,
    Usuario,
)
from apps.contratos import prontos
from apps.contratos import services as contratos_services
from apps.contratos.models import ModeloContrato
from apps.filiais import services as filiais_services
from apps.filiais.models import Filial
from apps.financeiro import services as financeiro_services
from apps.financeiro.models import Caixa, ContaReceber, StatusConta
from apps.locacoes import services as locacoes_services
from apps.locacoes.models import Locacao, PlanoEspecial
from apps.plataforma.models import Empresa, Plano
from apps.plataforma.services import Administrador, criar_empresa, registrar_passo_implantacao
from apps.veiculos.models import Categoria, Veiculo
from comum.estados import transicionar

from . import carteira, frota
from . import financeiro as financeiro_do_seed
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


# Equipe da plataforma Giro (schema público): o dono, com 2 etapas (PLT-08, PLT-09).
DONO_DA_PLATAFORMA = ("Dono Giro", "dono@giro.example")
# Empresas fictícias para o painel da plataforma (PLT-01, PLT-02). subdomínio → (nome, estado,
# início do teste). A assinatura ativa e a inadimplente seguem a tabela de estados (em_teste →
# ativa → inadimplente). Pausada e cancelada ficam em teste: `Empresa.TRANSICOES` ainda não tem
# serviço de pausar nem de cancelar (fase 2), e o seed não grava estado direto (ver T-138).
OUTRAS_EMPRESAS = {
    "pedalada": ("Pedalada Motos", "ativa", "2026-08-03"),
    "rodavida": ("Roda Vida Locações", "inadimplente", "2026-07-06"),
    "ventosul": ("Vento Sul Veículos", "pausada", "2026-08-17"),
    "estradafacil": ("Estrada Fácil Aluguel", "cancelada", "2026-06-01"),
}
DIA_DA_ATIVACAO = {"ativa": "2026-08-18", "inadimplente": "2026-07-21"}
DIA_DA_FALTA = "2026-09-25"  # fatura de 21 set sem pagamento: inadimplente (PLT-02)


def _cnpj_ficticio(base: int) -> str:
    digitos = [int(d) for d in f"{base:08d}0001"]
    for _ in range(2):
        pesos = [(len(digitos) - i - 1) % 8 + 2 for i in range(len(digitos))]
        soma = sum(d * p for d, p in zip(digitos, pesos, strict=True))
        resto = soma % 11
        digitos.append(0 if resto < 2 else 11 - resto)
    texto = "".join(map(str, digitos))
    return f"{texto[:2]}.{texto[2:5]}.{texto[5:8]}/{texto[8:12]}-{texto[12:]}"


def _dono_da_plataforma(criado: list[str]) -> None:
    """Usuário da plataforma no schema público, com a função Dono e 2 etapas confirmadas."""
    nome, email = DONO_DA_PLATAFORMA
    with schema_context(get_public_schema_name()):
        if Usuario.objects.filter(email=email).exists():
            return
        with transaction.atomic():
            usuario, _ = contas_services.convidar_equipe_plataforma(
                email, FuncaoPlataforma.DONO, nome
            )
            _ativar(usuario)
        criado.append("dono da plataforma")


# Equipe da plataforma (linha "Pessoas" dos dados de referência): a Larissa fica com o convite
# pendente.
EQUIPE_DA_PLATAFORMA = (
    ("Diego Santos", "diego@giro.example", FuncaoPlataforma.SUPORTE, True),
    ("Paula Andrade", "paula@giro.example", FuncaoPlataforma.FINANCEIRO, True),
    ("Caio Ribeiro", "caio@giro.example", FuncaoPlataforma.SUCESSO, True),
    ("Larissa Melo", "larissa@giro.example", FuncaoPlataforma.SUPORTE, False),
)


def _equipe_da_plataforma(criado: list[str]) -> None:
    with schema_context(get_public_schema_name()):
        for nome, email, funcao, ativa in EQUIPE_DA_PLATAFORMA:
            if Usuario.objects.filter(email=email).exists():
                continue
            with transaction.atomic():
                usuario, _ = contas_services.convidar_equipe_plataforma(email, funcao, nome)
                if ativa:
                    _ativar(usuario)
            criado.append(f"equipe {nome.split()[0]}")


def _outras_empresas(relogio: RelogioDoSeed, criado: list[str]) -> None:
    """4 empresas pequenas (empresa, administrador e uma filial), cada uma no estado da assinatura
    que os serviços alcançam hoje."""
    for numero, (subdominio, (nome, estado, inicio)) in enumerate(OUTRAS_EMPRESAS.items(), 1):
        with schema_context(get_public_schema_name()):
            if Empresa.objects.filter(subdominio=subdominio).exists():
                continue
        relogio.em(f"{inicio} 09:00")
        email = f"admin@{subdominio}.example"
        empresa = criar_empresa(
            razao_social=f"{nome} Ltda",
            nome_exibicao=nome,
            cnpj=_cnpj_ficticio(30000000 + numero * 1111),
            subdominio=subdominio,
            plano=Plano.objects.get(nome="Essencial" if numero % 2 else "Profissional"),
            administrador=Administrador(nome=f"Admin {nome.split()[0]}", email=email),
            cidade="Fortaleza",
            uf="CE",
        )
        with tenant_context(empresa):
            administrador = Usuario.objects.get(email=email)
            _ativar(administrador)
            filiais_services.criar_filial(
                {**CENTRO, "nome": "Filial Matriz", "cnpj": None}, administrador
            )
        if estado in DIA_DA_ATIVACAO:
            relogio.em(f"{DIA_DA_ATIVACAO[estado]} 09:00")
            transicionar(empresa, "ativa", acao="empresa.ativar", regra="PLT-01")
        if estado == "inadimplente":
            relogio.em(f"{DIA_DA_FALTA} 09:00")
            transicionar(empresa, "inadimplente", acao="empresa.inadimplente", regra="PLT-02")
        criado.append(f"empresa {subdominio}")


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
    if usuario.funcao_plataforma or usuario.perfil in PERFIS_COM_2FA:
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
                        carteira.carregar(
                            base,
                            pessoas["Bruna Alves"],
                            relogio,
                            gerente=pessoas["Rodrigo Pinheiro"],
                            conferencia=True,
                        )
                        _bloquear_rafael()
                        criado.append("locações")
            else:
                existente.append("frota")
            _configuracao(criado)
            if not Caixa.objects.exists():
                with transaction.atomic():
                    financeiro_do_seed.carregar(centro, pessoas, relogio)
                    criado.append("financeiro")
    with RelogioDoSeed(INICIO) as relogio:
        _dono_da_plataforma(criado)
        _equipe_da_plataforma(criado)
        _outras_empresas(relogio, criado)
    return Resultado(empresa, criado, existente)


PASSOS_FEITOS_NO_DEV = ("marca", "ramo", "precos", "contrato", "recebimentos", "importar", "equipe")


def _configuracao(criado: list[str]) -> None:
    """Planos especiais da tabela (Entregador R$ 279,00 por semana, Mensal fidelidade −10% a
    partir do 3º mês) e os passos do assistente de implantação (IMP-01): a Moto Rápida já passou
    por todos, e a Mariana entra no painel geral."""
    if not PlanoEspecial.objects.exists():
        urbana = Categoria.objects.get(nome="Urbana 110–125")
        locacoes_services.criar_plano(
            {
                "nome": "Entregador",
                "periodicidade": "semanal",
                "regra": "preco_fixo",
                "preco_centavos": 27900,
                "categorias": [urbana.pk],
                "condicoes": "Km livre e troca de óleo inclusa",
            }
        )
        locacoes_services.criar_plano(
            {
                "nome": "Mensal fidelidade",
                "periodicidade": "mensal",
                "regra": "desconto",
                "desconto_pct": "10.00",
                "a_partir_do_periodo": 3,
                "categorias": [],
                "condicoes": "10% a partir do 3º mês seguido",
            }
        )
        criado.append("planos especiais")
    for passo in PASSOS_FEITOS_NO_DEV:
        registrar_passo_implantacao(passo)


def _bloquear_rafael() -> None:
    """Caso "Bloqueio" (CLI-05): Rafael Sousa, conta de 12 set, 25 dias de atraso em 07 out. O
    pedido fica gravado na conta, como a régua faz (AUT-03): o desbloqueio manual vale."""
    conta = ContaReceber.objects.get(
        cliente__nome="Rafael Sousa", status=StatusConta.ABERTA, vencimento=date(2026, 9, 12)
    )
    financeiro_services.pedir_bloqueio(conta, 25)


def codigo_de_2fa(email: str) -> str:
    """Código TOTP de agora do autenticador do seed (relógio de verdade)."""
    equipe = {DONO_DA_PLATAFORMA[1], *(e for _, e, _, ativa in EQUIPE_DA_PLATAFORMA if ativa)}
    plataforma = email.strip().lower() in equipe
    empresa = Empresa.objects.get(subdominio=SUBDOMINIO)
    with schema_context(get_public_schema_name()) if plataforma else tenant_context(empresa):
        dispositivo = Autenticador.objects.get(user__email=email.strip().lower(), confirmed=True)
        return f"{dispositivo.totp().token():0{dispositivo.DIGITOS}d}"


def _publicar_modelo_de_contrato() -> None:
    """A locação só se confirma com modelo de contrato publicado (IMP-04)."""
    if not ModeloContrato.objects.filter(publicado=True, finalidade="locacao").exists():
        modelo = contratos_services.criar_de_pronto(None, prontos.PRONTOS[0].chave)
        contratos_services.publicar_modelo(modelo)
