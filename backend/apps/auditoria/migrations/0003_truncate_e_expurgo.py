"""Imutabilidade sem variável de sessão (ADR 0016, S-10, C-05 da T-039).

- O trigger de linha recusa UPDATE sempre e DELETE, exceto do papel `giro_expurgo` em evento
  com mais de 5 anos. A variável `giro.expurgo_auditoria` deixa de existir.
- Trigger de comando recusa TRUNCATE.
- `auditoria_expurgar(limite date)` é SECURITY DEFINER, com search_path fixo no schema, e
  recusa limite mais recente que 5 anos (AUD-02). O dono e os GRANT são aplicados por
  `apps.auditoria.banco.aplicar_permissoes` no post_migrate.
"""

from django.db import migrations

CRIAR = r"""
DROP FUNCTION IF EXISTS auditoria_expurgar_vencidos();

CREATE OR REPLACE FUNCTION auditoria_evento_imutavel() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_user = 'giro_expurgo'
       AND OLD.ocorrido_em < now() - interval '5 years' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'Evento de auditoria é imutável (AUD-01): % recusado', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION auditoria_evento_sem_truncate() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Evento de auditoria é imutável (AUD-01): TRUNCATE recusado'
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auditoria_evento_sem_truncate
    BEFORE TRUNCATE ON auditoria_eventoauditoria
    FOR EACH STATEMENT EXECUTE FUNCTION auditoria_evento_sem_truncate();

DO $do$
BEGIN
    EXECUTE format($f$
        CREATE OR REPLACE FUNCTION auditoria_expurgar(limite date) RETURNS integer
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = %I, pg_temp AS $$
        DECLARE
            apagados integer;
        BEGIN
            IF limite IS NULL OR limite > (now() - interval '5 years')::date THEN
                RAISE EXCEPTION 'Expurgo só de eventos com mais de 5 anos (AUD-02)'
                    USING ERRCODE = 'insufficient_privilege';
            END IF;
            DELETE FROM auditoria_eventoauditoria WHERE ocorrido_em < limite;
            GET DIAGNOSTICS apagados = ROW_COUNT;
            RETURN apagados;
        END;
        $$
    $f$, current_schema());
END;
$do$;
"""

DESFAZER = r"""
DROP FUNCTION IF EXISTS auditoria_expurgar(date);
DROP TRIGGER IF EXISTS auditoria_evento_sem_truncate ON auditoria_eventoauditoria;
DROP FUNCTION IF EXISTS auditoria_evento_sem_truncate();
"""


class Migration(migrations.Migration):
    dependencies = [("auditoria", "0002_trigger_imutavel")]

    operations = [migrations.RunSQL(CRIAR, DESFAZER)]
