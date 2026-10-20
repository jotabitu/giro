"""Formato dos eventos e das exportações (docs/api/auditoria.md)."""

from typing import Any

from rest_framework import serializers

from comum.auditoria import Categoria, TipoAtor

from ..models import FormatoExportacao, ItemExportacao, StatusExportacao


class AtorSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoAtor.choices)
    id = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField()
    iniciais = serializers.CharField()


class SuporteDoEventoSerializer(serializers.Serializer[Any]):
    atendente = serializers.CharField()
    motivo = serializers.CharField()
    permissao = serializers.CharField()
    acesso_suporte_id = serializers.IntegerField()


class ObjetoDoEventoSerializer(serializers.Serializer[Any]):
    tipo = serializers.CharField()
    id = serializers.IntegerField(allow_null=True)
    codigo = serializers.CharField(allow_null=True)
    filial = serializers.CharField(allow_null=True)


class EventoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    ocorrido_em = serializers.DateTimeField()
    ator = AtorSerializer()
    suporte = SuporteDoEventoSerializer(allow_null=True)
    categoria = serializers.ChoiceField(choices=Categoria.choices)
    acao = serializers.CharField()
    resumo = serializers.CharField()
    detalhe = serializers.CharField(allow_blank=True)
    objeto = ObjetoDoEventoSerializer(allow_null=True)
    regra = serializers.CharField(allow_null=True)
    tom = serializers.ChoiceField(
        choices=["info", "alerta", "perigo"],
        allow_null=True,
        help_text="Como a linha aparece (T-201); `null` é texto comum. A tela não escolhe tom.",
    )


class EventoDetalheSerializer(EventoSerializer):
    antes = serializers.DictField()
    depois = serializers.DictField()
    ip = serializers.CharField(allow_null=True)
    aparelho = serializers.CharField(allow_blank=True)


class ListaDeEventosSerializer(serializers.Serializer[Any]):
    resultados = EventoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class PessoaDaAuditoriaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoAtor.choices)
    id = serializers.IntegerField(allow_null=True)
    nome = serializers.CharField()


class ListaDePessoasSerializer(serializers.Serializer[Any]):
    resultados = PessoaDaAuditoriaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


# --- Exportação ---


class PeriodoSerializer(serializers.Serializer[Any]):
    de = serializers.DateField()
    ate = serializers.DateField()


class ExportacaoEntradaSerializer(serializers.Serializer[Any]):
    itens = serializers.ListField(
        child=serializers.ChoiceField(choices=ItemExportacao.choices), allow_empty=True
    )
    formato = serializers.ChoiceField(choices=FormatoExportacao.choices)
    periodo = PeriodoSerializer(allow_null=True, required=False)
    # Só com `despesas` (FIN-16): o mês `AAAA-MM` e a filial da tela (`null` = todas).
    mes = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    filial_id = serializers.IntegerField(required=False, allow_null=True)


class ExportacaoCriadaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusExportacao.choices)


class ExportacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    solicitada_em = serializers.DateTimeField()
    solicitada_por = serializers.CharField()
    conteudo = serializers.CharField()
    formato = serializers.ChoiceField(choices=FormatoExportacao.choices)
    tamanho_bytes = serializers.IntegerField(allow_null=True)
    status = serializers.ChoiceField(choices=StatusExportacao.choices)
    expira_em = serializers.DateTimeField(allow_null=True)


class ListaDeExportacoesSerializer(serializers.Serializer[Any]):
    resultados = ExportacaoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)
