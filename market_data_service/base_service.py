import logging
from abc import ABC, abstractmethod
from typing import Optional, Union, Dict, Any, List, Tuple
import pandas as pd

class BaseDataService(ABC):
    """Classe base para todos os serviços de dados de mercado"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        
    @abstractmethod
    def get_price_data(self, ticker: str) -> Optional[float]:
        """Obtém dados de preço para um ticker"""
        pass
    
    @abstractmethod
    def get_fundamental_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Obtém dados fundamentalistas para um ticker"""
        pass
    
    @abstractmethod
    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        pass

    @abstractmethod
    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        pass

    @abstractmethod
    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        pass

    def handle_error(self, error: Exception, ticker: str, service_name: str):
        """Tratamento padrão de erros"""
        logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None    
   
   