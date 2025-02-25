import requests
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class TwelveDataService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.twelvedata.com"
        self.endpoints = {
            'price': '/price',
            'quote': '/quote',
            'fundamentals': '/fundamentals',
            'earnings': '/earnings',
            'statistics': '/statistics',
            'technicals': '/technical_indicators'
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
            params['apikey'] = self.api_key
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'status' in data and data['status'] == 'error':
                logging.error(f"Twelve Data API error: {data.get('message')}")
                return None
            return data
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na requisição Twelve Data: {e}")
            return None

    def get_price_data(self, ticker: str) -> float:
        """Obtém o preço atual da ação"""
        try:
            data = self._make_request(self.endpoints['price'], {'symbol': ticker})
            if data and 'price' in data:
                return float(data['price'])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Twelve Data Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """Obtém dados fundamentalistas"""
        try:
            # Buscar dados fundamentais
            fundamental_data = self._make_request(self.endpoints['fundamentals'], {'symbol': ticker})
            # Buscar cotação atual
            quote_data = self._make_request(self.endpoints['quote'], {'symbol': ticker})
            # Buscar estatísticas
            stats_data = self._make_request(self.endpoints['statistics'], {'symbol': ticker})

            result = {}

            if quote_data:
                result.update({
                    'previousClose': self._safe_float(quote_data.get('previous_close')),
                    'open': self._safe_float(quote_data.get('open')),
                    'dayLow': self._safe_float(quote_data.get('low')),
                    'dayHigh': self._safe_float(quote_data.get('high')),
                    'volume': self._safe_float(quote_data.get('volume')),
                })

            if fundamental_data:
                metrics = fundamental_data.get('fundamentals', {})
                result.update({
                    'marketCap': self._safe_float(metrics.get('market_capitalization')),
                    'peRatio': self._safe_float(metrics.get('pe_ratio')),
                    'forwardPE': self._safe_float(metrics.get('forward_pe')),
                    'dividendYield': self._safe_float(metrics.get('dividend_yield')),
                    'grossMargins': self._safe_float(metrics.get('gross_margin')),
                    'profitMargins': self._safe_float(metrics.get('profit_margin')),
                    'roic': self._safe_float(metrics.get('roic')),
                    'returnOnEquity': self._safe_float(metrics.get('roe')),
                    'revenueGrowth': self._safe_float(metrics.get('revenue_growth')),
                    'netIncomeGrowth': self._safe_float(metrics.get('net_income_growth'))
                })

            if stats_data:
                result.update({
                    'ocfNetIncomeRatio': self._safe_float(stats_data.get('ocf_to_net_income')),
                    'netDebtEbitda': self._safe_float(stats_data.get('net_debt_to_ebitda')),
                    'insiderOwnership': self._safe_float(stats_data.get('insider_ownership')),
                    'capexSales': self._safe_float(stats_data.get('capex_to_revenue')),
                    'capexOCF': self._safe_float(stats_data.get('capex_to_operating_cash_flow'))
                })

            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Twelve Data Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """Obtém dados trimestrais"""
        try:
            data = self._make_request(self.endpoints['earnings'], {
                'symbol': ticker,
                'interval': 'quarterly',
                'past_days': 730  # Últimos 2 anos
            })

            result = []
            if data and 'earnings' in data:
                quarters = data['earnings'][:8]  # Últimos 8 trimestres
                
                for i, quarter in enumerate(quarters):
                    date = datetime.strptime(quarter['date'], '%Y-%m-%d')
                    quarter_str = date.strftime('%b-%y')
                    
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
            return self.handle_error(e, ticker, "Twelve Data Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """Obtém dados anuais"""
        try:
            data = self._make_request(self.endpoints['earnings'], {
                'symbol': ticker,
                'interval': 'annual'
            })

            result = []
            if data and 'earnings' in data:
                years = data['earnings'][:10]  # Últimos 10 anos
                
                for i, year in enumerate(years):
                    year_str = datetime.strptime(year['date'], '%Y-%m-%d').strftime('%Y')
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
            return self.handle_error(e, ticker, "Twelve Data Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """Obtém ratings e indicadores técnicos"""
        try:
            # Buscar dados técnicos
            technicals = self._make_request(self.endpoints['technicals'], {
                'symbol': ticker,
                'interval': '1day'
            })
            
            # Buscar dados fundamentais para métricas adicionais
            fundamentals = self._make_request(self.endpoints['fundamentals'], {'symbol': ticker})
            
            ratings = []
            
            # Adicionar indicadores técnicos
            if technicals:
                technical_indicators = [
                    ('RSI', 'rsi'),
                    ('MACD', 'macd'),
                    ('ADX', 'adx'),
                    ('Stochastic %K', 'stoch'),
                    ('Bollinger Bands', 'bbands')
                ]
                
                for label, key in technical_indicators:
                    if key in technicals:
                        value = self._safe_float(technicals[key])
                        if value is not None:
                            ratings.append((label, f"{value:.2f}"))

            # Adicionar métricas fundamentais
            if fundamentals and 'fundamentals' in fundamentals:
                fund = fundamentals['fundamentals']
                metrics = [
                    ('P/E Ratio', 'pe_ratio'),
                    ('Forward P/E', 'forward_pe'),
                    ('PEG Ratio', 'peg_ratio'),
                    ('Price/Book', 'price_to_book'),
                    ('Dividend Yield', 'dividend_yield'),
                    ('Beta', 'beta')
                ]
                
                for label, key in metrics:
                    value = self._safe_float(fund.get(key))
                    if value is not None:
                        if key == 'dividend_yield':
                            ratings.append((label, f"{value:.2f}%"))
                        else:
                            ratings.append((label, f"{value:.2f}"))

            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "Twelve Data Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """Tratamento de erros específico"""
        error_msg = str(error)
        if "Invalid API key" in error_msg:
            logging.error(f"Chave API inválida para Twelve Data")
        elif "Rate limit exceeded" in error_msg:
            logging.error(f"Limite de requisições excedido para Twelve Data")
        elif "Symbol not found" in error_msg:
            logging.error(f"Símbolo {ticker} não encontrado no Twelve Data")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None