# gui/analise_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

class AnaliseTab(tk.Frame):
    """
    Aba de Análise: permite pesquisar uma ação e exibir dados financeiros.
    """
    def __init__(self, parent, pm):
        super().__init__(parent)
        self.pm = pm  # Referência ao PortfolioManager, que tem market_data_service
        self.create_widgets()

    def create_widgets(self):
        # Frame superior: campo de texto + botão pesquisar
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(top_frame, text="Código da Ação:").pack(side="left", padx=5)
        self.entry_analise = tk.Entry(top_frame, width=10)
        self.entry_analise.pack(side="left", padx=5)

        search_button = tk.Button(top_frame, text="Pesquisar", command=self.search_stock_info)
        search_button.pack(side="left", padx=5)

        # Frame intermediário: duas TreeViews (básico e avançado)
        middle_frame = tk.Frame(self)
        middle_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # ----- Tabela 1: Dados básicos -----
        basic_label = tk.Label(middle_frame, text="Dados de Mercado (Básico)", font=("Arial", 11, "bold"))
        basic_label.pack(pady=5)
        
        self.basic_tree = ttk.Treeview(middle_frame, columns=("Campo", "Valor"), show="headings", height=10)
        self.basic_tree.heading("Campo", text="Campo")
        self.basic_tree.heading("Valor", text="Valor")
        self.basic_tree.column("Campo", anchor="center", width=200)
        self.basic_tree.column("Valor", anchor="center", width=200)
        self.basic_tree.pack(fill="x", expand=False, padx=5, pady=5)

        # ----- Tabela 2: Dados Avançados -----
        advanced_label = tk.Label(middle_frame, text="Indicadores Fundamentalistas (Avançado)", font=("Arial", 11, "bold"))
        advanced_label.pack(pady=5)

        self.advanced_tree = ttk.Treeview(middle_frame, columns=("Campo", "Valor"), show="headings", height=10)
        self.advanced_tree.heading("Campo", text="Campo")
        self.advanced_tree.heading("Valor", text="Valor")
        self.advanced_tree.column("Campo", anchor="center", width=200)
        self.advanced_tree.column("Valor", anchor="center", width=200)
        self.advanced_tree.pack(fill="x", expand=False, padx=5, pady=5)

        # Tabela 3 (opcional): EPS x Sales (3 últimos anos / trimestres)
        # Se desejar outra tabela para EPS / SALES, etc., crie aqui.

    def search_stock_info(self):
        ticker = self.entry_analise.get().upper().strip()
        if not ticker:
            messagebox.showerror("Erro", "Informe o código da ação.")
            return

        # 1) Define campos básicos (já existentes)
        campos_basicos = {
            "previousClose": "Fech. Anterior",
            "open": "Abertura",
            "dayLow": "Mínimo do Dia",
            "dayHigh": "Máximo do Dia",
            "volume": "Volume",
            "marketCap": "Market Cap",
            "trailingPE": "P/E (Últ. 12m)",
            "forwardPE": "P/E Futuro",
            "dividendYield": "Dividend Yield",
        }

        # 2) Define campos avançados
        campos_avancados = {
            "peRatio": "P/E Ratio",  # yfinance 'info' might have "trailingPE" ou algo similar
            "grossMargins": "Margem Bruta",  # Em yfinance: info['grossMargins']
            "profitMargins": "Margem de Lucro",  # Em yfinance: info['profitMargins']
            "roic": "ROIC",  # raramente presente direto em yfinance
            "returnOnEquity": "ROE",  # yfinance: info['returnOnEquity'] (talvez)
            # Abaixo, normalmente não constam em yfinance .info:
            "roe15years": "ROE (Últ. 15 anos)",
            "revenueGrowth": "Cresc. de Receita Anual",
            "netIncomeGrowth": "Cresc. de Lucro Anual",
            "ocfNetIncomeRatio": "Operating Cash Flow / Net Income",
            "netDebtEbitda": "Net Debt / EBITDA",
            "insiderOwnership": "INSIDER OWNERSHIP",
            "capexSales": "CAPEX / SALES",
            "capexOCF": "CAPEX / OPERATING CASH FLOW",
            "returnOfEquity": "RETURN OF EQUITY",  # se for algo distinto de 'returnOnEquity'
        }

        try:
            # 3) Busca dados básicos
            dados_basicos = self.pm.market_data_service.get_fundamental_data(ticker, campos_basicos)

            # 4) Busca dados avançados
            dados_avancados = self.pm.market_data_service.get_fundamental_data(ticker, campos_avancados)

            # Limpa as TreeViews
            for item in self.basic_tree.get_children():
                self.basic_tree.delete(item)
            for item in self.advanced_tree.get_children():
                self.advanced_tree.delete(item)

            # Preenche Tabela de dados básicos
            for campo, label in campos_basicos.items():
                valor = dados_basicos.get(campo, "N/A")
                if isinstance(valor, float):
                    valor = f"{valor:,.2f}"
                self.basic_tree.insert("", "end", values=(label, valor))

            # Preenche Tabela de dados avançados
            for campo, label in campos_avancados.items():
                valor = dados_avancados.get(campo, "N/A")
                if isinstance(valor, float):
                    valor = f"{valor:,.2f}"
                self.advanced_tree.insert("", "end", values=(label, valor))

        except Exception as e:
            logging.error(f"Erro ao buscar dados para {ticker}: {e}")
            messagebox.showerror("Erro", f"Não foi possível obter dados para {ticker}.")
