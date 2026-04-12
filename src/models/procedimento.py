"""Modelo de Procedimento + variante com delta CBHPO."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Procedimento:
    id: int
    nome: str
    categoria: str
    codigo_cbhpo: str | None
    valor_atual: Decimal
    tempo_estimado_min: int
    valor_hora_clinica_override: Decimal | None
    custo_material: Decimal
    custo_laboratorio: Decimal
    fator_complexidade_min: Decimal = Decimal("1.0")
    fator_complexidade_max: Decimal = Decimal("1.0")
    ativo: bool = True

    # Carregado via JOIN com cbhpo_referencia (None se sem código).
    valor_cbhpo_oficial: Decimal | None = None
    cbhpo_versao: str | None = None
    delta_percent: Decimal | None = None

    @classmethod
    def from_row(cls, row) -> "Procedimento":
        """Cria a partir de uma sqlite3.Row da view v_procedimentos_com_delta."""
        keys = row.keys()
        return cls(
            id=row["id"],
            nome=row["nome"],
            categoria=row["categoria"],
            codigo_cbhpo=row["codigo_cbhpo"],
            valor_atual=Decimal(str(row["valor_atual"])),
            tempo_estimado_min=row["tempo_estimado_min"],
            valor_hora_clinica_override=Decimal(str(row["valor_hora_clinica_override"])) if row["valor_hora_clinica_override"] is not None else None,
            custo_material=Decimal(str(row["custo_material"])),
            custo_laboratorio=Decimal(str(row["custo_laboratorio"])),
            fator_complexidade_min=Decimal(str(row["fator_complexidade_min"])),
            fator_complexidade_max=Decimal(str(row["fator_complexidade_max"])),
            ativo=bool(row["ativo"]),
            valor_cbhpo_oficial=Decimal(str(row["valor_cbhpo_oficial"])) if "valor_cbhpo_oficial" in keys and row["valor_cbhpo_oficial"] is not None else None,
            cbhpo_versao=row["cbhpo_versao"] if "cbhpo_versao" in keys else None,
            delta_percent=Decimal(str(row["delta_percent"])) if "delta_percent" in keys and row["delta_percent"] is not None else None,
        )
