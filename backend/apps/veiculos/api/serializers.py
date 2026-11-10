"""Entrada e formato de resposta de veículos, categorias, preços e extras (docs/api/veiculos.md).

As regras (placa, chassi, categoria da filial, unicidade, transições) são conferidas no
serviço; aqui só a forma.
"""

from typing import Any

from rest_framework import serializers

from ..models import Combustivel, Especie, Extra, StatusVeiculo, TipoDocumento, TipoVeiculo
from ..services import MENSAGENS_DA_VEI_09, MOTIVOS_DE_BAIXA

# --- Entrada ---


def _mensagens(chave: str) -> dict[str, Any]:
    """A mensagem da VEI-09 para qualquer recusa de forma do campo (CA-421-07)."""
    mensagem = MENSAGENS_DA_VEI_09[chave]
    return dict.fromkeys(
        ("invalid", "min_value", "max_value", "max_string_length", "max_length", "invalid_choice"),
        mensagem,
    )


def _inteiro(chave: str, minimo: int, maximo: int) -> serializers.IntegerField:
    return serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=minimo,
        max_value=maximo,
        error_messages=_mensagens(chave),
    )


def _texto(chave: str, maximo: int | None = None) -> serializers.CharField:
    """Até `maximo` depois de tirar os espaços das pontas; os códigos (motor, rastreador) o
    serviço confere depois de tirar os espaços do meio."""
    opcoes: dict[str, Any] = {"max_length": maximo} if maximo else {}
    return serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        error_messages=_mensagens(chave),
        **opcoes,
    )


class DocumentoDoVeiculoEntradaSerializer(serializers.Serializer[Any]):
    """Bloco `documento` da VEI-09 (T-421). Formato e mensagens em docs/api/veiculos.md."""

    potencia_cv = _inteiro("documento.potencia_cv", 1, 999)
    cilindrada_cc = _inteiro("documento.cilindrada_cc", 1, 9999)
    especie = serializers.ChoiceField(
        choices=Especie.choices,
        required=False,
        allow_null=True,
        allow_blank=True,
        error_messages=_mensagens("documento.especie"),
    )
    tipo = _texto("documento.tipo", 30)
    carroceria = _texto("documento.carroceria", 30)
    lotacao = _inteiro("documento.lotacao", 1, 99)
    peso_bruto_kg = _inteiro("documento.peso_bruto_kg", 1, 99999)
    numero_motor = _texto("documento.numero_motor")
    observacoes = _texto("documento.observacoes", 500)


class RastreadorEntradaSerializer(serializers.Serializer[Any]):
    numero = _texto("rastreador.numero")
    empresa = _texto("rastreador.empresa", 60)


def _pontuar(erros: Any) -> Any:
    """Erro dos blocos com a chave pontuada: `{"documento.potencia_cv": [...]}` (CA-421-07)."""
    if not isinstance(erros, dict):
        return erros
    achatados: dict[str, Any] = {}
    for chave, valor in erros.items():
        if chave in ("documento", "rastreador") and isinstance(valor, dict):
            achatados.update({f"{chave}.{campo}": v for campo, v in valor.items()})
        else:
            achatados[chave] = valor
    return achatados


class ComBlocosDaVei09:
    """Os blocos `documento` e `rastreador` e as `anotacoes` (VEI-09), todos opcionais. Em
    `multipart/form-data` os blocos vão achatados (`documento.potencia_cv`), e o DRF os monta."""

    def to_internal_value(self, data: Any) -> Any:
        try:
            return super().to_internal_value(data)  # type: ignore[misc]
        except serializers.ValidationError as erro:
            raise serializers.ValidationError(_pontuar(erro.detail)) from erro


