"""Aplicação do schema e seeds iniciais."""
from __future__ import annotations

from pathlib import Path

from .connection import get_connection

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
_SEEDS_DIR = _PROJECT_ROOT / "seeds"


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def apply_schema() -> None:
    """Cria todas as tabelas/índices/views se ainda não existirem."""
    conn = get_connection()
    conn.executescript(_read_sql(_SCHEMA_PATH))


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
    apply_seeds()
