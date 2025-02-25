# gui/base_gui.py

import tkinter as tk
from tkinter import ttk
from config import UPDATE_INTERVAL_MS

class BaseGUI:
    """
    Classe base que cria a janela principal, o Notebook, e gerencia a troca de abas.
    """

    def __init__(self, portfolio_manager):
        self.pm = portfolio_manager
        self.root = tk.Tk()
        self.root.title("Controle de Carteira")
        self.root.geometry("1200x700")
        self.update_interval_ms = UPDATE_INTERVAL_MS

        # Cria o Notebook para as abas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Armazena as referências às abas
        self.tabs = {}

    def add_tab(self, tab_obj, title):
        """
        Adiciona uma aba (Frame) ao Notebook.
        :param tab_obj: Instância de tk.Frame (ou herdeiro) contendo widgets
        :param title: Título da aba
        """
        self.notebook.add(tab_obj, text=title)
        self.tabs[title] = tab_obj

    def show_tab(self, title):
        """
        Seleciona a aba pelo título.
        """
        tab_obj = self.tabs.get(title)
        if tab_obj:
            self.notebook.select(tab_obj)

    def run(self):
        """
        Inicia o loop principal da interface.
        """
        self.root.mainloop()