class VeiculoEntradaSerializer(ComBlocosDaVei09, serializers.Serializer[Any]):
    placa = serializers.CharField(max_length=10)
    chassi = serializers.CharField(max_length=20)
    renavam = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    marca = serializers.CharField(max_length=40)
    modelo = serializers.CharField(max_length=60)
    ano_fabricacao = serializers.IntegerField()
    ano_modelo = serializers.IntegerField()
    cor = serializers.CharField(max_length=30)
    combustivel = serializers.ChoiceField(
        choices=Combustivel.choices, required=False, allow_null=True
    )
    km_atual = serializers.IntegerField(min_value=0, required=False)
    categoria_id = serializers.IntegerField()
    filial_id = serializers.IntegerField()
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, required=False, allow_null=True, min_value=0
    )
    valor_compra_centavos = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    data_compra = serializers.DateField(required=False, allow_null=True)
    entrou_na_frota_em = serializers.DateField(required=False)
    documento = DocumentoDoVeiculoEntradaSerializer(required=False)
    rastreador = RastreadorEntradaSerializer(required=False)
    anotacoes = _texto("anotacoes", 500)


class VeiculoComCrlvEntradaSerializer(VeiculoEntradaSerializer):
    """`multipart/form-data`: o cadastro e o CRLV lido pela leitura (VEI-08, ADR 0026, item 8)."""

    crlv_arquivo = serializers.FileField(required=False, allow_null=True)
    crlv_validade = serializers.DateField(required=False, allow_null=True)
    crlv_exercicio = serializers.IntegerField(
        required=False, allow_null=True, min_value=1900, max_value=2100
    )
    leitura = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if attrs.get("crlv_arquivo") and not attrs.get("crlv_validade"):
            raise serializers.ValidationError({"crlv_validade": "Informe a validade do CRLV."})
        return attrs


class LeituraCrlvEntradaSerializer(serializers.Serializer[Any]):
    """`multipart/form-data`: o PDF do CRLV-e, até 2 MB (ADR 0026, item 6)."""

    arquivo = serializers.FileField()


class CamposDoCrlvNoEditarSerializer(serializers.Serializer[Any]):
    """Os campos lidos no editar (T-421): sem placa e chassi, que no editar não mudam. Os da
    VEI-09 têm a chave pontuada (`documento.potencia_cv`), no formato do corpo do cadastro."""

    renavam = serializers.CharField(allow_null=True)
    marca = serializers.CharField(allow_null=True)
    modelo = serializers.CharField(allow_null=True)
    ano_fabricacao = serializers.IntegerField(allow_null=True)
    ano_modelo = serializers.IntegerField(allow_null=True)
    cor = serializers.CharField(allow_null=True)
    combustivel = serializers.ChoiceField(choices=Combustivel.choices, allow_null=True)

    def get_fields(self) -> dict[str, serializers.Field[Any, Any, Any, Any]]:
        campos = super().get_fields()
        campos.update(
            {
                "documento.potencia_cv": serializers.IntegerField(allow_null=True),
                "documento.cilindrada_cc": serializers.IntegerField(allow_null=True),
                "documento.especie": serializers.ChoiceField(
                    choices=Especie.choices, allow_null=True
                ),
                "documento.tipo": serializers.CharField(allow_null=True),
                "documento.carroceria": serializers.CharField(allow_null=True),
                "documento.lotacao": serializers.IntegerField(allow_null=True),
                "documento.peso_bruto_kg": serializers.IntegerField(allow_null=True),
                "documento.numero_motor": serializers.CharField(allow_null=True),
                "documento.observacoes": serializers.CharField(allow_null=True),
            }
        )
        return campos

    def to_representation(self, instance: Any) -> Any:
        # A chave pontuada é o nome do campo, não um caminho no dicionário.
        return {
            nome: None if instance.get(nome) is None else campo.to_representation(instance[nome])
            for nome, campo in self.fields.items()
        }


class CamposDoCrlvSerializer(CamposDoCrlvNoEditarSerializer):
    """Os campos lidos no cadastro: os 9 da VEI-08 e, com a chave pontuada
    (`documento.potencia_cv`), os 9 do documento da VEI-09 (T-421)."""

    placa = serializers.CharField(allow_null=True)
    chassi = serializers.CharField(allow_null=True)


