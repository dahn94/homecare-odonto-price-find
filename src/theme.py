"""Tema visual da aplicação Basis — paleta de cores, fontes e helpers."""

COLORS = {
    "bg_primary":     "#0F1B2D",
    "bg_secondary":   "#1A2B45",
    "bg_card":        "#223553",
    "accent":         "#00BFA6",
    "accent_hover":   "#00A68E",
    "accent_warm":    "#FF6B6B",
    "gold":           "#FFD700",
    "text_primary":   "#FFFFFF",
    "text_secondary": "#A0B4C8",
    "text_muted":     "#5A7A96",
    "border":         "#2A4060",
    "success":        "#4CAF50",
    "purple":         "#B388FF",
    "input_bg":       "#2A3F5F",
    "warning":        "#FFA726",
    "error":          "#EF5350",
}

FONTS = {
    "title":     ("Segoe UI", 22, "bold"),
    "subtitle":  ("Segoe UI", 16, "bold"),
    "heading":   ("Segoe UI", 13, "bold"),
    "body":      ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "small":     ("Segoe UI", 10),
    "mono":      ("Consolas", 13),
    "mono_lg":   ("Consolas", 18, "bold"),
}


from decimal import Decimal


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def fmt_brl(valor: Decimal | float | int | str) -> str:
    """Formata valor em R$ no padrão brasileiro."""
    try:
        d = _to_decimal(valor).quantize(Decimal("0.01"))
        s = f"{d:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"


def fmt_pct(valor: Decimal | float | int | str) -> str:
    try:
        d = _to_decimal(valor) * Decimal("100")
        s = f"{d:.2f}"
        return s.replace(".", ",") + "%"
    except Exception:
        return "0,00%"
