"""
pg-local — MCP de SOLO LECTURA sobre el PostgreSQL local de William.

Autodescubre TODAS las bases del instance (incluidas las que crees después):
no hay que listarlas a mano. Cada tool abre la conexión a la base que le indiques
(PostgreSQL ata cada conexión a una sola base). Auth trust local (usuario del SO).

Se lanza vía:
  uv run --with mcp --with 'psycopg[binary]' ~/.claude/mcp/pg-local.py
"""
import json
import psycopg
from mcp.server.fastmcp import FastMCP

HOST = "localhost"
PORT = 5432
MAX_ROWS = 200

mcp = FastMCP("pg-local")


def _conn(dbname: str):
    # default_transaction_read_only=on => cualquier INSERT/UPDATE/DELETE/DDL falla.
    return psycopg.connect(
        host=HOST, port=PORT, dbname=dbname, autocommit=True,
        connect_timeout=8, options="-c default_transaction_read_only=on",
    )


def _cell(v):
    return v if isinstance(v, (str, int, float, bool, type(None))) else str(v)


@mcp.tool()
def list_databases() -> list[str]:
    """Lista TODAS las bases del PostgreSQL local (autodescubre; incluye nuevas). No hay que configurarlas."""
    with _conn("postgres") as c, c.cursor() as cur:
        cur.execute("SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY 1")
        return [r[0] for r in cur.fetchall()]


@mcp.tool()
def list_tables(database: str, schema: str = "public") -> list[str]:
    """Lista las tablas de un schema (default 'public') de la base indicada."""
    with _conn(database) as c, c.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = %s ORDER BY 1",
            (schema,),
        )
        return [r[0] for r in cur.fetchall()]


@mcp.tool()
def describe_table(database: str, table: str, schema: str = "public") -> str:
    """Devuelve columnas (nombre, tipo, nullable) de una tabla, en JSON."""
    with _conn(database) as c, c.cursor() as cur:
        cur.execute(
            "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (schema, table),
        )
        cols = [{"column": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
        return json.dumps({"database": database, "table": f"{schema}.{table}", "columns": cols},
                          ensure_ascii=False)


@mcp.tool()
def query(database: str, sql: str) -> str:
    """Ejecuta SQL de SOLO LECTURA contra 'database' (cualquiera de list_databases()).
    Devuelve JSON con columns y rows (máx 200 filas). Las escrituras fallan por diseño."""
    with _conn(database) as c, c.cursor() as cur:
        cur.execute(sql)
        if cur.description is None:
            return json.dumps({"database": database, "note": "consulta sin resultset"})
        cols = [d.name for d in cur.description]
        rows = [[_cell(v) for v in row] for row in cur.fetchmany(MAX_ROWS)]
        truncated = cur.fetchone() is not None
        return json.dumps(
            {"database": database, "columns": cols, "rows": rows,
             "shown": len(rows), "truncated": truncated},
            ensure_ascii=False, default=str,
        )


if __name__ == "__main__":
    mcp.run()
