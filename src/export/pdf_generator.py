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


def _fmt_brl_preciso(v: Decimal | float | int | str) -> str:
    d = Decimal(str(v)).normalize()
    s = format(d, "f").replace(".", ",")
    return f"R$ {s}"


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
    """PDF interno (dentista): decomposição completa e auditoria de deslocamento.

    Este PDF não é pensado para o paciente — é um log técnico do cálculo.
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
        textColor=ACCENT, spaceBefore=10, spaceAfter=6,
    )
    mono = ParagraphStyle(
        "mono", parent=styles["Normal"],
        fontName="Courier", fontSize=9,
        textColor=colors.black, leading=11,
    )

    hoje = datetime.now()
    numero_str = f"#{numero_orcamento:05d}" if numero_orcamento else "—"

    story.append(Paragraph("Log interno de precificação", h1))
    story.append(Paragraph(f"{numero_str} · {hoje.strftime('%d/%m/%Y %H:%M')}", sub))
    story.append(Paragraph(f"<b>Cliente:</b> {cliente_nome}", mono))
    ent = resultado.entrada
    story.append(Paragraph(
        f"<b>Asfalto (ida+volta):</b> {ent.km_asfalto:.2f} km · <b>Terra (ida+volta):</b> {ent.km_terra:.2f} km · "
        f"<b>Total:</b> {ent.distancia_km:.2f} km",
        mono,
    ))
    story.append(Paragraph(f"<b>Bairro nobre:</b> {'sim' if ent.bairro_nobre else 'não'}", mono))
    est_txt = (
        "gratuito"
        if getattr(ent, "estacionamento_gratuito", True)
        else f"pago — {resultado.tempo_procedimentos_min:.0f} min × tarifa (≈ {_fmt_brl(resultado.custo_estacionamento)})"
    )
    story.append(Paragraph(f"<b>Estacionamento:</b> {est_txt}", mono))
    story.append(Paragraph(f"<b>NEE:</b> {'sim' if resultado.entrada.is_nee else 'não'}", mono))
    story.append(Paragraph(
        f"<b>Regime aplicado:</b> {resultado.regime_aplicado.value} · <b>Alíquota:</b> {(resultado.aliquota_aplicada * 100):.2f}%".replace(".", ","),
        mono,
    ))
    story.append(Spacer(1, 8))

    # Procedimentos (com valores atuais)
    story.append(Paragraph("Procedimentos (inputs)", section))
    procs_map = ProcedimentoRepo.por_ids([pid for pid, _ in resultado.entrada.procedimentos])
    proc_rows = [["ID", "Procedimento", "Qtd.", "Valor atual (R$)", "Tempo (min)", "Mat.", "Lab", "Hora override"]]
    for pid, qtd in resultado.entrada.procedimentos:
        p = procs_map.get(pid)
        if not p:
            proc_rows.append([str(pid), f"Procedimento #{pid}", str(qtd), "—", "—", "—", "—", "—"])
            continue
        proc_rows.append([
            str(p.id),
            p.nome,
            str(qtd),
            _fmt_brl(p.valor_atual),
            str(int(p.tempo_estimado_min)),
            _fmt_brl(p.custo_material),
            _fmt_brl(p.custo_laboratorio),
            _fmt_brl(p.valor_hora_clinica_override) if p.valor_hora_clinica_override else "global",
        ])

    tbl = Table(proc_rows, colWidths=[1.0 * cm, 7.2 * cm, 1.3 * cm, 2.6 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 2.1 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tbl)

    # Deslocamento detalhado
    story.append(Paragraph("Deslocamento (auditoria)", section))
    if cfg is not None:
        d = calc_deslocamento.calcular_composto(
            resultado.entrada.km_asfalto,
            resultado.entrada.km_terra,
            resultado.entrada.bairro_nobre,
            resultado.entrada.tempo_waze_min,
            cfg,
        )
        rows = [
            ["Item", "Detalhe", "Valor"],
            ["Combustível (R$/km)", "preço/L ÷ km/L", _fmt_brl_preciso(d.custo_combustivel_km)],
            ["Manutenção base (R$/km)", "config veículo", _fmt_brl_preciso(d.custo_manutencao_km_base)],
            ["Tempo asfalto (R$/km)", "hora ÷ vel asfalto", _fmt_brl_preciso(d.custo_tempo_km_asfalto)],
            ["Tempo terra (R$/km)", "hora ÷ vel terra", _fmt_brl_preciso(d.custo_tempo_km_terra)],
            [
                "Tempo Waze (min)",
                "input (opcional)",
                f"{d.tempo_waze_min:.0f}".replace(".", ",") if d.tempo_waze_min is not None else "—",
            ],
            ["Km asfalto", "input", f"{d.km_asfalto:.6f}".replace(".", ",")],
            ["Km terra", "input", f"{d.km_terra:.6f}".replace(".", ",")],
            ["Custo real — asfalto", "trecho", _fmt_brl_preciso(d.custo_real_asfalto)],
            ["Custo real — terra", "trecho (manut. × fator)", _fmt_brl_preciso(d.custo_real_terra)],
            ["Combustível total", "soma trechos", _fmt_brl_preciso(d.custo_combustivel_total)],
            ["Manutenção total", "soma trechos", _fmt_brl_preciso(d.custo_manutencao_total)],
            ["Veículo total", "comb+manut", _fmt_brl_preciso(d.custo_veiculo)],
            ["Tempo total", "soma trechos / Waze", _fmt_brl_preciso(d.custo_tempo)],
            ["Custo real", "veículo + tempo", _fmt_brl_preciso(d.custo_real)],
            ["Margem deslocamento", "config", f"{(d.margem_lucro * 100):.4f}%".replace(".", ",")],
            ["Taxa após margem", "custo_real × (1+margem)", _fmt_brl_preciso(d.taxa_apos_margem_sem_nobre)],
            ["Bairro nobre", "acréscimo config" if d.bairro_nobre else "—", f"{(d.acrescimo_bairro_nobre_percent * 100):.4f}%".replace(".", ",") if d.bairro_nobre else "—"],
            ["Taxa ao paciente (final)", "após margem (+ nobre se aplicável)", _fmt_brl_preciso(d.taxa_ao_paciente)],
        ]
        dt = Table(rows, colWidths=[5.3 * cm, 7.2 * cm, 4.0 * cm])
        dt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(dt)
        story.append(Spacer(1, 6))
    else:
        story.append(Paragraph(
            f"Total cobrado de deslocamento (com margem): <b>{_fmt_brl_preciso(resultado.custo_deslocamento)}</b>",
            mono,
        ))

    # Resumo da decomposição
    story.append(Paragraph("Decomposição (totais)", section))
    decomp = [
        ["Componente", "Valor"],
        ["Procedimentos (com acréscimo domiciliar/NEE)", _fmt_brl_preciso(resultado.custo_procedimentos)],
        ["Hora clínica", _fmt_brl_preciso(resultado.custo_hora_clinica)],
        ["Materiais + laboratório", _fmt_brl_preciso(resultado.custo_materiais_lab)],
        ["Deslocamento (taxa ao paciente)", _fmt_brl_preciso(resultado.custo_deslocamento)],
        ["Estacionamento (tempo proced. × R$/h)", _fmt_brl_preciso(resultado.custo_estacionamento)],
        ["Custos fixos rateados", _fmt_brl_preciso(resultado.custo_fixos_rateado)],
        ["Margem retrabalho", _fmt_brl_preciso(resultado.margem_retrabalho)],
        ["Impostos (fórmula inversa)", _fmt_brl_preciso(resultado.valor_impostos)],
        ["Subtotal à vista (base p/ maquineta)", _fmt_brl_preciso(resultado.subtotal_a_vista)],
    ]
    d_tbl = Table(decomp, colWidths=[10 * cm, 6 * cm])
    d_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FB")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9E2EF")),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(d_tbl)

    # Cenários
    story.append(Paragraph("Cenários (maquineta)", section))
    cen_rows = [["Forma", "Total", "Parcelas"]]
    for c in resultado.cenarios:
        if c.parcela and c.parcelas > 1:
            if getattr(c, "parcela_ultima", None) is not None:
                parcelas = (
                    f"{c.parcelas - 1}× {_fmt_brl_preciso(c.parcela)} "
                    f"+ 1× {_fmt_brl_preciso(c.parcela_ultima)}"
                )
            else:
                parcelas = f"{c.parcelas}× {_fmt_brl_preciso(c.parcela)}"
        else:
            parcelas = "à vista"
        cen_rows.append([c.forma, _fmt_brl_preciso(c.total), parcelas])
    cen_tbl = Table(cen_rows, colWidths=[6 * cm, 5 * cm, 5 * cm])
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
