# market_data_service/market_data_service.py
import yfinance as yf
import pandas as pd
import logging
import time
import threading
from typing import List, Dict, Any, Tuple
from functools import lru_cache

from .services.yfinance_service import YFinanceService
from .services.fmp_service import FMPService
from .services.quandl_service import QuandlService
from .services.finnhub_service import FinnhubService
from .services.alpha_vantage_service import AlphaVantageService
from .services.twelvedata_service import TwelveDataService
from .services.stockdata_service import StockDataService
from .services.investpy_service import InvestpyService
from .services.pandas_datareader_service import PandasDatareaderService

class MarketDataService:
    def __init__(self):
        self.ALPHA_VANTAGE_API_KEY = "NBZL62FD1HKVA0AW"
        self.FINNHUB_API_KEY = "cuqhjn9r01qsd02ec5d0cuqhjn9r01qsd02ec5dg"
        self.TWELVEDATA_API_KEY = "62f5298820cb4eff819799dad1dfcc33"
        self.STOCKDATA_API_KEY = "yFJbOlzB8nwSvKxD8EQQsWnzGQ8qhgqh1ouC6qa4"
        self.QUANDL_API_KEY = "<nLxxPsYFSxEZTHp6muGp>"
        self.FMP_API_KEY = "<8jrrXikpOdIUX5D6Hm4p677W3GfdppUq>"

        self.services = {
            'yfinance': YFinanceService(),
            'fmp': FMPService(self.FMP_API_KEY),
            'quandl': QuandlService(self.QUANDL_API_KEY),
            'finnhub': FinnhubService(self.FINNHUB_API_KEY),
            'alphavantage': AlphaVantageService(self.ALPHA_VANTAGE_API_KEY),
            'twelvedata': TwelveDataService(self.TWELVEDATA_API_KEY),
            'stockdata': StockDataService(self.STOCKDATA_API_KEY),
            'investpy': InvestpyService(),
            'pandas_datareader': PandasDatareaderService(),
        }

        # Inicia o limpador de cache
        self._market_data_cache = {}
        self._cache_ttl = 120

    def _fetch_market_data(self, tickers: List[str]) -> pd.DataFrame:
        """
        Método interno que realiza a busca efetiva dos dados
        """
        logging.info(f"Buscando dados de mercado para tickers: {tickers}")
        result = pd.DataFrame()
        
        for service_name, service in self.services.items():
            logging.info(f"Tentando serviço: {service_name}")
            try:
                for ticker in tickers:
                    price = service.get_price_data(ticker)
                    logging.info(f"Ticker: {ticker}, Preço obtido: {price}")
                    if price is not None:
                        if result.empty:
                            result = pd.DataFrame(index=[pd.Timestamp.now()])
                        result[f"{ticker}, Close"] = price
                        logging.info(f"Dados adicionados para {ticker}: {price}")
            except Exception as e:
                logging.error(f"Erro no serviço {service_name} para tickers {tickers}: {str(e)}")
                continue

            if not result.empty:
                logging.info(f"Dados obtidos com sucesso do serviço {service_name}")
                break
        
        return result

    @lru_cache(maxsize=100)

    def _get_cached_data(self, tickers_tuple: Tuple[str, ...]) -> pd.DataFrame:
        """
        Wrapper cacheado para _fetch_market_data
        """
        return self._fetch_market_data(list(tickers_tuple))

    def clear_cache(self):
        """
        Limpa o cache de dados de mercado
        """
        self._get_cached_data.cache_clear()
        logging.info("Cache limpo")

    def _start_cache_cleaner(self, ttl_seconds: int = 120):
        """
        Inicia um thread que limpa o cache periodicamente
        """
        def clean_cache():
            while True:
                time.sleep(ttl_seconds)
                self.clear_cache()

        thread = threading.Thread(target=clean_cache, daemon=True)
        thread.start()



    def get_market_data(self, tickers: List[str]) -> pd.DataFrame:
        """
        Interface pública para obter dados de mercado com cache
        """
        tickers_key = tuple(sorted(tickers))
        current_time = time.time()
        
        # Verifica se os dados estão em cache e ainda são válidos
        if tickers_key in self._market_data_cache:
            cache_time, cached_data = self._market_data_cache[tickers_key]
            if current_time - cache_time < self._cache_ttl:
                logging.info(f"Usando dados em cache para {tickers}")
                return cached_data
        
        # Se não estiver em cache ou expirou, busca novos dados
        result = self._fetch_market_data(tickers)
        
        # Atualiza o cache
        self._market_data_cache[tickers_key] = (current_time, result)
        
        return result

    def get_fundamental_data(self, ticker: str, campos: Dict[str, str]) -> Dict[str, Any]:
        result = {campo: None for campo in campos.keys()}
        
        for service_name, service in self.services.items():
            try:
                missing_fields = [k for k, v in result.items() if v is None]
                if not missing_fields:
                    break
                    
                data = service.get_fundamental_data(ticker)
                if data:
                    for campo in missing_fields:
                        if campo in data:
                            result[campo] = data[campo]
            except Exception as e:
                logging.warning(f"Erro no serviço {service_name}: {e}")
                continue
                
        return result    

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Obtém dados trimestrais de EPS e vendas
        Retorna: Lista de tuplas (Quarter, EPS, %ChgEPS, Sales, %ChgSales)
        """
        logging.info(f"Buscando dados trimestrais para {ticker}")
        result = []
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_quarterly_data'):
                    data = service.get_quarterly_data(ticker)
                    if data:
                        logging.info(f"Dados trimestrais obtidos via {service_name}")
                        return data
            except Exception as e:
                logging.error(f"Erro ao buscar dados trimestrais via {service_name}: {e}")
                continue
        
        return result

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """
        Obtém dados anuais de EPS
        Retorna: Lista de tuplas (Year, EPS, %Chg)
        """
        logging.info(f"Buscando dados anuais para {ticker}")
        result = []
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_yearly_data'):
                    data = service.get_yearly_data(ticker)
                    if data:
                        logging.info(f"Dados anuais obtidos via {service_name}")
                        return data
            except Exception as e:
                logging.error(f"Erro ao buscar dados anuais via {service_name}: {e}")
                continue
        
        return result

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """
        Obtém dados de ratings e indicadores
        Retorna: Lista de tuplas (Campo, Valor)
        """
        logging.info(f"Buscando ratings para {ticker}")
        result = []
        
        for service_name, service in self.services.items():
            try:
                if hasattr(service, 'get_ratings_data'):
                    data = service.get_ratings_data(ticker)
                    if data:
                        logging.info(f"Ratings obtidos via {service_name}")
                        return data
            except Exception as e:
                logging.error(f"Erro ao buscar ratings via {service_name}: {e}")
                continue
        
        return result

    