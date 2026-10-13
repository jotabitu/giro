"""Entrada e formato de resposta de clientes (docs/api/clientes.md).

As regras (CPF, unicidade, pendências, transições) são conferidas no serviço; aqui só a forma.
"""

from typing import Any

from rest_framework import serializers

from ..models import CategoriaCnh, StatusCliente, TipoCliente, TipoDocumentoCliente

# --- Entrada ---


class CnhEntradaClienteSerializer(serializers.Serializer[Any]):
    numero = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    categoria = serializers.ChoiceField(
        choices=CategoriaCnh.choices, required=False, allow_blank=True, allow_null=True
    )
    validade = serializers.DateField(required=False, allow_null=True)
    primeira_habilitacao = serializers.DateField(required=False, allow_null=True)


class ResponsavelEntradaClienteSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    cpf = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    celular = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )


class EnderecoEntradaClienteSerializer(serializers.Serializer[Any]):
    cep = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    logradouro = serializers.CharField(
        max_length=150, required=False, allow_blank=True, allow_null=True
    )
    numero = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    complemento = serializers.CharField(
        max_length=80, required=False, allow_blank=True, allow_null=True
    )
    bairro = serializers.CharField(max_length=80, required=False, allow_blank=True, allow_null=True)
    cidade = serializers.CharField(max_length=80, required=False, allow_blank=True, allow_null=True)
    uf = serializers.CharField(max_length=2, required=False, allow_blank=True, allow_null=True)


class ReferenciaEntradaClienteSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=150, required=False, allow_blank=True, allow_null=True)
    parentesco = serializers.CharField(
        max_length=40, required=False, allow_blank=True, allow_null=True
    )
    telefone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )


class ClienteEdicaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=150, required=False)
    documento = serializers.CharField(max_length=20, required=False)
    nascimento = serializers.DateField(required=False, allow_null=True)
    celular = serializers.CharField(max_length=20, required=False)
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)
    profissao = serializers.CharField(
        max_length=80, required=False, allow_blank=True, allow_null=True
    )
    cnh = CnhEntradaClienteSerializer(required=False, allow_null=True)
    responsavel = ResponsavelEntradaClienteSerializer(required=False, allow_null=True)
    endereco = EnderecoEntradaClienteSerializer(required=False, allow_null=True)
    referencia = ReferenciaEntradaClienteSerializer(required=False, allow_null=True)
    consentimento = serializers.BooleanField(required=False)


class ClienteEntradaSerializer(ClienteEdicaoSerializer):
    tipo = serializers.ChoiceField(choices=TipoCliente.choices)
    nome = serializers.CharField(max_length=150)
    documento = serializers.CharField(max_length=20)
    celular = serializers.CharField(max_length=20)


class DocumentoEntradaClienteSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoDocumentoCliente.choices)
    arquivo = serializers.FileField()


class MotivoClienteSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField()


# --- Saída ---


class SituacaoClienteSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class AlvoClienteSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["conta", "cliente", "venda", "locacao"])
    id = serializers.IntegerField()


class AcaoPrincipalClienteSerializer(serializers.Serializer[Any]):
    codigo = serializers.ChoiceField(
        choices=["cobrar", "completar_cadastro", "ver_proposta", "ver_locacao", "nova_locacao"]
    )
    rotulo = serializers.CharField()
    alvo = AlvoClienteSerializer(allow_null=True)


class ClienteSerializer(serializers.Serializer[Any]):
    """Representação resumida: listas e quem não cadastra (AUD-04, AUD-09)."""

    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoCliente.choices)
    nome = serializers.CharField()
    documento_mascarado = serializers.CharField()
    celular = serializers.CharField()
    status = serializers.ChoiceField(choices=StatusCliente.choices)
    situacao = SituacaoClienteSerializer()
    cliente_desde = serializers.DateField()
    locacao_atual = serializers.DictField(allow_null=True)
    ultima_locacao = serializers.DictField(allow_null=True)
    financeiro = serializers.DictField(allow_null=True)
    venda_aberta = serializers.DictField(allow_null=True)
    acao_principal = AcaoPrincipalClienteSerializer(allow_null=True)


