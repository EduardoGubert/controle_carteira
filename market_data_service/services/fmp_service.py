import requests
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class FMPService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://financialmodelingprep.com/api/v3"
        
    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
        
    def get_price_data(self, ticker: str) -> float:
        try:
            url = f"{self.base_url}/quote/{ticker}?apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            if isinstance(data, list) and len(data) > 0 and "price" in data[0]:
                return float(data[0]["price"])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "FMP")
            
    def get_fundamental_data(self, ticker: str) -> dict:
        try:
            result = {}
            
            # Dados básicos da empresa
            url_profile = f"{self.base_url}/profile/{ticker}?apikey={self.api_key}"
            profile_data = requests.get(url_profile).json()
            
            # Ratios financeiros
            url_ratios = f"{self.base_url}/ratios-ttm/{ticker}?apikey={self.api_key}"
            ratios_data = requests.get(url_ratios).json()
            
            # Métricas chave
            url_metrics = f"{self.base_url}/key-metrics-ttm/{ticker}?apikey={self.api_key}"
            metrics_data = requests.get(url_metrics).json()
            
            # Dados financeiros
            url_financial = f"{self.base_url}/financial-growth/{ticker}?apikey={self.api_key}"
            financial_data = requests.get(url_financial).json()
            
            if isinstance(profile_data, list) and len(profile_data) > 0:
                profile = profile_data[0]
                result.update({
                    'previousClose': self._safe_float(profile.get('price')),
                    'open': self._safe_float(profile.get('open')),
                    'dayLow': self._safe_float(profile.get('dayLow')),
                    'dayHigh': self._safe_float(profile.get('dayHigh')),
                    'volume': self._safe_float(profile.get('volume')),
                    'marketCap': self._safe_float(profile.get('mktCap'))
                })
            
            if isinstance(ratios_data, list) and len(ratios_data) > 0:
                ratios = ratios_data[0]
                result.update({
                    'dividendYield': self._safe_float(ratios.get('dividendYieldTTM')),
                    'peRatio': self._safe_float(ratios.get('peRatioTTM')),
                    'roic': self._safe_float(ratios.get('roicTTM')),
                    'returnOnEquity': self._safe_float(ratios.get('returnOnEquityTTM')),
                    'profitMargins': self._safe_float(ratios.get('netProfitMarginTTM')),
                    'grossMargins': self._safe_float(ratios.get('grossProfitMarginTTM')),
                    'operatingMargin': self._safe_float(ratios.get('operatingProfitMarginTTM')),
                    'priceToBook': self._safe_float(ratios.get('priceToBookRatioTTM')),
                    'priceToSales': self._safe_float(ratios.get('priceToSalesRatioTTM'))
                })
            
            if isinstance(metrics_data, list) and len(metrics_data) > 0:
                metrics = metrics_data[0]
                result.update({
                    'netDebtEbitda': self._safe_float(metrics.get('netDebtToEBITDATTM')),
                    'capexSales': self._safe_float(metrics.get('capexToRevenueTTM')),
                    'capexOCF': self._safe_float(metrics.get('capexToOperatingCashFlowTTM')),
                    'ocfNetIncomeRatio': self._safe_float(metrics.get('operatingCashFlowToNetIncomeTTM'))
                })
            
            if isinstance(financial_data, list) and len(financial_data) > 0:
                financial = financial_data[0]
                result.update({
                    'revenueGrowth': self._safe_float(financial.get('revenueGrowth')),
                    'netIncomeGrowth': self._safe_float(financial.get('netIncomeGrowth'))
                })
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "FMP")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        try:
            url = f"{self.base_url}/income-statement/{ticker}?period=quarter&limit=8&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            result = []
            if isinstance(data, list):
                for i, quarter in enumerate(data):
                    date = datetime.strptime(quarter.get('date', ''), '%Y-%m-%d')
                    quarter_str = date.strftime('%b-%y')
                    
                    eps = self._safe_float(quarter.get('eps'))
                    revenue = self._safe_float(quarter.get('revenue'))
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if i < len(data) - 1:
                        prev_eps = self._safe_float(data[i + 1].get('eps'))
                        prev_revenue = self._safe_float(data[i + 1].get('revenue'))
                        
                        if eps and prev_eps:
                            eps_change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                        if revenue and prev_revenue:
                            revenue_change = f"{((revenue / prev_revenue) - 1) * 100:+.1f}%"
                    
                    revenue_millions = f"{revenue / 1_000_000:.1f}" if revenue else "N/A"
                    eps_str = f"{eps:.2f}" if eps else "N/A"
                    
                    result.append((
                        quarter_str,
                        eps_str,
                        eps_change,
                        revenue_millions,
                        revenue_change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "FMP Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        try:
            url = f"{self.base_url}/income-statement/{ticker}?limit=10&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            result = []
            if isinstance(data, list):
                for i, year in enumerate(data):
                    year_str = year.get('date', '')[:4]
                    eps = self._safe_float(year.get('eps'))
                    
                    # Calcular variação
                    change = "N/A"
                    if i < len(data) - 1:
                        prev_eps = self._safe_float(data[i + 1].get('eps'))
                        if eps and prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    eps_str = f"{eps:.2f}" if eps else "N/A"
                    
                    result.append((year_str, eps_str, change))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "FMP Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        try:
            # Dados de rating
            url_rating = f"{self.base_url}/rating/{ticker}?apikey={self.api_key}"
            rating_data = requests.get(url_rating).json()
            
            # Dados técnicos
            url_metrics = f"{self.base_url}/key-metrics-ttm/{ticker}?apikey={self.api_key}"
            metrics_data = requests.get(url_metrics).json()
            
            ratings = []
            
            if isinstance(rating_data, list) and len(rating_data) > 0:
                rating = rating_data[0]
                ratings.extend([
                    ("Rating Geral", rating.get('rating', 'N/A')),
                    ("Rating ROE", rating.get('roeRating', 'N/A')),
                    ("Rating ROA", rating.get('roaRating', 'N/A')),
                    ("Rating D/E", rating.get('deRating', 'N/A')),
                    ("Rating P/E", rating.get('peRating', 'N/A')),
                    ("Rating P/B", rating.get('pbRating', 'N/A'))
                ])
            
            if isinstance(metrics_data, list) and len(metrics_data) > 0:
                metrics = metrics_data[0]
                ratings.extend([
                    ("P/E Ratio", f"{self._safe_float(metrics.get('peRatioTTM', 'N/A')):.2f}"),
                    ("P/B Ratio", f"{self._safe_float(metrics.get('pbRatioTTM', 'N/A')):.2f}"),
                    ("EV/EBITDA", f"{self._safe_float(metrics.get('enterpriseValueOverEBITDATTM', 'N/A')):.2f}"),
                    ("Dividend Yield", f"{self._safe_float(metrics.get('dividendYieldTTM', 'N/A')):.2f}%"),
                    ("Debt/Equity", f"{self._safe_float(metrics.get('debtToEquityTTM', 'N/A')):.2f}"),
                    ("Current Ratio", f"{self._safe_float(metrics.get('currentRatioTTM', 'N/A')):.2f}")
                ])
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "FMP Ratings")