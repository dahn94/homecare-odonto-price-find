"""Resolução da alíquota efetiva por regime tributário."""
from __future__ import annotations

from ..models.config import ConfigStore
from ..models.orcamento import Regime


def aliquota_para(regime: Regime, cfg: ConfigStore, custom: float | None = None) -> float:
    """Devolve a alíquota efetiva (decimal, ex: 0.275) pro regime informado."""
    if regime == Regime.DEFAULT:
        return 0.0
    if regime == Regime.CUSTOM:
        if custom is None:
            raise ValueError("regime=CUSTOM exige aliquota_override")
        return float(custom)
    if regime == Regime.PF:
        return float(cfg.get("impostos.aliquota_pf"))
    if regime == Regime.MEI:
        return float(cfg.get("impostos.aliquota_mei"))
    if regime == Regime.SIMPLES:
        return float(cfg.get("impostos.aliquota_simples"))
    raise ValueError(f"regime desconhecido: {regime}")


def regime_default(cfg: ConfigStore) -> Regime:
    nome = cfg.get("impostos.regime_default", "PF")
    try:
        return Regime(nome)
    except ValueError:
        return Regime.PF