class CnhClienteSerializer(serializers.Serializer[Any]):
    numero = serializers.CharField()
    categoria = serializers.CharField()
    validade = serializers.DateField(allow_null=True)
    primeira_habilitacao = serializers.DateField(allow_null=True)
    situacao = serializers.ChoiceField(
        choices=["valida", "vencida", "vencida_impede"], allow_null=True
    )


class ResponsavelClienteSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    cpf = serializers.CharField()
    celular = serializers.CharField()


class EnderecoClienteSerializer(serializers.Serializer[Any]):
    cep = serializers.CharField()
    logradouro = serializers.CharField()
    numero = serializers.CharField()
    complemento = serializers.CharField(allow_null=True)
    bairro = serializers.CharField()
    cidade = serializers.CharField()
    uf = serializers.CharField()


class ReferenciaClienteSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    parentesco = serializers.CharField()
    telefone = serializers.CharField()


class BloqueioClienteSerializer(serializers.Serializer[Any]):
    motivo = serializers.ChoiceField(choices=["atraso", "manual"])
    desde = serializers.DateTimeField()
    descricao = serializers.CharField()
    desbloqueia_sozinho = serializers.BooleanField()


class DocumentoClienteSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoDocumentoCliente.choices)
    enviado_em = serializers.DateTimeField(allow_null=True)
    url = serializers.CharField(allow_null=True)
    url_expira_em = serializers.DateTimeField(allow_null=True)


class ItemAnaliseClienteSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    situacao = serializers.ChoiceField(choices=["ok", "pendente", "problema"])
    rotulo = serializers.CharField()


class AnaliseClienteSerializer(serializers.Serializer[Any]):
    itens = ItemAnaliseClienteSerializer(many=True)


class ClienteDoFinanceiroSerializer(ClienteSerializer):
    """USR-09: a ficha do cliente para o financeiro, com contato e o motivo do bloqueio."""

    email = serializers.CharField()
    bloqueio = BloqueioClienteSerializer(allow_null=True)


class ClienteDetalheSerializer(ClienteSerializer):
    """Representação completa: só quem cadastra, nunca o suporte."""

    documento = serializers.CharField()
    nascimento = serializers.DateField(allow_null=True)
    idade = serializers.IntegerField(allow_null=True)
    email = serializers.CharField()
    profissao = serializers.CharField()
    cnh = CnhClienteSerializer(allow_null=True)
    responsavel = ResponsavelClienteSerializer(allow_null=True)
    endereco = EnderecoClienteSerializer(allow_null=True)
    referencia = ReferenciaClienteSerializer(allow_null=True)
    consentimento_em = serializers.DateTimeField(allow_null=True)
    bloqueio = BloqueioClienteSerializer(allow_null=True)
    documentos = DocumentoClienteSerializer(many=True)
    pendencias = serializers.ListField(child=serializers.CharField())
    analise = AnaliseClienteSerializer()


class ContagensClienteSerializer(serializers.Serializer[Any]):
    todos = serializers.IntegerField()
    com_locacao = serializers.IntegerField(allow_null=True)
    em_aberto = serializers.IntegerField(allow_null=True)
    bloqueados = serializers.IntegerField()
    incompletos = serializers.IntegerField()
    inativos = serializers.IntegerField()


class IndicadoresClienteSerializer(serializers.Serializer[Any]):
    novos_no_mes_anterior = serializers.IntegerField()
    com_locacao_pct = serializers.CharField(allow_null=True)
    em_aberto_total_centavos = serializers.IntegerField(allow_null=True)


class ListaDeClientesSerializer(serializers.Serializer[Any]):
    contagens = ContagensClienteSerializer()
    indicadores = IndicadoresClienteSerializer()
    resultados = ClienteSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class PedidoAprovacaoClienteSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    status = serializers.CharField()


class PedidoAprovacaoCriadoClienteSerializer(serializers.Serializer[Any]):
    pedido_aprovacao = PedidoAprovacaoClienteSerializer()
