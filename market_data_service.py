# market_data_service.py
import yfinance as yf
import pandas as pd
import requests
import logging
from cachetools import TTLCache, cached

# Configuração do cache: guarda até 100 itens com TTL de 120 segundos (2 minutos)
data_cache = TTLCache(maxsize=100, ttl=120)

class MarketDataService:
    ALPHA_VANTAGE_API_KEY = "NBZL62FD1HKVA0AW"  # Insira sua chave de Alpha Vantage
    FINNHUB_API_KEY = "cuqhjn9r01qsd02ec5d0cuqhjn9r01qsd02ec5dg"
    TWELVEDATA_API_KEY = "62f5298820cb4eff819799dad1dfcc33"
    STOCKDATA_API_KEY = "yFJbOlzB8nwSvKxD8EQQsWnzGQ8qhgqh1ouC6qa4"

    @cached(data_cache, key=lambda self, tickers: tuple(tickers))
    def get_yfinance_data(self, tickers):
        try:
            # Converte de volta para lista para passar para yf.download
            return yf.download(list(tickers), period="1d", group_by='ticker', threads=True)
        except Exception as e:
            logging.error(f"Erro na consulta yfinance: {e}")
            return pd.DataFrame()

    def get_alpha_vantage_close(self, ticker):
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={self.ALPHA_VANTAGE_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            time_series = data.get("Time Series (Daily)")
            if time_series:
                latest_date = sorted(time_series.keys())[-1]
                return float(time_series[latest_date]["4. close"])
            else:
                logging.error(f"Alpha Vantage não retornou dados para {ticker}: {data.get('Note') or data}")
        except Exception as e:
            logging.error(f"Erro na chamada Alpha Vantage para {ticker}: {e}")
        return None

    def get_finnhub_quote(self, ticker):
        """Obtém o preço atual do ticker via Finnhub."""
        url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={self.FINNHUB_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            if "c" in data:
                return float(data["c"])
            else:
                logging.error(f"Finnhub: dados inválidos para {ticker}: {data}")
        except Exception as e:
            logging.error(f"Erro na chamada Finnhub para {ticker}: {e}")
        return None

    def get_twelvedata_quote(self, ticker):
        """Obtém o preço atual do ticker via Twelve Data."""
        url = f"https://api.twelvedata.com/time_series?symbol={ticker}&interval=1day&outputsize=1&apikey={self.TWELVEDATA_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            if "values" in data and data["values"]:
                return float(data["values"][0]["close"])
            else:
                logging.error(f"Twelve Data: dados inválidos para {ticker}: {data.get('message') or data}")
        except Exception as e:
            logging.error(f"Erro na chamada Twelve Data para {ticker}: {e}")
        return None

    def get_stockdata_org_quote(self, ticker):
        """Obtém o preço atual do ticker via StockData.org."""
        url = f"https://api.stockdata.org/v1/data/quote?symbols={ticker}&api_token={self.STOCKDATA_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return float(data["data"][0]["last"])
            else:
                logging.error(f"StockData.org: dados inválidos para {ticker}: {data.get('message') or data}")
        except Exception as e:
            logging.error(f"Erro na chamada StockData.org para {ticker}: {e}")
        return None

    def get_market_data(self, tickers):
        # Primeiro, tenta com yfinance
        logging.info("Tentando obter dados via yfinance...")
        data = self.get_yfinance_data(tickers)
        if not data.empty:
            logging.info("Dados obtidos com sucesso via yfinance")
            return data

        # Se falhar, tenta fallback com Alpha Vantage, Finnhub, Twelve Data e StockData.org, nessa ordem
        logging.info("yfinance falhou. Usando serviços alternativos para obter dados de mercado.")
        fallback_data = {}
        
        for ticker in tickers:
            # Try each service in sequence until we get a valid price
            close = None
            services = [
                ("Alpha Vantage", self.get_alpha_vantage_close),
                ("Finnhub", self.get_finnhub_quote),
                ("Twelve Data", self.get_twelvedata_quote),
                ("StockData.org", self.get_stockdata_org_quote)
            ]
            
            for service_name, service_func in services:
                logging.info(f"Tentando obter dados para {ticker} via {service_name}...")
                close = service_func(ticker)
                if close is not None:
                    logging.info(f"Dados obtidos com sucesso para {ticker} via {service_name}")
                    break
                else:
                    logging.warning(f"Falha ao obter dados para {ticker} via {service_name}")
            
            if close is not None:
                fallback_data[ticker] = pd.DataFrame({"Close": [close]})
            else:
                logging.error(f"Dados não encontrados para {ticker} em nenhum serviço disponível")
        
        return fallback_data if fallback_data else pd.DataFrame()
