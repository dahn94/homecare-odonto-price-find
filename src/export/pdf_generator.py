"""Gerador de PDF do orçamento — minimalista, pensado pro paciente.

Não exibe decomposição interna de custos. Mostra:
- Cabeçalho (logo, título, data, número)
- Dados do paciente
- Lista simples de procedimentos (nome + qtd)
- Bloco destacado: cenários de pagamento (Pix, 7x, 10x, 12x)
- Validade 30 dias
- Rodapé com contato/CRO
"""
from __future__ import annotations

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None

import re
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..db.repositories import ProcedimentoRepo
from ..models.config import ConfigStore
from ..models.orcamento import ResultadoPrecificacao
from ..calc import deslocamento as calc_deslocamento

# Paleta (espelha src/theme.py adaptada pro PDF)
ACCENT = colors.HexColor("#00BFA6")
BG_DARK = colors.HexColor("#0F1B2D")
BG_CARD = colors.HexColor("#223553")
TEXT_MUTED = colors.HexColor("#5A7A96")
GOLD = colors.HexColor("#FFD700")

from ..paths import get_bundle_dir

ASSETS_DIR = get_bundle_dir() / "assets"
LOGO_PATH = ASSETS_DIR / "logo_basis.png"
PYPROJECT_PATH = get_bundle_dir() / "pyproject.toml"


def _read_project_version() -> str | None:
    if not PYPROJECT_PATH.exists():
        return None
    try:
        if tomllib is not None:
            with PYPROJECT_PATH.open("rb") as handle:
                data = tomllib.load(handle)
            version = data.get("project", {}).get("version")
            return f"v{version}" if version else None
        text = PYPROJECT_PATH.read_text(encoding="utf-8")
        match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
        return f"v{match.group(1)}" if match else None
    except Exception:
        return None


PDF_VERSION = _read_project_version()


def _fmt_brl(v: Decimal | float | int | str) -> str:
    d = Decimal(str(v)).quantize(Decimal("0.01"))
    s = f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _fmt_brl_4(v: Decimal | float | int | str) -> str:
    """Formato monetário com 4 casas decimais (padrão bancário — cálculos intermediários)."""
    d = Decimal(str(v)).quantize(Decimal("0.0001"))
    s = f"{d:,.4f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _fmt_pct(v: Decimal | float | int | str) -> str:
    d = Decimal(str(v)) * 100
    s = f"{d:.2f}".replace(".", ",")
    return f"{s}%"


