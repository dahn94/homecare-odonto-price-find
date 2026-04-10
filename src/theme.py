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


def fmt_brl(valor: float) -> str:
    """Formata valor em R$ no padrão brasileiro."""
    try:
        s = f"{valor:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"


def fmt_pct(valor: float) -> str:
    return f"{valor * 100:.2f}%".replace(".", ",")
