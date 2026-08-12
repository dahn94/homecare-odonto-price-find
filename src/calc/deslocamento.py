"""Cálculo do custo de deslocamento por km (asfalto + estrada de terra opcional)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..models.config import ConfigStore


@dataclass
class CustoDeslocamento:
    # Referência (combustível é o mesmo R$/km em qualquer trecho)
    custo_combustivel_km: Decimal
    custo_manutencao_km_base: Decimal
    custo_tempo_km_asfalto: Decimal
    custo_tempo_km_terra: Decimal

    km_asfalto: Decimal
    km_terra: Decimal
    distancia_km: Decimal
    tempo_waze_min: Decimal | None
    margem_lucro: Decimal

    # Totais (ida+volta), soma dos trechos
    custo_combustivel_total: Decimal
    custo_manutencao_total: Decimal
    custo_veiculo: Decimal
    custo_tempo: Decimal
    custo_real: Decimal

    taxa_apos_margem_sem_nobre: Decimal
    bairro_nobre: bool
    acrescimo_bairro_nobre_percent: Decimal
    taxa_ao_paciente: Decimal

    # Auditoria por trecho
    custo_real_asfalto: Decimal = Decimal("0.00")
    custo_real_terra: Decimal = Decimal("0.00")
    custo_combustivel_asfalto: Decimal = Decimal("0.00")
    custo_combustivel_terra: Decimal = Decimal("0.00")
    custo_manutencao_asfalto: Decimal = Decimal("0.00")
    custo_manutencao_terra: Decimal = Decimal("0.00")
    custo_tempo_asfalto: Decimal = Decimal("0.00")
    custo_tempo_terra: Decimal = Decimal("0.00")


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _segmento(
    km: Decimal,
    cfg: ConfigStore,
    *,
    velocidade_kmh: Decimal,
    fator_manutencao: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Retorna (comb_total, manut_total, veiculo, tempo, custo_real) para o trecho."""
    if km <= 0:
        return (Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))

    consumo = _to_decimal(cfg.get("veiculo.consumo_km_l"))
    preco_combustivel = _to_decimal(cfg.get("veiculo.preco_combustivel_litro"))
    custo_manutencao_km = _to_decimal(cfg.get("veiculo.custo_manutencao_km"))
    valor_hora = _to_decimal(cfg.get("tempo.valor_hora_clinica"))

    custo_combustivel_km = preco_combustivel / consumo
    custo_manut_ef = custo_manutencao_km * fator_manutencao
    custo_total_km = custo_combustivel_km + custo_manut_ef
    custo_tempo_km = valor_hora / velocidade_kmh

    custo_combustivel_total = custo_combustivel_km * km
    custo_manut_total = custo_manut_ef * km
    custo_veiculo = custo_total_km * km
    custo_tempo = custo_tempo_km * km
    custo_real = custo_veiculo + custo_tempo
    return (custo_combustivel_total, custo_manut_total, custo_veiculo, custo_tempo, custo_real)


