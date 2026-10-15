"""Formato das respostas da plataforma (docs/api/plataforma.md). Só leitura na fase 1.

Os valores são montados nos selectors; estes serializers descrevem o formato para o OpenAPI.
"""

from typing import Any

from rest_framework import serializers

from ..models import Plano


class PlanoSerializer(serializers.ModelSerializer[Plano]):
    preco_anual_centavos = serializers.IntegerField(read_only=True)
    empresas_no_plano = serializers.IntegerField(read_only=True)
    recursos = serializers.ListField(child=serializers.CharField())

    class Meta:
        model = Plano
        fields = [
            "id",
            "nome",
            "ativo",
            "ordem",
            "preco_mensal_centavos",
            "meses_cobrados_no_anual",
            "preco_anual_centavos",
            "limite_veiculos",
            "limite_filiais",
            "limite_usuarios",
            "recursos",
            "empresas_no_plano",
        ]


class SituacaoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class PlanoResumoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class UsoNaListaSerializer(serializers.Serializer[Any]):
    veiculos = serializers.IntegerField()
    limite_veiculos = serializers.IntegerField(allow_null=True)
    filiais = serializers.IntegerField()
    usuarios = serializers.IntegerField()


class EmpresaListaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome_exibicao = serializers.CharField()
    subdominio = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()
    plano = PlanoResumoSerializer(allow_null=True)
    status = serializers.CharField()
    uso = UsoNaListaSerializer()
    situacao = SituacaoSerializer()
    ultimo_acesso_em = serializers.DateTimeField(allow_null=True)


class UsoDoItemSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField(allow_null=True)
    aviso = serializers.BooleanField()


class UsoDoItemNaAssinaturaSerializer(UsoDoItemSerializer):
    bloqueado = serializers.BooleanField()


class UsoDetalheSerializer(serializers.Serializer[Any]):
    veiculos = UsoDoItemSerializer()
    filiais = UsoDoItemSerializer()
    usuarios = UsoDoItemSerializer()


class UsoAssinaturaSerializer(serializers.Serializer[Any]):
    veiculos = UsoDoItemNaAssinaturaSerializer()
    filiais = UsoDoItemNaAssinaturaSerializer()
    usuarios = UsoDoItemNaAssinaturaSerializer()


class ResponsavelSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    email = serializers.CharField()
    telefone = serializers.CharField()


class TesteSerializer(serializers.Serializer[Any]):
    inicio = serializers.DateField(allow_null=True)
    fim = serializers.DateField(allow_null=True)
    dias_restantes = serializers.IntegerField(allow_null=True)


class PassoSerializer(serializers.Serializer[Any]):
    passo = serializers.CharField()
    rotulo = serializers.CharField()
    concluido_em = serializers.DateField(allow_null=True)


class ImplantacaoSerializer(serializers.Serializer[Any]):
    etapa_funil = serializers.CharField()
    concluidos = serializers.IntegerField()
    total = serializers.IntegerField()
    passos = PassoSerializer(many=True)


class AcoesSerializer(serializers.Serializer[Any]):
    entrar_como_suporte = serializers.BooleanField()
    estender_teste = serializers.BooleanField()
    mudar_plano = serializers.BooleanField()
    suspender = serializers.BooleanField()


class FaturaRecenteSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    status = serializers.ChoiceField(choices=["aberta", "paga", "atrasada", "cancelada"])
    observacao = serializers.CharField(allow_null=True)


class EmpresaDetalheSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    razao_social = serializers.CharField()
    nome_exibicao = serializers.CharField()
    cnpj = serializers.CharField(allow_null=True)
    subdominio = serializers.CharField(allow_null=True)
    endereco_acesso = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()
    responsavel = ResponsavelSerializer()
    cliente_desde = serializers.DateField(allow_null=True)
    plano = PlanoResumoSerializer(allow_null=True)
    ciclo = serializers.CharField()
    preco_contratado_centavos = serializers.IntegerField()
    status = serializers.CharField()
    situacao = SituacaoSerializer()
    teste = TesteSerializer()
    uso = UsoDetalheSerializer()
    implantacao = ImplantacaoSerializer()
    locacoes_total = serializers.IntegerField()
    chamados_abertos = serializers.IntegerField()
    suporte_bloqueado = serializers.BooleanField()
    faturas_recentes = FaturaRecenteSerializer(many=True)
    acoes = AcoesSerializer()


class PlanoDaAssinaturaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    preco_contratado_centavos = serializers.IntegerField()
    ciclo = serializers.CharField()


class TesteDaAssinaturaSerializer(serializers.Serializer[Any]):
    fim = serializers.DateField()
    dias_restantes = serializers.IntegerField()


class AssinaturaSerializer(serializers.Serializer[Any]):
    plano = PlanoDaAssinaturaSerializer()
    status = serializers.CharField()
    teste = TesteDaAssinaturaSerializer(allow_null=True)
    faixa_aviso = serializers.CharField(allow_null=True)
    uso = UsoAssinaturaSerializer()
    somente_leitura = serializers.BooleanField()


class ContagensSerializer(serializers.Serializer[Any]):
    todas = serializers.IntegerField()
    pagantes = serializers.IntegerField()
    em_teste = serializers.IntegerField()
    ativa = serializers.IntegerField()
    com_problema = serializers.IntegerField()
    saindo = serializers.IntegerField()


class ListaDeEmpresasSerializer(serializers.Serializer[Any]):
    contagens = ContagensSerializer()
    resultados = EmpresaListaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class ListaDePlanosSerializer(serializers.Serializer[Any]):
    resultados = PlanoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
