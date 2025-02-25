import requests
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class StockDataService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.stockdata.org/v1"
        self.endpoints = {
            'quote': f"{self.base_url}/data/quote",
            'fundamentals': f"{self.base_url}/fundamentals",
            'earnings': f"{self.base_url}/earnings",
            'metrics': f"{self.base_url}/metrics"
        }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _make_request(self, endpoint: str, params: dict) -> Optional[dict]:
        """Faz requisição à API com tratamento de erros"""
        try:
            params['api_token'] = self.api_key
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]
            logging.warning(f"StockData.org: Sem dados para parâmetros {params}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição StockData.org: {e}")
            return None

    def get_price_data(self, ticker: str) -> float:
        """Obtém o preço atual da ação"""
        try:
            data = self._make_request(self.endpoints['quote'], {'symbols': ticker})
            if data and 'close' in data:
                return float(data['close'])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "StockData Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """Obtém dados fundamentalistas"""
        try:
            # Dados básicos de cotação
            quote_data = self._make_request(self.endpoints['quote'], {'symbols': ticker})
            # Dados fundamentalistas
            fundamental_data = self._make_request(self.endpoints['fundamentals'], {'symbols': ticker})
            # Métricas adicionais
            metrics_data = self._make_request(self.endpoints['metrics'], {'symbols': ticker})

            result = {}

            if quote_data:
                result.update({
                    'previousClose': self._safe_float(quote_data.get('previous_close')),
                    'open': self._safe_float(quote_data.get('open')),
                    'dayLow': self._safe_float(quote_data.get('day_low')),
                    'dayHigh': self._safe_float(quote_data.get('day_high')),
                    'volume': self._safe_float(quote_data.get('volume')),
                    'marketCap': self._safe_float(quote_data.get('market_cap'))
                })

            if fundamental_data:
                result.update({
                    'peRatio': self._safe_float(fundamental_data.get('pe_ratio')),
                    'forwardPE': self._safe_float(fundamental_data.get('forward_pe')),
                    'dividendYield': self._safe_float(fundamental_data.get('dividend_yield')),
                    'grossMargins': self._safe_float(fundamental_data.get('gross_margin')),
                    'profitMargins': self._safe_float(fundamental_data.get('profit_margin')),
                    'roic': self._safe_float(fundamental_data.get('roic')),
                    'returnOnEquity': self._safe_float(fundamental_data.get('roe')),
                    'revenueGrowth': self._safe_float(fundamental_data.get('revenue_growth')),
                    'netIncomeGrowth': self._safe_float(fundamental_data.get('net_income_growth'))
                })

            if metrics_data:
                result.update({
                    'ocfNetIncomeRatio': self._safe_float(metrics_data.get('ocf_net_income_ratio')),
                    'netDebtEbitda': self._safe_float(metrics_data.get('net_debt_to_ebitda')),
                    'insiderOwnership': self._safe_float(metrics_data.get('insider_ownership')),
                    'capexSales': self._safe_float(metrics_data.get('capex_to_sales')),
                    'capexOCF': self._safe_float(metrics_data.get('capex_to_ocf'))
                })

            return result
        except Exception as e:
            return self.handle_error(e, ticker, "StockData Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """Obtém dados trimestrais"""
        try:
            earnings_data = self._make_request(
                self.endpoints['earnings'],
                {'symbols': ticker, 'period': 'quarterly', 'limit': 8}
            )

            result = []
            if earnings_data and 'quarterly' in earnings_data:
                quarters = earnings_data['quarterly']
                for i, quarter in enumerate(quarters):
                    quarter_date = datetime.strptime(quarter['date'], '%Y-%m-%d')
                    quarter_str = quarter_date.strftime('%b-%y')
                    
                    eps = self._safe_float(quarter.get('eps'))
                    revenue = self._safe_float(quarter.get('revenue'))
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if i < len(quarters) - 1:
                        prev_eps = self._safe_float(quarters[i + 1].get('eps'))
                        prev_revenue = self._safe_float(quarters[i + 1].get('revenue'))
                        
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
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "StockData Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """Obtém dados anuais"""
        try:
            earnings_data = self._make_request(
                self.endpoints['earnings'],
                {'symbols': ticker, 'period': 'annual', 'limit': 10}
            )

            result = []
            if earnings_data and 'annual' in earnings_data:
                years = earnings_data['annual']
                for i, year in enumerate(years):
                    year_str = str(datetime.strptime(year['date'], '%Y-%m-%d').year)
                    eps = self._safe_float(year.get('eps'))
                    
                    # Calcular variação
                    change = "N/A"
                    if i < len(years) - 1:
                        prev_eps = self._safe_float(years[i + 1].get('eps'))
                        if eps and prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        year_str,
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "StockData Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """Obtém ratings e indicadores"""
        try:
            # Combinar dados de diferentes endpoints
            quote_data = self._make_request(self.endpoints['quote'], {'symbols': ticker})
            metrics_data = self._make_request(self.endpoints['metrics'], {'symbols': ticker})
            
            ratings = []
            
            if quote_data:
                ratings.extend([
                    ("52-Week High", f"${self._safe_float(quote_data.get('52_week_high')):.2f}"),
                    ("52-Week Low", f"${self._safe_float(quote_data.get('52_week_low')):.2f}"),
                    ("50-Day MA", f"${self._safe_float(quote_data.get('50_day_ma')):.2f}"),
                    ("200-Day MA", f"${self._safe_float(quote_data.get('200_day_ma')):.2f}"),
                    ("P/E Ratio", f"{self._safe_float(quote_data.get('pe_ratio')):.2f}"),
                    ("Market Cap", f"${self._safe_float(quote_data.get('market_cap'))/1e9:.2f}B"),
                    ("Volume", f"{self._safe_float(quote_data.get('volume'))/1e6:.1f}M")
                ])

            if metrics_data:
                for key, value in metrics_data.items():
                    if isinstance(value, (int, float)):
                        ratings.append((
                            key.replace('_', ' ').title(),
                            f"{self._safe_float(value):.2f}"
                        ))

            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "StockData Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """Tratamento de erros específico"""
        error_msg = str(error)
        if "Invalid API token" in error_msg:
            logging.error(f"Token API inválido para StockData.org")
        elif "Rate limit exceeded" in error_msg:
            logging.error(f"Limite de requisições excedido para StockData.org")
        elif "Symbol not found" in error_msg:
            logging.error(f"Símbolo {ticker} não encontrado no StockData.org")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None