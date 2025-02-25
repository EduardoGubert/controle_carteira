import requests
import logging
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class FinnhubService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://finnhub.io/api/v1"

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def get_price_data(self, ticker: str) -> float:
        """
        Obtém o preço atual do ticker via Finnhub.
        """
        try:
            url = f"{self.base_url}/quote?symbol={ticker}&token={self.api_key}"
            response = requests.get(url)
            data = response.json()
            if "c" in data:  # 'c' é o preço atual no Finnhub
                return float(data["c"])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Finnhub")

    def get_fundamental_data(self, ticker: str) -> dict:
        """
        Obtém dados fundamentalistas via Finnhub.
        """
        try:
            # Busca métricas básicas
            metrics_url = f"{self.base_url}/stock/metric?symbol={ticker}&metric=all&token={self.api_key}"
            metrics_response = requests.get(metrics_url)
            metrics_data = metrics_response.json()

            # Busca dados financeiros
            financials_url = f"{self.base_url}/stock/financials?symbol={ticker}&statement=income&freq=annual&token={self.api_key}"
            financials_response = requests.get(financials_url)
            financials_data = financials_response.json()

            # Busca dados da empresa
            company_url = f"{self.base_url}/stock/profile2?symbol={ticker}&token={self.api_key}"
            company_response = requests.get(company_url)
            company_data = company_response.json()

            result = {}
            
            # Processar métricas básicas
            if "metric" in metrics_data:
                metrics = metrics_data["metric"]
                result.update({
                    # Dados básicos
                    'previousClose': self._safe_float(metrics.get('52WeekHigh')),
                    'open': None,  # Não disponível diretamente
                    'dayLow': self._safe_float(metrics.get('52WeekLow')),
                    'dayHigh': self._safe_float(metrics.get('52WeekHigh')),
                    'volume': self._safe_float(metrics.get('10DayAverageTradingVolume')),
                    'marketCap': self._safe_float(company_data.get('marketCapitalization')),
                    'trailingPE': self._safe_float(metrics.get('peBasicExclExtraTTM')),
                    'forwardPE': self._safe_float(metrics.get('forwardPE')),
                    'dividendYield': self._safe_float(metrics.get('dividendYieldTTM')),

                    # Indicadores fundamentalistas
                    'peRatio': self._safe_float(metrics.get('peBasicExclExtraTTM')),
                    'grossMargins': self._safe_float(metrics.get('grossMarginTTM')),
                    'profitMargins': self._safe_float(metrics.get('netProfitMarginTTM')),
                    'roic': self._safe_float(metrics.get('roicTTM')),
                    'returnOnEquity': self._safe_float(metrics.get('roeTTM')),
                    'revenueGrowth': self._safe_float(metrics.get('revenueGrowthTTM3Y')),
                    'netIncomeGrowth': self._safe_float(metrics.get('netIncomeGrowthTTM3Y')),
                    'ocfNetIncomeRatio': self._safe_float(metrics.get('cfToNetIncomeTTM')),
                    'netDebtEbitda': self._safe_float(metrics.get('netDebtToEBITDATTM')),
                    'insiderOwnership': self._safe_float(metrics.get('insiderPercentHeld')),
                    'capexSales': self._safe_float(metrics.get('capexToRevenueTTM')),
                    'capexOCF': self._safe_float(metrics.get('capexToOperatingCashFlowTTM'))
                })

            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Finnhub")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Obtém dados trimestrais de EPS e vendas.
        """
        try:
            # Busca dados financeiros trimestrais
            url = f"{self.base_url}/stock/financials?symbol={ticker}&statement=income&freq=quarterly&token={self.api_key}"
            response = requests.get(url)
            data = response.json()

            result = []
            if "financials" in data:
                financials = sorted(data["financials"], key=lambda x: x.get("period"), reverse=True)[:8]
                
                for i, quarter in enumerate(financials):
                    period = datetime.strptime(quarter.get("period", ""), "%Y-%m-%d")
                    quarter_str = period.strftime("%b-%y")
                    
                    revenue = self._safe_float(quarter.get("revenue"))
                    net_income = self._safe_float(quarter.get("netIncome"))
                    shares = self._safe_float(quarter.get("sharesOutstanding"))
                    
                    eps = net_income / shares if net_income and shares else None
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if i < len(financials) - 1:
                        prev_revenue = self._safe_float(financials[i + 1].get("revenue"))
                        prev_net_income = self._safe_float(financials[i + 1].get("netIncome"))
                        prev_shares = self._safe_float(financials[i + 1].get("sharesOutstanding"))
                        prev_eps = prev_net_income / prev_shares if prev_net_income and prev_shares else None
                        
                        if eps and prev_eps:
                            eps_change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                        if revenue and prev_revenue:
                            revenue_change = f"{((revenue / prev_revenue) - 1) * 100:+.1f}%"
                    
                    result.append((
                        quarter_str,
                        f"{eps:.2f}" if eps else "N/A",
                        eps_change,
                        f"{revenue/1_000_000:.1f}" if revenue else "N/A",  # Converter para milhões
                        revenue_change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Finnhub Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """
        Obtém dados anuais de EPS.
        """
        try:
            url = f"{self.base_url}/stock/financials?symbol={ticker}&statement=income&freq=annual&token={self.api_key}"
            response = requests.get(url)
            data = response.json()

            result = []
            if "financials" in data:
                financials = sorted(data["financials"], key=lambda x: x.get("period"), reverse=True)[:10]
                
                for i, year in enumerate(financials):
                    period = datetime.strptime(year.get("period", ""), "%Y-%m-%d")
                    year_str = period.strftime("%Y")
                    
                    net_income = self._safe_float(year.get("netIncome"))
                    shares = self._safe_float(year.get("sharesOutstanding"))
                    
                    eps = net_income / shares if net_income and shares else None
                    
                    # Calcular variação
                    change = "N/A"
                    if i < len(financials) - 1:
                        prev_net_income = self._safe_float(financials[i + 1].get("netIncome"))
                        prev_shares = self._safe_float(financials[i + 1].get("sharesOutstanding"))
                        prev_eps = prev_net_income / prev_shares if prev_net_income and prev_shares else None
                        
                        if eps and prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        year_str,
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Finnhub Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """
        Obtém dados de ratings e indicadores técnicos.
        """
        try:
            # Busca recomendações de analistas
            recommendation_url = f"{self.base_url}/stock/recommendation?symbol={ticker}&token={self.api_key}"
            recommendation_response = requests.get(recommendation_url)
            recommendation_data = recommendation_response.json()

            # Busca indicadores técnicos
            technical_url = f"{self.base_url}/stock/technicals?symbol={ticker}&resolution=D&token={self.api_key}"
            technical_response = requests.get(technical_url)
            technical_data = technical_response.json()

            ratings = []
            
            # Adicionar recomendações de analistas
            if recommendation_data and len(recommendation_data) > 0:
                latest = recommendation_data[0]
                ratings.extend([
                    ("Strong Buy", str(latest.get("strongBuy", "N/A"))),
                    ("Buy", str(latest.get("buy", "N/A"))),
                    ("Hold", str(latest.get("hold", "N/A"))),
                    ("Sell", str(latest.get("sell", "N/A"))),
                    ("Strong Sell", str(latest.get("strongSell", "N/A")))
                ])

            # Adicionar métricas técnicas se disponíveis
            if "metric" in technical_data:
                metrics = technical_data["metric"]
                for key, value in metrics.items():
                    if value is not None:
                        ratings.append((key, str(value)))

            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "Finnhub Ratings")