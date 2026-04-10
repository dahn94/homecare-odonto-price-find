"""Picker de procedimentos com busca fuzzy ao vivo."""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk
from thefuzz import fuzz

from ..models.procedimento import Procedimento
from ..theme import COLORS, FONTS


class ProcedimentoPicker(ctk.CTkFrame):
    """Campo de busca + dropdown de resultados.

    Quando o usuário clica em um item, dispara `on_pick(proc)`.
    """

    def __init__(
        self,
        master,
        procedimentos: list[Procedimento],
        on_pick: Callable[[Procedimento], None],
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._procs = procedimentos
        self._on_pick = on_pick
        self._items: list[ctk.CTkButton] = []

        self.entry = ctk.CTkEntry(
            self,
            placeholder_text="🔍 Buscar procedimento...",
            font=FONTS["body"],
            height=42,
            border_color=COLORS["gold"],
            border_width=2,
            fg_color=COLORS["input_bg"],
        )
        self.entry.pack(fill="x", pady=(0, 8))
        self.entry.bind("<KeyRelease>", self._on_type)
        self.entry.bind("<Return>", self._pick_first)

        self.results_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            height=200,
            corner_radius=10,
        )
        self.results_frame.pack(fill="x")

        self._render([])

    def set_procedimentos(self, procs: list[Procedimento]) -> None:
        self._procs = procs

    def _on_type(self, _event=None) -> None:
        query = self.entry.get().strip()
        if not query:
            self._render([])
            return
        scored = [
            (fuzz.WRatio(query.lower(), p.nome.lower()), p)
            for p in self._procs
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [p for score, p in scored[:8] if score > 50]
        self._render(top)

    def _pick_first(self, _event=None) -> None:
        query = self.entry.get().strip()
        if not query:
            return
        scored = [(fuzz.WRatio(query.lower(), p.nome.lower()), p) for p in self._procs]
        scored.sort(key=lambda x: x[0], reverse=True)
        if scored and scored[0][0] > 50:
            self._pick(scored[0][1])

    def _render(self, results: list[Procedimento]) -> None:
        for w in self._items:
            w.destroy()
        self._items.clear()

        if not results:
            placeholder = ctk.CTkLabel(
                self.results_frame,
                text="Digite pra buscar entre os procedimentos cadastrados…",
                font=FONTS["small"],
                text_color=COLORS["text_muted"],
            )
            placeholder.pack(pady=12)
            self._items.append(placeholder)
            return

        for proc in results:
            btn = ctk.CTkButton(
                self.results_frame,
                text=f"  {proc.nome}\n  {proc.categoria} · R$ {proc.valor_atual:.2f}".replace(".", ","),
                anchor="w",
                font=FONTS["body"],
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_primary"],
                height=46,
                corner_radius=8,
                command=lambda p=proc: self._pick(p),
            )
            btn.pack(fill="x", padx=4, pady=2)
            self._items.append(btn)

    def _pick(self, proc: Procedimento) -> None:
        self._on_pick(proc)
        self.entry.delete(0, "end")
        self._render([])
