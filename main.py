#!/usr/bin/env python3
"""Ponto de entrada da aplicação Basis Precificador."""
import customtkinter as ctk
from src.db.migrations import initialize
from src.app import BasisApp

if __name__ == "__main__":
    # Garante que o banco existe e está com schema + seeds
    initialize()
    print("✅ Banco de dados (basis.db) inicializado com sucesso!")

    # Tema escuro (o visual customizado está em theme.py dentro das views)
    ctk.set_appearance_mode("dark")

    app = BasisApp()
    app.mainloop()
