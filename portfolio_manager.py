# portfolio_manager.py
import yfinance as yf
import pandas as pd
import logging
import requests
from cachetools import TTLCache, cached
from db import update_portfolio_in_db, record_transaction, get_first_purchase_date, record_portfolio_history_if_market_closed,remove_stock_from_portfolio
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
            logging.info("Tentando obter taxa do dólar")
            data = self.market_data_service.get_market_data(["USDBRL=X"])
            
            logging.info(f"Dados recebidos para dólar: {data}")

            if isinstance(data, pd.DataFrame) and not data.empty:
                # Verifica se é MultiIndex
                if isinstance(data.columns, pd.MultiIndex):
                    if "USDBRL=X" in data.columns.get_level_values(0):
                        rate = data["USDBRL=X"]["Close"].iloc[-1]
                        logging.info(f"Taxa do dólar obtida (MultiIndex): {rate}")
                        return rate
                # Se não for MultiIndex, tenta acessar diretamente
                elif "Close" in data.columns:
                    rate = data["Close"].iloc[-1]
                    logging.info(f"Taxa do dólar obtida (Single Index): {rate}")
                    return rate
                elif "USDBRL=X, Close" in data.columns:
                    rate = data["USDBRL=X, Close"].iloc[-1]
                    logging.info(f"Taxa do dólar obtida (Column Name): {rate}")
                    return rate

            logging.warning("Usando taxa do dólar padrão")
            return 5.70

        except Exception as e:
            logging.error(f"Erro ao obter taxa do dólar: {str(e)}\nDataFrame: {data if 'data' in locals() else 'None'}")
            return 5.70


    def update_portfolio(self):
        logging.info("Iniciando atualização do portfolio")
        total_valor_acoes = 0
        total_investido = 0
        
        tickers = list(self.portfolio.keys())
        logging.info(f"Tickers a serem atualizados: {tickers}")
        
        data = self.market_data_service.get_market_data(tickers)
        logging.info(f"Dados recebidos: {data}")
        
        if isinstance(data, pd.DataFrame):
            if data.empty:
                logging.error("DataFrame vazio recebido")
                return 0, 0, 0, 0, 0
                
            logging.info(f"Colunas disponíveis: {data.columns}")
            
            # Primeiro, atualiza os preços e valores
            for ticker in tickers:
                try:
                    column_name = f"{ticker}, Close"
                    if column_name in data.columns:
                        preco_atual = data[column_name].iloc[-1]
                        logging.info(f"Preço atual para {ticker}: {preco_atual}")
                        
                        self.portfolio[ticker]["preco_atual"] = preco_atual
                        self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                        preco_medio = self.portfolio[ticker]["preco_medio"]
                        self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                        
                        total_valor_acoes += self.portfolio[ticker]["valor_atual"]
                        total_investido += self.portfolio[ticker]["quantidade"] * preco_medio
                    else:
                        logging.warning(f"Coluna {column_name} não encontrada")
                except Exception as e:
                    logging.error(f"Erro ao processar {ticker}: {str(e)}")

            # Calcula o valor total do portfolio (incluindo saldo)
            saldo_restante = self.valor_inicial_total - total_investido
            total_portfolio = total_valor_acoes + saldo_restante

            # Depois, calcula a composição para cada ativo
            for ticker in tickers:
                if "valor_atual" in self.portfolio[ticker]:
                    self.portfolio[ticker]["composicao"] = (self.portfolio[ticker]["valor_atual"] / total_valor_acoes) * 100 if total_valor_acoes > 0 else 0
                    logging.info(f"Composição calculada para {ticker}: {self.portfolio[ticker]['composicao']}%")

            variacao_total = ((total_portfolio / self.valor_inicial_total) - 1) * 100 if self.valor_inicial_total > 0 else 0
            valor_variacao_total = total_portfolio - self.valor_inicial_total
            valor_total_acoes_saldo = total_valor_acoes + saldo_restante
            logging.info(f"""
            Resultados da atualização:
            Total valor ações: {total_valor_acoes}
            Total portfolio: {total_portfolio}
            Variação total: {variacao_total}
            Valor variação total: {valor_variacao_total}
            Total investido: {total_investido}
            Saldo restante: {saldo_restante}
            """)

            return valor_total_acoes_saldo, total_portfolio, variacao_total, valor_variacao_total, total_investido, saldo_restante
        else:
            logging.error(f"Tipo de dados inesperado: {type(data)}")
            return 0, 0, 0, 0, 0

    def get_returns(self):
        """
        Calcula os rendimentos para os períodos: Diário, Semanal, Mensal, Trimestral e Anual,
        com base nos dados históricos da coleção 'portfolio_history'.
        """
        valor_total_acoes_saldo, _, _, _, _, _ = self.update_portfolio()
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
            percentual = ((valor_total_acoes_saldo - valor_anterior) / valor_anterior) * 100 if valor_anterior != 0 else 0.0
            retorno_usd = valor_total_acoes_saldo - valor_anterior
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

    def sell_stock(self, ticker, quantity, price, manual_date=None):
        ticker = ticker.upper().strip()
        if ticker not in self.portfolio:
            raise ValueError("Ticker não encontrado na carteira")
        current_data = self.portfolio[ticker]
        old_quantity = current_data["quantidade"]
        if quantity > old_quantity:
            raise ValueError("Quantidade para vender maior que a disponível")
        elif quantity == old_quantity:
            del self.portfolio[ticker]
            remove_stock_from_portfolio(ticker)
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
            "preco": price,
            "observacao": observacao
        }
        if manual_date is not None:
            transaction["data_operacao_manual"] = manual_date
        record_transaction(transaction)
