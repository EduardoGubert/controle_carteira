# market_data_service.py
import yfinance as yf
import pandas as pd
import requests
import logging
import quandl
from cachetools import TTLCache, cached

# Configuração do cache: guarda até 100 itens com TTL de 120 segundos (2 minutos)
data_cache = TTLCache(maxsize=100, ttl=120)

class MarketDataService:
    ALPHA_VANTAGE_API_KEY = "NBZL62FD1HKVA0AW"  # Insira sua chave de Alpha Vantage
    FINNHUB_API_KEY = "cuqhjn9r01qsd02ec5d0cuqhjn9r01qsd02ec5dg"
    TWELVEDATA_API_KEY = "62f5298820cb4eff819799dad1dfcc33"
    STOCKDATA_API_KEY = "yFJbOlzB8nwSvKxD8EQQsWnzGQ8qhgqh1ouC6qa4"
    QUANDL_API_KEY = "<nLxxPsYFSxEZTHp6muGp>"
    FMP_API_KEY = "<8jrrXikpOdIUX5D6Hm4p677W3GfdppUq>"
    STOCKDEX_API_KEY = "yFJbOlzB8nwSvKxD8EQQsWnzGQ8qhgqh1ouC6qa4" 

    @cached(data_cache, key=lambda self, tickers: tuple(tickers))
    def get_yfinance_data(self, tickers):
        try:
            # Tenta baixar todos os tickers de uma vez
            ticker_totais = yf.download(list(tickers), period="1d", group_by='ticker', threads=True)
            
            # Se não conseguir dados ou retornar vazio, tenta um por um
            if ticker_totais.empty:
                ticker_totais = pd.DataFrame()
                for ticker in tickers:
                    try:
                        ticker_unitario = yf.Ticker(ticker)
                        data = ticker_unitario.history(period="1d")
                        if not data.empty:
                            # Adiciona os dados do ticker individual ao DataFrame total
                            if ticker_totais.empty:
                                ticker_totais = pd.DataFrame(index=data.index)
                            ticker_totais[f"{ticker}, Close"] = data['Close']
                        else:
                            logging.warning(f"Não foi possível obter dados para {ticker}")
                            
                    except Exception as e:
                        logging.error(f"Erro ao atualizar {ticker}: {e}")
                        
            return ticker_totais
        except Exception as e:
            logging.error(f"Erro na consulta yfinance: {e}")
            return pd.DataFrame()
        
    def get_quandl_data(self, ticker):
        """
        Exemplo de obtenção de dados via Quandl.
        Necessita instalar 'quandl' (pip install quandl) e configurar QUANDL_API_KEY.
        """
        try:
            quandl.ApiConfig.api_key = self.QUANDL_API_KEY
            # Ex.: ticker = "WIKI/AAPL" -> ajusta conforme doc oficial e o mercado que deseja
            df = quandl.get(ticker, rows=1)  # pega apenas 1 linha (a mais recente)
            if not df.empty:
                # Supondo que a coluna seja 'Close'
                return float(df['Close'].iloc[-1])
        except Exception as e:
            logging.error(f"Erro na chamada Quandl para {ticker}: {e}")
        return None
    
    def get_fmpapi_close(self, ticker):
        """
        Exemplo de obtenção de dados via Financial Modeling Prep (fmpapi).
        Documentação: https://site.financialmodelingprep.com/developer/docs/
        """
        base_url = "https://financialmodelingprep.com/api/v3/quote/"
        url = f"{base_url}{ticker}?apikey={self.FMP_API_KEY}"
        try:
            r = requests.get(url)
            data = r.json()
            if isinstance(data, list) and len(data) > 0 and "price" in data[0]:
                return float(data[0]["price"])
            else:
                logging.error(f"FMPAPI: Dados inválidos para {ticker}: {data}")
        except Exception as e:
            logging.error(f"Erro na chamada FMPAPI para {ticker}: {e}")
        return None
    
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
    
    def get_stockdex_close(self, ticker):
        """
        Exemplo hipotético de API Stockdex.
        Ajuste conforme a documentação real do Stockdex.
        """
        url = f"https://api.stockdex.com/v1/quote?symbol={ticker}&apikey={self.STOCKDEX_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            # Supondo que a resposta tenha um campo 'close'
            if "close" in data:
                return float(data["close"])
            else:
                logging.error(f"Stockdex: dados inválidos para {ticker}: {data}")
        except Exception as e:
            logging.error(f"Erro na chamada Stockdex para {ticker}: {e}")
        return None
    
    def get_investpy_close(self, ticker, country="united states"):
        """
        Exemplo de uso do Investpy para obter dados recentes.
        Necessita 'investpy' (pip install investpy).
        
        OBS.: O investpy funciona melhor com símbolos do tipo 'AAPL' e nomes de país.
        Ajuste conforme doc oficial: https://github.com/alvarobartt/investpy
        """
        try:
            # Exemplo: investpy.get_stock_recent_data(stock='AAPL', country='united states')
            df = investpy.get_stock_recent_data(stock=ticker, country=country)
            if not df.empty:
                return float(df['Close'].iloc[-1])
        except Exception as e:
            logging.error(f"Erro na chamada Investpy para {ticker}: {e}")
        return None
    
    def get_pandas_datareader_close(self, ticker):
        """
        Exemplo de uso do pandas_datareader para obter dados de ações (via Yahoo).
        Necessita 'pandas_datareader' (pip install pandas-datareader).
        """
        try:
            df = pdr.DataReader(ticker, 'yahoo', pd.Timestamp.now() - pd.Timedelta(days=1), pd.Timestamp.now())
            if not df.empty:
                return float(df['Close'].iloc[-1])
        except Exception as e:
            logging.error(f"Erro na chamada pandas_datareader para {ticker}: {e}")
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
                ("StockData.org", self.get_stockdata_org_quote),
                ("Quandl", self.get_quandl_data),
                ("FMPAPI", self.get_fmpapi_close),
                # ("Stockdex", self.get_stockdex_close),
                ("Investpy", lambda t: self.get_investpy_close(t, country="united states")),
                ("Pandas DataReader", self.get_pandas_datareader_close),
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

    def get_fundamental_data(self, ticker, campos):
        """
        Tenta obter valores para os campos informados em `campos` usando:
        1) yfinance (Ticker.info)
        2) Fallback com get_market_data (para 'previousClose', etc.)

        :param ticker: string, ex. "AAPL"
        :param campos: dict { "previousClose": "Fech. Anterior", "open": "Abertura", ... }
                    As chaves são os nomes dos campos no .info do yfinance
        :return: dict { "previousClose": float ou None, "open": float ou None, ... }
        """
        # Cria um dict de resultado com todas as chaves = None
        resultado = {campo: None for campo in campos.keys()}

        # 1) Tentar via yfinance: Ticker.info
        try:
            yfticker = yf.Ticker(ticker)
            info = yfticker.info  # dict com vários campos
            if info and len(info) > 0:
                for campo in resultado.keys():
                    valor = info.get(campo, None)
                    resultado[campo] = valor
        except Exception as e:
            logging.warning(f"Yfinance falhou ou não retornou info para {ticker}: {e}")

        # 2) Identifica quais campos ainda estão None
        missing_fields = [k for k, v in resultado.items() if v is None]
        if missing_fields:
            logging.info(f"Campos faltando para {ticker}: {missing_fields}")
            # Tenta fallback, ex.: get_market_data (que só retorna 'Close' por padrão).
            fallback = self.get_market_data([ticker])

            # Se for DataFrame
            if isinstance(fallback, pd.DataFrame) and not fallback.empty:
                try:
                    if isinstance(fallback.columns, pd.MultiIndex):
                        if ticker in fallback.columns.get_level_values(0):
                            # Exemplo: se "previousClose" estiver faltando, definimos = Close[-1]
                            # Caso deseje, você pode mapear "open", "high", "low" caso haja colunas extras
                            # mas por padrão, get_market_data retorna apenas 'Close'.
                            close_val = fallback[ticker]["Close"].iloc[-1]
                            if "previousClose" in resultado and resultado["previousClose"] is None:
                                resultado["previousClose"] = close_val
                    else:
                        close_val = fallback["Close"].iloc[-1]
                        if "previousClose" in resultado and resultado["previousClose"] is None:
                            resultado["previousClose"] = close_val

                except Exception as e:
                    logging.error(f"Erro ao processar fallback DataFrame p/ {ticker}: {e}")

            # Se for dict
            elif isinstance(fallback, dict) and ticker in fallback:
                df = fallback[ticker]
                if not df.empty:
                    close_val = df["Close"].iloc[-1]
                    if "previousClose" in resultado and resultado["previousClose"] is None:
                        resultado["previousClose"] = close_val

        # 3) Retorna o dict de resultado
        return resultado
