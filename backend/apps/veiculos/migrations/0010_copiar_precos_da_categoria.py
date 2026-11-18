"""Copia o preço da categoria para os planos de cada veículo (ADR 0041, item 3, passo 3).

Para cada veículo sem `RegrasVeiculo`: planos `diaria`, `semanal` e `mensal` com o preço vigente
hoje (`America/Sao_Paulo`) na categoria, a caução da categoria, à vista, o "como paga" padrão do
período, as quatro formas, franquia livre, sem prazo mínimo e ligados com valor maior que zero; o
primeiro preço futuro da categoria vira o agendado de cada plano (um segundo não cabe e é listado);
regras com o dia de atraso e a multa mínima iguais à diária, 5% sem aprovação; custos vazios; o
histórico com `origem = migracao`, um lote por veículo. Idempotente: a chave é "o veículo já tem
regras", e o `get_or_create` por `(veiculo, tipo)` protege uma rodada interrompida. A reversa não
faz nada (nada de negócio se apaga).
"""

import sys
import uuid
from zoneinfo import ZoneInfo

from django.db import migrations
from django.utils import timezone

FORMAS = ["pix", "boleto", "cartao", "dinheiro"]
PLANOS = (
    ("diaria", "dia", "tudo_na_retirada", "diaria_centavos", "Diária"),
    ("semanal", "semana", "semana_adiantado", "semanal_centavos", "Semanal"),
    ("mensal", "mes", "mes_uma_parcela", "mensal_centavos", "Mensal"),
)


def copiar(apps, schema_editor):  # type: ignore[no-untyped-def]
    veiculo_model = apps.get_model("veiculos", "Veiculo")
    preco_model = apps.get_model("veiculos", "PrecoCategoria")
    plano_model = apps.get_model("veiculos", "PlanoVeiculo")
    regras_model = apps.get_model("veiculos", "RegrasVeiculo")
    custos_model = apps.get_model("veiculos", "CustosVeiculo")
    historico_model = apps.get_model("veiculos", "HistoricoPrecoVeiculo")

    agora = timezone.now()
    hoje = timezone.localdate(agora, ZoneInfo("America/Sao_Paulo"))
    por_categoria: dict[int, tuple[object, object]] = {}
    nao_couberam: list[str] = []

    def precos_da(categoria_id: int) -> tuple[object, object]:
        if categoria_id not in por_categoria:
            precos = preco_model.objects.filter(categoria_id=categoria_id)
            vigente = precos.filter(vigente_desde__lte=hoje).order_by("-vigente_desde").first()
            futuros = list(precos.filter(vigente_desde__gt=hoje).order_by("vigente_desde")[:2])
            if len(futuros) > 1:
                nao_couberam.append(
                    f"categoria {categoria_id}: preço de {futuros[1].vigente_desde} não migrado"
                )
            por_categoria[categoria_id] = (vigente, futuros[0] if futuros else None)
        return por_categoria[categoria_id]

    sem_regras = veiculo_model.objects.exclude(
        pk__in=regras_model.objects.values("veiculo_id")
    ).order_by("pk")
    for veiculo in sem_regras.iterator():
        vigente, futuro = precos_da(veiculo.categoria_id)
        caucao = vigente.caucao_centavos if vigente is not None else None
        lote = uuid.uuid4()
        linhas = []

        def mudou(  # type: ignore[no-untyped-def]
            alvo,
            campo,
            para,
            alvo_id=None,
            alvo_nome="",
            lote=lote,
            linhas=linhas,
            veiculo_id=veiculo.pk,
        ):
            linhas.append(
                historico_model(
                    veiculo_id=veiculo_id,
                    em=agora,
                    por=None,
                    origem="migracao",
                    alvo=alvo,
                    alvo_id=alvo_id,
                    alvo_nome=alvo_nome,
                    campo=campo,
                    de=None,
                    para=para,
                    lote=lote,
                )
            )

        for tipo, periodo, como_paga, campo, rotulo in PLANOS:
            valor = getattr(vigente, campo) if vigente is not None else 0
            plano, criado = plano_model.objects.get_or_create(
                veiculo_id=veiculo.pk,
                tipo=tipo,
                ativo=True,
                defaults={
                    "periodo": periodo,
                    "como_paga": como_paga,
                    "formas_aceitas": list(FORMAS),
                    "valor_centavos": valor,
                    "caucao_centavos": caucao,
                    "caucao_parcelas": 1,
                    "ligado": valor > 0 and caucao is not None,
                    "valor_agendado_centavos": getattr(futuro, campo) if futuro else None,
                    "caucao_agendada_centavos": futuro.caucao_centavos if futuro else None,
                    "agendado_para": futuro.vigente_desde if futuro else None,
                },
            )
            if criado:
                mudou("plano", "valor_centavos", valor, plano.pk, rotulo)
                mudou("plano", "caucao_centavos", caucao, plano.pk, rotulo)
                mudou("plano", "ligado", plano.ligado, plano.pk, rotulo)
                if futuro is not None:
                    mudou(
                        "plano", "valor_agendado_centavos", getattr(futuro, campo), plano.pk, rotulo
                    )
                    mudou(
                        "plano", "agendado_para", futuro.vigente_desde.isoformat(), plano.pk, rotulo
                    )
        diaria = vigente.diaria_centavos if vigente is not None else 0
        custos_model.objects.get_or_create(veiculo_id=veiculo.pk)
        regras_model.objects.create(
            veiculo_id=veiculo.pk, dia_atraso_centavos=diaria, multa_minima_centavos=diaria
        )
        mudou("regras", "dia_atraso_centavos", diaria)
        mudou("regras", "multa_minima_centavos", diaria)
        mudou("regras", "desconto_sem_aprovacao_pct", "5.00")
        historico_model.objects.bulk_create(linhas)

    for linha in nao_couberam:  # ADR 0041, risco 2: um agendado por plano
        sys.stdout.write(f"\n  [veiculos 0010] {linha}")


class Migration(migrations.Migration):
    dependencies = [
        ("veiculos", "0009_precos_por_veiculo"),
        ("empresas", "0006_margem_minima"),
    ]

    operations = [migrations.RunPython(copiar, migrations.RunPython.noop)]
