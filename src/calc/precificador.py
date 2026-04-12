"""Orquestrador único: recebe EntradaPrecificacao e devolve ResultadoPrecificacao.

Toda a complexidade do app converge aqui — é a única função que a UI da tela
principal precisa chamar.
"""
from __future__ import annotations

from decimal import Decimal

from ..db.repositories import ProcedimentoRepo
from ..models.config import ConfigStore
from ..models.orcamento import (
    EntradaPrecificacao,
    Regime,
    ResultadoPrecificacao,
)
from . import custos_fixos, deslocamento, impostos, maquineta


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def precificar(entrada: EntradaPrecificacao, cfg: ConfigStore) -> ResultadoPrecificacao:
    if not entrada.procedimentos:
        raise ValueError("entrada.procedimentos vazia")

    # 1. Carrega procedimentos
    ids = [pid for pid, _ in entrada.procedimentos]
    procs_map = ProcedimentoRepo.por_ids(ids)
    faltantes = [pid for pid in ids if pid not in procs_map]
    if faltantes:
        raise ValueError(f"procedimentos inexistentes: {faltantes}")

    acrescimo_dom = _to_decimal(cfg.get("domiciliar.acrescimo_padrao"))
    acrescimo_nee = _to_decimal(cfg.get("domiciliar.acrescimo_nee"))
    valor_hora_global = _to_decimal(cfg.get("tempo.valor_hora_clinica"))
    margem_retrabalho_pct = _to_decimal(cfg.get("retrabalho.margem_percent"))

    # 2. Soma custo dos procedimentos com acréscimo domiciliar
    custo_procedimentos = Decimal("0.00")
    custo_hora_clinica = Decimal("0.00")
    custo_materiais_lab = Decimal("0.00")

    tempo_procedimentos_min = Decimal("0.00")
    for pid, qtd in entrada.procedimentos:
        proc = procs_map[pid]
        tempo_procedimentos_min += Decimal(proc.tempo_estimado_min) * qtd
        valor_dom = proc.valor_atual * (Decimal("1") + acrescimo_dom)
        custo_procedimentos += valor_dom * qtd

        valor_hora = proc.valor_hora_clinica_override or valor_hora_global
        custo_hora_clinica += valor_hora * (Decimal(proc.tempo_estimado_min) / Decimal("60")) * qtd

        custo_materiais_lab += (proc.custo_material + proc.custo_laboratorio) * qtd

    # 3. NEE +25% sobre procedimentos (não sobre deslocamento, materiais, etc)
    if entrada.is_nee:
        custo_procedimentos *= Decimal("1") + acrescimo_nee

    # 4. Deslocamento (1x por visita)
    desloc = deslocamento.calcular_composto(
        entrada.km_asfalto,
        entrada.km_terra,
        entrada.bairro_nobre,
        entrada.tempo_waze_min,
        cfg,
    )

    # 5. Estacionamento (pago = proporcional ao tempo dos procedimentos × R$/h)
    custo_estacionamento = Decimal("0.00")
    if not entrada.estacionamento_gratuito:
        tarifa_h = entrada.estacionamento_tarifa_hora
        if tarifa_h is None:
            tarifa_h = _to_decimal(cfg.get("estacionamento.tarifa_hora_padrao", Decimal("0.00")))
        else:
            tarifa_h = _to_decimal(tarifa_h)
        custo_estacionamento = (tempo_procedimentos_min / Decimal("60")) * tarifa_h

    # 6. Custos fixos rateados (uma fatia por visita)
    custo_fixos = _to_decimal(custos_fixos.rateio_por_atendimento(cfg))

    # 7. Subtotal antes de impostos e maquineta
    subtotal_antes_impostos = (
        custo_procedimentos
        + custo_hora_clinica
        + custo_materiais_lab
        + desloc.taxa_ao_paciente
        + custo_estacionamento
        + custo_fixos
    )

    # 8. Margem de retrabalho sobre o subtotal
    margem_retrabalho = subtotal_antes_impostos * margem_retrabalho_pct
    subtotal_antes_impostos += margem_retrabalho

    # 9. Regime tributário é escolhido no orçamento (fallback PF por segurança)
    regime_aplicado = entrada.regime_override or Regime.PF
    aliquota = impostos.aliquota_para(regime_aplicado, cfg, entrada.aliquota_override)

    # Imposto cobrado pela fórmula inversa: subtotal / (1 - aliquota) - subtotal
    if aliquota > Decimal("0"):
        valor_com_imposto = subtotal_antes_impostos / (Decimal("1") - aliquota)
        valor_impostos = valor_com_imposto - subtotal_antes_impostos
    else:
        valor_com_imposto = subtotal_antes_impostos
        valor_impostos = Decimal("0.00")

    subtotal_a_vista = valor_com_imposto

    # 10. Cenários de pagamento (aplica fórmula inversa da maquineta)
    cenarios = maquineta.gerar_cenarios(subtotal_a_vista, cfg)

    return ResultadoPrecificacao(
        entrada=entrada,
        custo_procedimentos=custo_procedimentos,
        custo_hora_clinica=custo_hora_clinica,
        custo_materiais_lab=custo_materiais_lab,
        custo_deslocamento=desloc.taxa_ao_paciente,
        custo_estacionamento=custo_estacionamento,
        tempo_procedimentos_min=tempo_procedimentos_min,
        custo_fixos_rateado=custo_fixos,
        margem_retrabalho=margem_retrabalho,
        valor_impostos=valor_impostos,
        subtotal_a_vista=subtotal_a_vista,
        regime_aplicado=regime_aplicado,
        aliquota_aplicada=aliquota,
        cenarios=cenarios,
    )
