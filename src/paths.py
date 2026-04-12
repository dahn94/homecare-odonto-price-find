"""Resolução de caminhos compatível com PyInstaller."""
from __future__ import annotations

import sys
from pathlib import Path


def _is_bundled() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Diretório onde os recursos empacotados foram extraídos (assets, seeds, schema)."""
    if _is_bundled():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def get_data_dir() -> Path:
    """Diretório gravável para dados do usuário (basis.db, PDFs).

    Quando empacotado, usa ~/.basis-precificador (garante escrita em qualquer plataforma).
    Em desenvolvimento, usa a raiz do projeto.
    """
    if _is_bundled():
        data = Path.home() / ".basis-precificador"
        data.mkdir(parents=True, exist_ok=True)
        return data
    return Path(__file__).resolve().parents[1]
