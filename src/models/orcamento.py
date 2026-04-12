"""Modelos do fluxo de precificação."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
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
    # Ida + volta, em km — pode ser só asfalto, só terra, ou combinação
    km_asfalto: float = 0.0
    km_terra: float = 0.0
    # Tempo do Waze (ida+volta) em minutos. Quando informado, substitui o cálculo por velocidade média.
    tempo_waze_min: float | None = None
    bairro_nobre: bool = False
    # Estacionamento: gratuito ou pago proporcional ao tempo total dos procedimentos (min) × tarifa R$/h
    estacionamento_gratuito: bool = True
    estacionamento_tarifa_hora: Decimal | None = None  # se pago e None, precificador usa config
    is_nee: bool = False
    regime_override: Regime | None = None
    aliquota_override: Decimal | None = None  # só usado se regime_override == CUSTOM

    @property
    def distancia_km(self) -> float:
        return self.km_asfalto + self.km_terra


@dataclass
class CenarioPagamento:
    forma: str           # 'Pix' | 'Cartão 7x' | 'Cartão 10x' | 'Cartão 12x'
    total: Decimal
    parcela: Decimal | None = None
    parcelas: int = 1
    parcela_ultima: Decimal | None = None


@dataclass
class ResultadoPrecificacao:
    entrada: EntradaPrecificacao

    # Decomposição interna (não exibida ao usuário, mas guardada no histórico).
    custo_procedimentos: Decimal = Decimal("0.00")
    custo_hora_clinica: Decimal = Decimal("0.00")
    custo_materiais_lab: Decimal = Decimal("0.00")
    custo_deslocamento: Decimal = Decimal("0.00")
    custo_estacionamento: Decimal = Decimal("0.00")
    tempo_procedimentos_min: Decimal = Decimal("0.00")
    custo_fixos_rateado: Decimal = Decimal("0.00")
    margem_retrabalho: Decimal = Decimal("0.00")
    valor_impostos: Decimal = Decimal("0.00")
    subtotal_a_vista: Decimal = Decimal("0.00")

    regime_aplicado: Regime = Regime.PF
    aliquota_aplicada: Decimal = Decimal("0.00")

    cenarios: list[CenarioPagamento] = field(default_factory=list)
