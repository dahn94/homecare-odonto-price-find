"""Orquestrador único: recebe EntradaPrecificacao e devolve ResultadoPrecificacao.

Toda a complexidade do app converge aqui — é a única função que a UI da tela
principal precisa chamar.
"""
from __future__ import annotations

from ..db.repositories import ProcedimentoRepo
from ..models.config import ConfigStore
from ..models.orcamento import (
    EntradaPrecificacao,
    Regime,
    ResultadoPrecificacao,
)
from . import custos_fixos, deslocamento, impostos, maquineta


def precificar(entrada: EntradaPrecificacao, cfg: ConfigStore) -> ResultadoPrecificacao:
    if not entrada.procedimentos:
        raise ValueError("entrada.procedimentos vazia")

    # 1. Carrega procedimentos
    ids = [pid for pid, _ in entrada.procedimentos]
    procs_map = ProcedimentoRepo.por_ids(ids)
    faltantes = [pid for pid in ids if pid not in procs_map]
    if faltantes:
        raise ValueError(f"procedimentos inexistentes: {faltantes}")

    acrescimo_dom = cfg.get("domiciliar.acrescimo_padrao")
    acrescimo_nee = cfg.get("domiciliar.acrescimo_nee")
    valor_hora_global = cfg.get("tempo.valor_hora_clinica")
    margem_retrabalho_pct = cfg.get("retrabalho.margem_percent")

    # 2. Soma custo dos procedimentos com acréscimo domiciliar
    custo_procedimentos = 0.0
    custo_hora_clinica = 0.0
    custo_materiais_lab = 0.0

    for pid, qtd in entrada.procedimentos:
        proc = procs_map[pid]
        valor_dom = proc.valor_atual * (1 + acrescimo_dom)
        custo_procedimentos += valor_dom * qtd

        valor_hora = proc.valor_hora_clinica_override or valor_hora_global
        custo_hora_clinica += valor_hora * (proc.tempo_estimado_min / 60.0) * qtd

        custo_materiais_lab += (proc.custo_material + proc.custo_laboratorio) * qtd

    # 3. NEE +25% sobre procedimentos (não sobre deslocamento, materiais, etc)
    if entrada.is_nee:
        custo_procedimentos *= (1 + acrescimo_nee)

    # 4. Deslocamento (1x por visita)
    desloc = deslocamento.calcular(entrada.distancia_km, cfg)

    # 5. Custos fixos rateados (uma fatia por visita)
    custo_fixos = custos_fixos.rateio_por_atendimento(cfg)

    # 6. Subtotal antes de impostos e maquineta
    subtotal_antes_impostos = (
        custo_procedimentos
        + custo_hora_clinica
        + custo_materiais_lab
        + desloc.taxa_ao_paciente
        + custo_fixos
    )

    # 7. Margem de retrabalho sobre o subtotal
    margem_retrabalho = subtotal_antes_impostos * margem_retrabalho_pct
    subtotal_antes_impostos += margem_retrabalho

    # 8. Resolve regime tributário (default ou override)
    regime_aplicado = entrada.regime_override or impostos.regime_default(cfg)
    aliquota = impostos.aliquota_para(regime_aplicado, cfg, entrada.aliquota_override)

    # Imposto cobrado pela fórmula inversa: subtotal / (1 - aliquota) - subtotal
    if aliquota > 0:
        valor_com_imposto = subtotal_antes_impostos / (1 - aliquota)
        valor_impostos = valor_com_imposto - subtotal_antes_impostos
    else:
        valor_com_imposto = subtotal_antes_impostos
        valor_impostos = 0.0

    subtotal_a_vista = valor_com_imposto

    # 9. Cenários de pagamento (aplica fórmula inversa da maquineta)
    cenarios = maquineta.gerar_cenarios(subtotal_a_vista, cfg)

    return ResultadoPrecificacao(
        entrada=entrada,
        custo_procedimentos=custo_procedimentos,
        custo_hora_clinica=custo_hora_clinica,
        custo_materiais_lab=custo_materiais_lab,
        custo_deslocamento=desloc.taxa_ao_paciente,
        custo_fixos_rateado=custo_fixos,
        margem_retrabalho=margem_retrabalho,
        valor_impostos=valor_impostos,
        subtotal_a_vista=subtotal_a_vista,
        regime_aplicado=regime_aplicado,
        aliquota_aplicada=aliquota,
        cenarios=cenarios,
    )