def gerar_pdf_orcamento(
    resultado: ResultadoPrecificacao,
    cliente_nome: str,
    output_path: str | Path,
    numero_orcamento: int | None = None,
    cliente_observacao: str | None = None,
    cfg: ConfigStore | None = None,
) -> Path:
    """Gera o PDF e retorna o caminho final."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Orçamento Basis — {cliente_nome}",
        author="Basis Odontologia Domiciliar",
    )

    story: list = []
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "h1", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=18,
        textColor=BG_DARK, spaceAfter=2,
    )
    sub = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName="Helvetica", fontSize=10,
        textColor=TEXT_MUTED, spaceAfter=12,
    )
    label = ParagraphStyle(
        "label", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=10,
        textColor=BG_DARK, spaceAfter=4,
    )
    body = ParagraphStyle(
        "body", parent=styles["Normal"],
        fontName="Helvetica", fontSize=11,
        textColor=colors.black, spaceAfter=6,
    )
    section = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=13,
        textColor=ACCENT, spaceBefore=14, spaceAfter=8,
    )
    footer_style = ParagraphStyle(
        "footer", parent=styles["Normal"],
        fontName="Helvetica", fontSize=8,
        textColor=TEXT_MUTED, alignment=TA_CENTER,
    )

    # ─────────── Cabeçalho ───────────
    hoje = datetime.now()
    numero_str = f"#{numero_orcamento:05d}" if numero_orcamento else "—"

    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=4 * cm, height=1.4 * cm, kind="proportional")
    else:
        logo = Paragraph("<b>BASIS</b>", h1)

    header_data = [[
        logo,
        Paragraph(
            f"<b>Orçamento Odontológico Domiciliar</b><br/>"
            f"<font size=9 color='#5A7A96'>{numero_str} · {hoje.strftime('%d/%m/%Y')}</font>",
            ParagraphStyle("hr", fontName="Helvetica", fontSize=12, alignment=TA_RIGHT, textColor=BG_DARK),
        ),
    ]]
    header_tbl = Table(header_data, colWidths=[6 * cm, 11 * cm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.2, ACCENT),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 14))

    # ─────────── Paciente ───────────
    story.append(Paragraph("PACIENTE", label))
    story.append(Paragraph(cliente_nome, body))
    if cliente_observacao:
        story.append(Paragraph(cliente_observacao, sub))

    extras = []
    ent = resultado.entrada
    if ent.distancia_km > 0:
        det = [f"{ent.distancia_km:.0f} km (ida e volta)"]
        if ent.km_asfalto > 0:
            det.append(f"asfalto {ent.km_asfalto:.0f} km")
        if ent.km_terra > 0:
            det.append(f"terra {ent.km_terra:.0f} km")
        extras.append("Atendimento domiciliar — " + ", ".join(det))
    if getattr(ent, "bairro_nobre", False):
        extras.append("Bairro nobre (acréscimo de deslocamento)")
    if not getattr(ent, "estacionamento_gratuito", True):
        extras.append("Estacionamento pago (estimado pelo tempo dos procedimentos)")
    if resultado.entrada.is_nee:
        extras.append("Paciente com necessidades especiais (NEE)")
    if extras:
        story.append(Paragraph(" · ".join(extras), sub))

    # ─────────── Procedimentos ───────────
    story.append(Paragraph("PROCEDIMENTOS", section))

    procs_map = ProcedimentoRepo.por_ids([pid for pid, _ in resultado.entrada.procedimentos])
    rows = [["Procedimento", "Qtd."]]
    for pid, qtd in resultado.entrada.procedimentos:
        proc = procs_map.get(pid)
        nome = proc.nome if proc else f"Procedimento #{pid}"
        rows.append([nome, str(qtd)])

    proc_tbl = Table(rows, colWidths=[14 * cm, 3 * cm])
    proc_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 11),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(proc_tbl)

    # ─────────── Cenários de Pagamento ───────────
    story.append(Paragraph("FORMAS DE PAGAMENTO", section))

    cen_rows = [["Forma", "Total", "Detalhe"]]
    for c in resultado.cenarios:
        if c.parcela and c.parcelas > 1:
            if getattr(c, "parcela_ultima", None) is not None:
                detalhe = (
                    f"{c.parcelas - 1}× de {_fmt_brl(c.parcela)} "
                    f"+ 1× de {_fmt_brl(c.parcela_ultima)}"
                )
            else:
                detalhe = f"{c.parcelas}× de {_fmt_brl(c.parcela)}"
        else:
            detalhe = "à vista"
        cen_rows.append([c.forma, _fmt_brl(c.total), detalhe])

    cen_tbl = Table(cen_rows, colWidths=[5 * cm, 5 * cm, 7 * cm])
    cen_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.white),
    ]
    # Destaca a primeira linha de dados (Pix / à vista)
    if len(cen_rows) > 1:
        cen_style += [
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E0FFF9")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 1), (1, 1), ACCENT),
        ]
    cen_tbl.setStyle(TableStyle(cen_style))
    story.append(cen_tbl)

    # ─────────── Validade ───────────
    validade_dias = 30
    if cfg is not None:
        try:
            validade_dias = int(cfg.get("orcamento.validade_dias", 30))
        except Exception:
            validade_dias = 30
    validade = hoje + timedelta(days=validade_dias)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"<i>Orçamento válido até <b>{validade.strftime('%d/%m/%Y')}</b> ({validade_dias} dias).</i>",
        sub,
    ))

    # ─────────── Rodapé ───────────
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "Basis Odontologia Domiciliar · Blumenau / SC<br/>"
        "Atendimento humanizado em domicílio para a região do Vale do Itajaí",
        footer_style,
    ))

    def _draw_version_footer(canvas, doc):
        if not PDF_VERSION:
            return
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_MUTED)
        left_x = doc.leftMargin
        right_x = doc.pagesize[0] - doc.rightMargin
        footer_y = 12
        canvas.drawString(left_x, footer_y, PDF_VERSION)
        canvas.drawRightString(right_x, footer_y, PDF_VERSION)
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_version_footer, onLaterPages=_draw_version_footer)
    return output_path


def gerar_pdf_orcamento_interno(
    resultado: ResultadoPrecificacao,
    cliente_nome: str,
    output_path: str | Path,
    numero_orcamento: int | None = None,
    cfg: ConfigStore | None = None,
) -> Path:
    """PDF interno (dentista): formação do preço + resultado líquido.

    Estrutura:
    1. Resumo (inputs)
    2. Formação do preço (cascata — cada componente somando ao acumulado)
    3. Resultado líquido (o que sobra pro profissional)
    4. Cenários de pagamento
    5. Deslocamento (detalhe técnico)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"Log interno — {cliente_nome}",
        author="Basis Odontologia Domiciliar",
    )

    story: list = []
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "h1", parent=styles["Heading1"],
        fontName="Helvetica-Bold", fontSize=16,
        textColor=BG_DARK, spaceAfter=6,
    )
    sub = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontName="Helvetica", fontSize=9,
        textColor=TEXT_MUTED, spaceAfter=10,
    )
    section = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontName="Helvetica-Bold", fontSize=12,
        textColor=ACCENT, spaceBefore=12, spaceAfter=6,
    )
    mono = ParagraphStyle(
        "mono", parent=styles["Normal"],
        fontName="Courier", fontSize=9,
        textColor=colors.black, leading=12,
    )

    hoje = datetime.now()
    numero_str = f"#{numero_orcamento:05d}" if numero_orcamento else ""
    ent = resultado.entrada

    # Recalcular deslocamento para ter os custos reais
    d = None
    if cfg is not None:
        d = calc_deslocamento.calcular_composto(
            ent.km_asfalto, ent.km_terra, ent.bairro_nobre,
            ent.tempo_waze_min, cfg,
        )

    # Carregar dados dos procedimentos
    procs_map = ProcedimentoRepo.por_ids([pid for pid, _ in ent.procedimentos])
    acrescimo_dom = Decimal(str(cfg.get("domiciliar.acrescimo_padrao"))) if cfg else Decimal("0")
    acrescimo_nee = Decimal(str(cfg.get("domiciliar.acrescimo_nee"))) if cfg else Decimal("0")
    valor_hora_global = Decimal(str(cfg.get("tempo.valor_hora_clinica"))) if cfg else Decimal("150")

    # ─────────── 1. RESUMO ───────────
    story.append(Paragraph("Log interno de precificação", h1))
    story.append(Paragraph(f"{numero_str} · {hoje.strftime('%d/%m/%Y %H:%M')}", sub))

    # Info compacta
    flags = []
    if ent.is_nee:
        flags.append("NEE")
    if ent.bairro_nobre:
        flags.append("bairro nobre")
    if not getattr(ent, "estacionamento_gratuito", True):
        flags.append(f"estac. pago ({_fmt_brl(resultado.custo_estacionamento)})")
    flags_txt = f" · {', '.join(flags)}" if flags else ""

    regime_nomes = {"PF": "PF (carnê-leão)", "MEI": "MEI", "SIMPLES": "Simples Nacional", "DEFAULT": "sem impostos"}
    regime_txt = regime_nomes.get(resultado.regime_aplicado.value, resultado.regime_aplicado.value)

    story.append(Paragraph(
        f"<b>Cliente:</b> {cliente_nome} · "
        f"<b>Deslocamento:</b> {ent.km_asfalto:.0f}km asf + {ent.km_terra:.0f}km terra = {ent.distancia_km:.0f}km"
        f"{flags_txt}",
        mono,
    ))
    story.append(Paragraph(
        f"<b>Regime:</b> {regime_txt} ({_fmt_pct(resultado.aliquota_aplicada)}) · "
        f"<b>Acréscimo domiciliar:</b> {_fmt_pct(acrescimo_dom)}"
        + (f" · <b>NEE:</b> +{_fmt_pct(acrescimo_nee)}" if ent.is_nee else ""),
        mono,
    ))
    story.append(Spacer(1, 6))

    # ─────────── 2. FORMAÇÃO DO PREÇO (cascata) ───────────
    story.append(Paragraph("Formação do preço", section))

    # Estilos para células com wrap
    cell_normal = ParagraphStyle("cell_normal", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.black)
    cell_bold = ParagraphStyle("cell_bold", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.black)
    cell_calc = ParagraphStyle("cell_calc", fontName="Helvetica", fontSize=7.5, leading=9, textColor=TEXT_MUTED)

    cascade_rows = [["Etapa", "Cálculo", "Valor", "Acumulado"]]
    acumulado = Decimal("0")

    # 2a. Procedimentos (um por um, com acréscimo domiciliar visível)
    for pid, qtd in ent.procedimentos:
        p = procs_map.get(pid)
        if not p:
            continue
        valor_dom = p.valor_atual * (Decimal("1") + acrescimo_dom)
        if ent.is_nee:
            valor_dom *= (Decimal("1") + acrescimo_nee)
        valor_total = valor_dom * qtd
        acumulado += valor_total

        calc_txt = f"{_fmt_brl(p.valor_atual)}"
        if acrescimo_dom > 0:
            calc_txt += f" x (1+{_fmt_pct(acrescimo_dom)})"
        if ent.is_nee:
            calc_txt += f" x (1+{_fmt_pct(acrescimo_nee)})"
        if qtd > 1:
            calc_txt += f" x {qtd}"

        cascade_rows.append([
            Paragraph(p.nome, cell_bold),
            Paragraph(calc_txt, cell_calc),
            _fmt_brl_4(valor_total),
            _fmt_brl_4(acumulado),
        ])

    # 2b. Hora clínica
    acumulado += resultado.custo_hora_clinica
    hora_calc_parts = []
    for pid, qtd in ent.procedimentos:
        p = procs_map.get(pid)
        if not p:
            continue
        vh = p.valor_hora_clinica_override or valor_hora_global
        hora_calc_parts.append(f"{_fmt_brl(vh)}/h x {p.tempo_estimado_min}min")
    cascade_rows.append([
        Paragraph("Hora clínica", cell_normal),
        Paragraph(" + ".join(hora_calc_parts) if len(hora_calc_parts) == 1 else "soma proc.", cell_calc),
        _fmt_brl_4(resultado.custo_hora_clinica),
        _fmt_brl_4(acumulado),
    ])

    # 2c. Material + lab
    if resultado.custo_materiais_lab > 0:
        acumulado += resultado.custo_materiais_lab
        cascade_rows.append([
            Paragraph("Material + laboratório", cell_normal),
            Paragraph("custo real (sem acréscimo)", cell_calc),
            _fmt_brl_4(resultado.custo_materiais_lab),
            _fmt_brl_4(acumulado),
        ])

    # 2d. Deslocamento
    if d:
        desloc_calc = f"{ent.distancia_km:.0f}km, custo {_fmt_brl_4(d.custo_real)} + margem {_fmt_pct(d.margem_lucro)}"
    else:
        desloc_calc = "com margem"
    acumulado += resultado.custo_deslocamento
    cascade_rows.append([
        Paragraph("Deslocamento", cell_normal),
        Paragraph(desloc_calc, cell_calc),
        _fmt_brl_4(resultado.custo_deslocamento),
        _fmt_brl_4(acumulado),
    ])

    # 2e. Estacionamento
    if resultado.custo_estacionamento > 0:
        acumulado += resultado.custo_estacionamento
        cascade_rows.append([
            Paragraph("Estacionamento", cell_normal),
            Paragraph(f"{resultado.tempo_procedimentos_min:.0f}min x tarifa", cell_calc),
            _fmt_brl_4(resultado.custo_estacionamento),
            _fmt_brl_4(acumulado),
        ])

    # 2f. Custos fixos
    acumulado += resultado.custo_fixos_rateado
    cascade_rows.append([
        Paragraph("Custos fixos (rateio)", cell_normal),
        Paragraph("R$ mensal / atend. estimados", cell_calc),
        _fmt_brl_4(resultado.custo_fixos_rateado),
        _fmt_brl_4(acumulado),
    ])

    # 2g. Retrabalho
    acumulado += resultado.margem_retrabalho
    retrabalho_pct = _fmt_pct(cfg.get("retrabalho.margem_percent")) if cfg else "5%"
    cascade_rows.append([
        Paragraph(f"Retrabalho ({retrabalho_pct})", cell_normal),
        Paragraph(f"{retrabalho_pct} x subtotal", cell_calc),
        _fmt_brl_4(resultado.margem_retrabalho),
        _fmt_brl_4(acumulado),
    ])

    # 2h. Impostos
    acumulado += resultado.valor_impostos
    cascade_rows.append([
        Paragraph(f"Impostos ({regime_txt})", cell_normal),
        Paragraph(f"fórmula inversa {_fmt_pct(resultado.aliquota_aplicada)}", cell_calc),
        _fmt_brl_4(resultado.valor_impostos),
        _fmt_brl_4(acumulado),
    ])

    # Linha final
    cascade_rows.append([
        "PREÇO FINAL (Pix)",
        "",
        "",
        _fmt_brl(resultado.subtotal_a_vista),
    ])

    n_rows = len(cascade_rows)
    c_tbl = Table(cascade_rows, colWidths=[4.5 * cm, 5.2 * cm, 3.2 * cm, 3.6 * cm])
    c_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -2), 9),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F4F7FB")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        # Linha final destacada
        ("BACKGROUND", (0, n_rows - 1), (-1, n_rows - 1), BG_DARK),
        ("TEXTCOLOR", (0, n_rows - 1), (-1, n_rows - 1), colors.white),
        ("FONTNAME", (0, n_rows - 1), (-1, n_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, n_rows - 1), (-1, n_rows - 1), 10),
    ]
    c_tbl.setStyle(TableStyle(c_style))
    story.append(c_tbl)

    # ─────────── 2b. LEGENDA ───────────
    legenda_style = ParagraphStyle(
        "legenda", fontName="Helvetica", fontSize=7.5, leading=10,
        textColor=TEXT_MUTED, spaceBefore=2, spaceAfter=1,
    )
    legenda_titulo = ParagraphStyle(
        "legenda_titulo", fontName="Helvetica-Bold", fontSize=8,
        textColor=BG_DARK, spaceBefore=8, spaceAfter=3,
    )
    story.append(Paragraph("Glossário", legenda_titulo))

    glossario = [
        ("Acréscimo domiciliar",
         "Percentual adicional sobre o valor do procedimento por ser atendimento em domicílio (padrão CNCC/CRO: 100%)."),
        ("NEE",
         "Necessidades Especiais — acréscimo adicional pela complexidade do atendimento a pacientes com necessidades especiais."),
        ("Hora clínica",
         "Custo do tempo da profissional dedicado ao procedimento, calculado como (valor da hora × tempo estimado em minutos ÷ 60)."),
        ("Material + laboratório",
         "Custo real de materiais odontológicos e serviços de laboratório (ex: próteses). Repassado sem acréscimo."),
        ("Deslocamento",
         "Custo da ida e volta até o paciente: combustível + manutenção do veículo + custo de oportunidade do tempo no trânsito, com margem de lucro aplicada."),
        ("Custos fixos (rateio)",
         "Despesas mensais fixas (CRO, seguro, contabilidade, depreciação de equipamento, IPVA, seguro veicular, etc.) divididas pelo número estimado de atendimentos no mês."),
        ("Retrabalho",
         "Margem de segurança para cobrir eventuais refações ou retornos não previstos."),
        ("Impostos",
         "Calculado por fórmula inversa: o valor é embutido no preço para que, após o desconto do imposto, sobre o valor desejado. Fórmula: subtotal ÷ (1 − alíquota)."),
        ("Fórmula inversa (maquineta)",
         "Mesmo princípio dos impostos aplicado à taxa do cartão: valor ÷ (1 − taxa), garantindo que o líquido recebido seja o valor correto."),
    ]
    for termo, explicacao in glossario:
        story.append(Paragraph(f"<b>{termo}:</b> {explicacao}", legenda_style))

    # ─────────── 3. RESULTADO LÍQUIDO ───────────
    story.append(Paragraph("Resultado para a profissional", section))

    receita = resultado.subtotal_a_vista

    # Custos reais (saem do bolso)
    custo_combustivel = d.custo_combustivel_total if d else Decimal("0")
    custo_manutencao = d.custo_manutencao_total if d else Decimal("0")
    custo_mat_lab = resultado.custo_materiais_lab
    custo_impostos = resultado.valor_impostos
    custo_fixos = resultado.custo_fixos_rateado
    custo_estac = resultado.custo_estacionamento

    total_custos = custo_combustivel + custo_manutencao + custo_mat_lab + custo_impostos + custo_fixos + custo_estac
    lucro = receita - total_custos

    # Tempo total (procedimentos + deslocamento estimado)
    tempo_proc = resultado.tempo_procedimentos_min
    if d and d.tempo_waze_min is not None:
        tempo_desloc = d.tempo_waze_min
    elif cfg:
        vel = Decimal(str(cfg.get("tempo.velocidade_media_km_h", 40)))
        tempo_desloc = (Decimal(str(ent.distancia_km)) / vel) * 60 if vel > 0 else Decimal("0")
    else:
        tempo_desloc = Decimal("0")
    tempo_total = tempo_proc + tempo_desloc
    lucro_hora = (lucro / (tempo_total / Decimal("60"))) if tempo_total > 0 else Decimal("0")
    margem_liquida = (lucro / receita * 100) if receita > 0 else Decimal("0")

    profit_rows = [
        ["", "Valor"],
        ["Receita (à vista Pix)", _fmt_brl(receita)],
        ["", ""],
        [" (-) Impostos", _fmt_brl_4(custo_impostos)],
        [" (-) Material + laboratório", _fmt_brl_4(custo_mat_lab)],
        [" (-) Combustível", _fmt_brl_4(custo_combustivel)],
        [" (-) Manutenção veículo", _fmt_brl_4(custo_manutencao)],
        [" (-) Custos fixos (rateio mensal)", _fmt_brl_4(custo_fixos)],
    ]
    if custo_estac > 0:
        profit_rows.append([" (-) Estacionamento", _fmt_brl_4(custo_estac)])
    profit_rows += [
        ["TOTAL CUSTOS REAIS", _fmt_brl(total_custos)],
        ["", ""],
        ["LUCRO LÍQUIDO", _fmt_brl(lucro)],
        [f"Margem líquida", f"{margem_liquida:.1f}%".replace(".", ",")],
        ["", ""],
        [f"Tempo procedimentos", f"{tempo_proc:.0f} min"],
        [f"Tempo deslocamento (est.)", f"~{tempo_desloc:.0f} min"],
        [f"Tempo total", f"~{tempo_total:.0f} min"],
        ["Lucro por hora trabalhada", f"{_fmt_brl(lucro_hora)}/h"],
    ]

    n_profit = len(profit_rows)
    p_tbl = Table(profit_rows, colWidths=[10 * cm, 6 * cm])

    # Encontrar índices das linhas especiais
    idx_receita = 1
    idx_total_custos = next(i for i, r in enumerate(profit_rows) if r[0] == "TOTAL CUSTOS REAIS")
    idx_lucro = next(i for i, r in enumerate(profit_rows) if r[0] == "LUCRO LÍQUIDO")
    idx_lucro_hora = n_profit - 1

    p_style = [
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        # Receita
        ("FONTNAME", (0, idx_receita), (-1, idx_receita), "Helvetica-Bold"),
        ("BACKGROUND", (0, idx_receita), (-1, idx_receita), colors.HexColor("#E0FFF9")),
        # Total custos
        ("FONTNAME", (0, idx_total_custos), (-1, idx_total_custos), "Helvetica-Bold"),
        ("LINEABOVE", (0, idx_total_custos), (-1, idx_total_custos), 1, BG_DARK),
        # Lucro
        ("BACKGROUND", (0, idx_lucro), (-1, idx_lucro), BG_DARK),
        ("TEXTCOLOR", (0, idx_lucro), (-1, idx_lucro), colors.white),
        ("FONTNAME", (0, idx_lucro), (-1, idx_lucro), "Helvetica-Bold"),
        ("FONTSIZE", (0, idx_lucro), (-1, idx_lucro), 12),
        # Lucro/hora
        ("FONTNAME", (0, idx_lucro_hora), (-1, idx_lucro_hora), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, idx_lucro_hora), (-1, idx_lucro_hora), ACCENT),
    ]
    p_tbl.setStyle(TableStyle(p_style))
    story.append(p_tbl)

    # ─────────── 4. CENÁRIOS DE PAGAMENTO ───────────
    story.append(Paragraph("Cenários de pagamento (maquineta)", section))
    cen_rows = [["Forma", "Total", "Parcelas"]]
    for c in resultado.cenarios:
        if c.parcela and c.parcelas > 1:
            if getattr(c, "parcela_ultima", None) is not None:
                parcelas = (
                    f"{c.parcelas - 1}x {_fmt_brl(c.parcela)} "
                    f"+ 1x {_fmt_brl(c.parcela_ultima)}"
                )
            else:
                parcelas = f"{c.parcelas}x {_fmt_brl(c.parcela)}"
        else:
            parcelas = "à vista"
        cen_rows.append([c.forma, _fmt_brl(c.total), parcelas])
    cen_tbl = Table(cen_rows, colWidths=[5.5 * cm, 5 * cm, 6 * cm])
    cen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(cen_tbl)

    # ─────────── 5. DESLOCAMENTO (detalhe técnico) ───────────
    if d:
        story.append(Paragraph("Deslocamento (detalhe)", section))
        def _cell(v: Decimal, km: Decimal) -> str:
            return _fmt_brl_4(v) if km > 0 else "—"

        desloc_rows = [
            ["", "Asfalto", "Terra", "Total"],
            ["Distância", f"{d.km_asfalto:.1f} km", f"{d.km_terra:.1f} km", f"{d.distancia_km:.1f} km"],
            ["Combustível", _cell(d.custo_combustivel_asfalto, d.km_asfalto), _cell(d.custo_combustivel_terra, d.km_terra), _fmt_brl_4(d.custo_combustivel_total)],
            ["Manutenção", _cell(d.custo_manutencao_asfalto, d.km_asfalto), _cell(d.custo_manutencao_terra, d.km_terra), _fmt_brl_4(d.custo_manutencao_total)],
            ["Custo tempo", _cell(d.custo_tempo_asfalto, d.km_asfalto), _cell(d.custo_tempo_terra, d.km_terra), _fmt_brl_4(d.custo_tempo)],
            ["Custo real (trecho)", _cell(d.custo_real_asfalto, d.km_asfalto), _cell(d.custo_real_terra, d.km_terra), _fmt_brl_4(d.custo_real)],
            [f"+ Margem ({_fmt_pct(d.margem_lucro)})", "", "", _fmt_brl_4(d.taxa_apos_margem_sem_nobre - d.custo_real)],
        ]
        if d.bairro_nobre:
            desloc_rows.append([
                f"+ Bairro nobre ({_fmt_pct(d.acrescimo_bairro_nobre_percent)})",
                "", "",
                _fmt_brl_4(d.taxa_ao_paciente - d.taxa_apos_margem_sem_nobre),
            ])
        desloc_rows.append(["Taxa ao paciente", "", "", _fmt_brl(d.taxa_ao_paciente)])

        n_desloc = len(desloc_rows)
        dt = Table(desloc_rows, colWidths=[4.5 * cm, 4 * cm, 4 * cm, 4 * cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#F4F7FB")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            # Última linha destacada
            ("FONTNAME", (0, n_desloc - 1), (-1, n_desloc - 1), "Helvetica-Bold"),
            ("LINEABOVE", (0, n_desloc - 1), (-1, n_desloc - 1), 1, BG_DARK),
        ]))
        story.append(dt)

    def _draw_version_footer(canvas, doc):
        if not PDF_VERSION:
            return
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_MUTED)
        left_x = doc.leftMargin
        right_x = doc.pagesize[0] - doc.rightMargin
        footer_y = 12
        canvas.drawString(left_x, footer_y, PDF_VERSION)
        canvas.drawRightString(right_x, footer_y, PDF_VERSION)
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_version_footer, onLaterPages=_draw_version_footer)
    return output_path
