# portfolio_manager.py
import yfinance as yf
import pandas as pd
import logging
from db import update_portfolio_in_db, record_transaction, record_portfolio_history

class PortfolioManager:
    """
    Gerencia os dados e cálculos da carteira.
    """
    def __init__(self, portfolio, valor_inicial_total, valor_inicial_total_reais):
        self.portfolio = portfolio
        self.valor_inicial_total = valor_inicial_total
        self.valor_inicial_total_reais = valor_inicial_total_reais
        # A data de início pode ser definida via configuração
        self.data_inicio = None

    def get_dollar_rate(self):
        try:
            ticker = yf.Ticker("USDBRL=X")
            data = ticker.history(period="1d")
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            logging.error(f"Erro ao obter taxa do dólar: {e}")
        return 5.70

    def update_portfolio(self):
        total_valor_acoes = 0
        total_investido = 0

        tickers = list(self.portfolio.keys())
        try:
            data = yf.download(tickers, period="1d", group_by='ticker', threads=True)
        except Exception as e:
            logging.error(f"Erro ao baixar dados para múltiplos tickers: {e}")
            data = None

        for ticker in tickers:
            if data is not None:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        if ticker in data.columns.get_level_values(0):
                            preco_atual = data[ticker]['Close'].iloc[-1]
                        else:
                            logging.warning(f"Dados para {ticker} não encontrados.")
                            continue
                    else:
                        preco_atual = data['Close'].iloc[-1]
                    self.portfolio[ticker]["preco_atual"] = preco_atual
                    self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                    preco_medio = self.portfolio[ticker]["preco_medio"]
                    self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                    total_valor_acoes += self.portfolio[ticker]["valor_atual"]
                except Exception as e:
                    logging.error(f"Erro ao atualizar {ticker}: {e}")
            else:
                logging.error("Nenhum dado disponível para atualizar a carteira.")

        for ticker in tickers:
            total_investido += self.portfolio[ticker].get("custo_medio", 0)
        saldo_restante = self.valor_inicial_total - total_investido
        total_portfolio = total_valor_acoes + saldo_restante

        for ticker in tickers:
            if "valor_atual" in self.portfolio[ticker]:
                self.portfolio[ticker]["composicao"] = (self.portfolio[ticker]["valor_atual"] / total_portfolio) * 100

        variacao_total = ((total_portfolio - self.valor_inicial_total) / self.valor_inicial_total) * 100
        valor_variacao_total = total_portfolio - self.valor_inicial_total

        # Se desejar, registre o histórico (pode ser via agendamento)
        # record_portfolio_history(total_portfolio)

        return total_portfolio, variacao_total, valor_variacao_total, total_investido, saldo_restante

    def buy_stock(self, ticker, quantity, price, manual_date=None):
        ticker = ticker.upper().strip()
        if ticker in self.portfolio:
            current_data = self.portfolio[ticker]
            old_quantity = current_data["quantidade"]
            old_total_cost = current_data["custo_medio"]
            new_quantity = old_quantity + quantity
            new_total_cost = old_total_cost + (quantity * price)
            new_avg_price = new_total_cost / new_quantity
            self.portfolio[ticker]["quantidade"] = new_quantity
            self.portfolio[ticker]["preco_medio"] = new_avg_price
            self.portfolio[ticker]["custo_medio"] = new_total_cost
        else:
            self.portfolio[ticker] = {
                "quantidade": quantity,
                "preco_medio": price,
                "custo_medio": quantity * price
            }
        logging.info(f"Compra efetuada: {ticker}, Qtd: {quantity}, Preço: {price}")
        update_portfolio_in_db(self.portfolio)
        transaction = {
            "ticker": ticker,
            "tipo": "compra",
            "quantidade": quantity,
            "preco": price,
            "observacao": "Aumento de posição"
        }
        if manual_date is not None:
            transaction["data_operacao_manual"] = manual_date
        record_transaction(transaction)

    def sell_stock(self, ticker, quantity, manual_date=None):
        ticker = ticker.upper().strip()
        if ticker not in self.portfolio:
            raise ValueError("Ticker não encontrado na carteira")
        current_data = self.portfolio[ticker]
        old_quantity = current_data["quantidade"]
        if quantity > old_quantity:
            raise ValueError("Quantidade para vender maior que a disponível")
        elif quantity == old_quantity:
            del self.portfolio[ticker]
            logging.info(f"Venda completa: {ticker} removido da carteira.")
            observacao = "Zeragem de posição"
        else:
            new_quantity = old_quantity - quantity
            old_total_cost = current_data["custo_medio"]
            new_total_cost = old_total_cost * (new_quantity / old_quantity)
            new_avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
            self.portfolio[ticker]["quantidade"] = new_quantity
            self.portfolio[ticker]["preco_medio"] = new_avg_price
            self.portfolio[ticker]["custo_medio"] = new_total_cost
            logging.info(f"Venda parcial: {ticker}, Qtd vendida: {quantity}, Qtd restante: {new_quantity}")
            observacao = "Redução de posição"
        update_portfolio_in_db(self.portfolio)
        transaction = {
            "ticker": ticker,
            "tipo": "venda",
            "quantidade": quantity,
            "preco": None,  # Preencher se disponível
            "observacao": observacao
        }
        if manual_date is not None:
            transaction["data_operacao_manual"] = manual_date
        record_transaction(transaction)
