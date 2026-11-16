"""Permissões dos papéis de banco em cada schema (ADR 0016, S-10).

`giro_app` atende requisições e roda o Celery: lê e grava nas tabelas de negócio, mas na
auditoria só `SELECT` e `INSERT`. `giro_expurgo` é dono da função `auditoria_expurgar`, a única
que apaga evento (com mais de 5 anos). Os papéis são criados pelo devops
(`infra/postgres/01-papeis.sh`); papel que não existe é ignorado, então em dev com um papel só
nada muda.

Roda depois de toda migração do schema (`post_migrate`), como o papel da migração
(`giro_migracao`, dono do schema, sem superusuário), e pode rodar de novo sem efeito. É o único
lugar das concessões por schema (ADR 0040, item 2): também roda na criação do schema, antes e
depois das migrações (`plataforma.banco.criar_schema`), e pelo `conceder_privilegios`.
"""

from django.db.backends.utils import CursorWrapper

PAPEL_APP = "giro_app"
PAPEL_EXPURGO = "giro_expurgo"
PAPEL_MIGRACAO = "giro_migracao"
TABELA = "auditoria_eventoauditoria"


def _papel_existe(cursor: CursorWrapper, papel: str) -> bool:
    cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [papel])
    return cursor.fetchone() is not None


def _sem_aspas(nome: str) -> str:
    """Schema e papel vêm do banco, mas entram no SQL: só aceita identificador simples."""
    if not nome.replace("_", "").isalnum() or not nome.isascii():
        raise ValueError(f"Identificador inesperado: {nome!r}")
    return f'"{nome}"'


def _conceder_ao_app(cursor: CursorWrapper, s: str, tem_migracao: bool) -> None:
    cursor.execute(f"GRANT USAGE ON SCHEMA {s} TO {PAPEL_APP}")
    cursor.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {s} TO {PAPEL_APP}"
    )
    cursor.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {s} TO {PAPEL_APP}")
    # `FOR ROLE` explícito (ADR 0040, item 2): a regra vale para o que o giro_migracao criar,
    # qualquer que seja o papel que rode isto. Sem o papel (desenvolvimento com um papel só), vale
    # para quem roda, que é quem cria as tabelas.
    para = f"FOR ROLE {PAPEL_MIGRACAO} " if tem_migracao else ""
    cursor.execute(
        f"ALTER DEFAULT PRIVILEGES {para}IN SCHEMA {s} "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {PAPEL_APP}"
    )
    cursor.execute(
        f"ALTER DEFAULT PRIVILEGES {para}IN SCHEMA {s} "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {PAPEL_APP}"
    )


def aplicar_permissoes(cursor: CursorWrapper, schema: str) -> None:
    s = _sem_aspas(schema)
    tem_app = _papel_existe(cursor, PAPEL_APP)
    tem_migracao = _papel_existe(cursor, PAPEL_MIGRACAO)
    funcao = f"{s}.auditoria_expurgar(date)"
    cursor.execute("SELECT to_regprocedure(%s)", [funcao])
    linha = cursor.fetchone()
    tem_funcao = linha is not None and linha[0] is not None

    # Antes das migrações (schema recém-criado, sem tabelas): só o USAGE e as regras padrão, para
    # que cada tabela que a migração criar já nasça com o DML do giro_app.
    if tem_app:
        _conceder_ao_app(cursor, s, tem_migracao)
    if not tem_funcao:
        return  # migração da auditoria ainda não chegou à 0003 neste schema
    tem_expurgo = _papel_existe(cursor, PAPEL_EXPURGO)

    cursor.execute(f"REVOKE EXECUTE ON FUNCTION {funcao} FROM PUBLIC")
    if tem_expurgo:
        cursor.execute(f"GRANT USAGE ON SCHEMA {s} TO {PAPEL_EXPURGO}")
        cursor.execute(f"GRANT SELECT, DELETE ON {s}.{TABELA} TO {PAPEL_EXPURGO}")
        # O PostgreSQL só troca o dono se o dono novo tiver CREATE no schema. A migração roda
        # como giro_migracao, dona do schema e sem superusuário: o CREATE vale só para a troca
        # e sai em seguida, na mesma transação (T-276). O expurgo nunca cria nada no schema.
        cursor.execute(f"GRANT CREATE ON SCHEMA {s} TO {PAPEL_EXPURGO}")
        cursor.execute(f"ALTER FUNCTION {funcao} OWNER TO {PAPEL_EXPURGO}")
        cursor.execute(f"REVOKE CREATE ON SCHEMA {s} FROM {PAPEL_EXPURGO}")

    if tem_app:
        cursor.execute(f"GRANT EXECUTE ON FUNCTION {funcao} TO {PAPEL_APP}")
        # Sempre por último: na auditoria, só SELECT e INSERT, mesmo que uma migração tenha
        # recriado a tabela e o GRANT geral acima a tenha alcançado.
        cursor.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON {s}.{TABELA} FROM {PAPEL_APP}")
