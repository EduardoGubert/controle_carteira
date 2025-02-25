import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
import pandas_datareader as pdr
import pandas as pd
import yfinance as yf  # Usado como complemento para dados fundamentais
from ..base_service import BaseDataService

class PandasDatareaderService(BaseDataService):
    def __init__(self):
        super().__init__(api_key=None)
        self._initialize_readers()

    def _initialize_readers(self):
        """Inicializa os diferentes readers disponíveis"""
        self.readers = {
            'yahoo': pdr.DataReader,
            'iex': pdr.DataReader,
            'av-daily': pdr.DataReader
        }

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _format_ticker(self, ticker: str) -> str:
        """Formata o ticker adequadamente"""
        if not ticker.endswith('.SA') and not any(c.isdigit() for c in ticker):
            ticker = f"{ticker}.SA"
        return ticker

    def get_price_data(self, ticker: str) -> float:
        """
        Obtém o preço mais recente usando pandas_datareader
        """
        try:
            ticker = self._format_ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            
            df = pdr.DataReader(ticker, 'yahoo', start_date, end_date)
            
            if not df.empty:
                return float(df['Close'].iloc[-1])
            return None
            
        except Exception as e:
            return self.handle_error(e, ticker, "Pandas Datareader Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """
        Obtém dados fundamentais usando uma combinação de pandas_datareader e yfinance
        """
        try:
            ticker = self._format_ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=2)
            
            # Dados básicos via pandas_datareader
            df = pdr.DataReader(ticker, 'yahoo', start_date, end_date)
            
            # Usar yfinance para dados fundamentais complementares
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info if hasattr(yf_ticker, 'info') else {}
            
            result = {
                # Dados básicos do pandas_datareader
                'previousClose': float(df['Close'].iloc[-2]) if len(df) > 1 else None,
                'open': float(df['Open'].iloc[-1]) if not df.empty else None,
                'dayLow': float(df['Low'].iloc[-1]) if not df.empty else None,
                'dayHigh': float(df['High'].iloc[-1]) if not df.empty else None,
                'volume': float(df['Volume'].iloc[-1]) if not df.empty else None,
                
                # Dados complementares do yfinance
                'marketCap': self._safe_float(info.get('marketCap')),
                'trailingPE': self._safe_float(info.get('trailingPE')),
                'forwardPE': self._safe_float(info.get('forwardPE')),
                'dividendYield': self._safe_float(info.get('dividendYield')),
                
                # Indicadores fundamentalistas
                'peRatio': self._safe_float(info.get('trailingPE')),
                'grossMargins': self._safe_float(info.get('grossMargins')),
                'profitMargins': self._safe_float(info.get('profitMargins')),
                'roic': self._safe_float(info.get('returnOnCapital')),
                'returnOnEquity': self._safe_float(info.get('returnOnEquity')),
                'revenueGrowth': self._safe_float(info.get('revenueGrowth')),
                'netIncomeGrowth': None,  # Não disponível diretamente
                'ocfNetIncomeRatio': None,  # Não disponível diretamente
                'netDebtEbitda': None,  # Não disponível diretamente
                'insiderOwnership': self._safe_float(info.get('heldPercentInsiders')),
                'capexSales': None,  # Não disponível diretamente
                'capexOCF': None  # Não disponível diretamente
            }
            
            return result
            
        except Exception as e:
            return self.handle_error(e, ticker, "Pandas Datareader Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Obtém dados trimestrais usando yfinance como complemento
        """
        try:
            ticker = self._format_ticker(ticker)
            yf_ticker = yf.Ticker(ticker)
            
            result = []
            
            # Obter dados financeiros trimestrais
            earnings = yf_ticker.quarterly_earnings if hasattr(yf_ticker, 'quarterly_earnings') else pd.DataFrame()
            financials = yf_ticker.quarterly_financials if hasattr(yf_ticker, 'quarterly_financials') else pd.DataFrame()
            
            if not earnings.empty and not financials.empty:
                for date in earnings.index[:8]:  # Últimos 8 trimestres
                    quarter_str = date.strftime('%b-%y')
                    
                    eps = earnings.loc[date, 'Earnings'] if date in earnings.index else None
                    revenue = financials.loc[date, 'Total Revenue'] if date in financials.index else None
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if eps is not None and len(earnings.index) > earnings.index.get_loc(date) + 1:
                        prev_date = earnings.index[earnings.index.get_loc(date) + 1]
                        prev_eps = earnings.loc[prev_date, 'Earnings']
                        if prev_eps and eps:
                            eps_change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    if revenue is not None and len(financials.index) > financials.index.get_loc(date) + 1:
                        prev_date = financials.index[financials.index.get_loc(date) + 1]
                        prev_revenue = financials.loc[prev_date, 'Total Revenue']
                        if prev_revenue and revenue:
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
            return self.handle_error(e, ticker, "Pandas Datareader Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """
        Obtém dados anuais usando yfinance como complemento
        """
        try:
            ticker = self._format_ticker(ticker)
            yf_ticker = yf.Ticker(ticker)
            
            result = []
            
            # Obter dados financeiros anuais
            earnings = yf_ticker.earnings if hasattr(yf_ticker, 'earnings') else pd.DataFrame()
            
            if not earnings.empty:
                for year in earnings.index[-10:]:  # Últimos 10 anos
                    eps = earnings.loc[year, 'Earnings']
                    
                    # Calcular variação
                    change = "N/A"
                    if year > earnings.index[0]:
                        prev_eps = earnings.loc[year - 1, 'Earnings'] if year - 1 in earnings.index else None
                        if prev_eps and eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        str(year),
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
            
        except Exception as e:
            return self.handle_error(e, ticker, "Pandas Datareader Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """
        Obtém ratings e indicadores técnicos usando yfinance como complemento
        """
        try:
            ticker = self._format_ticker(ticker)
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info if hasattr(yf_ticker, 'info') else {}
            
            ratings = [
                ("Recomendação", info.get('recommendationKey', 'N/A')),
                ("Beta", f"{self._safe_float(info.get('beta')):.2f}" if 'beta' in info else 'N/A'),
                ("52-Week High", f"${self._safe_float(info.get('fiftyTwoWeekHigh')):.2f}" if 'fiftyTwoWeekHigh' in info else 'N/A'),
                ("52-Week Low", f"${self._safe_float(info.get('fiftyTwoWeekLow')):.2f}" if 'fiftyTwoWeekLow' in info else 'N/A'),
                ("50-Day MA", f"${self._safe_float(info.get('fiftyDayAverage')):.2f}" if 'fiftyDayAverage' in info else 'N/A'),
                ("200-Day MA", f"${self._safe_float(info.get('twoHundredDayAverage')):.2f}" if 'twoHundredDayAverage' in info else 'N/A'),
                ("P/E Ratio", f"{self._safe_float(info.get('trailingPE')):.2f}" if 'trailingPE' in info else 'N/A'),
                ("Forward P/E", f"{self._safe_float(info.get('forwardPE')):.2f}" if 'forwardPE' in info else 'N/A'),
                ("PEG Ratio", f"{self._safe_float(info.get('pegRatio')):.2f}" if 'pegRatio' in info else 'N/A'),
                ("Price/Book", f"{self._safe_float(info.get('priceToBook')):.2f}" if 'priceToBook' in info else 'N/A')
            ]
            
            return ratings
            
        except Exception as e:
            return self.handle_error(e, ticker, "Pandas Datareader Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """
        Tratamento de erros específico para pandas_datareader
        """
        error_msg = str(error)
        if "No data fetched" in error_msg:
            logging.error(f"Nenhum dado encontrado para {ticker}")
        elif "Cannot connect to" in error_msg:
            logging.error(f"Erro de conexão ao buscar dados para {ticker}")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None