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

from datetime import datetime, timedelta
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
from ..models.orcamento import ResultadoPrecificacao

# Paleta (espelha src/theme.py adaptada pro PDF)
ACCENT = colors.HexColor("#00BFA6")
BG_DARK = colors.HexColor("#0F1B2D")
BG_CARD = colors.HexColor("#223553")
TEXT_MUTED = colors.HexColor("#5A7A96")
GOLD = colors.HexColor("#FFD700")

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
LOGO_PATH = ASSETS_DIR / "logo_basis.png"


def _fmt_brl(v: float) -> str:
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def gerar_pdf_orcamento(
    resultado: ResultadoPrecificacao,
    cliente_nome: str,
    output_path: str | Path,
    numero_orcamento: int | None = None,
    cliente_observacao: str | None = None,
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
    if resultado.entrada.distancia_km > 0:
        extras.append(f"Atendimento domiciliar — {resultado.entrada.distancia_km:.0f} km (ida e volta)")
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
    validade = hoje + timedelta(days=30)
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        f"<i>Orçamento válido até <b>{validade.strftime('%d/%m/%Y')}</b> (30 dias).</i>",
        sub,
    ))

    # ─────────── Rodapé ───────────
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "Basis Odontologia Domiciliar · Blumenau / SC<br/>"
        "Atendimento humanizado em domicílio para a região do Vale do Itajaí",
        footer_style,
    ))

    doc.build(story)
    return output_path
