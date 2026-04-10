"""Modelo de Procedimento + variante com delta CBHPO."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Procedimento:
    id: int
    nome: str
    categoria: str
    codigo_cbhpo: str | None
    valor_atual: float
    tempo_estimado_min: int
    valor_hora_clinica_override: float | None
    custo_material: float
    custo_laboratorio: float
    fator_complexidade_min: float = 1.0
    fator_complexidade_max: float = 1.0
    ativo: bool = True

    # Carregado via JOIN com cbhpo_referencia (None se sem código).
    valor_cbhpo_oficial: float | None = None
    cbhpo_versao: str | None = None
    delta_percent: float | None = None

    @classmethod
    def from_row(cls, row) -> "Procedimento":
        """Cria a partir de uma sqlite3.Row da view v_procedimentos_com_delta."""
        keys = row.keys()
        return cls(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            codigo_cbhpo=row["codigo_cbhpo"],
            valor_atual=row["valor_atual"],
            tempo_estimado_min=row["tempo_estimado_min"],
            valor_hora_clinica_override=row["valor_hora_clinica_override"],
            custo_material=row["custo_material"],
            custo_laboratorio=row["custo_laboratorio"],
            fator_complexidade_min=row["fator_complexidade_min"],
            fator_complexidade_max=row["fator_complexidade_max"],
            ativo=bool(row["ativo"]),
            valor_cbhpo_oficial=row["valor_cbhpo_oficial"] if "valor_cbhpo_oficial" in keys else None,
            cbhpo_versao=row["cbhpo_versao"] if "cbhpo_versao" in keys else None,
            delta_percent=row["delta_percent"] if "delta_percent" in keys else None,
        )
