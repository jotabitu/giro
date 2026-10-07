"""Trigger que recusa UPDATE e DELETE em eventos de auditoria (AUD-01, ADR 0010, item 3).

A função e o trigger são criados em cada schema (o primeiro do search_path). A única exceção é
o expurgo de eventos com mais de 5 anos (AUD-02), pela função auditoria_expurgar_vencidos(),
que liga giro.expurgo_auditoria só dentro da própria transação.
"""

from django.db import migrations

CRIAR = r"""
CREATE OR REPLACE FUNCTION auditoria_evento_imutavel() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('giro.expurgo_auditoria', true) = 'on'
       AND OLD.ocorrido_em < now() - interval '5 years' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION 'Evento de auditoria é imutável (AUD-01): % recusado', TG_OP
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auditoria_evento_imutavel
    BEFORE UPDATE OR DELETE ON auditoria_eventoauditoria
    FOR EACH ROW EXECUTE FUNCTION auditoria_evento_imutavel();

CREATE OR REPLACE FUNCTION auditoria_expurgar_vencidos() RETURNS integer AS $$
DECLARE
    apagados integer;
BEGIN
    PERFORM set_config('giro.expurgo_auditoria', 'on', true);
    DELETE FROM auditoria_eventoauditoria WHERE ocorrido_em < now() - interval '5 years';
    GET DIAGNOSTICS apagados = ROW_COUNT;
    PERFORM set_config('giro.expurgo_auditoria', 'off', true);
    RETURN apagados;
END;
$$ LANGUAGE plpgsql;
"""

DESFAZER = r"""
DROP TRIGGER IF EXISTS auditoria_evento_imutavel ON auditoria_eventoauditoria;
DROP FUNCTION IF EXISTS auditoria_evento_imutavel();
DROP FUNCTION IF EXISTS auditoria_expurgar_vencidos();
"""


class Migration(migrations.Migration):
    dependencies = [("auditoria", "0001_initial")]

    operations = [migrations.RunSQL(CRIAR, DESFAZER)]
