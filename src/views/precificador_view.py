"""Tela principal — o 'precificador de 10 segundos'."""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import json
import customtkinter as ctk
from PIL import Image

from ..calc.precificador import precificar
from ..db.repositories import HistoricoRepo, ProcedimentoRepo, ZonasRepo
from ..models.config import ConfigStore
from ..models.orcamento import EntradaPrecificacao, Regime, ResultadoPrecificacao
from ..models.procedimento import Procedimento
from ..theme import COLORS, FONTS, fmt_brl, fmt_pct
from ..widgets.procedimento_picker import ProcedimentoPicker

from ..paths import get_bundle_dir

ASSETS = get_bundle_dir() / "assets"


class PrecificadorView(ctk.CTkFrame):
    """Tela única — procedimento(s) + km → 4 cenários de pagamento."""

    def __init__(
        self,
        master,
        cfg: ConfigStore,
        on_open_config: Callable[[], None],
        on_export_pdf: Callable[[ResultadoPrecificacao, str, int], tuple[Path, Path]],
    ):
        super().__init__(master, fg_color=COLORS["bg_primary"])
        self.cfg = cfg
        self._on_open_config = on_open_config
        self._on_export_pdf = on_export_pdf
        self._selected: list[tuple[Procedimento, int]] = []
        self._last_resultado: ResultadoPrecificacao | None = None
        self._last_historico_id: int | None = None
        self._last_cliente_nome: str | None = None
        self._pdf_groups: list[dict[str, str | float | list[dict[str, str]]]] = []
        self._selected_pdf_group_ids: set[int] = set()
        self._pdf_page: int = 1
        self._pdf_page_size: int = 10
        self._pdf_page_size_options: list[int] = [10, 20, 50]
        self._pdf_total_groups: int = 0

        self._build()

    # ─────────────────────────── Layout ───────────────────────────
    def _build(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], height=72, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        try:
            logo_img = ctk.CTkImage(
                light_image=Image.open(ASSETS / "logo_basis.png"),
                dark_image=Image.open(ASSETS / "logo_basis.png"),
                size=(120, 40),
            )
            ctk.CTkLabel(header, image=logo_img, text="").pack(side="left", padx=20, pady=16)
        except Exception:
            ctk.CTkLabel(header, text="BASIS", font=FONTS["title"], text_color=COLORS["accent"]).pack(side="left", padx=20)

        ctk.CTkLabel(
            header,
            text="Precificador",
            font=FONTS["subtitle"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=(0, 20))

        ctk.CTkButton(
            header,
            text="⚙",
            width=44,
            height=44,
            font=("Segoe UI", 20),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_hover"],
            corner_radius=22,
            command=self._on_open_config,
        ).pack(side="right", padx=20, pady=14)

        # Corpo: 2 colunas (entrada à esquerda, resultado à direita)
        body = ctk.CTkFrame(self, fg_color=COLORS["bg_primary"])
        body.pack(fill="both", expand=True, padx=24, pady=24)
        body.grid_columnconfigure(0, weight=1, uniform="col")
        body.grid_columnconfigure(1, weight=1, uniform="col")
        body.grid_rowconfigure(0, weight=1)

        self._build_input_panel(body)
        self._build_result_panel(body)

    def _build_input_panel(self, parent) -> None:
        panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=12)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            inner, text="Procedimentos", font=FONTS["heading"], text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 8))

        # Picker
        procs = ProcedimentoRepo.listar()
        self.picker = ProcedimentoPicker(inner, procs, on_pick=self._add_procedimento)
        self.picker.pack(fill="x", pady=(0, 12))

        # Lista de selecionados
        ctk.CTkLabel(
            inner, text="Selecionados:", font=FONTS["small"], text_color=COLORS["text_secondary"]
        ).pack(anchor="w")
        self.selected_frame = ctk.CTkFrame(inner, fg_color=COLORS["bg_card"], corner_radius=8)
        self.selected_frame.pack(fill="x", pady=(4, 16))
        self._render_selected()

        # Distância (asfalto + terra, ida + volta)
        ctk.CTkLabel(
            inner, text="Deslocamento (ida + volta)", font=FONTS["heading"], text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))

        dist_row = ctk.CTkFrame(inner, fg_color="transparent")
        dist_row.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(dist_row, text="Asfalto", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
        self.km_asfalto_entry = ctk.CTkEntry(
            dist_row,
            placeholder_text="km",
            font=FONTS["body"],
            height=36,
            width=88,
            border_color=COLORS["gold"],
            border_width=2,
            fg_color=COLORS["input_bg"],
        )
        self.km_asfalto_entry.pack(side="left", padx=(8, 16))

        ctk.CTkLabel(dist_row, text="Estrada de terra", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
        self.km_terra_entry = ctk.CTkEntry(
            dist_row,
            placeholder_text="km",
            font=FONTS["body"],
            height=36,
            width=88,
            border_color=COLORS["gold"],
            border_width=2,
            fg_color=COLORS["input_bg"],
        )
        self.km_terra_entry.pack(side="left", padx=8)
        ctk.CTkLabel(dist_row, text="km", font=FONTS["small"], text_color=COLORS["text_muted"]).pack(side="left")

        self.dist_total_label = ctk.CTkLabel(
            inner, text="Total: 0 km", font=FONTS["small"], text_color=COLORS["text_muted"]
        )
        self.dist_total_label.pack(anchor="w", pady=(0, 4))

        def _update_total_label(*_):
            try:
                a = float(self.km_asfalto_entry.get().replace(",", ".") or 0)
                t = float(self.km_terra_entry.get().replace(",", ".") or 0)
                self.dist_total_label.configure(text=f"Total: {a + t:.1f} km (ida + volta)")
            except ValueError:
                self.dist_total_label.configure(text="Total: —")

        self.km_asfalto_entry.bind("<KeyRelease>", _update_total_label)
        self.km_terra_entry.bind("<KeyRelease>", _update_total_label)

        # Tempo Waze (opcional; quando preenchido, manda no custo de tempo do deslocamento)
        waze_row = ctk.CTkFrame(inner, fg_color="transparent")
        waze_row.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(
            waze_row, text="Tempo (Waze)", font=FONTS["small"], text_color=COLORS["text_secondary"]
        ).pack(side="left")
        self.tempo_waze_entry = ctk.CTkEntry(
            waze_row,
            placeholder_text="min (ida+volta)",
            font=FONTS["body"],
            height=36,
            width=140,
            border_color=COLORS["gold"],
            border_width=2,
            fg_color=COLORS["input_bg"],
        )
        self.tempo_waze_entry.pack(side="left", padx=8)
        ctk.CTkLabel(
            waze_row,
            text="(opcional — se vazio usa velocidade média)",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(side="left", padx=8)

        # Atalhos de zonas
        zonas = ZonasRepo.listar()
        zona_row = ctk.CTkFrame(inner, fg_color="transparent")
        zona_row.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(
            zona_row, text="📍 atalhos:", font=FONTS["small"], text_color=COLORS["text_muted"]
        ).pack(side="left")
        for z in zonas:
            ctk.CTkButton(
                zona_row,
                text=f"{z['nome'].split(' — ')[0]} ({int(z['distancia_ida_volta_km'])})",
                font=FONTS["small"],
                fg_color=COLORS["bg_card"],
                hover_color=COLORS["accent_hover"],
                text_color=COLORS["text_secondary"],
                height=24,
                corner_radius=12,
                width=10,
                command=lambda km=z["distancia_ida_volta_km"]: self._set_distancia(km),
            ).pack(side="left", padx=2)

        self.bairro_nobre_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner,
            text="Bairro nobre (acréscimo sobre o deslocamento — config)",
            variable=self.bairro_nobre_var,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        ).pack(anchor="w", pady=(0, 12))

        # Estacionamento: gratuito vs pago (pago = tempo dos procedimentos × R$/h)
        ctk.CTkLabel(
            inner, text="Estacionamento", font=FONTS["heading"], text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))
        est_row = ctk.CTkFrame(inner, fg_color="transparent")
        est_row.pack(fill="x", pady=(0, 4))
        self.estacionamento_gratuito_var = ctk.BooleanVar(value=True)

        def _toggle_estacionamento_pago():
            pago = not self.estacionamento_gratuito_var.get()
            self._btn_est_gr.configure(fg_color=COLORS["accent"] if not pago else COLORS["bg_card"])
            self._btn_est_pg.configure(fg_color=COLORS["accent"] if pago else COLORS["bg_card"])
            self.estacionamento_tarifa_entry.configure(state="normal" if pago else "disabled")
            self._update_estacionamento_preview()

        self._btn_est_gr = ctk.CTkButton(
            est_row,
            text="Gratuito",
            width=100,
            height=32,
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: (self.estacionamento_gratuito_var.set(True), _toggle_estacionamento_pago()),
        )
        self._btn_est_gr.pack(side="left", padx=(0, 8))
        self._btn_est_pg = ctk.CTkButton(
            est_row,
            text="Pago",
            width=100,
            height=32,
            font=FONTS["body"],
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_hover"],
            command=lambda: (self.estacionamento_gratuito_var.set(False), _toggle_estacionamento_pago()),
        )
        self._btn_est_pg.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(est_row, text="Tarifa R$/h", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
        tarifa_default = self.cfg.get("estacionamento.tarifa_hora_padrao", 8.0)
        self.estacionamento_tarifa_entry = ctk.CTkEntry(
            est_row,
            width=88,
            height=32,
            font=FONTS["mono"],
            fg_color=COLORS["input_bg"],
            border_color=COLORS["gold"],
            border_width=2,
            state="disabled",
        )
        self.estacionamento_tarifa_entry.insert(0, str(tarifa_default).replace(".", ","))
        self.estacionamento_tarifa_entry.pack(side="left", padx=8)
        self.estacionamento_tarifa_entry.bind("<KeyRelease>", lambda e: self._update_estacionamento_preview())

        self.estacionamento_preview_label = ctk.CTkLabel(
            inner,
            text="",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
            anchor="w",
        )
        self.estacionamento_preview_label.pack(anchor="w", pady=(0, 16))
        _toggle_estacionamento_pago()
        self._update_estacionamento_preview()

        # NEE
        self.nee_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner,
            text="NEE — Necessidades Especiais (+25%)",
            variable=self.nee_var,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
        ).pack(anchor="w", pady=(0, 16))

        # Regime tributário com % visível
        ctk.CTkLabel(
            inner, text="Regime tributário", font=FONTS["heading"], text_color=COLORS["text_primary"]
        ).pack(anchor="w")

        # Regime é escolhido por orçamento (sem default global)
        self.regime_var = ctk.StringVar(value="PF")

        # Mostra o % atual do regime escolhido
        def update_regime_label(*args):
            regime = self.regime_var.get()
            aliquota = self.cfg.get(f"impostos.aliquota_{regime.lower()}" if regime != "DEFAULT" else "impostos.aliquota_pf", 0.0)
            label.configure(text=f"{regime} • {fmt_pct(aliquota)}")

        label = ctk.CTkLabel(inner, text="", font=FONTS["small"], text_color=COLORS["success"])
        label.pack(anchor="w", pady=(0, 4))

        self.regime_var.trace("w", update_regime_label)

        ctk.CTkOptionMenu(
            inner,
            values=["PF", "MEI", "SIMPLES", "DEFAULT"],
            variable=self.regime_var,
            font=FONTS["body"],
            fg_color=COLORS["input_bg"],
        ).pack(anchor="w", pady=(0, 16))

        update_regime_label()  # atualiza na primeira vez

        # Botão Calcular
        ctk.CTkButton(
            inner,
            text="CALCULAR",
            font=FONTS["subtitle"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg_primary"],
            height=52,
            corner_radius=12,
            command=self._on_calcular,
        ).pack(fill="x", pady=(8, 0))

    def _build_result_panel(self, parent) -> None:
        self.result_panel = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=12)
        self.result_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        self.result_inner = ctk.CTkFrame(self.result_panel, fg_color="transparent")
        self.result_inner.pack(fill="both", expand=True, padx=24, pady=24)

        self.pdf_list_items = ctk.CTkFrame(self.result_inner, fg_color="transparent")
        self.pdf_list_items.pack(fill="both", expand=True)

        self._load_pdf_history()
        self._render_empty_result()

    # ─────────────────────────── State ───────────────────────────
    def _add_procedimento(self, proc: Procedimento) -> None:
        # Se já está, incrementa qty
        for i, (p, qtd) in enumerate(self._selected):
            if p.id == proc.id:
                self._selected[i] = (p, qtd + 1)
                self._render_selected()
                return
        self._selected.append((proc, 1))
        self._render_selected()

    def _remove_procedimento(self, idx: int) -> None:
        self._selected.pop(idx)
        self._render_selected()

    def _change_qty(self, idx: int, delta: int) -> None:
        proc, qtd = self._selected[idx]
        new_qtd = qtd + delta
        if new_qtd <= 0:
            self._remove_procedimento(idx)
        else:
            self._selected[idx] = (proc, new_qtd)
            self._render_selected()

    def _tempo_total_procedimentos_min(self) -> float:
        return float(sum(p.tempo_estimado_min * q for p, q in self._selected))

    def _update_estacionamento_preview(self) -> None:
        if not hasattr(self, "estacionamento_preview_label"):
            return
        tmin = self._tempo_total_procedimentos_min()
        if self.estacionamento_gratuito_var.get():
            self.estacionamento_preview_label.configure(
                text=f"Tempo estimado dos procedimentos: {tmin:.0f} min (estacionamento gratuito)"
            )
            return
        try:
            tarifa = Decimal(self.estacionamento_tarifa_entry.get().replace(",", ".").replace("R$", "").strip() or "0")
        except Exception:
            self.estacionamento_preview_label.configure(
                text=f"Tempo: {tmin:.0f} min — tarifa inválida"
            )
            return
        valor = (Decimal(str(tmin)) / Decimal("60")) * tarifa
        self.estacionamento_preview_label.configure(
            text=f"Tempo: {tmin:.0f} min × {fmt_brl(tarifa)}/h ≈ {fmt_brl(valor)} de estacionamento"
        )

    def _set_distancia(self, km: float) -> None:
        """Atalho de zona: preenche todo o trecho como asfalto (ajuste terra depois se precisar)."""
        self.km_asfalto_entry.delete(0, "end")
        self.km_asfalto_entry.insert(0, str(int(km) if km == int(km) else km))
        self.km_terra_entry.delete(0, "end")
        self.km_terra_entry.insert(0, "0")
        try:
            a = float(self.km_asfalto_entry.get().replace(",", "."))
            t = float(self.km_terra_entry.get().replace(",", ".") or 0)
            self.dist_total_label.configure(text=f"Total: {a + t:.1f} km (ida + volta)")
        except ValueError:
            pass

    def _render_selected(self) -> None:
        for w in self.selected_frame.winfo_children():
            w.destroy()

        if not self._selected:
            ctk.CTkLabel(
                self.selected_frame,
                text="DEFAULT procedimento selecionado",
                font=FONTS["small"],
                text_color=COLORS["text_muted"],
            ).pack(pady=10)
            self._update_estacionamento_preview()
            return

        for idx, (proc, qtd) in enumerate(self._selected):
            row = ctk.CTkFrame(self.selected_frame, fg_color="transparent")
            row.pack(fill="x", padx=8, pady=4)

            ctk.CTkLabel(
                row, text=proc.nome, font=FONTS["body"], text_color=COLORS["text_primary"], anchor="w"
            ).pack(side="left", fill="x", expand=True)

            ctk.CTkButton(
                row, text="−", width=24, height=24, font=FONTS["body_bold"],
                fg_color=COLORS["bg_secondary"], hover_color=COLORS["accent_hover"],
                command=lambda i=idx: self._change_qty(i, -1),
            ).pack(side="left", padx=2)

            ctk.CTkLabel(
                row, text=str(qtd), font=FONTS["body_bold"], text_color=COLORS["accent"], width=20
            ).pack(side="left")

            ctk.CTkButton(
                row, text="+", width=24, height=24, font=FONTS["body_bold"],
                fg_color=COLORS["bg_secondary"], hover_color=COLORS["accent_hover"],
                command=lambda i=idx: self._change_qty(i, 1),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                row, text="×", width=24, height=24, font=FONTS["body_bold"],
                fg_color=COLORS["bg_secondary"], hover_color=COLORS["accent_warm"],
                text_color=COLORS["text_primary"],
                command=lambda i=idx: self._remove_procedimento(i),
            ).pack(side="left", padx=2)

        self._update_estacionamento_preview()

    def _render_empty_result(self) -> None:
        for w in self.result_inner.winfo_children():
            if w is not self.pdf_list_items:
                w.destroy()
        if not self._pdf_groups:
            ctk.CTkLabel(
                self.result_inner,
                text="Nenhum relatório gerado ainda.",
                font=FONTS["subtitle"],
                text_color=COLORS["text_secondary"],
                anchor="center",
            ).pack(fill="x", pady=(40, 4))
            ctk.CTkLabel(
                self.result_inner,
                text=(
                    "Clique em GERAR PDF para adicionar o orçamento à Lista de Precificação."
                ),
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                justify="center",
                wraplength=320,
            ).pack(padx=24)
        self._render_pdf_list()

    # ─────────────────────────── Calcular ───────────────────────────
    def _on_calcular(self) -> None:
        if not self._selected:
            self._show_error("Adicione pelo menos um procedimento")
            return
        try:
            km_asf = float(self.km_asfalto_entry.get().replace(",", ".") or 0)
            km_ter = float(self.km_terra_entry.get().replace(",", ".") or 0)
        except ValueError:
            self._show_error("Km de asfalto e terra inválidos")
            return
        tempo_waze_min = None
        try:
            tw = (self.tempo_waze_entry.get() or "").strip()
            if tw:
                tempo_waze_min = float(tw.replace(",", "."))
        except ValueError:
            self._show_error("Tempo (Waze) inválido")
            return
        if km_asf < 0 or km_ter < 0:
            self._show_error("Km não pode ser negativo")
            return
        if km_asf + km_ter <= 0:
            self._show_error("Informe km de asfalto e/ou estrada de terra (ida+volta)")
            return
        if not self.estacionamento_gratuito_var.get():
            try:
                Decimal(self.estacionamento_tarifa_entry.get().replace(",", ".").replace("R$", "").strip() or "0")
            except Exception:
                self._show_error("Tarifa de estacionamento (R$/h) inválida")
                return

        # Pedir cliente antes de mostrar resultado
        self._prompt_cliente(km_asf, km_ter, tempo_waze_min)

    def _prompt_cliente(self, km_asfalto: float, km_terra: float, tempo_waze_min: float | None) -> None:
        dialog = ctk.CTkInputDialog(
            title="Cliente",
            text="Nome do cliente / paciente:",
        )
        cliente = dialog.get_input()
        if not cliente or not cliente.strip():
            return
        cliente = cliente.strip()

        tarifa_est = None
        if not self.estacionamento_gratuito_var.get():
            try:
                tarifa_est = Decimal(
                    self.estacionamento_tarifa_entry.get().replace(",", ".").replace("R$", "").strip() or "0"
                )
            except Exception:
                tarifa_est = None

        entrada = EntradaPrecificacao(
            procedimentos=[(p.id, q) for p, q in self._selected],
            km_asfalto=km_asfalto,
            km_terra=km_terra,
            tempo_waze_min=tempo_waze_min,
            bairro_nobre=self.bairro_nobre_var.get(),
            estacionamento_gratuito=self.estacionamento_gratuito_var.get(),
            estacionamento_tarifa_hora=tarifa_est,
            is_nee=self.nee_var.get(),
            regime_override=Regime(self.regime_var.get()),
        )
        try:
            res = precificar(entrada, self.cfg)
        except Exception as e:
            self._show_error(f"Erro ao calcular: {e}")
            return

        # Salva no histórico imediatamente
        payload = self._build_payload(res)
        hist_id = HistoricoRepo.salvar(
            cliente_nome=cliente,
            cliente_observacao=None,
            distancia_km=entrada.distancia_km,
            is_nee=entrada.is_nee,
            regime_aplicado=res.regime_aplicado.value,
            aliquota_aplicada=res.aliquota_aplicada,
            total_a_vista=res.cenarios[0].total,
            total_cartao_7x=res.cenarios[1].total,
            total_cartao_10x=res.cenarios[2].total,
            total_cartao_12x=res.cenarios[3].total,
            payload=payload,
        )
        self._last_resultado = res
        self._last_historico_id = hist_id
        self._last_cliente_nome = cliente
        self._render_resultado(res, cliente)

    def _build_payload(self, res: ResultadoPrecificacao) -> dict:
        return {
            "procedimentos": [
                {"id": p.id, "nome": p.nome, "qtd": q, "valor_atual": p.valor_atual}
                for p, q in self._selected
            ],
            "distancia_km": res.entrada.distancia_km,
            "km_asfalto": res.entrada.km_asfalto,
            "km_terra": res.entrada.km_terra,
            "tempo_waze_min": res.entrada.tempo_waze_min,
            "bairro_nobre": res.entrada.bairro_nobre,
            "estacionamento_gratuito": res.entrada.estacionamento_gratuito,
            "estacionamento_tarifa_hora": res.entrada.estacionamento_tarifa_hora,
            "is_nee": res.entrada.is_nee,
            "regime": res.regime_aplicado.value,
            "aliquota": res.aliquota_aplicada,
            "decomposicao": {
                "custo_procedimentos": res.custo_procedimentos,
                "custo_hora_clinica": res.custo_hora_clinica,
                "custo_materiais_lab": res.custo_materiais_lab,
                "custo_deslocamento": res.custo_deslocamento,
                "custo_estacionamento": res.custo_estacionamento,
                "tempo_procedimentos_min": res.tempo_procedimentos_min,
                "custo_fixos_rateado": res.custo_fixos_rateado,
                "margem_retrabalho": res.margem_retrabalho,
                "valor_impostos": res.valor_impostos,
                "subtotal_a_vista": res.subtotal_a_vista,
            },
            "cenarios": [
                {"forma": c.forma, "total": c.total, "parcela": c.parcela, "parcelas": c.parcelas}
                for c in res.cenarios
            ],
        }

    # ─────────────────────────── Resultado ───────────────────────────
    def _render_resultado(self, res: ResultadoPrecificacao, cliente: str) -> None:
        for w in self.result_inner.winfo_children():
            if w is not self.pdf_list_items:
                w.destroy()

        # Cabeçalho do resultado
        ctk.CTkLabel(
            self.result_inner,
            text=f"Orçamento — {cliente}",
            font=FONTS["heading"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        # === MOSTRA O REGIME + % (o que você pediu) ===
        regime_nome = {
            "PF": "PF – Carnê-leão",
            "MEI": "MEI – Microempreendedor Individual",
            "SIMPLES": "Simples Nacional",
            "DEFAULT": "Sem impostos"
        }.get(res.regime_aplicado.value, res.regime_aplicado.value)

        aliquota_txt = fmt_pct(res.aliquota_aplicada)

        ctk.CTkLabel(
            self.result_inner,
            text=f"Impostos: {regime_nome} • {aliquota_txt}",
            font=FONTS["body_bold"],
            text_color=COLORS["success"],
            anchor="w",
        ).pack(fill="x", pady=(0, 16))

        # Cenários de pagamento
        for i, c in enumerate(res.cenarios):
            self._render_cenario(c, destaque=(i == 0))

        # Botão Gerar PDF
        ctk.CTkButton(
            self.result_inner,
            text="📄 GERAR PDF",
            font=FONTS["subtitle"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg_primary"],
            height=52,
            corner_radius=12,
            command=self._on_gerar_pdf,
        ).pack(fill="x", pady=(20, 0))
        self._render_pdf_list()
    
    def _render_cenario(self, cenario, destaque: bool) -> None:
        card = ctk.CTkFrame(
            self.result_inner,
            fg_color=COLORS["accent"] if destaque else COLORS["bg_card"],
            corner_radius=10,
            height=64,
        )
        card.pack(fill="x", pady=4)
        card.pack_propagate(False)

        text_color = COLORS["bg_primary"] if destaque else COLORS["text_primary"]
        sub_color = COLORS["bg_primary"] if destaque else COLORS["text_secondary"]

        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="y", padx=16)
        ctk.CTkLabel(
            left, text=cenario.forma, font=FONTS["body_bold"], text_color=text_color
        ).pack(anchor="w", pady=(12, 0))
        if cenario.parcela:
            if getattr(cenario, "parcela_ultima", None) is not None:
                ctk.CTkLabel(
                    left,
                    text=(
                        f"{cenario.parcelas - 1}× de {fmt_brl(cenario.parcela)} "
                        f"+ 1× de {fmt_brl(cenario.parcela_ultima)}"
                    ),
                    font=FONTS["small"],
                    text_color=sub_color,
                ).pack(anchor="w")
            else:
                ctk.CTkLabel(
                    left,
                    text=f"{cenario.parcelas}× de {fmt_brl(cenario.parcela)}",
                    font=FONTS["small"],
                    text_color=sub_color,
                ).pack(anchor="w")

        ctk.CTkLabel(
            card,
            text=fmt_brl(cenario.total),
            font=FONTS["mono_lg"],
            text_color=text_color,
        ).pack(side="right", padx=20)

    def _on_gerar_pdf(self) -> None:
        if self._last_resultado is None or self._last_historico_id is None or not self._last_cliente_nome:
            return
        try:
            pdf_cliente, pdf_interno = self._on_export_pdf(
                self._last_resultado,
                self._last_cliente_nome,
                self._last_historico_id,
            )
            HistoricoRepo.atualizar_pdf_paths(
                self._last_historico_id,
                str(pdf_cliente),
                str(pdf_interno),
            )
            data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            self._load_pdf_history(1)
        except Exception as e:
            self._show_error(f"Erro no PDF: {e}")

    def _add_pdf_group(
        self,
        group_id: int,
        cliente_nome: str,
        data_hora: str,
        total: float,
        cliente_path: str | None,
        interno_path: str | None,
    ) -> None:
        paths: list[dict[str, str]] = []
        if cliente_path:
            paths.append({"label": "Cliente", "path": cliente_path})
        if interno_path:
            paths.append({"label": "Interno", "path": interno_path})
        if not paths:
            return

        self._pdf_groups.insert(0, {
            "id": group_id,
            "titulo": f"Orçamento — {cliente_nome}",
            "data_hora": data_hora,
            "total": total,
            "paths": paths,
        })

    def _load_pdf_history(self, page: int = 1) -> None:
        self._pdf_groups = []
        self._selected_pdf_group_ids.clear()
        self._pdf_page = max(1, page)
        self._pdf_total_groups = HistoricoRepo.contar_pdfs_gerados()
        offset = (self._pdf_page - 1) * self._pdf_page_size
        for record in HistoricoRepo.listar_pdfs_gerados(self._pdf_page_size, offset):
            data_hora = record.get("data_hora")
            total = record.get("total_a_vista", 0.0)
            cliente_path = record.get("pdf_cliente_path")
            interno_path = record.get("pdf_interno_path")
            self._add_pdf_group(
                record["id"],
                record.get("cliente_nome", "Cliente"),
                data_hora,
                total,
                cliente_path,
                interno_path,
            )
        self._render_pdf_list()

    def _render_pdf_list(self) -> None:
        for w in self.pdf_list_items.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self.pdf_list_items,
            text="Lista de Precificação",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        header_row = ctk.CTkFrame(self.pdf_list_items, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header_row,
            text=f"Mostrando {len(self._pdf_groups)} de {self._pdf_total_groups} relatórios gerados.",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        controls = ctk.CTkFrame(header_row, fg_color="transparent")
        controls.pack(side="right")

        ctk.CTkButton(
            controls,
            text="← Anteriores",
            width=120,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_hover"],
            state="disabled" if self._pdf_page <= 1 else "normal",
            command=lambda: self._change_pdf_page(-1),
        ).pack(side="left", padx=4)
        ctk.CTkLabel(
            controls,
            text=f"Página {self._pdf_page} / {max(1, (self._pdf_total_groups + self._pdf_page_size - 1) // self._pdf_page_size)}",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left", padx=4)
        page_size_menu = ctk.CTkOptionMenu(
            controls,
            values=[str(option) for option in self._pdf_page_size_options],
            command=lambda value: self._on_change_pdf_page_size(int(value)),
            width=100,
            fg_color=COLORS["bg_card"],
            button_color=COLORS["bg_card"],
            button_hover_color=COLORS["accent_hover"],
            text_color=COLORS["text_primary"],
            dropdown_text_color=COLORS["text_primary"],
            dropdown_fg_color=COLORS["bg_secondary"],
        )
        page_size_menu.set(str(self._pdf_page_size))
        page_size_menu.pack(side="left", padx=4)
        ctk.CTkButton(
            controls,
            text="Próximos →",
            width=120,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent_hover"],
            state="disabled" if self._pdf_page * self._pdf_page_size >= self._pdf_total_groups else "normal",
            command=lambda: self._change_pdf_page(1),
        ).pack(side="left", padx=4)

        action_row = ctk.CTkFrame(self.pdf_list_items, fg_color="transparent")
        action_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(
            action_row,
            text=f"{len(self._selected_pdf_group_ids)} selecionado(s)",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
        ).pack(side="left")
        ctk.CTkButton(
            action_row,
            text="Excluir selecionados",
            width=180,
            fg_color=COLORS["error"],
            hover_color=COLORS["bg_card"],
            state="normal" if self._selected_pdf_group_ids else "disabled",
            command=self._on_delete_selected,
        ).pack(side="right")

        if not self._pdf_groups:
            ctk.CTkLabel(
                self.pdf_list_items,
                text="Nenhum relatório gerado ainda.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                justify="center",
            ).pack(fill="x", pady=12)
            return

        for group in self._pdf_groups:
            row = ctk.CTkFrame(self.pdf_list_items, fg_color=COLORS["bg_secondary"], corner_radius=10)
            row.pack(fill="x", pady=6)

            left = ctk.CTkFrame(row, fg_color="transparent")
            left.pack(side="left", fill="both", expand=True, padx=(12, 8), pady=12)

            selected_var = ctk.BooleanVar(value=group["id"] in self._selected_pdf_group_ids)
            ctk.CTkCheckBox(
                left,
                text="",
                variable=selected_var,
                command=lambda gid=group["id"], var=selected_var: self._on_pdf_group_toggled(gid, var.get()),
            ).pack(side="left", padx=(0, 8), pady=2)

            info = ctk.CTkFrame(left, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True)
            ctk.CTkLabel(
                info,
                text=group["titulo"],
                font=FONTS["body_bold"],
                text_color=COLORS["text_primary"],
                anchor="w",
            ).pack(fill="x")
            ctk.CTkLabel(
                info,
                text=f"{group['data_hora']} · {fmt_brl(group['total'])}",
                font=FONTS["small"],
                text_color=COLORS["text_secondary"],
                anchor="w",
            ).pack(fill="x", pady=(4, 0))

            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=(0, 12), pady=12)
            for path_info in group["paths"]:
                ctk.CTkButton(
                    actions,
                    text=f"Abrir {path_info['label']}",
                    width=120,
                    fg_color=COLORS["accent"],
                    hover_color=COLORS["accent_hover"],
                    command=lambda p=path_info["path"]: self._open_pdf(p),
                ).pack(side="left", padx=4)

    def _on_pdf_group_toggled(self, group_id: int, selected: bool) -> None:
        if selected:
            self._selected_pdf_group_ids.add(group_id)
        else:
            self._selected_pdf_group_ids.discard(group_id)
        self._render_pdf_list()

    def _change_pdf_page(self, delta: int) -> None:
        new_page = self._pdf_page + delta
        max_page = max(1, (self._pdf_total_groups + self._pdf_page_size - 1) // self._pdf_page_size)
        if new_page < 1 or new_page > max_page:
            return
        self._load_pdf_history(new_page)

    def _on_change_pdf_page_size(self, page_size: int) -> None:
        if page_size not in self._pdf_page_size_options:
            return
        self._pdf_page_size = page_size
        self._load_pdf_history(1)

    def _on_delete_selected(self) -> None:
        if not self._selected_pdf_group_ids:
            return
        if not messagebox.askyesno(
            title="Excluir relatórios",
            message=(
                f"Deseja excluir {len(self._selected_pdf_group_ids)} grupo(s) de relatórios gerados?"
                " Isto também removerá o histórico e os arquivos PDF correspondentes."
            ),
        ):
            return

        selected_ids = set(self._selected_pdf_group_ids)
        for group_id in selected_ids:
            group = next((g for g in self._pdf_groups if g["id"] == group_id), None)
            if not group:
                continue
            for path_info in group["paths"]:
                try:
                    Path(path_info["path"]).unlink()
                except FileNotFoundError:
                    pass
                except Exception:
                    pass
            HistoricoRepo.excluir(group_id)
        self._selected_pdf_group_ids.clear()
        if self._pdf_page > 1 and self._pdf_page * self._pdf_page_size > HistoricoRepo.contar_pdfs_gerados():
            self._pdf_page = max(1, self._pdf_page - 1)
        self._load_pdf_history(self._pdf_page)

    def _open_pdf(self, path: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(path)
            elif os.name == "posix":
                opener = "open" if "darwin" in os.uname().sysname.lower() else "xdg-open"
                os.system(f'{opener} "{path}"')
        except Exception:
            self._show_error("Não foi possível abrir o PDF. Verifique se o arquivo existe.")

    def _show_error(self, msg: str) -> None:
        # Mensagem simples no topo do painel de resultado
        for w in self.result_inner.winfo_children():
            if w is not self.pdf_list_items:
                w.destroy()
        ctk.CTkLabel(
            self.result_inner, text="⚠️", font=("Segoe UI", 48), text_color=COLORS["warning"]
        ).pack(pady=(80, 12))
        ctk.CTkLabel(
            self.result_inner, text=msg, font=FONTS["body"],
            text_color=COLORS["error"], wraplength=300, justify="center",
        ).pack()
