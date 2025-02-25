import yfinance as yf
import pandas as pd
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
from ..base_service import BaseDataService


class YFinanceService(BaseDataService):
    def get_price_data(self, ticker: str) -> float:
        try:
            ticker_data = yf.Ticker(ticker)
            data = ticker_data.history(period="1d")
            if not data.empty:
                return float(data['Close'].iloc[-1])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "YFinance")
            
    def get_fundamental_data(self, ticker: str) -> dict:
        try:
            ticker_data = yf.Ticker(ticker)
            info = ticker_data.info
            
            # Função auxiliar para converter valores em float
            def safe_float(value):
                try:
                    return float(value) if value is not None else None
                except (ValueError, TypeError):
                    return None

            return {
                # Dados básicos
                'previousClose': safe_float(info.get('previousClose')),
                'open': safe_float(info.get('open')),
                'dayLow': safe_float(info.get('dayLow')),
                'dayHigh': safe_float(info.get('dayHigh')),
                'volume': safe_float(info.get('volume')),
                'marketCap': safe_float(info.get('marketCap')),
                'trailingPE': safe_float(info.get('trailingPE')),
                'forwardPE': safe_float(info.get('forwardPE')),
                'dividendYield': safe_float(info.get('dividendYield')),

                # Campos avançados
                'peRatio': safe_float(info.get('trailingPE')),
                'grossMargins': safe_float(info.get('grossMargins')),
                'profitMargins': safe_float(info.get('profitMargins')),
                'roic': safe_float(info.get('returnOnCapital')),
                'returnOnEquity': safe_float(info.get('returnOnEquity')),
                'revenueGrowth': safe_float(info.get('revenueGrowth')),
                'netIncomeGrowth': safe_float(info.get('netIncomeGrowth')),
                'ocfNetIncomeRatio': None,  # Precisa ser calculado
                'netDebtEbitda': None,  # Precisa ser calculado
                'insiderOwnership': safe_float(info.get('heldPercentInsiders')),
                'capexSales': None,  # Precisa ser calculado
                'capexOCF': None,  # Precisa ser calculado
                'returnOfEquity': safe_float(info.get('returnOnEquity'))
            }
        except Exception as e:
            return self.handle_error(e, ticker, "YFinance")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        try:
            ticker_data = yf.Ticker(ticker)
            
            # Obter dados financeiros trimestrais
            earnings = ticker_data.quarterly_earnings
            financials = ticker_data.quarterly_financials
            
            result = []
            if not earnings.empty and not financials.empty:
                # Combinar dados de lucros e receitas
                for date in earnings.index[:8]:  # Últimos 8 trimestres
                    quarter = date.strftime('%b-%y')
                    
                    # EPS dados
                    eps = earnings.loc[date, 'Earnings'] if date in earnings.index else None
                    revenue = financials.loc[date, 'Total Revenue'] if date in financials.index else None
                    
                    # Calcular variações
                    if eps is not None and earnings.index.size > earnings.index.get_loc(date) + 1:
                        prev_date = earnings.index[earnings.index.get_loc(date) + 1]
                        prev_eps = earnings.loc[prev_date, 'Earnings']
                        eps_change = ((eps / prev_eps) - 1) * 100 if prev_eps else 0
                    else:
                        eps_change = 0

                    if revenue is not None and financials.index.size > financials.index.get_loc(date) + 1:
                        prev_date = financials.index[financials.index.get_loc(date) + 1]
                        prev_revenue = financials.loc[prev_date, 'Total Revenue']
                        revenue_change = ((revenue / prev_revenue) - 1) * 100 if prev_revenue else 0
                        revenue_millions = revenue / 1_000_000
                    else:
                        revenue_change = 0
                        revenue_millions = 0

                    result.append((
                        quarter,
                        f"{eps:.2f}" if eps is not None else "N/A",
                        f"{eps_change:+.1f}%" if eps is not None else "N/A",
                        f"{revenue_millions:.1f}" if revenue is not None else "N/A",
                        f"{revenue_change:+.1f}%" if revenue is not None else "N/A"
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "YFinance Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        try:
            ticker_data = yf.Ticker(ticker)
            earnings = ticker_data.earnings
            
            result = []
            if not earnings.empty:
                # Processar dados anuais
                for year in earnings.index[-10:]:  # Últimos 10 anos
                    eps = earnings.loc[year, 'Earnings']
                    
                    # Calcular variação
                    if year > earnings.index[0]:
                        prev_eps = earnings.loc[year - 1, 'Earnings'] if year - 1 in earnings.index else None
                        change = ((eps / prev_eps) - 1) * 100 if prev_eps and eps else 0
                    else:
                        change = 0
                    
                    result.append((
                        str(year),
                        f"{eps:.2f}" if eps else "N/A",
                        f"{change:+.1f}%" if change != 0 else "N/A"
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "YFinance Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        try:
            ticker_data = yf.Ticker(ticker)
            info = ticker_data.info
            
            # Função auxiliar para formatar valores
            def format_value(value, is_percentage=False, prefix=""):
                if value is None:
                    return "N/A"
                try:
                    value = float(value)
                    if is_percentage:
                        return f"{value:.2f}%"
                    return f"{prefix}{value:.2f}"
                except (ValueError, TypeError):
                    return str(value)

            # Lista de ratings e indicadores
            ratings = [
                ("Recomendação", info.get('recommendationKey', 'N/A')),
                ("Beta", format_value(info.get('beta'))),
                ("52-Week High", format_value(info.get('fiftyTwoWeekHigh'), prefix="$")),
                ("52-Week Low", format_value(info.get('fiftyTwoWeekLow'), prefix="$")),
                ("50-Day MA", format_value(info.get('fiftyDayAverage'), prefix="$")),
                ("200-Day MA", format_value(info.get('twoHundredDayAverage'), prefix="$")),
                ("P/E Ratio", format_value(info.get('trailingPE'))),
                ("Forward P/E", format_value(info.get('forwardPE'))),
                ("PEG Ratio", format_value(info.get('pegRatio'))),
                ("Price/Book", format_value(info.get('priceToBook'))),
                ("Price/Sales", format_value(info.get('priceToSalesTrailing12Months'))),
                ("EV/EBITDA", format_value(info.get('enterpriseToEbitda'))),
                ("Profit Margin", format_value(info.get('profitMargins'), is_percentage=True)),
                ("Operating Margin", format_value(info.get('operatingMargins'), is_percentage=True)),
                ("Target Price", format_value(info.get('targetMeanPrice'), prefix="$")),
                ("Volume Médio (3m)", format_value(info.get('averageVolume3Month')))
            ]
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "YFinance Ratings")
        
    # def get_yfinance_data(self, tickers):
    #     try:
    #         # Tenta baixar todos os tickers de uma vez
    #         ticker_totais = yf.download(list(tickers), period="1d", group_by='ticker', threads=True)
            
    #         # Se não conseguir dados ou retornar vazio, tenta um por um
    #         if ticker_totais.empty:
    #             ticker_totais = pd.DataFrame()
    #             for ticker in tickers:
    #                 try:
    #                     ticker_unitario = yf.Ticker(ticker)
    #                     data = ticker_unitario.history(period="1d")
    #                     if not data.empty:
    #                         # Adiciona os dados do ticker individual ao DataFrame total
    #                         if ticker_totais.empty:
    #                             ticker_totais = pd.DataFrame(index=data.index)
    #                         ticker_totais[f"{ticker}, Close"] = data['Close']
    #                     else:
    #                         logging.warning(f"Não foi possível obter dados para {ticker}")
                            
    #                 except Exception as e:
    #                     logging.error(f"Erro ao atualizar {ticker}: {e}")
                        
    #         return ticker_totais
    #     except Exception as e:
    #         logging.error(f"Erro na consulta yfinance: {e}")
    #         return pd.DataFrame()    