def calcular_composto(
    km_asfalto: float | Decimal,
    km_terra: float | Decimal,
    bairro_nobre: bool,
    tempo_waze_min: float | Decimal | None,
    cfg: ConfigStore,
) -> CustoDeslocamento:
    """Deslocamento = trecho asfalto + trecho terra (cada um com regras próprias) + opcional bairro nobre."""
    km_asfalto = max(Decimal("0"), _to_decimal(km_asfalto))
    km_terra = max(Decimal("0"), _to_decimal(km_terra))

    consumo = _to_decimal(cfg.get("veiculo.consumo_km_l"))
    preco_combustivel = _to_decimal(cfg.get("veiculo.preco_combustivel_litro"))
    custo_manutencao_km = _to_decimal(cfg.get("veiculo.custo_manutencao_km"))
    valor_hora = _to_decimal(cfg.get("tempo.valor_hora_clinica"))
    vel_asfalto = _to_decimal(cfg.get("tempo.velocidade_media_km_h"))
    vel_terra = _to_decimal(cfg.get("deslocamento.velocidade_media_km_h_estrada_terra", 20))
    fator_terra = _to_decimal(cfg.get("deslocamento.fator_manutencao_estrada_terra", 1.5))
    margem = _to_decimal(cfg.get("deslocamento.margem_lucro"))
    acrescimo_nobre = _to_decimal(cfg.get("deslocamento.acrescimo_bairro_nobre_percent", 0.0))

    custo_combustivel_km = preco_combustivel / consumo
    custo_tempo_km_asfalto = valor_hora / vel_asfalto
    custo_tempo_km_terra = valor_hora / vel_terra

    ca = _segmento(km_asfalto, cfg, velocidade_kmh=vel_asfalto, fator_manutencao=Decimal("1.0"))
    ct = _segmento(km_terra, cfg, velocidade_kmh=vel_terra, fator_manutencao=fator_terra)

    comb_t = ca[0] + ct[0]
    manut_t = ca[1] + ct[1]
    veic_t = ca[2] + ct[2]  # só combustível + manutenção (sem tempo)

    if tempo_waze_min is not None:
        tempo_waze_min = max(Decimal("0"), _to_decimal(tempo_waze_min))
        tempo_t = valor_hora * (tempo_waze_min / Decimal("60"))
        dist_tmp = km_asfalto + km_terra
        if dist_tmp > 0:
            custo_tempo_km_asfalto = tempo_t / dist_tmp
            custo_tempo_km_terra = tempo_t / dist_tmp
    else:
        tempo_t = ca[3] + ct[3]

    # custo_real por trecho (veículo + tempo proporcional à distância do trecho)
    dist_total = km_asfalto + km_terra
    if tempo_waze_min is None:
        tempo_a, tempo_t_trecho = ca[3], ct[3]
    elif dist_total > 0:
        tempo_a = tempo_t * km_asfalto / dist_total
        tempo_t_trecho = tempo_t * km_terra / dist_total
    else:
        tempo_a = tempo_t_trecho = Decimal("0")
    real_a = ca[2] + tempo_a
    real_t = ct[2] + tempo_t_trecho

    custo_real = veic_t + tempo_t

    taxa_sem_nobre = custo_real * (Decimal("1") + margem)
    taxa = taxa_sem_nobre
    if bairro_nobre and acrescimo_nobre > 0:
        taxa *= Decimal("1") + acrescimo_nobre

    dist = km_asfalto + km_terra

    return CustoDeslocamento(
        custo_combustivel_km=custo_combustivel_km,
        custo_manutencao_km_base=custo_manutencao_km,
        custo_tempo_km_asfalto=custo_tempo_km_asfalto,
        custo_tempo_km_terra=custo_tempo_km_terra,
        km_asfalto=km_asfalto,
        km_terra=km_terra,
        distancia_km=dist,
        tempo_waze_min=tempo_waze_min,
        margem_lucro=margem,
        custo_combustivel_total=comb_t,
        custo_manutencao_total=manut_t,
        custo_veiculo=veic_t,
        custo_tempo=tempo_t,
        custo_real=custo_real,
        taxa_apos_margem_sem_nobre=taxa_sem_nobre,
        bairro_nobre=bairro_nobre,
        acrescimo_bairro_nobre_percent=acrescimo_nobre if bairro_nobre else Decimal("0"),
        taxa_ao_paciente=taxa,
        custo_real_asfalto=real_a,
        custo_real_terra=real_t,
        custo_combustivel_asfalto=ca[0],
        custo_combustivel_terra=ct[0],
        custo_manutencao_asfalto=ca[1],
        custo_manutencao_terra=ct[1],
        custo_tempo_asfalto=tempo_a,
        custo_tempo_terra=tempo_t_trecho,
    )


def calcular(distancia_km: float | Decimal, cfg: ConfigStore) -> CustoDeslocamento:
    """Compatibilidade: trata toda a distância como asfalto, sem bairro nobre."""
    return calcular_composto(distancia_km, Decimal("0"), False, None, cfg)
