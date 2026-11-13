"""Modelos prontos (passo 9 da implantação e "Novo modelo") e o texto padrão do aditivo.

Todos usam só marcadores da lista e já trazem a cláusula de multa e juros (`FIN-03`).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModeloPronto:
    chave: str
    nome: str
    texto: str
    finalidade: str = "locacao"


_PERIODO = {
    "diaria": ("diária", "por dia"),
    "semanal": ("semanal", "por semana"),
    "mensal": ("mensal", "por mês"),
}
_VEICULO = {"moto": ("moto", "a motocicleta"), "carro": ("carro", "o automóvel")}


def _texto(periodo: str, veiculo: str) -> str:
    nome_periodo, por = _PERIODO[periodo]
    _, artigo = _VEICULO[veiculo]
    return f"""<h1>Contrato de locação {nome_periodo}</h1>
<p><strong>Locadora:</strong> {{{{empresa.razao_social}}}}, CNPJ {{{{empresa.cnpj}}}}, \
{{{{empresa.endereco}}}}, {{{{empresa.cidade}}}}, pela {{{{filial.nome}}}}, \
{{{{filial.endereco}}}}, telefone {{{{filial.telefone}}}}.</p>
<p><strong>Locatário:</strong> {{{{cliente.nome}}}}, CPF ou CNPJ {{{{cliente.cpf}}}}, \
nascido em {{{{cliente.nascimento}}}}, residente em {{{{cliente.endereco}}}}, celular \
{{{{cliente.celular}}}}, e-mail {{{{cliente.email}}}}, CNH {{{{cliente.cnh_numero}}}}, \
categoria {{{{cliente.cnh_categoria}}}}, válida até {{{{cliente.cnh_validade}}}}.</p>
<h2>1. Objeto</h2>
<p>A locadora aluga ao locatário {artigo} {{{{veiculo.marca}}}} {{{{veiculo.modelo}}}}, \
ano {{{{veiculo.ano}}}}, cor {{{{veiculo.cor}}}}, placa {{{{veiculo.placa}}}}, chassi \
{{{{veiculo.chassi}}}}, Renavam {{{{veiculo.renavam}}}}, com {{{{veiculo.km_saida}}}} km na \
saída, conforme a vistoria de saída, que faz parte deste contrato.</p>
<h2>2. Prazo</h2>
<p>A locação {{{{locacao.codigo}}}} começa em {{{{locacao.inicio}}}} e a devolução está \
prevista para {{{{locacao.fim_previsto}}}}. Há uma tolerância de {{{{locacao.tolerancia_atraso}}}} \
na devolução. Depois dela, cada dia a mais custa {{{{locacao.diaria_atraso}}}}.</p>
<h2>3. Preço e pagamento</h2>
<p>O locatário paga {{{{locacao.valor}}}} {por}, no plano {{{{locacao.plano}}}}, por \
{{{{locacao.forma_pagamento}}}}. Extras: {{{{locacao.extras}}}}.</p>
{{{{locacao.parcelas}}}}
<p>A caução de {{{{locacao.caucao}}}} é paga na retirada e devolvida no acerto da devolução, \
descontado o que for devido.</p>
<h2>4. Atraso no pagamento</h2>
<p>A parcela paga depois do vencimento tem multa de {{{{cobranca.multa_atraso_pct}}}} e juros \
de {{{{cobranca.juros_mes_pct}}}} ao mês, calculados por dia de atraso.</p>
<h2>5. Uso do veículo</h2>
<p>O locatário usa o veículo com cuidado, só ele dirige e responde pelas multas de trânsito \
e pelos danos do período da locação.</p>
<p>{{{{contrato.cidade_assinatura}}}}, {{{{contrato.data}}}}.</p>
"""


PRONTOS: tuple[ModeloPronto, ...] = tuple(
    ModeloPronto(
        f"locacao_{periodo}_{veiculo}",
        f"Locação {_PERIODO[periodo][0]} de {_VEICULO[veiculo][0]}",
        _texto(periodo, veiculo),
    )
    for veiculo in _VEICULO
    for periodo in _PERIODO
)

# LOC-16 (T-420, ADR 0037): o modelo da locação com intenção de compra, um só para moto e carro.
# Traz o prazo, as parcelas, a caução e o abatimento, a transferência na quitação sem valor
# extra, a perda do que foi pago no encerramento antes do fim e os custos com a locadora.
TEXTO_COMPRA = """<h1>Contrato de locação com intenção de compra</h1>
<p><strong>Locadora:</strong> {{empresa.razao_social}}, CNPJ {{empresa.cnpj}}, \
{{empresa.endereco}}, {{empresa.cidade}}, pela {{filial.nome}}, {{filial.endereco}}, telefone \
{{filial.telefone}}.</p>
<p><strong>Locatário:</strong> {{cliente.nome}}, CPF ou CNPJ {{cliente.cpf}}, nascido em \
{{cliente.nascimento}}, residente em {{cliente.endereco}}, celular {{cliente.celular}}, e-mail \
{{cliente.email}}, CNH {{cliente.cnh_numero}}, categoria {{cliente.cnh_categoria}}, válida até \
{{cliente.cnh_validade}}.</p>
<h2>1. Objeto</h2>
<p>A locadora aluga ao locatário o veículo {{veiculo.marca}} {{veiculo.modelo}}, ano \
{{veiculo.ano}}, cor {{veiculo.cor}}, placa {{veiculo.placa}}, chassi {{veiculo.chassi}}, \
Renavam {{veiculo.renavam}}, com {{veiculo.km_saida}} km na saída, conforme a vistoria de saída, \
que faz parte deste contrato, no plano {{compra.plano}}.</p>
<h2>2. Prazo e parcelas</h2>
<p>A locação {{locacao.codigo}} começa em {{locacao.inicio}} e dura {{compra.prazo}}, até \
{{locacao.fim_previsto}}. O locatário paga {{compra.parcelas}} parcelas antecipadas de \
{{compra.valor_parcela}}, por {{locacao.forma_pagamento}}, nos vencimentos abaixo. O prazo é \
fixo: este contrato não se renova e o veículo não se troca.</p>
{{locacao.parcelas}}
<h2>3. Caução</h2>
<p>A caução de {{locacao.caucao}} é paga na retirada e abatida na última parcela, que fica em \
{{compra.ultima_parcela}}. Se a caução for maior que a parcela, a diferença volta ao locatário \
na quitação.</p>
<h2>4. Quitação e transferência</h2>
<p>Pagas todas as parcelas e sem outra conta da locação em aberto, a locação fica quitada e o \
veículo passa ao locatário, sem nenhum valor extra. A locadora faz a transferência no \
Detran.</p>
<h2>5. Encerramento antes do fim</h2>
<p>Se a locação for encerrada antes da quitação, a pedido do locatário ou pela locadora por \
atraso no pagamento, o que foi pago fica como aluguel do período usado, sem crédito, sem \
devolução de parcela e sem multa de encerramento. O veículo volta com a vistoria de devolução; \
as parcelas vencidas e não pagas entram no acerto, e a caução cobre o acerto. Se o veículo não \
voltar no dia do encerramento, cada dia a mais custa {{locacao.diaria_atraso}}.</p>
<h2>6. Atraso no pagamento</h2>
<p>A parcela paga depois do vencimento tem multa de {{cobranca.multa_atraso_pct}} e juros de \
{{cobranca.juros_mes_pct}} ao mês, calculados por dia de atraso.</p>
<h2>7. Custos durante o contrato</h2>
<p>Até a quitação, o veículo é da locadora, que paga o IPVA, o seguro, os documentos e a \
manutenção. O locatário usa o veículo com cuidado, só ele dirige e responde pelas multas de \
trânsito e pelos danos do período.</p>
<p>{{contrato.cidade_assinatura}}, {{contrato.data}}.</p>
"""
PRONTOS = (
    *PRONTOS,
    ModeloPronto(
        "locacao_compra", "Locação com intenção de compra", TEXTO_COMPRA, "locacao_compra"
    ),
)
POR_CHAVE = {pronto.chave: pronto for pronto in PRONTOS}

# LOC-08: o aditivo da renovação não tem modelo da locadora; usa este texto do sistema.
TEXTO_ADITIVO = """<h1>Aditivo de renovação</h1>
<p>Aditivo ao contrato da locação {{locacao.codigo}}, entre {{empresa.razao_social}}, CNPJ \
{{empresa.cnpj}}, e {{cliente.nome}}, CPF ou CNPJ {{cliente.cpf}}.</p>
<p>A locação do veículo {{veiculo.marca}} {{veiculo.modelo}}, placa {{veiculo.placa}}, fica \
renovada. A devolução passa a ser prevista para {{locacao.fim_previsto}}, com {{locacao.valor}} \
por período.</p>
{{locacao.parcelas}}
<p>As demais cláusulas do contrato continuam valendo.</p>
<p>{{contrato.cidade_assinatura}}, {{contrato.data}}.</p>
"""
