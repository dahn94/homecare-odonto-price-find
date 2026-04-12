"""Resolução da alíquota efetiva por regime tributário."""
from __future__ import annotations

from decimal import Decimal

from ..models.config import ConfigStore
from ..models.orcamento import Regime


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def aliquota_para(regime: Regime, cfg: ConfigStore, custom: Decimal | float | None = None) -> Decimal:
    """Devolve a alíquota efetiva (decimal, ex: 0.275) pro regime informado."""
    if regime == Regime.DEFAULT:
        return Decimal("0.00")
    if regime == Regime.CUSTOM:
        if custom is None:
            raise ValueError("regime=CUSTOM exige aliquota_override")
        return _to_decimal(custom)
    if regime == Regime.PF:
        return _to_decimal(cfg.get("impostos.aliquota_pf"))
    if regime == Regime.MEI:
        return _to_decimal(cfg.get("impostos.aliquota_mei"))
    if regime == Regime.SIMPLES:
        return _to_decimal(cfg.get("impostos.aliquota_simples"))
    raise ValueError(f"regime desconhecido: {regime}")


def regime_default(cfg: ConfigStore) -> Regime:
    nome = cfg.get("impostos.regime_default", "PF")
    try:
        return Regime(nome)
    except ValueError:
        return Regime.PF
