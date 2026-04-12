"""Cálculo da fórmula inversa da maquineta."""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from ..models.config import ConfigStore
from ..models.orcamento import CenarioPagamento


def _to_decimal(value: float | Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def cobrar_para_receber(valor_liquido: Decimal | float | int, taxa: Decimal | float | int) -> Decimal:
    """Quanto cobrar pra receber `valor_liquido` líquido após a taxa.

    Fórmula correta: valor / (1 - taxa). NÃO é valor × (1 + taxa).
    """
    valor_liquido = _to_decimal(valor_liquido)
    taxa = _to_decimal(taxa)
    if taxa <= 0:
        return valor_liquido.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if taxa >= 1:
        raise ValueError("Taxa de maquineta deve ser < 100%")
    resultado = valor_liquido / (Decimal("1") - taxa)
    return resultado.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parcelas(total: Decimal, parcelas: int) -> tuple[Decimal, Decimal | None]:
    parcela_base = (total / Decimal(parcelas)).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    if parcela_base * parcelas == total:
        return parcela_base, None
    ultima = (total - parcela_base * (parcelas - 1)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return parcela_base, ultima


def gerar_cenarios(valor_liquido: Decimal | float | int, cfg: ConfigStore) -> list[CenarioPagamento]:
    """Gera os 4 cenários de pagamento (Pix, 7x, 10x, 12x)."""
    taxa_pix = cfg.get("maquineta.taxa_pix", 0.0)
    taxa_7x = cfg.get("maquineta.taxa_7x")
    taxa_10x = cfg.get("maquineta.taxa_10x")
    taxa_12x = cfg.get("maquineta.taxa_12x")

    pix = cobrar_para_receber(valor_liquido, taxa_pix)
    c7 = cobrar_para_receber(valor_liquido, taxa_7x)
    c10 = cobrar_para_receber(valor_liquido, taxa_10x)
    c12 = cobrar_para_receber(valor_liquido, taxa_12x)

    parcela_7, ultima_7 = _parcelas(c7, 7)
    parcela_10, ultima_10 = _parcelas(c10, 10)
    parcela_12, ultima_12 = _parcelas(c12, 12)

    return [
        CenarioPagamento(forma="À vista (Pix)", total=pix, parcela=None, parcelas=1),
        CenarioPagamento(
            forma="Cartão 7x",
            total=c7,
            parcela=parcela_7,
            parcelas=7,
            parcela_ultima=ultima_7,
        ),
        CenarioPagamento(
            forma="Cartão 10x",
            total=c10,
            parcela=parcela_10,
            parcelas=10,
            parcela_ultima=ultima_10,
        ),
        CenarioPagamento(
            forma="Cartão 12x",
            total=c12,
            parcela=parcela_12,
            parcelas=12,
            parcela_ultima=ultima_12,
        ),
    ]
