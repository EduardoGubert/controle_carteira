import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from config import UPDATE_INTERVAL_MS
from db import update_config_in_db

class PortfolioGUI:
    """
    Interface gráfica para exibir a carteira em tempo real.
    """
    def __init__(self, portfolio_manager):
        self.pm = portfolio_manager
        self.root = tk.Tk()
        self.root.title("Carteira Tempo Real")
        self.root.geometry("900x600")
        self.update_interval_ms = UPDATE_INTERVAL_MS  # valor inicial vindo do config
        self.create_widgets()
        self.refresh()
        self.root.mainloop()

    def create_widgets(self):
        """Cria e configura os widgets da interface."""
        # Cabeçalho com informações resumidas
        self.header_frame = tk.Frame(self.root)
        self.header_frame.pack(pady=10)
        self.header_tree = ttk.Treeview(self.header_frame, columns=("Descricao", "Valor"), show="headings", height=10)
        self.header_tree.heading("Descricao", text="Descrição")
        self.header_tree.heading("Valor", text="Valor")
        self.header_tree.column("Descricao", anchor="center", width=300)
        self.header_tree.column("Valor", anchor="center", width=150)
        self.header_tree.pack()

        # Configuração das tags para cores
        self.header_tree.tag_configure("positive", foreground="green")
        self.header_tree.tag_configure("negative", foreground="red")

        # Itens do cabeçalho
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

        # Botão de operações (comprar/vender)
        trade_button = tk.Button(self.root, text="Operar (Comprar/Vender)", command=self.open_trade_window)
        trade_button.pack(pady=5)
        
        # Botão para abrir a janela de configurações
        config_button = tk.Button(self.root, text="Configurações", command=self.open_config_window)
        config_button.pack(pady=5)

        # Tabela principal da carteira
        columns = ("Ticker", "Quantidade", "Preço Médio", "Custo Médio", "Preço Atual", "Valor Atual", "Variação (%)", "Variação (US$)", "Composição (%)")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=15)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.pack(expand=True, fill="both", padx=20, pady=10)
        self.tree.tag_configure("positive", foreground="green")
        self.tree.tag_configure("negative", foreground="red")

    def open_config_window(self):
        """Abre uma janela para alterar as configurações."""
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

        tk.Label(config_window, text="Data de Início da Carteira (dd/mm/yyyy):").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        entry_data_inicio = tk.Entry(config_window)
        # Se já houver data definida, formata-a
        if self.pm.data_inicio:
            entry_data_inicio.insert(0, self.pm.data_inicio.strftime("%d/%m/%Y"))
        entry_data_inicio.grid(row=3, column=1, padx=5, pady=5)

        def save_config():
            try:
                novo_valor_usd = float(entry_valor_usd.get())
                novo_valor_reais = float(entry_valor_reais.get())
                novo_interval = int(entry_interval.get())
            except ValueError:
                messagebox.showerror("Erro", "Insira valores numéricos válidos.")
                return

            data_inicio_input = entry_data_inicio.get().strip()
            if data_inicio_input != "":
                try:
                    novo_data_inicio = datetime.strptime(data_inicio_input, "%d/%m/%Y")
                except ValueError:
                    messagebox.showerror("Erro", "Data de Início deve estar no formato dd/mm/yyyy.")
                    return
            else:
                novo_data_inicio = None

            # Atualiza as configurações na memória
            self.pm.valor_inicial_total = novo_valor_usd
            self.pm.valor_inicial_total_reais = novo_valor_reais
            self.update_interval_ms = novo_interval
            self.pm.data_inicio = novo_data_inicio

            # Salva no MongoDB
            new_config = {
                "valor_inicial_total_usd": novo_valor_usd,
                "valor_inicial_total_reais": novo_valor_reais,
                "update_interval_ms": novo_interval,
                "data_inicio": novo_data_inicio
            }
            update_config_in_db(new_config)
            messagebox.showinfo("Sucesso", "Configurações atualizadas!")
            config_window.destroy()

        save_button = tk.Button(config_window, text="Salvar", command=save_config)
        save_button.grid(row=4, column=0, columnspan=2, pady=10)

    def open_trade_window(self):
        """Abre uma janela para operações de compra/venda."""
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
        self.root.after(self.update_interval_ms, self.refresh)
