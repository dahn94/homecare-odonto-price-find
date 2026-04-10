"""Tela principal — o 'precificador de 10 segundos'."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import customtkinter as ctk
from PIL import Image

from ..calc.precificador import precificar
from ..db.repositories import HistoricoRepo, ProcedimentoRepo, ZonasRepo
from ..models.config import ConfigStore
from ..models.orcamento import EntradaPrecificacao, Regime, ResultadoPrecificacao
from ..models.procedimento import Procedimento
from ..theme import COLORS, FONTS, fmt_brl, fmt_pct
from ..widgets.procedimento_picker import ProcedimentoPicker

ASSETS = Path(__file__).resolve().parents[2] / "assets"


class PrecificadorView(ctk.CTkFrame):
    """Tela única — procedimento(s) + km → 4 cenários de pagamento."""

    def __init__(
        self,
        master,
        cfg: ConfigStore,
        on_open_config: Callable[[], None],
        on_export_pdf: Callable[[ResultadoPrecificacao, str, int], None],
    ):
        super().__init__(master, fg_color=COLORS["bg_primary"])
        self.cfg = cfg
        self._on_open_config = on_open_config
        self._on_export_pdf = on_export_pdf
        self._selected: list[tuple[Procedimento, int]] = []
        self._last_resultado: ResultadoPrecificacao | None = None
        self._last_historico_id: int | None = None
        self._last_cliente_nome: str | None = None

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

        # Distância
        ctk.CTkLabel(
            inner, text="Distância (ida + volta)", font=FONTS["heading"], text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 4))

        dist_row = ctk.CTkFrame(inner, fg_color="transparent")
        dist_row.pack(fill="x", pady=(0, 4))
        self.dist_entry = ctk.CTkEntry(
            dist_row,
            placeholder_text="km",
            font=FONTS["body"],
            height=42,
            width=120,
            border_color=COLORS["gold"],
            border_width=2,
            fg_color=COLORS["input_bg"],
        )
        self.dist_entry.pack(side="left")
        ctk.CTkLabel(dist_row, text="km", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left", padx=8)

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

        # a chave correta (seed) é impostos.regime_default
        default_regime = self.cfg.get("impostos.regime_default", "PF")
        self.regime_var = ctk.StringVar(value=default_regime)

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

    def _set_distancia(self, km: float) -> None:
        self.dist_entry.delete(0, "end")
        self.dist_entry.insert(0, str(int(km) if km == int(km) else km))

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

    def _render_empty_result(self) -> None:
        for w in self.result_inner.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.result_inner,
            text="💡",
            font=("Segoe UI", 48),
        ).pack(pady=(80, 12))
        ctk.CTkLabel(
            self.result_inner,
            text="Adicione procedimentos, informe a distância\ne clique em CALCULAR",
            font=FONTS["body"],
            text_color=COLORS["text_muted"],
            justify="center",
        ).pack()

    # ─────────────────────────── Calcular ───────────────────────────
    def _on_calcular(self) -> None:
        if not self._selected:
            self._show_error("Adicione pelo menos um procedimento")
            return
        try:
            distancia = float(self.dist_entry.get().replace(",", "."))
        except ValueError:
            self._show_error("Distância inválida")
            return
        if distancia < 0:
            self._show_error("Distância deve ser ≥ 0")
            return

        # Pedir cliente antes de mostrar resultado
        self._prompt_cliente(distancia)

    def _prompt_cliente(self, distancia: float) -> None:
        dialog = ctk.CTkInputDialog(
            title="Cliente",
            text="Nome do cliente / paciente:",
        )
        cliente = dialog.get_input()
        if not cliente or not cliente.strip():
            return
        cliente = cliente.strip()

        entrada = EntradaPrecificacao(
            procedimentos=[(p.id, q) for p, q in self._selected],
            distancia_km=distancia,
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
            distancia_km=distancia,
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
            "is_nee": res.entrada.is_nee,
            "regime": res.regime_aplicado.value,
            "aliquota": res.aliquota_aplicada,
            "decomposicao": {
                "custo_procedimentos": res.custo_procedimentos,
                "custo_hora_clinica": res.custo_hora_clinica,
                "custo_materiais_lab": res.custo_materiais_lab,
                "custo_deslocamento": res.custo_deslocamento,
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
            self._on_export_pdf(self._last_resultado, self._last_cliente_nome, self._last_historico_id)
            HistoricoRepo.marcar_pdf_gerado(self._last_historico_id)
        except Exception as e:
            self._show_error(f"Erro no PDF: {e}")

    def _show_error(self, msg: str) -> None:
        # Mensagem simples no topo do painel de resultado
        for w in self.result_inner.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.result_inner, text="⚠️", font=("Segoe UI", 48), text_color=COLORS["warning"]
        ).pack(pady=(80, 12))
        ctk.CTkLabel(
            self.result_inner, text=msg, font=FONTS["body"],
            text_color=COLORS["error"], wraplength=300, justify="center",
        ).pack()
