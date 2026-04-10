"""Rateio dos custos fixos pelo nº de atendimentos estimados."""
from __future__ import annotations

from ..db.repositories import CustosFixosRepo
from ..models.config import ConfigStore


def rateio_por_atendimento(cfg: ConfigStore) -> float:
    """Quanto cada visita absorve dos custos fixos mensais."""
    total = CustosFixosRepo.total_mensal()
    atendimentos = cfg.get("meta.atendimentos_estimados_mes", 1)
    if not atendimentos or atendimentos <= 0:
        return 0.0
    return total / atendimentos
