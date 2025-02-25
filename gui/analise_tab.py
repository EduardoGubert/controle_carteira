# gui/analise_tab.py

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime

class AnaliseTab(tk.Frame):
    """
    Aba de Análise com 4 colunas na parte inferior:
      1) Quarterly EPS & Sales
      2) Yearly EPS
      3) Ratings / Indicadores
      4) Campos Avançados (roic, margin, etc.)
    """
    def __init__(self, parent, pm):
        super().__init__(parent)
        self.pm = pm  # Referência ao PortfolioManager
        self.create_widgets()

    def create_widgets(self):
        # -------------------- Frame Superior: entrada + botão pesquisar --------------------
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(top_frame, text="Código da Ação:").pack(side="left", padx=5)
        self.entry_analise = tk.Entry(top_frame, width=10)
        self.entry_analise.pack(side="left", padx=5)

        search_button = tk.Button(top_frame, text="Pesquisar", command=self.search_stock_info)
        search_button.pack(side="left", padx=5)

        # -------------------- Frame Principal para as 4 partes --------------------
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Configuramos 4 colunas, 1 linha
        for col_index in range(4):
            bottom_frame.grid_columnconfigure(col_index, weight=1)

        # ========== 1) Quarterly EPS & Sales ==========
        quarterly_label = tk.Label(bottom_frame, text="Quarterly EPS & Sales", font=("Arial", 11, "bold"))
        quarterly_label.grid(row=0, column=0, sticky="n", padx=5, pady=5)

        columns_quarterly = ("Quarter", "EPS($)", "%ChgEPS", "Sales($Mil)", "%ChgSales")
        self.quarterly_tree = ttk.Treeview(bottom_frame, columns=columns_quarterly, show="headings", height=14)
        for col in columns_quarterly:
            self.quarterly_tree.heading(col, text=col)
            self.quarterly_tree.column(col, anchor="center", width=90)
        self.quarterly_tree.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # ========== 2) Yearly EPS ==========
        yearly_label = tk.Label(bottom_frame, text="Yearly EPS", font=("Arial", 11, "bold"))
        yearly_label.grid(row=0, column=1, sticky="n", padx=5, pady=5)

        columns_yearly = ("Year (Dec)", "EPS($)", "%Chg")
        self.yearly_tree = ttk.Treeview(bottom_frame, columns=columns_yearly, show="headings", height=14)
        for col in columns_yearly:
            self.yearly_tree.heading(col, text=col)
            self.yearly_tree.column(col, anchor="center", width=80)
        self.yearly_tree.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        # ========== 3) Ratings e Outros Indicadores ==========
        ratings_label = tk.Label(bottom_frame, text="Ratings / Indicadores", font=("Arial", 11, "bold"))
        ratings_label.grid(row=0, column=2, sticky="n", padx=5, pady=5)

        columns_ratings = ("Campo", "Valor")
        self.ratings_tree = ttk.Treeview(bottom_frame, columns=columns_ratings, show="headings", height=14)
        self.ratings_tree.heading("Campo", text="Campo")
        self.ratings_tree.heading("Valor", text="Valor")
        self.ratings_tree.column("Campo", anchor="w", width=140)
        self.ratings_tree.column("Valor", anchor="center", width=140)
        self.ratings_tree.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        # ========== 4) Campos Avançados (roic, margin, etc.) ==========
        advanced_label = tk.Label(bottom_frame, text="Campos Avançados", font=("Arial", 11, "bold"))
        advanced_label.grid(row=0, column=3, sticky="n", padx=5, pady=5)

        self.advanced_tree = ttk.Treeview(bottom_frame, columns=("Campo", "Valor"), show="headings", height=14)
        self.advanced_tree.heading("Campo", text="Campo")
        self.advanced_tree.heading("Valor", text="Valor")
        self.advanced_tree.column("Campo", anchor="w", width=150)
        self.advanced_tree.column("Valor", anchor="center", width=150)
        self.advanced_tree.grid(row=1, column=3, sticky="nsew", padx=5, pady=5)


    def search_stock_info(self):
        """
        Método chamado ao clicar em 'Pesquisar'.
        Busca e exibe todos os dados disponíveis para o ticker.
        """
        ticker = self.entry_analise.get().upper().strip()
        if not ticker:
            messagebox.showerror("Erro", "Informe o código da ação.")
            return

        try:
            # Limpa todas as tabelas antes de inserir novos dados
            for tree in [self.quarterly_tree, self.yearly_tree, self.ratings_tree, self.advanced_tree]:
                for item in tree.get_children():
                    tree.delete(item)

            logging.info(f"Buscando dados para {ticker}")

            # 1. Buscar e preencher dados trimestrais
            quarterly_data = self.pm.market_data_service.get_quarterly_data(ticker)
            for row in quarterly_data:
                self.quarterly_tree.insert("", "end", values=row)
            logging.info(f"Dados trimestrais obtidos: {len(quarterly_data)} registros")

            # 2. Buscar e preencher dados anuais
            yearly_data = self.pm.market_data_service.get_yearly_data(ticker)
            for row in yearly_data:
                self.yearly_tree.insert("", "end", values=row)
            logging.info(f"Dados anuais obtidos: {len(yearly_data)} registros")

            # 3. Buscar e preencher ratings
            ratings_data = self.pm.market_data_service.get_ratings_data(ticker)
            for row in ratings_data:
                self.ratings_tree.insert("", "end", values=row)
            logging.info(f"Dados de ratings obtidos: {len(ratings_data)} registros")

            # 4. Buscar e preencher dados fundamentais avançados
            campos_avancados = {
                "peRatio": "P/E Ratio",
                "grossMargins": "Margem Bruta",
                "profitMargins": "Margem de Lucro",
                "roic": "ROIC",
                "returnOnEquity": "ROE",
                "roe15years": "ROE (Últ. 15 anos)",
                "revenueGrowth": "Cresc. de Receita Anual",
                "netIncomeGrowth": "Cresc. de Lucro Anual",
                "ocfNetIncomeRatio": "Operating Cash Flow / Net Income",
                "netDebtEbitda": "Net Debt / EBITDA",
                "insiderOwnership": "INSIDER OWNERSHIP",
                "capexSales": "CAPEX / SALES",
                "capexOCF": "CAPEX / OPERATING CASH FLOW",
                "returnOfEquity": "RETURN OF EQUITY",
            }

            advanced_data = self.pm.market_data_service.get_fundamental_data(ticker, campos_avancados)
            
            for campo, label in campos_avancados.items():
                valor = advanced_data.get(campo, "N/A")
                if isinstance(valor, float):
                    if campo in ["grossMargins", "profitMargins", "returnOnEquity", "roic"]:
                        valor = f"{valor * 100:.2f}%"  # Converte para porcentagem
                    else:
                        valor = f"{valor:.2f}"
                self.advanced_tree.insert("", "end", values=(label, valor))
            
            logging.info(f"Dados fundamentais avançados obtidos com sucesso")

        except Exception as e:
            logging.error(f"Erro ao buscar dados para {ticker}: {e}")
            messagebox.showerror("Erro", f"Não foi possível obter dados para {ticker}.\nErro: {str(e)}")