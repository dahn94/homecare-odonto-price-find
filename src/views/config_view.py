"""Tela de Configurações — Versão Melhorada (foco em impostos intuitivos)"""
from __future__ import annotations
from decimal import Decimal
import customtkinter as ctk
from ..models.config import ConfigStore
from ..db.repositories import ProcedimentoRepo, CustosFixosRepo
from ..calc import deslocamento as calc_deslocamento
from ..theme import COLORS, FONTS, fmt_brl, fmt_pct
from ..models.procedimento import Procedimento


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x = self.widget.winfo_rootx() + 30
        y = self.widget.winfo_rooty() + 30
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        ctk.CTkLabel(tw, text=self.text, font=FONTS["small"], fg_color=COLORS["bg_secondary"],
                     text_color=COLORS["text_primary"], corner_radius=6, padx=10, pady=6).pack()

    def hide(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


class ConfigView(ctk.CTkToplevel):
    def __init__(self, master, cfg: ConfigStore, on_close=None):
        super().__init__(master)
        self.title("⚙️ Configurações • Basis Precificador")
        self.geometry("1220x760")
        self.cfg = cfg
        self.on_close = on_close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_ui()

    def _build_ui(self):
        tabview = ctk.CTkTabview(self, fg_color=COLORS["bg_primary"])
        tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self._create_tab(tabview.add("Geral"), ["veiculo", "tempo", "deslocamento", "domiciliar", "estacionamento", "orcamento"])
        self._create_tab(tabview.add("Maquineta"), ["maquineta"])
        self._create_impostos_tab(tabview.add("Impostos"))          # ← NOVA ABA MAIS CLARA
        self._create_custos_meta_tab(tabview.add("Custos & Meta"))
        self._create_tab(tabview.add("CBHPO"), ["cbhpo"])
        self._create_procedimentos_tab(tabview.add("Procedimentos"))

    # ==================== ABA IMPOSTOS (a mais importante agora) ====================
    def _create_impostos_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab)
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(scroll, text="Regime Tributário", font=FONTS["heading"], 
                     text_color=COLORS["accent"]).pack(anchor="w", pady=(0, 16))

        regimes = [
            ("impostos.aliquota_pf",      "PF – Pessoa Física (Carnê-leão)",      "Alíquota efetiva usada para recibo simples"),
            ("impostos.aliquota_mei",     "MEI – Microempreendedor Individual",   "DAS mensal fixo (aprox. 6%)"),
            ("impostos.aliquota_simples", "Simples Nacional (Anexo III ou V)",    "Alíquota efetiva do Simples"),
        ]

        for chave, nome_exibicao, descricao in regimes:
            row = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
            row.pack(fill="x", pady=8, padx=4)

            ctk.CTkLabel(row, text=nome_exibicao, font=FONTS["body_bold"], width=340, anchor="w").pack(side="left", padx=20)

            # Valor formatado com %
            valor = self.cfg.get(chave, 0.0)
            var = ctk.StringVar(value=fmt_pct(valor))

            entry = ctk.CTkEntry(row, textvariable=var, width=100, font=FONTS["mono"])
            entry.pack(side="left", padx=8)

            def save(k=chave, v=var):
                try:
                    raw = v.get().replace(",", ".").replace("%", "").strip()
                    pct = Decimal(raw) / Decimal("100")
                    self.cfg.set(k, pct)
                except Exception:
                    pass

            entry.bind("<FocusOut>", lambda e, s=save: s())

            # Tooltip
            btn = ctk.CTkLabel(row, text="❔", font=("Segoe UI", 14), text_color=COLORS["text_muted"])
            btn.pack(side="left", padx=12)
            Tooltip(btn, descricao)
        
        ctk.CTkLabel(
            scroll,
            text="O regime é selecionado na tela principal a cada orçamento.",
            font=FONTS["small"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(18, 0))

    # ==================== Helpers de UI ====================
    @staticmethod
    def _humanize_key(chave: str) -> str:
        # ex: "veiculo.preco_combustivel_litro" -> "Preço combustivel litro"
        tail = chave.split(".", 1)[1] if "." in chave else chave
        return tail.replace("_", " ").strip().capitalize()

    @staticmethod
    def _is_percent_key(chave: str) -> bool:
        needles = ("aliquota", "margem", "acrescimo", "percent", "taxa")
        return any(n in chave for n in needles)

    @staticmethod
    def _parse_decimalish(text: str) -> Decimal:
        t = (text or "").strip().replace("R$", "").replace(" ", "")
        if not t:
            return Decimal("0")
        # aceita "1.234,56" ou "1234,56" ou "1234.56"
        if "," in t and "." in t:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", ".")
        return Decimal(t)

    def _format_value(self, chave: str, tipo: str, value):
        if tipo == "bool":
            return bool(value)
        if tipo in ("int", "float"):
            v = Decimal(str(value))
            if self._is_percent_key(chave):
                return fmt_pct(v)
            if "hora_clinica" in chave or "preco" in chave or "valor" in chave or "faturamento" in chave:
                return fmt_brl(v)
            return str(int(v)) if tipo == "int" else str(v).replace(".", ",")
        if tipo == "json":
            return str(value)
        return str(value)

    def _save_entry_value(self, chave: str, tipo: str, var: ctk.StringVar) -> None:
        raw = (var.get() or "").strip()
        try:
            if tipo == "int":
                v = int(self._parse_decimalish(raw))
            elif tipo == "float":
                v = self._parse_decimalish(raw)
                if self._is_percent_key(chave):
                    # heurística: se digitou "30" ou "30%" vira 0.30
                    if "%" in raw:
                        v = v / Decimal("100")
                    elif v > Decimal("1"):
                        v = v / Decimal("100")
            elif tipo == "bool":
                return
            else:
                v = raw

            self.cfg.set(chave, v)
            # re-formata a própria caixa com valor "bonito"
            novo = self.cfg.get(chave)
            var.set(self._format_value(chave, tipo, novo))
        except Exception:
            # não bloqueia a UI; mantém o valor digitado
            return

    # ==================== Abas genéricas por grupo ====================
    def _create_tab(self, tab, grupos: list[str]):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        grouped = self.cfg.all_grouped()

        any_rendered = False
        for grupo in grupos:
            data = grouped.get(grupo, {})
            if not data:
                continue
            any_rendered = True

            ctk.CTkLabel(
                scroll,
                text=grupo.replace("_", " ").title(),
                font=FONTS["heading"],
                text_color=COLORS["accent"],
            ).pack(anchor="w", pady=(0, 10))

            for chave, info in data.items():
                row = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
                row.pack(fill="x", pady=6, padx=4)

                ctk.CTkLabel(
                    row,
                    text=self._humanize_key(chave),
                    font=FONTS["body_bold"],
                    width=360,
                    anchor="w",
                    text_color=COLORS["text_primary"],
                ).pack(side="left", padx=16, pady=10)

                tipo = info["tipo"]
                if tipo == "bool":
                    varb = ctk.BooleanVar(value=bool(info["value"]))
                    cb = ctk.CTkCheckBox(
                        row,
                        text="",
                        variable=varb,
                        fg_color=COLORS["accent"],
                        hover_color=COLORS["accent_hover"],
                    )
                    cb.pack(side="left", padx=8)

                    def save_bool(k=chave, vb=varb):
                        try:
                            self.cfg.set(k, bool(vb.get()))
                        except Exception:
                            return

                    cb.configure(command=save_bool)
                else:
                    var = ctk.StringVar(value=self._format_value(chave, tipo, info["value"]))
                    entry = ctk.CTkEntry(
                        row,
                        textvariable=var,
                        width=170,
                        font=FONTS["mono"],
                        fg_color=COLORS["input_bg"],
                        border_color=COLORS["gold"],
                        border_width=2,
                    )
                    entry.pack(side="left", padx=8, pady=10)
                    entry.bind("<FocusOut>", lambda e, k=chave, t=tipo, v=var: self._save_entry_value(k, t, v))

                # tooltip
                btn = ctk.CTkLabel(row, text="❔", font=("Segoe UI", 14), text_color=COLORS["text_muted"])
                btn.pack(side="left", padx=12)
                Tooltip(btn, info.get("descricao") or "Sem descrição")

            ctk.CTkFrame(scroll, fg_color="transparent", height=10).pack(fill="x")

            # Simulador rápido (ajuda a usuária a "ver" o cálculo do deslocamento)
            if grupo == "deslocamento":
                self._render_deslocamento_simulator(scroll)
                ctk.CTkFrame(scroll, fg_color="transparent", height=10).pack(fill="x")

        if not any_rendered:
            ctk.CTkLabel(
                scroll,
                text="Nenhuma configuração encontrada para esta aba.",
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
            ).pack(anchor="w", pady=10)

    def _render_deslocamento_simulator(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=12)
        card.pack(fill="x", padx=4, pady=(6, 12))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        ctk.CTkLabel(
            inner,
            text="Simulador de deslocamento (asfalto + terra + bairro nobre)",
            font=FONTS["heading"],
            text_color=COLORS["accent"],
        ).pack(anchor="w")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(10, 8))

        km_asf_var = ctk.StringVar(value="8")
        km_ter_var = ctk.StringVar(value="2")
        nobre_var = ctk.BooleanVar(value=False)

        ctk.CTkLabel(row, text="Asfalto", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkEntry(
            row, textvariable=km_asf_var, width=72, font=FONTS["mono"],
            fg_color=COLORS["input_bg"], border_color=COLORS["gold"], border_width=2,
        ).pack(side="left", padx=(6, 14))
        ctk.CTkLabel(row, text="Terra", font=FONTS["small"], text_color=COLORS["text_secondary"]).pack(side="left")
        ctk.CTkEntry(
            row, textvariable=km_ter_var, width=72, font=FONTS["mono"],
            fg_color=COLORS["input_bg"], border_color=COLORS["gold"], border_width=2,
        ).pack(side="left", padx=6)
        ctk.CTkCheckBox(
            row, text="Nobre", variable=nobre_var, font=FONTS["small"],
            text_color=COLORS["text_secondary"], fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
        ).pack(side="left", padx=(12, 0))

        out = ctk.CTkFrame(inner, fg_color=COLORS["bg_card"], corner_radius=10)
        out.pack(fill="x", pady=(6, 0))

        lines = {
            "seg": ctk.CTkLabel(out, text="", font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"),
            "comb": ctk.CTkLabel(out, text="", font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"),
            "manu": ctk.CTkLabel(out, text="", font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"),
            "tempo": ctk.CTkLabel(out, text="", font=FONTS["small"], text_color=COLORS["text_secondary"], anchor="w"),
            "real": ctk.CTkLabel(out, text="", font=FONTS["body_bold"], text_color=COLORS["text_primary"], anchor="w"),
            "taxa": ctk.CTkLabel(out, text="", font=FONTS["body_bold"], text_color=COLORS["success"], anchor="w"),
        }
        for k in ["seg", "comb", "manu", "tempo", "real", "taxa"]:
            lines[k].pack(fill="x", padx=14, pady=(8 if k == "seg" else 2, 2))
        ctk.CTkFrame(out, fg_color="transparent", height=6).pack()

        def recalc():
            try:
                ka = float(Decimal(km_asf_var.get().replace(",", ".") or "0"))
                kt = float(Decimal(km_ter_var.get().replace(",", ".") or "0"))
                d = calc_deslocamento.calcular_composto(ka, kt, nobre_var.get(), None, self.cfg)
                lines["seg"].configure(
                    text=f"Trechos: {ka:.1f} km asfalto + {kt:.1f} km terra = {d.distancia_km:.1f} km total (ida+volta)"
                )
                lines["comb"].configure(
                    text=f"Combustível: {fmt_brl(d.custo_combustivel_total)} ({fmt_brl(d.custo_combustivel_km)}/km)"
                )
                lines["manu"].configure(text=f"Manutenção (soma trechos): {fmt_brl(d.custo_manutencao_total)}")
                lines["tempo"].configure(text=f"Tempo/trânsito (soma): {fmt_brl(d.custo_tempo)}")
                lines["real"].configure(
                    text=f"Custo real: {fmt_brl(d.custo_real)} (asfalto {fmt_brl(d.custo_real_asfalto)} + terra {fmt_brl(d.custo_real_terra)})"
                )
                nb = f" + nobre {fmt_pct(d.acrescimo_bairro_nobre_percent)}" if d.bairro_nobre and d.acrescimo_bairro_nobre_percent > 0 else ""
                lines["taxa"].configure(
                    text=f"Taxa ao paciente: {fmt_brl(d.taxa_ao_paciente)} (margem {fmt_pct(d.margem_lucro)}{nb})"
                )
            except Exception:
                return

        ctk.CTkButton(
            row,
            text="Calcular",
            font=FONTS["body_bold"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color=COLORS["bg_primary"],
            height=36,
            width=120,
            corner_radius=10,
            command=recalc,
        ).pack(side="right")

        recalc()

    # ==================== Custos fixos + meta ====================
    def _create_custos_meta_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll,
            text="Custos Fixos Mensais (rateados por atendimento)",
            font=FONTS["heading"],
            text_color=COLORS["accent"],
        ).pack(anchor="w", pady=(0, 10))

        custos = CustosFixosRepo.listar()
        for item in custos:
            row = ctk.CTkFrame(scroll, fg_color=COLORS["bg_card"], corner_radius=10)
            row.pack(fill="x", pady=6, padx=4)

            ctk.CTkLabel(
                row,
                text=item["nome"],
                font=FONTS["body_bold"],
                anchor="w",
                width=420,
                text_color=COLORS["text_primary"],
            ).pack(side="left", padx=16, pady=10)

            var = ctk.StringVar(value=fmt_brl(item["valor_mensal"]))
            entry = ctk.CTkEntry(
                row,
                textvariable=var,
                width=170,
                font=FONTS["mono"],
                fg_color=COLORS["input_bg"],
                border_color=COLORS["gold"],
                border_width=2,
            )
            entry.pack(side="left", padx=8, pady=10)

            def save_cost(i=item["id"], v=var):
                try:
                    val = self._parse_decimalish(v.get())
                    CustosFixosRepo.atualizar(i, val)
                    v.set(fmt_brl(val))
                except Exception:
                    return

            entry.bind("<FocusOut>", lambda e, s=save_cost: s())

        ctk.CTkFrame(scroll, fg_color="transparent", height=18).pack(fill="x")

        # Meta + retrabalho são configs
        self._render_config_group_inline(scroll, "meta", title="Meta")
        self._render_config_group_inline(scroll, "retrabalho", title="Retrabalho")

    def _render_config_group_inline(self, parent, grupo: str, title: str):
        grouped = self.cfg.all_grouped()
        data = grouped.get(grupo, {})
        if not data:
            return
        ctk.CTkLabel(parent, text=title, font=FONTS["heading"], text_color=COLORS["accent"]).pack(
            anchor="w", pady=(0, 10)
        )
        for chave, info in data.items():
            row = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
            row.pack(fill="x", pady=6, padx=4)
            ctk.CTkLabel(
                row,
                text=self._humanize_key(chave),
                font=FONTS["body_bold"],
                width=360,
                anchor="w",
                text_color=COLORS["text_primary"],
            ).pack(side="left", padx=16, pady=10)

            tipo = info["tipo"]
            var = ctk.StringVar(value=self._format_value(chave, tipo, info["value"]))
            entry = ctk.CTkEntry(
                row,
                textvariable=var,
                width=170,
                font=FONTS["mono"],
                fg_color=COLORS["input_bg"],
                border_color=COLORS["gold"],
                border_width=2,
            )
            entry.pack(side="left", padx=8, pady=10)
            entry.bind("<FocusOut>", lambda e, k=chave, t=tipo, v=var: self._save_entry_value(k, t, v))

            btn = ctk.CTkLabel(row, text="❔", font=("Segoe UI", 14), text_color=COLORS["text_muted"])
            btn.pack(side="left", padx=12)
            Tooltip(btn, info.get("descricao") or "Sem descrição")

        ctk.CTkFrame(parent, fg_color="transparent", height=10).pack(fill="x")

    # ==================== Procedimentos (editor simples) ====================
    def _create_procedimentos_tab(self, tab):
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            scroll,
            text="Editar valores praticados (salva ao sair do campo)",
            font=FONTS["heading"],
            text_color=COLORS["accent"],
        ).pack(anchor="w", pady=(0, 12))

        try:
            procs = ProcedimentoRepo.listar(ativos=True)
        except Exception as e:
            ctk.CTkLabel(
                scroll,
                text=f"Erro ao carregar procedimentos: {e}",
                font=FONTS["body"],
                text_color=COLORS["error"],
            ).pack(anchor="w")
            return

        for proc in procs:
            self._render_proc_row(scroll, proc)

    def _render_proc_row(self, parent, proc: Procedimento) -> None:
        row = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        row.pack(fill="x", pady=6, padx=4)

        left = ctk.CTkFrame(row, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=16, pady=10)

        ctk.CTkLabel(
            left,
            text=proc.nome,
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
            anchor="w",
        ).pack(anchor="w")

        meta = []
        if proc.codigo_cbhpo:
            meta.append(proc.codigo_cbhpo)
        meta.append(f"{proc.tempo_estimado_min} min")
        if proc.custo_material:
            meta.append(f"Material {fmt_brl(proc.custo_material)}")
        if proc.custo_laboratorio:
            meta.append(f"Lab {fmt_brl(proc.custo_laboratorio)}")
        ctk.CTkLabel(
            left,
            text=" • ".join(meta),
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w",
        ).pack(anchor="w")

        right = ctk.CTkFrame(row, fg_color="transparent")
        right.pack(side="right", padx=16, pady=10)

        var = ctk.StringVar(value=fmt_brl(proc.valor_atual))
        entry = ctk.CTkEntry(
            right,
            textvariable=var,
            width=170,
            font=FONTS["mono"],
            fg_color=COLORS["input_bg"],
            border_color=COLORS["gold"],
            border_width=2,
        )
        entry.pack(anchor="e")

        delta_txt = "Sem referência"
        delta_color = COLORS["text_muted"]
        if proc.delta_percent is not None:
            sign = "▲" if proc.delta_percent > 0 else ("▼" if proc.delta_percent < 0 else "=")
            delta_txt = f"{sign} {fmt_pct(proc.delta_percent)} vs CBHPO {proc.cbhpo_versao or ''}".strip()
            delta_color = COLORS["success"] if proc.delta_percent > 0 else (COLORS["error"] if proc.delta_percent < 0 else COLORS["text_secondary"])

        ctk.CTkLabel(
            right,
            text=delta_txt,
            font=FONTS["small"],
            text_color=delta_color,
        ).pack(anchor="e", pady=(4, 0))

        def save_val():
            try:
                val = self._parse_decimalish(var.get())
                ProcedimentoRepo.atualizar_valor(proc.id, val)
                var.set(fmt_brl(val))
            except Exception:
                return

        entry.bind("<FocusOut>", lambda e: save_val())

    def _on_close(self):
        if self.on_close:
            self.on_close()
        self.destroy()