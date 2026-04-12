"""Aplicação do schema e seeds iniciais."""
from __future__ import annotations

from pathlib import Path

from .connection import get_connection
from ..paths import get_bundle_dir

_BUNDLE_DIR = get_bundle_dir()
_SCHEMA_PATH = _BUNDLE_DIR / "src" / "db" / "schema.sql"
_SEEDS_DIR = _BUNDLE_DIR / "seeds"


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def apply_schema() -> None:
    """Cria todas as tabelas/índices/views se ainda não existirem."""
    conn = get_connection()
    conn.executescript(_read_sql(_SCHEMA_PATH))


def _table_requires_decimal_migration(table: str, monitored_columns: list[str]) -> bool:
    conn = get_connection()
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
        if row[1] in monitored_columns and row[2].upper() == "REAL":
            return True
    return False


def _migrate_table_to_text(table: str, create_sql: str) -> None:
    conn = get_connection()
    temp = f"_migration_{table}"
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(f"ALTER TABLE {table} RENAME TO {temp}")
    conn.executescript(create_sql)
    conn.executescript(f"INSERT INTO {table} SELECT * FROM {temp}; DROP TABLE {temp};")
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_decimal_columns() -> None:
    migrations = [
        (
            "custos_fixos",
            ["valor_mensal"],
            """
            CREATE TABLE custos_fixos (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              nome          TEXT NOT NULL,
              valor_mensal  TEXT NOT NULL,
              ativo         INTEGER NOT NULL DEFAULT 1
            );
            """,
        ),
        (
            "cbhpo_referencia",
            ["valor_oficial"],
            """
            CREATE TABLE cbhpo_referencia (
              codigo_cbhpo  TEXT PRIMARY KEY,
              nome_oficial  TEXT NOT NULL,
              categoria     TEXT,
              valor_oficial TEXT NOT NULL,
              versao        TEXT NOT NULL,
              fonte         TEXT,
              atualizado_em TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_cbhpo_versao ON cbhpo_referencia(versao);
            """,
        ),
        (
            "procedimentos",
            ["valor_atual", "valor_hora_clinica_override", "custo_material", "custo_laboratorio", "fator_complexidade_min", "fator_complexidade_max"],
            """
            CREATE TABLE procedimentos (
              id                          INTEGER PRIMARY KEY AUTOINCREMENT,
              nome                        TEXT NOT NULL,
              categoria                   TEXT NOT NULL,
              codigo_cbhpo                TEXT,
              valor_atual                 TEXT NOT NULL,
              tempo_estimado_min          INTEGER NOT NULL,
              valor_hora_clinica_override TEXT,
              custo_material              TEXT NOT NULL DEFAULT 0,
              custo_laboratorio           TEXT NOT NULL DEFAULT 0,
              fator_complexidade_min      TEXT NOT NULL DEFAULT 1.0,
              fator_complexidade_max      TEXT NOT NULL DEFAULT 1.0,
              ativo                       INTEGER NOT NULL DEFAULT 1,
              FOREIGN KEY (codigo_cbhpo) REFERENCES cbhpo_referencia(codigo_cbhpo)
            );
            CREATE INDEX IF NOT EXISTS idx_proc_categoria ON procedimentos(categoria);
            CREATE INDEX IF NOT EXISTS idx_proc_codigo ON procedimentos(codigo_cbhpo);
            """,
        ),
        (
            "historico",
            ["aliquota_aplicada", "total_a_vista", "total_cartao_7x", "total_cartao_10x", "total_cartao_12x"],
            """
            CREATE TABLE historico (
              id                  INTEGER PRIMARY KEY AUTOINCREMENT,
              data_hora           TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
              cliente_nome        TEXT NOT NULL,
              cliente_observacao  TEXT,
              distancia_km        REAL NOT NULL,
              is_nee              INTEGER NOT NULL DEFAULT 0,
              regime_aplicado     TEXT NOT NULL,
              aliquota_aplicada   TEXT NOT NULL,
              total_a_vista       TEXT NOT NULL,
              total_cartao_7x     TEXT NOT NULL,
              total_cartao_10x    TEXT NOT NULL,
              total_cartao_12x    TEXT NOT NULL,
              pdf_gerado          INTEGER NOT NULL DEFAULT 0,
              payload_json        TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_historico_data ON historico(data_hora DESC);
            CREATE INDEX IF NOT EXISTS idx_historico_cliente ON historico(cliente_nome);
            """,
        ),
    ]
    for table, cols, create_sql in migrations:
        if _table_requires_decimal_migration(table, cols):
            _migrate_table_to_text(table, create_sql)


def apply_seeds() -> None:
    """Popula tabelas vazias com dados iniciais (idempotente)."""
    conn = get_connection()

    # Config: INSERT OR IGNORE (não sobrescreve mudanças)
    conn.executescript(_read_sql(_SEEDS_DIR / "config_default.sql"))

    # CBHPO referência: UPSERT (atualizado quando seed mudar)
    if _table_empty("cbhpo_referencia"):
        conn.executescript(_read_sql(_SEEDS_DIR / "cbhpo_2024.sql"))

    # Procedimentos: INSERT OR IGNORE (só popula se vazio)
    if _table_empty("procedimentos"):
        conn.executescript(_read_sql(_SEEDS_DIR / "procedimentos_basis.sql"))


def update_cbhpo_reference(versao: str = "2024") -> None:
    """Reaplica o seed da CBHPO via UPSERT. Não toca em procedimentos.valor_atual."""
    conn = get_connection()
    seed_file = _SEEDS_DIR / f"cbhpo_{versao}.sql"
    if not seed_file.exists():
        raise FileNotFoundError(f"Seed CBHPO não encontrado: {seed_file}")
    conn.executescript(_read_sql(seed_file))


def _table_empty(nome: str) -> bool:
    conn = get_connection()
    row = conn.execute(f"SELECT COUNT(*) AS n FROM {nome}").fetchone()
    return (row["n"] if row else 0) == 0


def initialize() -> None:
    """Ponto único de entrada: garante schema + seeds aplicados."""
    apply_schema()
    _migrate_decimal_columns()
    apply_seeds()
