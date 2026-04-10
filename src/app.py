"""Classe principal da aplicação Basis Precificador."""
from __future__ import annotations
import customtkinter as ctk
from pathlib import Path
from datetime import datetime
import os

from .db.connection import close_connection
from .models.config import ConfigStore
from .views.precificador_view import PrecificadorView
from .views.config_view import ConfigView
from .export.pdf_generator import gerar_pdf_orcamento
from .models.orcamento import ResultadoPrecificacao


class BasisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Basis Precificador • Odontologia Domiciliar")
        self.geometry("1280x720")
        self.minsize(1100, 680)

        self.cfg = ConfigStore()

        # Referências para as views
        self.precificador_view: PrecificadorView | None = None
        self.config_window: ConfigView | None = None

        self._build_ui()

    def _build_ui(self):
        """Tela principal = Precificador (conforme spec)"""
        self.precificador_view = PrecificadorView(
            master=self,
            cfg=self.cfg,
            on_open_config=self._open_config,
            on_export_pdf=self._export_pdf,
        )
        self.precificador_view.pack(fill="both", expand=True)

    def _open_config(self):
        """Abre a tela de configurações em janela separada (modal)"""
        if self.config_window is None or not self.config_window.winfo_exists():
            self.config_window = ConfigView(self, self.cfg, on_close=self._close_config)
        else:
            self.config_window.lift()

    def _close_config(self):
        self.config_window = None

    def _export_pdf(
        self, resultado: ResultadoPrecificacao, cliente_nome: str, historico_id: int
    ):
        """Gera o PDF e abre automaticamente (Windows/macOS/Linux)"""
        output_dir = Path("orcamentos")
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in cliente_nome if c.isalnum() or c in " -_")[:50]
        output_path = output_dir / f"orcamento_{safe_name}_{timestamp}.pdf"

        pdf_path = gerar_pdf_orcamento(
            resultado=resultado,
            cliente_nome=cliente_nome,
            output_path=output_path,
            numero_orcamento=historico_id,
        )

        print(f"📄 PDF gerado: {pdf_path}")

        # Abre o PDF automaticamente
        if os.name == "nt":  # Windows
            os.startfile(pdf_path)
        elif os.name == "posix":
            os.system(f'open "{pdf_path}"' if "darwin" in os.uname().sysname.lower() else f'xdg-open "{pdf_path}"')

    def destroy(self):
        close_connection()
        super().destroy()
