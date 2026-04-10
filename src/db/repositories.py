"""Repositórios CRUD pros principais agregados."""
from __future__ import annotations

import json
from typing import Any

from ..models.procedimento import Procedimento
from .connection import get_connection


# ───────────────────────── Procedimentos ──────────────────────────
class ProcedimentoRepo:
    @staticmethod
    def listar(ativos: bool = True) -> list[Procedimento]:
        conn = get_connection()
        sql = "SELECT * FROM v_procedimentos_com_delta"
        if ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY categoria, nome"
        rows = conn.execute(sql).fetchall()
        return [Procedimento.from_row(r) for r in rows]

    @staticmethod
    def por_id(id_: int) -> Procedimento | None:
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM v_procedimentos_com_delta WHERE id = ?", (id_,)
        ).fetchone()
        return Procedimento.from_row(row) if row else None

    @staticmethod
    def por_ids(ids: list[int]) -> dict[int, Procedimento]:
        if not ids:
            return {}
        conn = get_connection()
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM v_procedimentos_com_delta WHERE id IN ({placeholders})", ids
        ).fetchall()
        return {r["id"]: Procedimento.from_row(r) for r in rows}

    @staticmethod
    def atualizar_valor(id_: int, valor_atual: float) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE procedimentos SET valor_atual = ? WHERE id = ?",
            (valor_atual, id_),
        )

    @staticmethod
    def atualizar_completo(
        id_: int,
        nome: str,
        categoria: str,
        codigo_cbhpo: str | None,
        valor_atual: float,
        tempo_estimado_min: int,
        valor_hora_clinica_override: float | None,
        custo_material: float,
        custo_laboratorio: float,
    ) -> None:
        conn = get_connection()
        conn.execute(
            """
            UPDATE procedimentos
               SET nome = ?, categoria = ?, codigo_cbhpo = ?, valor_atual = ?,
                   tempo_estimado_min = ?, valor_hora_clinica_override = ?,
                   custo_material = ?, custo_laboratorio = ?
             WHERE id = ?
            """,
            (
                nome, categoria, codigo_cbhpo, valor_atual,
                tempo_estimado_min, valor_hora_clinica_override,
                custo_material, custo_laboratorio, id_,
            ),
        )

    @staticmethod
    def criar(
        nome: str,
        categoria: str,
        codigo_cbhpo: str | None,
        valor_atual: float,
        tempo_estimado_min: int,
        valor_hora_clinica_override: float | None = None,
        custo_material: float = 0.0,
        custo_laboratorio: float = 0.0,
    ) -> int:
        conn = get_connection()
        cur = conn.execute(
            """
            INSERT INTO procedimentos
                (nome, categoria, codigo_cbhpo, valor_atual,
                 tempo_estimado_min, valor_hora_clinica_override,
                 custo_material, custo_laboratorio)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome, categoria, codigo_cbhpo, valor_atual,
                tempo_estimado_min, valor_hora_clinica_override,
                custo_material, custo_laboratorio,
            ),
        )
        return cur.lastrowid or 0

    @staticmethod
    def excluir(id_: int) -> None:
        conn = get_connection()
        conn.execute("UPDATE procedimentos SET ativo = 0 WHERE id = ?", (id_,))

    @staticmethod
    def estatisticas_delta() -> dict[str, Any]:
        """Retorna {'total': N, 'comparaveis': M, 'media_delta': X}."""
        conn = get_connection()
        row = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN delta_percent IS NOT NULL THEN 1 ELSE 0 END) AS comparaveis,
                   AVG(delta_percent) AS media_delta
              FROM v_procedimentos_com_delta
             WHERE ativo = 1
            """
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "comparaveis": row["comparaveis"] or 0,
            "media_delta": row["media_delta"],
        }


# ───────────────────────── Custos Fixos ──────────────────────────
class CustosFixosRepo:
    @staticmethod
    def total_mensal() -> float:
        conn = get_connection()
        row = conn.execute(
            "SELECT COALESCE(SUM(valor_mensal), 0) AS total FROM custos_fixos WHERE ativo = 1"
        ).fetchone()
        return float(row["total"])

    @staticmethod
    def listar() -> list[dict[str, Any]]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, nome, valor_mensal, ativo FROM custos_fixos ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def atualizar(id_: int, valor_mensal: float) -> None:
        conn = get_connection()
        conn.execute("UPDATE custos_fixos SET valor_mensal = ? WHERE id = ?", (valor_mensal, id_))


# ───────────────────────── Zonas ──────────────────────────
class ZonasRepo:
    @staticmethod
    def listar() -> list[dict[str, Any]]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, nome, distancia_ida_volta_km, referencia FROM zonas WHERE ativo = 1 ORDER BY distancia_ida_volta_km"
        ).fetchall()
        return [dict(r) for r in rows]


# ───────────────────────── Histórico ──────────────────────────
class HistoricoRepo:
    @staticmethod
    def salvar(
        cliente_nome: str,
        cliente_observacao: str | None,
        distancia_km: float,
        is_nee: bool,
        regime_aplicado: str,
        aliquota_aplicada: float,
        total_a_vista: float,
        total_cartao_7x: float,
        total_cartao_10x: float,
        total_cartao_12x: float,
        payload: dict[str, Any],
    ) -> int:
        conn = get_connection()
        cur = conn.execute(
            """
            INSERT INTO historico
                (cliente_nome, cliente_observacao, distancia_km, is_nee,
                 regime_aplicado, aliquota_aplicada,
                 total_a_vista, total_cartao_7x, total_cartao_10x, total_cartao_12x,
                 payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cliente_nome, cliente_observacao, distancia_km, 1 if is_nee else 0,
                regime_aplicado, aliquota_aplicada,
                total_a_vista, total_cartao_7x, total_cartao_10x, total_cartao_12x,
                json.dumps(payload, ensure_ascii=False, default=str),
            ),
        )
        return cur.lastrowid or 0

    @staticmethod
    def marcar_pdf_gerado(id_: int) -> None:
        conn = get_connection()
        conn.execute("UPDATE historico SET pdf_gerado = 1 WHERE id = ?", (id_,))

    @staticmethod
    def listar_recentes(limit: int = 50) -> list[dict[str, Any]]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM historico ORDER BY data_hora DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
