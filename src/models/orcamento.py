"""Modelos do fluxo de precificação."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Regime(str, Enum):
    PF = "PF"
    MEI = "MEI"
    SIMPLES = "SIMPLES"
    DEFAULT = "DEFAULT"
    CUSTOM = "CUSTOM"


@dataclass
class EntradaPrecificacao:
    procedimentos: list[tuple[int, int]]   # [(procedimento_id, quantidade), ...]
    distancia_km: float
    is_nee: bool = False
    regime_override: Regime | None = None
    aliquota_override: float | None = None  # só usado se regime_override == CUSTOM


@dataclass
class CenarioPagamento:
    forma: str           # 'Pix' | 'Cartão 7x' | 'Cartão 10x' | 'Cartão 12x'
    total: float
    parcela: float | None = None
    parcelas: int = 1


@dataclass
class ResultadoPrecificacao:
    entrada: EntradaPrecificacao

    # Decomposição interna (não exibida ao usuário, mas guardada no histórico).
    custo_procedimentos: float = 0.0
    custo_hora_clinica: float = 0.0
    custo_materiais_lab: float = 0.0
    custo_deslocamento: float = 0.0
    custo_fixos_rateado: float = 0.0
    margem_retrabalho: float = 0.0
    valor_impostos: float = 0.0
    subtotal_a_vista: float = 0.0

    regime_aplicado: Regime = Regime.PF
    aliquota_aplicada: float = 0.0

    cenarios: list[CenarioPagamento] = field(default_factory=list)
