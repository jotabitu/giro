"""Entrada e formato de resposta da importação (docs/api/importacao.md). As regras ficam no
serviço; aqui só a forma."""

from typing import Any

from rest_framework import serializers

from ..models import StatusImportacao, StatusLinha, TipoImportacao

# --- Entrada ---


class EnvioSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=TipoImportacao.choices)
    arquivo = serializers.FileField(allow_empty_file=True)  # o serviço explica o vazio
    filial_id = serializers.IntegerField(required=False, allow_null=True)


class CorrecaoSerializer(serializers.Serializer[Any]):
    dados = serializers.DictField(
        child=serializers.CharField(allow_blank=True, allow_null=True, trim_whitespace=True),
        required=False,
        help_text="Só os campos corrigidos, com os nomes das colunas da planilha.",
    )
    categoria_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text=(
            "Veículos (IMP-08): a categoria só desta linha, exceção do modelo; `null` volta a "
            "seguir o modelo. Ausente, não muda."
        ),
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs.get("dados") and "categoria_id" not in attrs:
            raise serializers.ValidationError({"dados": ["Informe o que corrigir."]})
        return attrs


class ModeloEscolhidoSerializer(serializers.Serializer[Any]):
    marca = serializers.CharField(trim_whitespace=True)
    modelo = serializers.CharField(trim_whitespace=True)
    categoria_id = serializers.IntegerField()


class EscolhaDeCategoriasSerializer(serializers.Serializer[Any]):
    modelos = ModeloEscolhidoSerializer(many=True, allow_empty=False)


# --- Saída ---


class FilialDaImportacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class ContagensDaImportacaoSerializer(serializers.Serializer[Any]):
    linhas = serializers.IntegerField()
    prontas = serializers.IntegerField()
    com_erro = serializers.IntegerField()
    importadas = serializers.IntegerField()
    acima_do_limite = serializers.IntegerField()


class PlanoDaImportacaoSerializer(serializers.Serializer[Any]):
    usado = serializers.IntegerField()
    limite = serializers.IntegerField(allow_null=True)
    cabem = serializers.IntegerField(allow_null=True)


class AvisoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    mensagem = serializers.CharField()


class OpcaoDeCategoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    tipo_veiculo = serializers.ChoiceField(choices=["moto", "carro"])


class ModeloDaImportacaoSerializer(serializers.Serializer[Any]):
    marca = serializers.CharField()
    modelo = serializers.CharField()
    veiculos = serializers.IntegerField()
    categoria_id = serializers.IntegerField(allow_null=True)


class CategoriasDaImportacaoSerializer(serializers.Serializer[Any]):
    pergunta = serializers.BooleanField(
        help_text="Mais de uma categoria oferecida: a tela mostra a escolha por modelo."
    )
    opcoes = OpcaoDeCategoriaSerializer(many=True)
    modelos = ModeloDaImportacaoSerializer(many=True)
    falta_escolher = serializers.BooleanField(
        help_text='Alguma linha a gravar sem categoria: "Importar" fica travado.'
    )


class ImportacaoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoImportacao.choices)
    arquivo = serializers.CharField(help_text="Nome original do arquivo; exiba escapado.")
    status = serializers.ChoiceField(choices=StatusImportacao.choices)
    filial_padrao = FilialDaImportacaoSerializer(allow_null=True)
    contagens = ContagensDaImportacaoSerializer()
    plano = PlanoDaImportacaoSerializer(
        allow_null=True, help_text="Só em veículos (IMP-03); clientes não têm limite."
    )
    categorias = CategoriasDaImportacaoSerializer(
        allow_null=True, help_text="Só em veículos (IMP-08)."
    )
    aviso = AvisoSerializer(allow_null=True)
    enviada_por = serializers.CharField()
    enviada_em = serializers.DateTimeField()
    concluida_em = serializers.DateTimeField(allow_null=True)
    apagar_em = serializers.DateField()


class ListaDeImportacoesSerializer(serializers.Serializer[Any]):
    resultados = ImportacaoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class ErroDaLinhaSerializer(serializers.Serializer[Any]):
    campo = serializers.CharField()
    codigo = serializers.CharField(help_text="`VEI-01`, `CLI-01` ou `validacao`.")
    mensagem = serializers.CharField()


class ObjetoDaLinhaSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["veiculo", "cliente"])
    id = serializers.IntegerField()


class LinhaSerializer(serializers.Serializer[Any]):
    numero = serializers.IntegerField()
    status = serializers.ChoiceField(choices=StatusLinha.choices)
    dados = serializers.DictField(
        child=serializers.CharField(allow_blank=True),
        help_text=(
            "Os valores das colunas reconhecidas. Para o suporte, linha de cliente resumida "
            "(AUD-09): nome, tipo, documento_mascarado e celular."
        ),
    )
    erros = ErroDaLinhaSerializer(many=True)
    objeto = ObjetoDaLinhaSerializer(allow_null=True)
    categoria_id = serializers.IntegerField(
        allow_null=True, required=False, help_text="Só em veículos (IMP-08)."
    )
    categoria_propria = serializers.BooleanField(
        required=False, help_text="A linha é exceção do modelo (IMP-08). Só em veículos."
    )


class ListaDeLinhasSerializer(serializers.Serializer[Any]):
    resultados = LinhaSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class PreparoSerializer(serializers.Serializer[Any]):
    filiais = FilialDaImportacaoSerializer(many=True)
    pede_filial = serializers.BooleanField()
    filial = FilialDaImportacaoSerializer(allow_null=True)
    pode_importar = serializers.BooleanField()
    motivo = serializers.CharField(allow_null=True)
