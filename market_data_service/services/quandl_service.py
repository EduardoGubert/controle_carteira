import quandl
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class QuandlService(BaseDataService):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        quandl.ApiConfig.api_key = api_key
        self.base_dataset = 'SHARADAR/SF1'  # Dataset principal para dados fundamentais

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def _format_ticker(self, ticker: str) -> str:
        """Formata o ticker para o padrão Quandl"""
        return f"{ticker}_US" if "_" not in ticker else ticker

    def get_price_data(self, ticker: str) -> float:
        """
        Obtém o preço mais recente via Quandl
        """
        try:
            formatted_ticker = self._format_ticker(ticker)
            df = quandl.get(f"WIKI/{formatted_ticker}", rows=1)
            if not df.empty:
                return float(df['Adj. Close'].iloc[-1])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Quandl Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """
        Obtém dados fundamentais via Quandl Sharadar
        """
        try:
            formatted_ticker = self._format_ticker(ticker)
            
            # Colunas necessárias para dados fundamentais
            columns = [
                'ticker', 'datekey', 'price', 'marketcap', 'pe', 'pb',
                'roe', 'roa', 'roic', 'gpm', 'npm', 'divyield',
                'eps', 'revenue', 'netinc', 'ncf', 'capex', 'assets',
                'ebitda', 'debt', 'fcf', 'workingcapital'
            ]
            
            # Buscar dados fundamentais mais recentes
            df = quandl.get_table(
                self.base_dataset,
                ticker=formatted_ticker,
                dimension='MRY',  # Most Recent Year
                qopts={'columns': columns},
                paginate=True
            )
            
            if not df.empty:
                latest = df.iloc[0]
                
                # Calcular métricas derivadas
                try:
                    ocf_net_income = latest['ncf'] / latest['netinc'] if latest['netinc'] != 0 else None
                    capex_sales = latest['capex'] / latest['revenue'] if latest['revenue'] != 0 else None
                    capex_ocf = latest['capex'] / latest['ncf'] if latest['ncf'] != 0 else None
                    net_debt_ebitda = (latest['debt'] - latest['workingcapital']) / latest['ebitda'] if latest['ebitda'] != 0 else None
                except:
                    ocf_net_income = capex_sales = capex_ocf = net_debt_ebitda = None

                result = {
                    # Dados básicos
                    'previousClose': self._safe_float(latest.get('price')),
                    'marketCap': self._safe_float(latest.get('marketcap')),
                    'peRatio': self._safe_float(latest.get('pe')),
                    'priceToBook': self._safe_float(latest.get('pb')),
                    'dividendYield': self._safe_float(latest.get('divyield')),

                    # Indicadores fundamentalistas
                    'grossMargins': self._safe_float(latest.get('gpm')),
                    'profitMargins': self._safe_float(latest.get('npm')),
                    'roic': self._safe_float(latest.get('roic')),
                    'returnOnEquity': self._safe_float(latest.get('roe')),
                    'revenueGrowth': None,  # Precisa calcular com dados históricos
                    'netIncomeGrowth': None,  # Precisa calcular com dados históricos
                    'ocfNetIncomeRatio': self._safe_float(ocf_net_income),
                    'netDebtEbitda': self._safe_float(net_debt_ebitda),
                    'capexSales': self._safe_float(capex_sales),
                    'capexOCF': self._safe_float(capex_ocf)
                }
                
                return result
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Quandl Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Obtém dados trimestrais via Quandl
        """
        try:
            formatted_ticker = self._format_ticker(ticker)
            
            # Buscar dados trimestrais
            df = quandl.get_table(
                self.base_dataset,
                ticker=formatted_ticker,
                dimension='MRQ',  # Most Recent Quarter
                qopts={'columns': ['datekey', 'eps', 'revenue']},
                paginate=True
            )
            
            result = []
            if not df.empty:
                # Ordenar por data decrescente
                df = df.sort_values('datekey', ascending=False).head(8)
                
                for i, row in df.iterrows():
                    date = pd.to_datetime(row['datekey'])
                    quarter_str = date.strftime('%b-%y')
                    
                    eps = self._safe_float(row['eps'])
                    revenue = self._safe_float(row['revenue'])
                    
                    # Calcular variações
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if i < len(df) - 1:
                        prev_eps = self._safe_float(df.iloc[i+1]['eps'])
                        prev_revenue = self._safe_float(df.iloc[i+1]['revenue'])
                        
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
            return self.handle_error(e, ticker, "Quandl Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """
        Obtém dados anuais via Quandl
        """
        try:
            formatted_ticker = self._format_ticker(ticker)
            
            # Buscar dados anuais
            df = quandl.get_table(
                self.base_dataset,
                ticker=formatted_ticker,
                dimension='MRY',  # Most Recent Year
                qopts={'columns': ['datekey', 'eps']},
                paginate=True
            )
            
            result = []
            if not df.empty:
                # Ordenar por data decrescente
                df = df.sort_values('datekey', ascending=False).head(10)
                
                for i, row in df.iterrows():
                    year = pd.to_datetime(row['datekey']).year
                    eps = self._safe_float(row['eps'])
                    
                    # Calcular variação
                    change = "N/A"
                    if i < len(df) - 1:
                        prev_eps = self._safe_float(df.iloc[i+1]['eps'])
                        if eps and prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        str(year),
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Quandl Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """
        Obtém ratings e indicadores via Quandl
        """
        try:
            formatted_ticker = self._format_ticker(ticker)
            
            # Buscar métricas relevantes
            df = quandl.get_table(
                self.base_dataset,
                ticker=formatted_ticker,
                dimension='MRY',
                qopts={'columns': [
                    'pe', 'pb', 'roe', 'roa', 'roic', 'gpm', 'npm',
                    'divyield', 'currentratio', 'debt', 'ebitda'
                ]},
                paginate=True
            )
            
            ratings = []
            if not df.empty:
                latest = df.iloc[0]
                
                metrics = [
                    ("P/E Ratio", 'pe'),
                    ("P/B Ratio", 'pb'),
                    ("ROE", 'roe'),
                    ("ROA", 'roa'),
                    ("ROIC", 'roic'),
                    ("Gross Margin", 'gpm'),
                    ("Net Margin", 'npm'),
                    ("Dividend Yield", 'divyield'),
                    ("Current Ratio", 'currentratio')
                ]
                
                for label, key in metrics:
                    value = self._safe_float(latest.get(key))
                    if value is not None:
                        if key in ['divyield', 'gpm', 'npm', 'roe', 'roa', 'roic']:
                            ratings.append((label, f"{value:.2f}%"))
                        else:
                            ratings.append((label, f"{value:.2f}"))
                
                # Calcular métricas adicionais
                if latest['ebitda'] != 0:
                    debt_ebitda = latest['debt'] / latest['ebitda']
                    ratings.append(("Debt/EBITDA", f"{debt_ebitda:.2f}"))
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "Quandl Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """
        Tratamento de erros específico para Quandl
        """
        error_msg = str(error)
        if "Not Found" in error_msg:
            logging.error(f"Ticker {ticker} não encontrado no Quandl")
        elif "Forbidden" in error_msg:
            logging.error(f"Acesso negado ao Quandl. Verifique sua chave API")
        elif "Premium" in error_msg:
            logging.error(f"Dados premium necessários para {ticker}")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None