"""Formato das respostas da plataforma (docs/api/plataforma.md). Só leitura na fase 1.

Os valores são montados nos selectors; estes serializers descrevem o formato para o OpenAPI.
"""

from typing import Any

from rest_framework import serializers

from ..models import MotivoCancelamento, Plano


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
    id = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField()
    preco_contratado_centavos = serializers.IntegerField()
    ciclo = serializers.CharField()


class TesteDaAssinaturaSerializer(serializers.Serializer[Any]):
    inicio = serializers.DateField(allow_null=True)
    fim = serializers.DateField()
    dias_restantes = serializers.IntegerField()


class ProximaFaturaSerializer(serializers.Serializer[Any]):
    vencimento = serializers.DateField()
    valor_centavos = serializers.IntegerField()
    descricao = serializers.CharField()


class PlanoProximoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    ciclo = serializers.CharField()
    vale_em = serializers.DateField(allow_null=True)


class CartaoDaFormaSerializer(serializers.Serializer[Any]):
    """Só a bandeira e o final: o token do cartão nunca sai da API (ADR 0023)."""

    bandeira = serializers.CharField()
    final = serializers.CharField()


class FormaDePagamentoSerializer(serializers.Serializer[Any]):
    forma = serializers.ChoiceField(choices=["cartao", "pix_automatico", "boleto"], allow_null=True)
    situacao = SituacaoSerializer()
    cartao = CartaoDaFormaSerializer(allow_null=True)
    prazo = serializers.DateField(allow_null=True)


class EnderecoDaNotaSerializer(serializers.Serializer[Any]):
    cep = serializers.CharField()
    logradouro = serializers.CharField()
    numero = serializers.CharField()
    complemento = serializers.CharField(allow_null=True, required=False)
    bairro = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()


class DadosFiscaisSerializer(serializers.Serializer[Any]):
    razao_social = serializers.CharField()
    cnpj = serializers.CharField(allow_null=True)
    endereco = EnderecoDaNotaSerializer(allow_null=True)
    email_cobranca = serializers.CharField()


class PlanoDaOfertaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    preco_mensal_centavos = serializers.IntegerField()


class OfertaSerializer(serializers.Serializer[Any]):
    titulo = serializers.CharField()
    plano = PlanoDaOfertaSerializer()
    itens = serializers.ListField(child=serializers.CharField())


class AcoesDaAssinaturaSerializer(serializers.Serializer[Any]):
    mudar_plano = serializers.BooleanField()
    desfazer_mudanca_plano = serializers.BooleanField()
    escolher_forma_pagamento = serializers.BooleanField()
    editar_dados_fiscais = serializers.BooleanField()
    cancelar = serializers.BooleanField()
    desfazer_cancelamento = serializers.BooleanField()
    pausar = serializers.BooleanField()
    voltar_pausa = serializers.BooleanField()
    desistir_pausa = serializers.BooleanField()


class CancelamentoMarcadoSerializer(serializers.Serializer[Any]):
    """Só com cancelamento marcado (`cancelamento.md`, PLT-06)."""

    pedido_em = serializers.DateTimeField(allow_null=True)
    motivo = serializers.ChoiceField(choices=MotivoCancelamento.choices, allow_null=True)
    acesso_ate = serializers.DateField()
    rotulo = serializers.CharField()


class PausaMarcadaSerializer(serializers.Serializer[Any]):
    """Só com pausa marcada: agendada (`ativa`) ou em andamento (`pausada`)."""

    situacao = serializers.ChoiceField(choices=["agendada", "em_andamento"])
    meses = serializers.IntegerField()
    inicio = serializers.DateField()
    ate = serializers.DateField()
    volta_em = serializers.DateField()
    rotulo = serializers.CharField()


class AssinaturaSerializer(serializers.Serializer[Any]):
    plano = PlanoDaAssinaturaSerializer()
    status = serializers.CharField()
    teste = TesteDaAssinaturaSerializer(allow_null=True)
    proxima_fatura = ProximaFaturaSerializer(allow_null=True)
    plano_proximo = PlanoProximoSerializer(allow_null=True)
    faixa_aviso = serializers.CharField(allow_null=True)
    uso = UsoAssinaturaSerializer()
    somente_leitura = serializers.BooleanField()
    cancelamento = CancelamentoMarcadoSerializer(allow_null=True)
    pausa = PausaMarcadaSerializer(allow_null=True)
    # Só para o administrador (ausentes para os outros perfis).
    forma_pagamento = FormaDePagamentoSerializer(required=False)
    dados_fiscais = DadosFiscaisSerializer(required=False)
    oferta = OfertaSerializer(required=False, allow_null=True)
    acoes = AcoesDaAssinaturaSerializer(required=False)


def representar_assinatura(dados: dict[str, Any]) -> dict[str, Any]:
    """Os blocos do administrador ficam fora da resposta dos outros perfis (não vêm `null`)."""
    return {
        chave: valor for chave, valor in AssinaturaSerializer(dados).data.items() if chave in dados
    }


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


# --- Andamento do assistente (T-201, T-202) ---


class PassoDoAssistenteSerializer(serializers.Serializer[Any]):
    passo = serializers.CharField()
    numero = serializers.IntegerField()
    rotulo = serializers.CharField()
    feito = serializers.BooleanField()
    feito_em = serializers.DateField(allow_null=True)


class AndamentoDoAssistenteSerializer(serializers.Serializer[Any]):
    concluida = serializers.BooleanField(help_text="IMP-01: passo `primeira_locacao` marcado.")
    total = serializers.IntegerField(help_text="8 passos; 7 sem `recebimentos` (PLT-12).")
    feitos = serializers.IntegerField()
    proximo = serializers.CharField(allow_null=True)
    passos = PassoDoAssistenteSerializer(many=True)
