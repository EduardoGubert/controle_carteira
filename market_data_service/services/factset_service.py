import requests
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService
from fds.client import ConfigurationError
from fds.sdk.utils.authentication import ConfidentialClient

class FactSetService(BaseDataService):
    def __init__(self, client_id: str, client_secret: str):
        super().__init__(api_key=None)
        self.base_url = "https://api.factset.com/analytics/lookups/v3"
        self._initialize_client(client_id, client_secret)

    def _initialize_client(self, client_id: str, client_secret: str):
        """Inicializa o cliente OAuth2 do FactSet"""
        try:
            self.factset_client = ConfidentialClient(
                client_id=client_id,
                client_secret=client_secret
            )
        except ConfigurationError as e:
            logging.error(f"Erro ao inicializar cliente FactSet: {e}")
            raise

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Faz requisição autenticada à API do FactSet"""
        try:
            headers = {
                "Authorization": f"Bearer {self.factset_client.get_access_token()}",
                "Accept": "application/json"
            }
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logging.error(f"Erro na requisição FactSet: {e}")
            return None

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def get_price_data(self, ticker: str) -> float:
        """Obtém o preço atual via FactSet"""
        try:
            endpoint = "/prices/realtime"
            params = {
                "ids": ticker,
                "fields": "price"
            }
            data = self._make_request(endpoint, params)
            
            if data and "data" in data:
                return self._safe_float(data["data"][0]["price"])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "FactSet Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """Obtém dados fundamentais via FactSet"""
        try:
            # Buscar dados fundamentais
            fundamental_endpoint = "/fundamentals"
            fundamental_params = {
                "ids": ticker,
                "metrics": ",".join([
                    "FF_PE", "FF_MKTCAP", "FF_DIV_YLD",
                    "FF_GROSS_MGN", "FF_NET_MGN", "FF_ROE",
                    "FF_ROIC", "FF_REV_GRTH", "FF_NET_INC_GRTH",
                    "FF_OCF_NET_INC", "FF_NET_DEBT_EBITDA",
                    "FF_INSIDER_OWN", "FF_CAPEX_SALES", "FF_CAPEX_OCF"
                ])
            }
            
            fundamental_data = self._make_request(fundamental_endpoint, fundamental_params)
            
            result = {}
            if fundamental_data and "data" in fundamental_data:
                metrics = fundamental_data["data"][0]
                
                result.update({
                    'peRatio': self._safe_float(metrics.get("FF_PE")),
                    'marketCap': self._safe_float(metrics.get("FF_MKTCAP")),
                    'dividendYield': self._safe_float(metrics.get("FF_DIV_YLD")),
                    'grossMargins': self._safe_float(metrics.get("FF_GROSS_MGN")),
                    'profitMargins': self._safe_float(metrics.get("FF_NET_MGN")),
                    'roic': self._safe_float(metrics.get("FF_ROIC")),
                    'returnOnEquity': self._safe_float(metrics.get("FF_ROE")),
                    'revenueGrowth': self._safe_float(metrics.get("FF_REV_GRTH")),
                    'netIncomeGrowth': self._safe_float(metrics.get("FF_NET_INC_GRTH")),
                    'ocfNetIncomeRatio': self._safe_float(metrics.get("FF_OCF_NET_INC")),
                    'netDebtEbitda': self._safe_float(metrics.get("FF_NET_DEBT_EBITDA")),
                    'insiderOwnership': self._safe_float(metrics.get("FF_INSIDER_OWN")),
                    'capexSales': self._safe_float(metrics.get("FF_CAPEX_SALES")),
                    'capexOCF': self._safe_float(metrics.get("FF_CAPEX_OCF"))
                })
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "FactSet Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """Obtém dados trimestrais via FactSet"""
        try:
            endpoint = "/time-series"
            params = {
                "ids": ticker,
                "metrics": "FF_EPS,FF_SALES",
                "frequency": "QUARTERLY",
                "start_date": (datetime.now().year - 2),  # Últimos 2 anos
                "end_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            data = self._make_request(endpoint, params)
            result = []
            
            if data and "data" in data:
                time_series = data["data"]
                
                for i, period in enumerate(time_series):
                    quarter_date = datetime.strptime(period["date"], "%Y-%m-%d")
                    quarter_str = quarter_date.strftime("%b-%y")
                    
                    eps = self._safe_float(period.get("FF_EPS"))
                    revenue = self._safe_float(period.get("FF_SALES"))
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if i < len(time_series) - 1:
                        prev_eps = self._safe_float(time_series[i + 1].get("FF_EPS"))
                        prev_revenue = self._safe_float(time_series[i + 1].get("FF_SALES"))
                        
                        if eps and prev_eps:
                            eps_change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                        if revenue and prev_revenue:
                            revenue_change = f"{((revenue / prev_revenue) - 1) * 100:+.1f}%"
                    
                    result.append((
                        quarter_str,
                        f"{eps:.2f}" if eps else "N/A",
                        eps_change,
                        f"{revenue/1_000_000:.1f}" if revenue else "N/A",
                        revenue_change
                    ))
            
            return result[:8]  # Retorna apenas os últimos 8 trimestres
        except Exception as e:
            return self.handle_error(e, ticker, "FactSet Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """Obtém dados anuais via FactSet"""
        try:
            endpoint = "/time-series"
            params = {
                "ids": ticker,
                "metrics": "FF_EPS",
                "frequency": "YEARLY",
                "start_date": (datetime.now().year - 10),  # Últimos 10 anos
                "end_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            data = self._make_request(endpoint, params)
            result = []
            
            if data and "data" in data:
                time_series = data["data"]
                
                for i, period in enumerate(time_series):
                    year = datetime.strptime(period["date"], "%Y-%m-%d").year
                    eps = self._safe_float(period.get("FF_EPS"))
                    
                    # Calcular variação
                    change = "N/A"
                    if i < len(time_series) - 1:
                        prev_eps = self._safe_float(time_series[i + 1].get("FF_EPS"))
                        if eps and prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        str(year),
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "FactSet Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """Obtém ratings e métricas via FactSet"""
        try:
            endpoint = "/analytics"
            params = {
                "ids": ticker,
                "metrics": ",".join([
                    "FF_RATING", "FF_TGT_PRICE", "FF_BETA",
                    "FF_52W_HIGH", "FF_52W_LOW", "FF_50D_MA",
                    "FF_200D_MA", "FF_RSI", "FF_VOL_30D"
                ])
            }
            
            data = self._make_request(endpoint, params)
            ratings = []
            
            if data and "data" in data:
                metrics = data["data"][0]
                
                # Adicionar métricas disponíveis
                metrics_map = {
                    "FactSet Rating": "FF_RATING",
                    "Target Price": "FF_TGT_PRICE",
                    "Beta": "FF_BETA",
                    "52-Week High": "FF_52W_HIGH",
                    "52-Week Low": "FF_52W_LOW",
                    "50-Day MA": "FF_50D_MA",
                    "200-Day MA": "FF_200D_MA",
                    "RSI": "FF_RSI",
                    "30-Day Volatility": "FF_VOL_30D"
                }
                
                for label, key in metrics_map.items():
                    value = metrics.get(key)
                    if value is not None:
                        if isinstance(value, float):
                            ratings.append((label, f"{value:.2f}"))
                        else:
                            ratings.append((label, str(value)))
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "FactSet Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """Tratamento de erros específico para FactSet"""
        error_msg = str(error)
        if "401" in error_msg:
            logging.error(f"Erro de autenticação FactSet. Verifique suas credenciais.")
        elif "403" in error_msg:
            logging.error(f"Acesso negado à API FactSet. Verifique suas permissões.")
        elif "404" in error_msg:
            logging.error(f"Ticker {ticker} não encontrado no FactSet")
        elif "429" in error_msg:
            logging.error(f"Limite de requisições FactSet excedido")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None