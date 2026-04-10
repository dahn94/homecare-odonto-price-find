"""Cálculo do custo de deslocamento por km."""
from __future__ import annotations

from dataclasses import dataclass

from ..models.config import ConfigStore


@dataclass
class CustoDeslocamento:
    custo_veiculo: float
    custo_tempo: float
    custo_real: float
    taxa_ao_paciente: float    # com margem aplicada


def calcular(distancia_km: float, cfg: ConfigStore) -> CustoDeslocamento:
    """Calcula o valor cobrado pelo deslocamento (1x por visita)."""
    consumo = cfg.get("veiculo.consumo_km_l")
    preco_combustivel = cfg.get("veiculo.preco_combustivel_litro")
    custo_manutencao_km = cfg.get("veiculo.custo_manutencao_km")
    valor_hora = cfg.get("tempo.valor_hora_clinica")
    velocidade = cfg.get("tempo.velocidade_media_km_h")
    margem = cfg.get("deslocamento.margem_lucro")

    custo_combustivel_km = preco_combustivel / consumo
    custo_total_km = custo_combustivel_km + custo_manutencao_km
    custo_tempo_km = valor_hora / velocidade

    custo_veiculo = custo_total_km * distancia_km
    custo_tempo = custo_tempo_km * distancia_km
    custo_real = custo_veiculo + custo_tempo
    taxa_ao_paciente = custo_real * (1 + margem)

    return CustoDeslocamento(
        custo_veiculo=custo_veiculo,
        custo_tempo=custo_tempo,
        custo_real=custo_real,
        taxa_ao_paciente=taxa_ao_paciente,
    )