class ModeloSerializer(serializers.Serializer[Any]):
    marca = serializers.CharField()
    modelo = serializers.CharField()
    tipo = serializers.ChoiceField(choices=["moto", "carro"])

    class Meta:
        # Nome próprio no OpenAPI: `contratos` já tem um `Modelo` (T-265).
        ref_name = "ModeloDoCatalogo"


class DicasDaLeituraSerializer(serializers.Serializer[Any]):
    marca_modelo = serializers.CharField(allow_null=True)
    # T-415: as versões do catálogo que batem com o texto, para a pessoa escolher uma.
    candidatos = ModeloSerializer(many=True)


class LeituraCrlvSerializer(serializers.Serializer[Any]):
    documento = serializers.ChoiceField(choices=["crlv"])
    campos = CamposDoCrlvSerializer()
    lidos = serializers.ListField(child=serializers.CharField())
    quantidade = serializers.IntegerField()
    rotulo = serializers.CharField()
    exercicio = serializers.IntegerField(allow_null=True)
    dicas = DicasDaLeituraSerializer()
    leitura = serializers.CharField()


class LeituraCrlvNoEditarSerializer(LeituraCrlvSerializer):
    """POST /api/veiculos/{id}/leitura-crlv/ (T-421): placa e chassi fora de `campos`."""

    campos = CamposDoCrlvNoEditarSerializer()  # type: ignore[assignment]


class VeiculoEdicaoSerializer(ComBlocosDaVei09, serializers.Serializer[Any]):
    renavam = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    marca = serializers.CharField(max_length=40, required=False)
    modelo = serializers.CharField(max_length=60, required=False)
    ano_fabricacao = serializers.IntegerField(required=False)
    ano_modelo = serializers.IntegerField(required=False)
    cor = serializers.CharField(max_length=30, required=False)
    combustivel = serializers.ChoiceField(
        choices=Combustivel.choices, required=False, allow_null=True
    )
    categoria_id = serializers.IntegerField(required=False)
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, required=False, allow_null=True, min_value=0
    )
    valor_compra_centavos = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    data_compra = serializers.DateField(required=False, allow_null=True)
    # VEI-09 (T-421): cada chave enviada substitui o valor; `null` ou "" apaga.
    documento = DocumentoDoVeiculoEntradaSerializer(required=False)
    rastreador = RastreadorEntradaSerializer(required=False)
    anotacoes = _texto("anotacoes", 500)
    # O comprovante da leitura no editar (POST /api/veiculos/{id}/leitura-crlv/).
    leitura = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=4000
    )


class CorrigirIdentificacaoSerializer(serializers.Serializer[Any]):
    placa = serializers.CharField(max_length=10, required=False)
    chassi = serializers.CharField(max_length=20, required=False)
    motivo = serializers.CharField()


class BloquearVeiculoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField()


class DesbloquearVeiculoSerializer(serializers.Serializer[Any]):
    motivo = serializers.CharField(required=False, allow_blank=True)


class ColocarAVendaSerializer(serializers.Serializer[Any]):
    valor_venda_centavos = serializers.IntegerField(min_value=1)
    referencia_fipe_centavos = serializers.IntegerField(
        min_value=0, required=False, allow_null=True
    )


class BaixarSerializer(serializers.Serializer[Any]):
    motivo = serializers.ChoiceField(choices=list(MOTIVOS_DE_BAIXA))
    descricao = serializers.CharField(required=False, allow_blank=True, default="")


class KmSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0)


class CorrigirKmSerializer(serializers.Serializer[Any]):
    km = serializers.IntegerField(min_value=0)
    motivo = serializers.CharField()


class PrecoEntradaSerializer(serializers.Serializer[Any]):
    diaria_centavos = serializers.IntegerField(min_value=0)
    semanal_centavos = serializers.IntegerField(min_value=0)
    mensal_centavos = serializers.IntegerField(min_value=0)
    caucao_centavos = serializers.IntegerField(min_value=0)


class NovoPrecoSerializer(PrecoEntradaSerializer):
    vigente_desde = serializers.DateField(required=False)


class CategoriaEntradaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60)
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    filial_id = serializers.IntegerField(required=False, allow_null=True)
    preco = PrecoEntradaSerializer()


class CategoriaEdicaoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60, required=False)
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices, required=False)
    filial_id = serializers.IntegerField(required=False, allow_null=True)


class ExtraEntradaSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField(max_length=60)
    valor_centavos = serializers.IntegerField(min_value=0)
    cobranca = serializers.ChoiceField(choices=Extra.Cobranca.choices)


# --- Respostas (OpenAPI) ---


class IdNomeSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()


class PrecoSerializer(serializers.Serializer[Any]):
    diaria_centavos = serializers.IntegerField()
    semanal_centavos = serializers.IntegerField()
    mensal_centavos = serializers.IntegerField()
    caucao_centavos = serializers.IntegerField()


class PrecoComDataSerializer(PrecoSerializer):
    vigente_desde = serializers.DateField()


class SituacaoDoVeiculoSerializer(serializers.Serializer[Any]):
    codigo = serializers.CharField()
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class AcoesDoVeiculoSerializer(serializers.Serializer[Any]):
    editar = serializers.BooleanField()
    colocar_a_venda = serializers.BooleanField()
    voltar_para_frota = serializers.BooleanField()
    bloquear = serializers.BooleanField()
    desbloquear = serializers.BooleanField()
    transferir = serializers.BooleanField()
    baixar = serializers.BooleanField()
    registrar_km = serializers.BooleanField()
    corrigir_km = serializers.BooleanField()
    movimentar = serializers.BooleanField()  # MOV-02, MOV-03
    motivo_movimentar = serializers.CharField(allow_null=True)
    aviso_baixar = serializers.CharField(allow_null=True)  # MOV-03 (T-311)
    lancar_despesa = serializers.BooleanField()  # FIN-17 (T-417)


class MovimentacaoAbertaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    codigo = serializers.CharField()
    status = serializers.ChoiceField(choices=["agendada", "em_transito", "no_local"])
    rotulo = serializers.CharField()
    tom = serializers.CharField()


class ReservaDoVeiculoSerializer(serializers.Serializer[Any]):
    """Quem reservou o veículo `reservado` (T-410): a locação ou a troca pendente."""

    locacao_id = serializers.IntegerField()
    codigo = serializers.CharField()
    motivo = serializers.ChoiceField(choices=["locacao", "troca"])


class VeiculoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    placa = serializers.CharField()
    chassi = serializers.CharField()
    renavam = serializers.CharField(allow_null=True)
    marca = serializers.CharField()
    modelo = serializers.CharField()
    ano_fabricacao = serializers.IntegerField()
    ano_modelo = serializers.IntegerField()
    cor = serializers.CharField()
    combustivel = serializers.ChoiceField(choices=Combustivel.choices, allow_null=True)
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    categoria = IdNomeSerializer()
    filial = IdNomeSerializer()
    status = serializers.ChoiceField(choices=StatusVeiculo.choices)
    motivo_status = serializers.CharField(allow_null=True)
    km_atual = serializers.IntegerField()
    km_atualizado_em = serializers.DateTimeField(allow_null=True)
    capacidade_tanque_litros = serializers.DecimalField(
        max_digits=5, decimal_places=1, allow_null=True
    )
    # Ausentes para o vistoriador, que não vê valores (D-25, USR-09).
    preco_vigente = PrecoSerializer(allow_null=True, required=False)
    valor_venda_centavos = serializers.IntegerField(allow_null=True, required=False)
    referencia_fipe_centavos = serializers.IntegerField(allow_null=True, required=False)
    valor_compra_centavos = serializers.IntegerField(allow_null=True, required=False)
    data_compra = serializers.DateField(allow_null=True, required=False)
    entrou_na_frota_em = serializers.DateField()
    situacao = SituacaoDoVeiculoSerializer()
    locacao_atual = serializers.JSONField(allow_null=True)
    reserva = ReservaDoVeiculoSerializer(allow_null=True)  # T-410
    manutencao = serializers.JSONField(allow_null=True)
    documentos_resumo = serializers.JSONField(allow_null=True)
    movimentacao_aberta = MovimentacaoAbertaSerializer(allow_null=True)  # MOV-03
    acoes = AcoesDoVeiculoSerializer()


