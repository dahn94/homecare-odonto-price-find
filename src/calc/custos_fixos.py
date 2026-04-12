"""Rateio dos custos fixos pelo nº de atendimentos estimados."""
from __future__ import annotations

from decimal import Decimal

from ..db.repositories import CustosFixosRepo
from ..models.config import ConfigStore


def rateio_por_atendimento(cfg: ConfigStore) -> Decimal:
    """Quanto cada visita absorve dos custos fixos mensais."""
    total = CustosFixosRepo.total_mensal()
    atendimentos = cfg.get("meta.atendimentos_estimados_mes", 1)
    if not atendimentos or atendimentos <= 0:
        return Decimal("0.00")
    return total / Decimal(str(atendimentos))
