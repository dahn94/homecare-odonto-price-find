"""Conexão singleton ao basis.db."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ..paths import get_data_dir

_DB_PATH = get_data_dir() / "basis.db"
_conn: sqlite3.Connection | None = None


def get_db_path() -> Path:
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    """Retorna a conexão singleton, criando o arquivo se necessário."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_DB_PATH, isolation_level=None)  # autocommit
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
    return _conn


def close_connection() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
