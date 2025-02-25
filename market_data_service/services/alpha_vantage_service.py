import requests
from typing import List, Tuple
from ..base_service import BaseDataService

class AlphaVantageService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://www.alphavantage.co/query"

    def get_price_data(self, ticker: str) -> float:
        try:
            url = f"{self.base_url}?function=GLOBAL_QUOTE&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            if "Global Quote" in data and "05. price" in data["Global Quote"]:
                return float(data["Global Quote"]["05. price"])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Alpha Vantage")

    def get_fundamental_data(self, ticker: str) -> dict:
        try:
            url = f"{self.base_url}?function=OVERVIEW&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()

            if data:
                return {
                    'peRatio': float(data.get('PERatio', 0)) if data.get('PERatio') else None,
                    'returnOnEquity': float(data.get('ReturnOnEquityTTM', 0)) if data.get('ReturnOnEquityTTM') else None,
                    'dividendYield': float(data.get('DividendYield', 0)) if data.get('DividendYield') else None,
                    'profitMargin': float(data.get('ProfitMargin', 0)) if data.get('ProfitMargin') else None,
                }
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Alpha Vantage")
    
    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        try:
            # Buscar dados de EPS trimestrais
            url = f"{self.base_url}?function=EARNINGS&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            # Buscar dados de receita trimestrais
            url_income = f"{self.base_url}?function=INCOME_STATEMENT&symbol={ticker}&apikey={self.api_key}"
            response_income = requests.get(url_income)
            income_data = response_income.json()

            result = []
            if 'quarterlyEarnings' in data:
                quarterly_earnings = data['quarterlyEarnings']
                quarterly_reports = income_data.get('quarterlyReports', [])
                
                # Combinar dados de EPS e receita
                for i, earnings in enumerate(quarterly_earnings[:8]):  # Últimos 8 trimestres
                    quarter = earnings.get('fiscalDateEnding', '')
                    quarter = datetime.strptime(quarter, '%Y-%m-%d').strftime('%b-%y')
                    eps = self._safe_float(earnings.get('reportedEPS', 0))
                    
                    # Calcular variação do EPS
                    if i < len(quarterly_earnings) - 1:
                        prev_eps = self._safe_float(quarterly_earnings[i+1].get('reportedEPS', 0))
                        eps_change = ((eps / prev_eps) - 1) * 100 if prev_eps and eps else 0
                    else:
                        eps_change = 0
                    
                    # Buscar dados de receita correspondentes
                    sales = None
                    sales_change = 0
                    for report in quarterly_reports:
                        if report.get('fiscalDateEnding') == earnings.get('fiscalDateEnding'):
                            sales = self._safe_float(report.get('totalRevenue', 0))
                            if sales:
                                sales = sales / 1_000_000  # Converter para milhões
                    
                    result.append((
                        quarter,
                        f"{eps:.2f}" if eps else "N/A",
                        f"{eps_change:+.1f}%" if eps_change else "N/A",
                        f"{sales:.1f}" if sales else "N/A",
                        f"{sales_change:+.1f}%" if sales_change else "N/A"
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Alpha Vantage Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        try:
            url = f"{self.base_url}?function=EARNINGS&symbol={ticker}&apikey={self.api_key}"
            response = requests.get(url)
            data = response.json()

            result = []
            if 'annualEarnings' in data:
                annual_earnings = data['annualEarnings']
                for i, earnings in enumerate(annual_earnings[:10]):  # Últimos 10 anos
                    year = earnings.get('fiscalDateEnding', '')[:4]
                    eps = self._safe_float(earnings.get('reportedEPS', 0))
                    
                    # Calcular variação
                    if i < len(annual_earnings) - 1:
                        prev_eps = self._safe_float(annual_earnings[i+1].get('reportedEPS', 0))
                        change = ((eps / prev_eps) - 1) * 100 if prev_eps and eps else 0
                    else:
                        change = 0
                    
                    result.append((
                        year,
                        f"{eps:.2f}" if eps else "N/A",
                        f"{change:+.1f}%" if change else "N/A"
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Alpha Vantage Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        try:
            # Combinar dados de diferentes endpoints
            overview_url = f"{self.base_url}?function=OVERVIEW&symbol={ticker}&apikey={self.api_key}"
            overview_response = requests.get(overview_url)
            overview_data = overview_response.json()

            ratings = [
                ("Análise Técnica", overview_data.get('AnalystRating', 'N/A')),
                ("Beta", overview_data.get('Beta', 'N/A')),
                ("52-Week High", f"${overview_data.get('52WeekHigh', 'N/A')}"),
                ("52-Week Low", f"${overview_data.get('52WeekLow', 'N/A')}"),
                ("50-Day MA", overview_data.get('50DayMovingAverage', 'N/A')),
                ("200-Day MA", overview_data.get('200DayMovingAverage', 'N/A')),
                ("P/E Ratio", overview_data.get('PERatio', 'N/A')),
                ("Forward P/E", overview_data.get('ForwardPE', 'N/A')),
                ("PEG Ratio", overview_data.get('PEGRatio', 'N/A')),
                ("Price/Book", overview_data.get('PriceToBookRatio', 'N/A')),
                ("Price/Sales", overview_data.get('PriceToSalesRatioTTM', 'N/A')),
                ("EV/EBITDA", overview_data.get('EVToEBITDA', 'N/A')),
                ("Profit Margin", f"{self._safe_float(overview_data.get('ProfitMargin', 0))*100:.2f}%"),
                ("Operating Margin", f"{self._safe_float(overview_data.get('OperatingMarginTTM', 0))*100:.2f}%")
            ]
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "Alpha Vantage Ratings")