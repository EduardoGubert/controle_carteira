import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from config import UPDATE_INTERVAL_MS
from db import update_config_in_db
import yfinance as yf  # Usado para obter informações para a aba de Análise

class PortfolioGUI:
    """
    Interface gráfica com duas abas:
      - "Carteira": exibe os dados da carteira, botões de operação e a tabela de ações.
      - "Análise": permite pesquisar uma ação e visualizar dados financeiros.
    Também há botões inferiores para alternar entre as abas.
    """
    def __init__(self, portfolio_manager):
        self.pm = portfolio_manager
        self.root = tk.Tk()
        self.root.title("Controle de Carteira")
        self.root.geometry("1200x700")  # Largura e altura ajustadas para acomodar as abas e botões inferiores
        self.update_interval_ms = UPDATE_INTERVAL_MS
        self.sorting_state = {}  # para ordenação da tabela
        self.create_widgets()
        self.refresh()
        self.root.mainloop()

    def create_widgets(self):
        # Cria um Notebook para as abas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Aba Carteira (mantém o layout atual)
        self.tab_carteira = tk.Frame(self.notebook)
        self.notebook.add(self.tab_carteira, text="Carteira")

        # Aba Análise (nova)
        self.tab_analise = tk.Frame(self.notebook)
        self.notebook.add(self.tab_analise, text="Análise")

        # ----- Aba Carteira -----
        self.create_carteira_widgets(self.tab_carteira)

        # ----- Aba Análise -----
        self.create_analise_widgets(self.tab_analise)

        # Botões inferiores para alternar entre abas
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill="x", pady=5)
        btn_carteira = tk.Button(button_frame, text="Carteira", command=lambda: self.notebook.select(self.tab_carteira), width=15)
        btn_carteira.pack(side="left", padx=10)
        btn_analise = tk.Button(button_frame, text="Análise", command=lambda: self.notebook.select(self.tab_analise), width=15)
        btn_analise.pack(side="left", padx=10)

    def create_carteira_widgets(self, parent):
        # Layout original reorganizado para a aba "Carteira"
        main_frame = tk.Frame(parent)
        main_frame.pack(fill="both", expand=True)

        # Painel Superior
        top_frame = tk.Frame(main_frame)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        # Top Esquerdo: Cabeçalho com dados resumidos da carteira
        top_left = tk.Frame(top_frame)
        top_left.grid(row=0, column=0, sticky="nsew", padx=5)
        self.header_tree = ttk.Treeview(top_left, columns=("Descricao", "Valor"), show="headings", height=6)
        self.header_tree.heading("Descricao", text="Descrição")
        self.header_tree.heading("Valor", text="Valor")
        self.header_tree.column("Descricao", anchor="center", width=250)
        self.header_tree.column("Valor", anchor="center", width=120)
        self.header_tree.pack()
        self.header_tree.tag_configure("positive", foreground="green")
        self.header_tree.tag_configure("negative", foreground="red")
        self.header_tree.insert("", "end", iid="total", values=("Valor total da carteira (ações + saldo):", ""))
        self.header_tree.insert("", "end", iid="variacao", values=("Variação total da carteira:", ""))
        self.header_tree.insert("", "end", iid="valor_variacao", values=("Valor da Variação total da carteira:", ""))
        self.header_tree.insert("", "end", iid="investido", values=("Valor total investido           :", ""))
        self.header_tree.insert("", "end", iid="saldo", values=("Saldo restante                  :", ""))
        self.header_tree.insert("", "end", iid="inicial", values=("Valor total inicial             :", ""))
        self.header_tree.insert("", "end", iid="total_reais", values=("Valor total em Reais            :", ""))
        self.header_tree.insert("", "end", iid="inicial_reais", values=("Valor total inicial em Reais    :", ""))
        self.header_tree.insert("", "end", iid="variacao_reais", values=("Valor da Variação total investido em Reais    :", ""))
        self.header_tree.insert("", "end", iid="dolar", values=("Valor do dólar             :", ""))

        # Top Meio: Botões
        top_middle = tk.Frame(top_frame)
        top_middle.grid(row=0, column=1, sticky="nsew", padx=5)
        trade_button = tk.Button(top_middle, text="Operar (Comprar/Vender)", command=self.open_trade_window, width=20)
        trade_button.pack(pady=10)
        config_button = tk.Button(top_middle, text="Configurações", command=self.open_config_window, width=20)
        config_button.pack(pady=10)

        # Top Direito: Painel de Rendimentos
        top_right = tk.LabelFrame(top_frame, text="Rendimentos", padx=10, pady=10)
        top_right.grid(row=0, column=2, sticky="nsew", padx=5)
        self.returns_labels = {}
        periods = ["Diário", "Semanal", "Mensal", "Trimestral", "Anual"]
        headers = ["Período", "Rendimento (%)", "Rendimento (US$)", "Rendimento (R$)"]
        for col, header in enumerate(headers):
            lbl = tk.Label(top_right, text=header, font=("Arial", 10, "bold"))
            lbl.grid(row=0, column=col, padx=5, pady=5)
        for row, period in enumerate(periods, start=1):
            lbl_period = tk.Label(top_right, text=period)
            lbl_period.grid(row=row, column=0, padx=5, pady=2)
            self.returns_labels[period] = {}
            for col, key in enumerate(["percentual", "us$", "r$"], start=1):
                lbl_value = tk.Label(top_right, text="0", width=12)
                lbl_value.grid(row=row, column=col, padx=5, pady=2)
                self.returns_labels[period][key] = lbl_value

        top_frame.columnconfigure(0, weight=3)
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(2, weight=3)

        # Painel Inferior: Tabela detalhada de ações
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=10)
        columns = ("Ticker", "Quantidade", "Preço Médio", "Custo Médio", "Preço Atual", "Valor Atual", "Variação (%)", "Variação (US$)", "Composição (%)")
        self.tree = ttk.Treeview(bottom_frame, columns=columns, show="headings", height=12)
        for col in columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_treeview(_col))
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(expand=True, fill="both")
        self.tree.tag_configure("positive", foreground="green")
        self.tree.tag_configure("negative", foreground="red")

    def create_analise_widgets(self, parent):
        # Layout simples para a aba de Análise
        top_frame = tk.Frame(parent)
        top_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(top_frame, text="Código da Ação:").pack(side="left", padx=5)
        self.entry_analise = tk.Entry(top_frame, width=10)
        self.entry_analise.pack(side="left", padx=5)
        search_button = tk.Button(top_frame, text="Pesquisar", command=self.search_stock_info)
        search_button.pack(side="left", padx=5)

        # Tabela para exibir os dados financeiros
        self.analise_tree = ttk.Treeview(parent, columns=("Campo", "Valor"), show="headings", height=15)
        self.analise_tree.heading("Campo", text="Campo")
        self.analise_tree.heading("Valor", text="Valor")
        self.analise_tree.column("Campo", anchor="center", width=200)
        self.analise_tree.column("Valor", anchor="center", width=200)
        self.analise_tree.pack(fill="both", expand=True, padx=10, pady=10)

    def sort_treeview(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        def convert_value(value):
            if not value or value == "-":
                return 0
            clean_value = value.replace("US$", "").replace("R$", "").replace("%", "").strip()
            try:
                return float(clean_value)
            except ValueError:
                return clean_value
        items.sort(key=lambda t: convert_value(t[0]), reverse=self.sorting_state.get(col, False))
        for index, (_, item_id) in enumerate(items):
            self.tree.move(item_id, '', index)
        self.sorting_state[col] = not self.sorting_state.get(col, False)

    def open_config_window(self):
        config_window = tk.Toplevel(self.root)
        config_window.title("Configurações")
        config_window.grab_set()

        tk.Label(config_window, text="Valor Inicial Total (USD):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        entry_valor_usd = tk.Entry(config_window)
        entry_valor_usd.insert(0, str(self.pm.valor_inicial_total))
        entry_valor_usd.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(config_window, text="Valor Inicial Total (R$):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        entry_valor_reais = tk.Entry(config_window)
        entry_valor_reais.insert(0, str(self.pm.valor_inicial_total_reais))
        entry_valor_reais.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(config_window, text="Intervalo de Atualização (ms):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        entry_interval = tk.Entry(config_window)
        entry_interval.insert(0, str(self.update_interval_ms))
        entry_interval.grid(row=2, column=1, padx=5, pady=5)

        def save_config():
            try:
                novo_valor_usd = float(entry_valor_usd.get())
                novo_valor_reais = float(entry_valor_reais.get())
                novo_interval = int(entry_interval.get())
            except ValueError:
                messagebox.showerror("Erro", "Insira valores numéricos válidos.")
                return

            self.pm.valor_inicial_total = novo_valor_usd
            self.pm.valor_inicial_total_reais = novo_valor_reais
            self.update_interval_ms = novo_interval

            new_config = {
                "valor_inicial_total_usd": novo_valor_usd,
                "valor_inicial_total_reais": novo_valor_reais,
                "update_interval_ms": novo_interval
            }
            update_config_in_db(new_config)
            messagebox.showinfo("Sucesso", "Configurações atualizadas!")
            config_window.destroy()

        save_button = tk.Button(config_window, text="Salvar", command=save_config)
        save_button.grid(row=3, column=0, columnspan=2, pady=10)

    def open_trade_window(self):
        trade_window = tk.Toplevel(self.root)
        trade_window.title("Operar Ação")
        
        tk.Label(trade_window, text="Ticker (Ação):").grid(row=0, column=0, padx=5, pady=5)
        entry_ticker = tk.Entry(trade_window)
        entry_ticker.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(trade_window, text="Quantidade:").grid(row=1, column=0, padx=5, pady=5)
        entry_quantity = tk.Entry(trade_window)
        entry_quantity.grid(row=1, column=1, padx=5, pady=5)
        
        tk.Label(trade_window, text="Preço:").grid(row=2, column=0, padx=5, pady=5)
        entry_price = tk.Entry(trade_window)
        entry_price.grid(row=2, column=1, padx=5, pady=5)
        
        tk.Label(trade_window, text="Data da Operação (dd/mm/yyyy) [opcional]:").grid(row=3, column=0, padx=5, pady=5)
        entry_data_operacao = tk.Entry(trade_window)
        entry_data_operacao.grid(row=3, column=1, padx=5, pady=5)
        
        def buy_action():
            try:
                ticker = entry_ticker.get().upper().strip()
                quantity = float(entry_quantity.get())
                price = float(entry_price.get())
                manual_date = None
                if entry_data_operacao.get().strip() != "":
                    manual_date = datetime.strptime(entry_data_operacao.get().strip(), "%d/%m/%Y")
                self.pm.buy_stock(ticker, quantity, price, manual_date=manual_date)
                trade_window.destroy()
                self.refresh()
            except Exception as e:
                logging.error(f"Erro ao comprar: {e}")
                messagebox.showerror("Erro", str(e))
        
        def sell_action():
            try:
                ticker = entry_ticker.get().upper().strip()
                quantity = float(entry_quantity.get())
                manual_date = None
                if entry_data_operacao.get().strip() != "":
                    manual_date = datetime.strptime(entry_data_operacao.get().strip(), "%d/%m/%Y")
                self.pm.sell_stock(ticker, quantity, manual_date=manual_date)
                trade_window.destroy()
                self.refresh()
            except Exception as e:
                logging.error(f"Erro ao vender: {e}")
                messagebox.showerror("Erro", str(e))
        
        buy_button = tk.Button(trade_window, text="Comprar", command=buy_action)
        buy_button.grid(row=4, column=0, padx=5, pady=10)
        sell_button = tk.Button(trade_window, text="Vender", command=sell_action)
        sell_button.grid(row=4, column=1, padx=5, pady=10)

    def search_stock_info(self):
        """Pesquisa dados financeiros para o ticker informado na aba Análise."""
        ticker = self.entry_analise.get().upper().strip()
        if not ticker:
            messagebox.showerror("Erro", "Informe o código da ação.")
            return
        try:
            # Usamos yfinance para obter os dados financeiros (exemplo usando o método .info)
            stock = yf.Ticker(ticker)
            info = stock.info
            # Seleciona alguns campos de interesse para exibição
            campos = {
                "previousClose": "Fechamento Anterior",
                "open": "Abertura",
                "dayLow": "Mínimo do Dia",
                "dayHigh": "Máximo do Dia",
                "volume": "Volume",
                "marketCap": "Capitalização",
                "trailingPE": "P/E (Últimos 12M)",
                "forwardPE": "P/E Futuro",
                "dividendYield": "Dividend Yield",
            }
            # Limpa a tabela da aba de Análise
            for item in self.analise_tree.get_children():
                self.analise_tree.delete(item)
            # Insere os campos e valores na tabela
            for campo, descricao in campos.items():
                valor = info.get(campo, "N/A")
                # Formata valores numéricos
                if isinstance(valor, float):
                    valor = f"{valor:,.2f}"
                self.analise_tree.insert("", "end", values=(descricao, valor))
        except Exception as e:
            logging.error(f"Erro ao buscar dados financeiros para {ticker}: {e}")
            messagebox.showerror("Erro", f"Não foi possível obter dados para {ticker}.")

    def update_returns_widget(self):
        """Atualiza os valores dos rendimentos exibidos no painel direito."""
        returns = self.pm.get_returns()
        for period, data in returns.items():
            self.returns_labels[period]["percentual"].configure(text=f"{data['percentual']:.2f}%")
            self.returns_labels[period]["us$"].configure(text=f"US$ {data['us$']:.2f}")
            self.returns_labels[period]["r$"].configure(text=f"R$ {data['r$']:.2f}")

    def atualizar_header(self, total_portfolio, variacao_total, valor_variacao_total, dolar_rate, valor_investido, saldo_restante):
        self.header_tree.item("total", values=("Valor total da carteira (ações + saldo):", f"US$ {total_portfolio:.2f}"))
        var_tag = "positive" if variacao_total >= 0 else "negative"
        self.header_tree.item("variacao", values=("Variação total da carteira:", f"{variacao_total:.2f}%"), tags=(var_tag,))
        var_val_tag = "positive" if valor_variacao_total >= 0 else "negative"
        self.header_tree.item("valor_variacao", values=("Valor da Variação total da carteira:", f"US$ {valor_variacao_total:.2f}"), tags=(var_val_tag,))
        self.header_tree.item("investido", values=("Valor total investido           :", f"US$ {valor_investido:.2f}"))
        self.header_tree.item("saldo", values=("Saldo restante                  :", f"US$ {saldo_restante:.2f}"))
        self.header_tree.item("inicial", values=("Valor total inicial             :", f"US$ {self.pm.valor_inicial_total:.2f}"))
        total_reais = total_portfolio * dolar_rate
        total_reais_tag = "positive" if total_reais >= self.pm.valor_inicial_total_reais else "negative"
        self.header_tree.item("total_reais", values=("Valor total em Reais            :", f"R$ {total_reais:.2f}"), tags=(total_reais_tag,))
        self.header_tree.item("inicial_reais", values=("Valor total inicial em Reais    :", f"R$ {self.pm.valor_inicial_total_reais:.2f}"))
        var_val_total_reais = (total_portfolio * dolar_rate - self.pm.valor_inicial_total_reais)
        var_reais_tag = "positive" if var_val_total_reais >= 0 else "negative"
        self.header_tree.item("variacao_reais", values=("Valor da Variação total investido em Reais    :", f"R$ {var_val_total_reais:.2f}"), tags=(var_reais_tag,))
        self.header_tree.item("dolar", values=("Valor do dólar             :", f"US$ {dolar_rate:.2f}"))

    def refresh(self):
        total_portfolio, variacao_total, valor_variacao_total, valor_investido, saldo_restante = self.pm.update_portfolio()
        dolar_rate = self.pm.get_dollar_rate()
        self.atualizar_header(total_portfolio, variacao_total, valor_variacao_total, dolar_rate, valor_investido, saldo_restante)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for ticker, dados in self.pm.portfolio.items():
            if "preco_atual" in dados:
                valor_variacao = dados["valor_atual"] - dados["custo_medio"]
                tag = "positive" if dados.get("variacao", 0) >= 0 else "negative"
                self.tree.insert("", "end", values=(
                    ticker,
                    dados["quantidade"],
                    f"US$ {dados['preco_medio']:.2f}",
                    f"US$ {dados['custo_medio']:.2f}",
                    f"US$ {dados['preco_atual']:.2f}",
                    f"US$ {dados['valor_atual']:.2f}",
                    f"{dados['variacao']:.2f}%",
                    f"US$ {valor_variacao:.2f}",
                    f"{dados.get('composicao', 0):.2f}%"
                ), tags=(tag,))
            else:
                self.tree.insert("", "end", values=(
                    ticker,
                    dados["quantidade"],
                    f"US$ {dados['preco_medio']:.2f}",
                    f"US$ {dados['custo_medio']:.2f}",
                    "-", "-", "-", "-", "-"
                ))
        self.update_returns_widget()
        self.root.after(self.update_interval_ms, self.refresh)
