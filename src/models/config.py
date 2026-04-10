"""Acesso tipado à tabela config (chave/valor)."""
from __future__ import annotations
import json
from typing import Any
from ..db.connection import get_connection

class ConfigStore:
    def __init__(self):
        self._cache: dict[str, Any] = {}
        self._loaded = False

    def _load(self) -> None:
        if self._loaded:
            return
        conn = get_connection()
        rows = conn.execute("SELECT chave, valor, tipo, descricao FROM config").fetchall()
        for row in rows:
            self._cache[row["chave"]] = {
                "value": self._coerce(row["valor"], row["tipo"]),
                "tipo": row["tipo"],
                "descricao": row["descricao"] or "Sem descrição",
            }
        self._loaded = True

    @staticmethod
    def _coerce(valor: str, tipo: str) -> Any:
        if tipo == "float":
            return float(valor)
        if tipo == "int":
            return int(valor)
        if tipo == "bool":
            return valor.lower() in ("1", "true", "yes")
        if tipo == "json":
            return json.loads(valor)
        return valor

    def get(self, chave: str, default: Any = None) -> Any:
        self._load()
        data = self._cache.get(chave)
        return data["value"] if data else default

    def get_info(self, chave: str) -> dict | None:
        """Retorna value + descrição (para tooltip)"""
        self._load()
        return self._cache.get(chave)

    def set(self, chave: str, valor: Any) -> None:
        conn = get_connection()
        row = conn.execute("SELECT tipo FROM config WHERE chave = ?", (chave,)).fetchone()
        if row is None:
            raise KeyError(f"Chave de config inexistente: {chave}")

        tipo = row["tipo"]
        valor_str = json.dumps(valor) if tipo == "json" else str(valor)

        conn.execute(
            "UPDATE config SET valor = ?, atualizado_em = datetime('now', 'localtime') WHERE chave = ?",
            (valor_str, chave),
        )
        self._cache.clear()  # força reload
        self._loaded = False

    def reload(self) -> None:
        self._cache.clear()
        self._loaded = False
        self._load()

    def all_grouped(self) -> dict[str, dict]:
        """Usado na tela de configurações"""
        self._load()
        conn = get_connection()
        rows = conn.execute(
            "SELECT chave, valor, tipo, grupo, descricao FROM config ORDER BY grupo, chave"
        ).fetchall()
        result: dict[str, dict] = {}
        for row in rows:
            grupo = row["grupo"]
            result.setdefault(grupo, {})[row["chave"]] = {
                "value": self._coerce(row["valor"], row["tipo"]),
                "tipo": row["tipo"],
                "descricao": row["descricao"] or "Sem descrição",
            }
        return result
