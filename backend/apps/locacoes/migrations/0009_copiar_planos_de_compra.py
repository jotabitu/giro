"""Copia o plano de compra da categoria para cada veículo dela (ADR 0041, item 3, passo 4).

Para cada categoria com `PlanoCompra` ativo, o mais recente vai para o `PlanoCompraVeiculo` de cada
veículo dela que ainda não tem um: desligado, `modo = digitar`, `parcela_moto_centavos` = o valor
da parcela do plano antigo, a periodicidade e as parcelas dele, entrada 0, adicional 0 e a caução
vigente hoje na categoria (padrão A); o histórico com `origem = migracao`, um lote por veículo. Os
outros planos ativos da categoria não cabem (um por veículo) e são listados.

Escreve num model de `veiculos` de dentro de uma migration de `locacoes`: a única exceção ao "só por
serviço", porque migration não chama serviço, e a dependência vai no sentido permitido (ADR 0011).
Idempotente: a chave é "o veículo já tem plano de compra". A reversa não faz nada (nada de negócio
se apaga). Na empresa nova (schema vazio), não há plano nem veículo e nada é copiado.
"""

import sys
import uuid
from zoneinfo import ZoneInfo

from django.db import migrations
from django.utils import timezone

CAMPOS_DO_HISTORICO = (
    "ligado",
    "periodicidade",
    "parcelas",
    "modo",
    "parcela_moto_centavos",
    "caucao_centavos",
)


def copiar(apps, schema_editor):  # type: ignore[no-untyped-def]
    plano_antigo_model = apps.get_model("locacoes", "PlanoCompra")
    veiculo_model = apps.get_model("veiculos", "Veiculo")
    preco_model = apps.get_model("veiculos", "PrecoCategoria")
    compra_model = apps.get_model("veiculos", "PlanoCompraVeiculo")
    historico_model = apps.get_model("veiculos", "HistoricoPrecoVeiculo")
    # A conexão da migração, não a `default` (ADR 0040; a mesma lição da `veiculos` 0010).
    db = schema_editor.connection.alias if schema_editor is not None else "default"

    agora = timezone.now()
    hoje = timezone.localdate(agora, ZoneInfo("America/Sao_Paulo"))
    por_categoria: dict[int, list[object]] = {}
    for plano in (
        plano_antigo_model.objects.using(db).filter(ativo=True).order_by("-criado_em", "-pk")
    ):
        por_categoria.setdefault(plano.categoria_id, []).append(plano)

    nao_couberam: list[str] = []
    for categoria_id, planos in por_categoria.items():
        escolhido = planos[0]
        nao_couberam.extend(
            f"categoria {categoria_id}: plano de compra {p.pk} ({p.nome}) não migrado"
            for p in planos[1:]
        )
        vigente = (
            preco_model.objects.using(db)
            .filter(categoria_id=categoria_id, vigente_desde__lte=hoje)
            .order_by("-vigente_desde")
            .first()
        )
        caucao = int(vigente.caucao_centavos) if vigente is not None else 0
        sem_compra = (
            veiculo_model.objects.using(db)
            .filter(categoria_id=categoria_id)
            .exclude(pk__in=compra_model.objects.using(db).values("veiculo_id"))
            .order_by("pk")
        )
        for veiculo in sem_compra.iterator():
            compra = compra_model.objects.using(db).create(
                veiculo_id=veiculo.pk,
                ligado=False,
                periodicidade=escolhido.periodicidade,
                parcelas=escolhido.parcelas,
                entrada_centavos=0,
                modo="digitar",
                parcela_moto_centavos=escolhido.valor_parcela_centavos,
                adicional_centavos=0,
                caucao_centavos=caucao,
            )
            lote = uuid.uuid4()
            historico_model.objects.using(db).bulk_create(
                historico_model(
                    veiculo_id=veiculo.pk,
                    em=agora,
                    por=None,
                    origem="migracao",
                    alvo="plano_compra",
                    alvo_id=compra.pk,
                    alvo_nome="Locação com compra",
                    campo=campo,
                    de=None,
                    para=getattr(compra, campo),
                    lote=lote,
                )
                for campo in CAMPOS_DO_HISTORICO
            )

    for linha in nao_couberam:  # um plano de compra por veículo (VEI-16)
        sys.stdout.write(f"\n  [locacoes 0009] {linha}")


class Migration(migrations.Migration):
    dependencies = [
        ("locacoes", "0008_locacao_com_intencao_de_compra"),
        ("veiculos", "0010_copiar_precos_da_categoria"),
    ]

    operations = [migrations.RunPython(copiar, migrations.RunPython.noop)]