class OcupacaoSerializer(serializers.Serializer[Any]):
    pct = serializers.CharField()
    periodo_dias = serializers.IntegerField()


class HistoricoStatusSerializer(serializers.Serializer[Any]):
    de = serializers.CharField(allow_null=True)
    para = serializers.CharField()
    em = serializers.DateTimeField()
    origem_tipo = serializers.CharField()
    origem_codigo = serializers.CharField(allow_null=True)
    motivo = serializers.CharField(allow_null=True)


class LinksDaFotoSerializer(serializers.Serializer[Any]):
    """VEI-10, ADR 0036, item 4: `url` abre e `url_download` baixa com `nome_arquivo`; os dois
    valem 15 minutos e são novos a cada leitura (AUD-05)."""

    id = serializers.IntegerField()
    numero = serializers.IntegerField()
    url = serializers.CharField()
    url_download = serializers.CharField()
    url_expira_em = serializers.DateTimeField()
    nome_arquivo = serializers.CharField()


class FotoDaVistoriaRecenteSerializer(LinksDaFotoSerializer):
    """Todas as fotos ativas da vistoria: as fixas e as de avaria (VEI-10, T-414)."""

    posicao = serializers.ChoiceField(
        choices=["frente", "traseira", "lado_esquerdo", "lado_direito", "painel", "avaria"]
    )
    rotulo = serializers.CharField()
    tirada_em = serializers.DateTimeField()
    avaria_id = serializers.IntegerField(allow_null=True)


class FotoDaGaleriaSerializer(LinksDaFotoSerializer):
    """A galeria não tem legenda: `rotulo` é sempre `null` (VEI-10)."""

    rotulo = serializers.CharField(allow_null=True)
    capa = serializers.BooleanField()
    enviada_em = serializers.DateTimeField()
    enviada_por = IdNomeSerializer(allow_null=True)


class GaleriaSerializer(serializers.Serializer[Any]):
    """Bloco `galeria` da ficha: as ativas, capa primeiro, para todos os perfis (VEI-10)."""

    total = serializers.IntegerField()
    limite = serializers.IntegerField()
    fotos = FotoDaGaleriaSerializer(many=True)


class GaleriaDoEditarSerializer(GaleriaSerializer):
    """`GET .../fotos/`. `motivo`: com o perfil que edita e o veículo vendido ou baixado, a
    mensagem do 409; `null` nos outros casos."""

    editar = serializers.BooleanField()
    motivo = serializers.CharField(allow_null=True)


class GaleriaAlteradaSerializer(GaleriaDoEditarSerializer):
    """Resposta do envio e da troca: a galeria inteira e o id da foto nova."""

    foto_id = serializers.IntegerField()


class FotoEntradaSerializer(serializers.Serializer[Any]):
    """Uma foto por requisição (ADR 0036, item 3). A recusa (formato, tamanho, falta) vem do
    serviço, com a mensagem da VEI-10."""

    arquivo = serializers.FileField(required=False, allow_null=True, allow_empty_file=True)


class AvariaDaVistoriaRecenteSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    descricao = serializers.CharField()
    registrada_em = serializers.DateTimeField()
    preexistente = serializers.BooleanField()
    locacao_codigo = serializers.CharField(allow_null=True)
    foto_id = serializers.IntegerField(allow_null=True)


class VistoriaRecenteSerializer(serializers.Serializer[Any]):
    """VIS-01, T-275: a última vistoria concluída, com todas as fotos (VEI-10) e as avarias
    abertas."""

    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=["saida", "devolucao"])
    rotulo_tipo = serializers.CharField()  # "Vistoria de saída", "Vistoria de chegada"
    concluida_em = serializers.DateTimeField()
    vistoriador = IdNomeSerializer(allow_null=True)
    locacao_codigo = serializers.CharField(allow_null=True)
    total_fotos = serializers.IntegerField()
    fotos = FotoDaVistoriaRecenteSerializer(many=True)
    avarias = AvariaDaVistoriaRecenteSerializer(many=True)


