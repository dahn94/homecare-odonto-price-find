"""Cálculo da fórmula inversa da maquineta."""
from __future__ import annotations

from ..models.config import ConfigStore
from ..models.orcamento import CenarioPagamento


def cobrar_para_receber(valor_liquido: float, taxa: float) -> float:
    """Quanto cobrar pra receber `valor_liquido` líquido após a taxa.

    Fórmula correta: valor / (1 - taxa). NÃO é valor × (1 + taxa).
    """
    if taxa <= 0:
        return valor_liquido
    if taxa >= 1:
        raise ValueError("Taxa de maquineta deve ser < 100%")
    return valor_liquido / (1 - taxa)


def gerar_cenarios(valor_liquido: float, cfg: ConfigStore) -> list[CenarioPagamento]:
    """Gera os 4 cenários de pagamento (Pix, 7x, 10x, 12x)."""
    taxa_pix = cfg.get("maquineta.taxa_pix", 0.0)
    taxa_7x = cfg.get("maquineta.taxa_7x")
    taxa_10x = cfg.get("maquineta.taxa_10x")
    taxa_12x = cfg.get("maquineta.taxa_12x")

    pix = cobrar_para_receber(valor_liquido, taxa_pix)
    c7 = cobrar_para_receber(valor_liquido, taxa_7x)
    c10 = cobrar_para_receber(valor_liquido, taxa_10x)
    c12 = cobrar_para_receber(valor_liquido, taxa_12x)

    return [
        CenarioPagamento(forma="À vista (Pix)",  total=pix, parcela=None,    parcelas=1),
        CenarioPagamento(forma="Cartão 7x",      total=c7,  parcela=c7 / 7,  parcelas=7),
        CenarioPagamento(forma="Cartão 10x",     total=c10, parcela=c10 / 10, parcelas=10),
        CenarioPagamento(forma="Cartão 12x",     total=c12, parcela=c12 / 12, parcelas=12),
    ]
