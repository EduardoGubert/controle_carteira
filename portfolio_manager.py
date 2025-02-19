# portfolio_manager.py
import yfinance as yf
import pandas as pd
import logging
import requests
from cachetools import TTLCache, cached
from db import update_portfolio_in_db, record_transaction, get_first_purchase_date, record_portfolio_history_if_market_closed
from market_data_service import MarketDataService  # supondo que já esteja implementado

class PortfolioManager:
    """
    Gerencia os dados e regras de negócio da carteira.
    """
    def __init__(self, portfolio, valor_inicial_total, valor_inicial_total_reais, market_data_service=None):
        self.portfolio = portfolio
        self.valor_inicial_total = valor_inicial_total
        self.valor_inicial_total_reais = valor_inicial_total_reais
        self.data_inicio = get_first_purchase_date()
        self.market_data_service = market_data_service or MarketDataService()

    def get_dollar_rate(self):    
        try:
            # Reaproveitamos get_market_data para um único ticker: "USDBRL=X"
            data = self.market_data_service.get_market_data(["USDBRL=X"])

            # Se 'data' for um DataFrame e não estiver vazio:
            if isinstance(data, pd.DataFrame) and not data.empty:
                # Verifica se é MultiIndex (vários tickers) ou não
                if isinstance(data.columns, pd.MultiIndex):
                    # Checa se 'USDBRL=X' está nas colunas do nível 0
                    if "USDBRL=X" in data.columns.get_level_values(0):
                        # Retorna o último valor de Close
                        return data["USDBRL=X"]["Close"].iloc[-1]
                    else:
                        # Caso contrário, pode ser que seja uma única coluna "Close"
                        return data["Close"].iloc[-1]
                else:
                    # Se não for MultiIndex, assumimos que a coluna "Close" é única
                    return data["Close"].iloc[-1]

            # Se 'data' for um dicionário (fallback) e contiver a chave "USDBRL=X":
            elif isinstance(data, dict) and "USDBRL=X" in data:
                df = data["USDBRL=X"]
                if not df.empty:
                    return df["Close"].iloc[-1]

        except Exception as e:
            logging.error(f"Erro ao obter taxa do dólar: {e}")

        # Se chegou até aqui, retorna valor padrão
        return 5.70


    def update_portfolio(self):
        total_valor_acoes = 0
        total_investido = 0
        tickers = list(self.portfolio.keys())
        data = self.market_data_service.get_market_data(tickers)
        if isinstance(data, pd.DataFrame):
            if isinstance(data.columns, pd.MultiIndex):
                for ticker in tickers:
                    if ticker in data.columns.get_level_values(0):
                        preco_atual = data[ticker]["Close"].iloc[-1]
                    else:
                        logging.warning(f"Dados para {ticker} não encontrados.")
                        continue
                    self.portfolio[ticker]["preco_atual"] = preco_atual
                    self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                    preco_medio = self.portfolio[ticker]["preco_medio"]
                    self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                    total_valor_acoes += self.portfolio[ticker]["valor_atual"]
            else:
                try:
                    preco_atual = data["Close"].iloc[-1]
                    for ticker in tickers:
                        self.portfolio[ticker]["preco_atual"] = preco_atual
                        self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                        preco_medio = self.portfolio[ticker]["preco_medio"]
                        self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                        total_valor_acoes += self.portfolio[ticker]["valor_atual"]
                except Exception as e:
                    logging.error(f"Erro ao processar dados: {e}")
        elif isinstance(data, dict):
            for ticker in tickers:
                try:
                    if ticker in data:
                        preco_atual = data[ticker]["Close"].iloc[-1]
                        self.portfolio[ticker]["preco_atual"] = preco_atual
                        self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                        preco_medio = self.portfolio[ticker]["preco_medio"]
                        self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                        total_valor_acoes += self.portfolio[ticker]["valor_atual"]
                    else:
                        logging.warning(f"Fallback: Dados para {ticker} não encontrados.")
                except Exception as e:
                    logging.error(f"Erro ao processar fallback para {ticker}: {e}")

        for ticker in tickers:
            total_investido += self.portfolio[ticker].get("custo_medio", 0)
        saldo_restante = self.valor_inicial_total - total_investido
        total_portfolio = total_valor_acoes + saldo_restante

        for ticker in tickers:
            if "valor_atual" in self.portfolio[ticker]:
                self.portfolio[ticker]["composicao"] = (self.portfolio[ticker]["valor_atual"] / total_portfolio) * 100

        variacao_total = ((total_portfolio - self.valor_inicial_total) / self.valor_inicial_total) * 100
        valor_variacao_total = total_portfolio - self.valor_inicial_total

        # Registra o histórico se o mercado já fechou
        from db import record_portfolio_history_if_market_closed
        record_portfolio_history_if_market_closed(total_portfolio)

        return total_portfolio, variacao_total, valor_variacao_total, total_investido, saldo_restante

    def get_returns(self):
        """
        Calcula os rendimentos para os períodos: Diário, Semanal, Mensal, Trimestral e Anual,
        com base nos dados históricos da coleção 'portfolio_history'.
        """
        total_portfolio, _, _, _, _ = self.update_portfolio()
        dollar_rate = self.get_dollar_rate()
        from db import get_portfolio_history
        history = get_portfolio_history()
        if history.empty:
            return {
                "Diário": {"percentual": 0.0, "us$": 0.0, "r$": 0.0},
                "Semanal": {"percentual": 0.0, "us$": 0.0, "r$": 0.0},
                "Mensal": {"percentual": 0.0, "us$": 0.0, "r$": 0.0},
                "Trimestral": {"percentual": 0.0, "us$": 0.0, "r$": 0.0},
                "Anual": {"percentual": 0.0, "us$": 0.0, "r$": 0.0},
            }
        history['data'] = pd.to_datetime(history['data'])
        hoje = pd.Timestamp.now().normalize()

        def calcular_retorno(dias):
            data_referencia = hoje - pd.Timedelta(days=dias)
            registros_validos = history[history['data'] <= data_referencia]
            if registros_validos.empty:
                if not history.empty:
                    valor_anterior = history.iloc[0]['valor_total']  # ou o "último" registro
                else:
                    return 0.0, 0.0, 0.0
            else:    
                valor_anterior = registros_validos.iloc[-1]['valor_total']
            percentual = ((total_portfolio - valor_anterior) / valor_anterior) * 100 if valor_anterior != 0 else 0.0
            retorno_usd = total_portfolio - valor_anterior
            retorno_br = retorno_usd * dollar_rate
            return percentual, retorno_usd, retorno_br

        retornos = {
            "Diário": calcular_retorno(1),
            "Semanal": calcular_retorno(7),
            "Mensal": calcular_retorno(30),
            "Trimestral": calcular_retorno(90),
            "Anual": calcular_retorno(365)
        }
        retorno_dict = {}
        for periodo, (pct, usd, br) in retornos.items():
            retorno_dict[periodo] = {"percentual": pct, "us$": usd, "r$": br}
        return retorno_dict

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
            "preco": None,
            "observacao": observacao
        }
        if manual_date is not None:
            transaction["data_operacao_manual"] = manual_date
        record_transaction(transaction)