class DocumentoDoVeiculoSerializer(serializers.Serializer[Any]):
    """VEI-09 (T-421). `numero_motor` e `observacoes` só para administrador e gerente: para os
    outros perfis as chaves vêm ausentes, não `null` (CA-421-12, USR-09)."""

    potencia_cv = serializers.IntegerField(allow_null=True)
    cilindrada_cc = serializers.IntegerField(allow_null=True)
    especie = serializers.ChoiceField(choices=Especie.choices, allow_null=True)
    tipo = serializers.CharField(allow_null=True)
    carroceria = serializers.CharField(allow_null=True)
    lotacao = serializers.IntegerField(allow_null=True)
    peso_bruto_kg = serializers.IntegerField(allow_null=True)
    numero_motor = serializers.CharField(allow_null=True, required=False)
    observacoes = serializers.CharField(allow_null=True, required=False)

    def to_representation(self, instance: Any) -> Any:
        dados = super().to_representation(instance)
        for chave in ("numero_motor", "observacoes"):
            if chave not in instance:
                dados.pop(chave, None)
        return dados


class RastreadorSerializer(serializers.Serializer[Any]):
    numero = serializers.CharField(allow_null=True)
    empresa = serializers.CharField(allow_null=True)


class VeiculoComDadosDoDocumentoSerializer(VeiculoSerializer):
    """A ficha e as respostas do `POST` e do `PATCH` (VEI-09); a lista da Frota não os traz."""

    documento = DocumentoDoVeiculoSerializer()
    rastreador = RastreadorSerializer()
    anotacoes = serializers.CharField(allow_null=True)


class AcoesDaFichaSerializer(AcoesDoVeiculoSerializer):
    # Administrador e gerente, fora de vendido e baixado; nunca o suporte (VEI-10, PLT-07).
    editar_fotos = serializers.BooleanField()


class VeiculoDetalheSerializer(VeiculoComDadosDoDocumentoSerializer):
    acoes = AcoesDaFichaSerializer()
    galeria = GaleriaSerializer()  # VEI-10, para todos os perfis
    # Só para administrador, gerente e financeiro; ausente para os demais (USR-09, T-156).
    indicadores_financeiros = serializers.JSONField(allow_null=True, required=False)
    # Ausente para vistoriador e financeiro (T-275).
    movimentacoes = serializers.JSONField(allow_null=True, required=False)
    # Ausente para o financeiro; `null` se o veículo nunca teve vistoria (T-275).
    vistoria_recente = VistoriaRecenteSerializer(allow_null=True, required=False)
    ocupacao = OcupacaoSerializer()
    historico_status = HistoricoStatusSerializer(many=True)

    def to_representation(self, instance: Any) -> Any:
        dados = super().to_representation(instance)
        # O campo com allow_null viraria `null` quando a chave falta; aqui ela some.
        for chave in ("indicadores_financeiros", "movimentacoes", "vistoria_recente"):
            if chave not in instance:
                dados.pop(chave, None)
        return dados


class ContagensDaFrotaSerializer(serializers.Serializer[Any]):
    todos = serializers.IntegerField()
    disponivel = serializers.IntegerField()
    alugado = serializers.IntegerField()
    reservado = serializers.IntegerField()
    em_manutencao = serializers.IntegerField()
    a_venda = serializers.IntegerField()
    indisponivel = serializers.IntegerField()
    em_movimentacao = serializers.IntegerField()
    motos = serializers.IntegerField()
    carros = serializers.IntegerField()


class ListaDeVeiculosSerializer(serializers.Serializer[Any]):
    contagens = ContagensDaFrotaSerializer()
    resultados = VeiculoSerializer(many=True)
    proximo = serializers.CharField(allow_null=True)
    anterior = serializers.CharField(allow_null=True)


class CategoriaSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    tipo_veiculo = serializers.ChoiceField(choices=TipoVeiculo.choices)
    filial = IdNomeSerializer(allow_null=True)
    ativo = serializers.BooleanField()
    modelos_resumo = serializers.CharField()
    veiculos = serializers.IntegerField()
    # Ausentes para o vistoriador (D-25, USR-09).
    preco_vigente = PrecoComDataSerializer(allow_null=True, required=False)
    proximo_preco = PrecoComDataSerializer(allow_null=True, required=False)


class ListaDeCategoriasSerializer(serializers.Serializer[Any]):
    resultados = CategoriaSerializer(many=True)


class PrecoHistoricoSerializer(PrecoComDataSerializer):
    alterado_por = serializers.CharField(allow_null=True)
    alterado_em = serializers.DateTimeField()


class ListaDePrecosSerializer(serializers.Serializer[Any]):
    resultados = PrecoHistoricoSerializer(many=True)


class PrecoCriadoSerializer(PrecoHistoricoSerializer):
    locacoes_em_andamento_mantidas = serializers.IntegerField()


class MudancaDePrecoSerializer(serializers.Serializer[Any]):
    categoria = IdNomeSerializer()
    vigente_desde = serializers.DateField()
    campo = serializers.CharField()
    antes_centavos = serializers.IntegerField(allow_null=True)
    depois_centavos = serializers.IntegerField()
    alterado_por = serializers.CharField(allow_null=True)
    alterado_em = serializers.DateTimeField()


class ListaDeMudancasDePrecoSerializer(serializers.Serializer[Any]):
    resultados = MudancaDePrecoSerializer(many=True)


class ExtraSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    nome = serializers.CharField()
    valor_centavos = serializers.IntegerField()
    cobranca = serializers.ChoiceField(choices=Extra.Cobranca.choices)
    ativo = serializers.BooleanField()


class ListaDeExtrasSerializer(serializers.Serializer[Any]):
    resultados = ExtraSerializer(many=True)


class ListaDeModelosSerializer(serializers.Serializer[Any]):
    resultados = ModeloSerializer(many=True)

    class Meta:
        # Nome próprio no OpenAPI: `contratos` já tem um `ListaDeModelos` (T-265).
        ref_name = "ListaDeModelosDoCatalogo"


class FiltroDeModelosSerializer(serializers.Serializer[Any]):
    tipo = serializers.ChoiceField(choices=["moto", "carro"], required=False)
    marca = serializers.CharField(required=False, allow_blank=True, max_length=100)
    busca = serializers.CharField(required=False, allow_blank=True, max_length=100)


class PedidoRefSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    status = serializers.CharField()


class PedidoAprovacaoCriadoSerializer(serializers.Serializer[Any]):
    pedido_aprovacao = PedidoRefSerializer()


# --- Documentos (VEI-03, AUD-05) ---


class DocumentoEntradaSerializer(serializers.Serializer[Any]):
    """`multipart/form-data`. O arquivo é conferido pelo conteúdo no serviço (PDF, JPG ou PNG,
    até 10 MB)."""

    tipo = serializers.ChoiceField(choices=TipoDocumento.choices)
    validade = serializers.DateField()
    exercicio = serializers.IntegerField(
        required=False, allow_null=True, min_value=1900, max_value=2100
    )  # só no crlv: o ano do licenciamento (T-247)
    arquivo = serializers.FileField(required=False, allow_null=True)


class ArquivoAssinadoSerializer(serializers.Serializer[Any]):
    nome = serializers.CharField()
    url = serializers.CharField()
    url_expira_em = serializers.DateTimeField()


class DocumentoSerializer(serializers.Serializer[Any]):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoDocumento.choices)
    validade = serializers.DateField()
    situacao = serializers.ChoiceField(choices=["em_dia", "vence_em_breve", "vencido"])
    dias_para_vencer = serializers.IntegerField(allow_null=True)
    ativo = serializers.BooleanField()
    arquivo = ArquivoAssinadoSerializer(allow_null=True)


class ListaDeDocumentosSerializer(serializers.Serializer[Any]):
    resultados = DocumentoSerializer(many=True)
