import logging
import investpy
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from ..base_service import BaseDataService

class InvestpyService(BaseDataService):
    def __init__(self):
        super().__init__(api_key=None)
        self.country = 'united states'

    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def get_price_data(self, ticker: str) -> float:
        """
        Obtém o preço mais recente da ação
        """
        try:
            df = investpy.get_stock_recent_data(stock=ticker, country=self.country)
            if not df.empty:
                return float(df['Close'].iloc[-1])
            return None
        except Exception as e:
            return self.handle_error(e, ticker, "Investpy Price")

    def get_fundamental_data(self, ticker: str) -> dict:
        """
        Obtém dados fundamentalistas
        """
        try:
            info = investpy.get_stock_information(stock=ticker, country=self.country)
            technical = investpy.get_stock_technical_indicators(stock=ticker, country=self.country)
            
            result = {}
            
            if not info.empty:
                # Converter Series para dicionário
                info_dict = info.to_dict()
                
                # Dados básicos
                result.update({
                    'previousClose': self._safe_float(info_dict.get('Prev. Close')),
                    'open': self._safe_float(info_dict.get('Open')),
                    'dayLow': self._safe_float(info_dict.get('Low')),
                    'dayHigh': self._safe_float(info_dict.get('High')),
                    'volume': self._safe_float(info_dict.get('Volume')),
                    'marketCap': self._safe_float(info_dict.get('Market Cap')),
                    'peRatio': self._safe_float(info_dict.get('P/E Ratio')),
                    'dividendYield': self._safe_float(info_dict.get('Dividend Yield')),
                })

                # Campos avançados disponíveis
                result.update({
                    'profitMargins': self._safe_float(info_dict.get('Profit Margin')),
                    'returnOnEquity': self._safe_float(info_dict.get('ROE')),
                    'grossMargins': self._safe_float(info_dict.get('Gross Margin')),
                    'operatingMargin': self._safe_float(info_dict.get('Operating Margin')),
                })

            if not technical.empty:
                # Adicionar indicadores técnicos relevantes
                tech_dict = technical.to_dict()
                result.update({
                    'technicalScore': tech_dict.get('technical_score', None),
                    'movingAverages': tech_dict.get('moving_averages', None),
                })

            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Investpy Fundamentals")

    def get_quarterly_data(self, ticker: str) -> List[Tuple[str, str, str, str, str]]:
        """
        Obtém dados trimestrais de EPS e vendas
        """
        try:
            # Tentar obter dados financeiros trimestrais
            end_date = datetime.now()
            start_date = end_date - timedelta(days=730)  # 2 anos de dados
            
            financial_data = investpy.get_stock_financial_summary(
                stock=ticker,
                country=self.country,
                summary_type='income_statement',
                period='quarterly'
            )
            
            result = []
            if not financial_data.empty:
                # Ordenar por data decrescente e pegar os últimos 8 trimestres
                financial_data = financial_data.sort_index(ascending=False).head(8)
                
                for date, row in financial_data.iterrows():
                    quarter_str = date.strftime('%b-%y')
                    
                    # Tentar extrair EPS e receita
                    eps = self._safe_float(row.get('EPS'))
                    revenue = self._safe_float(row.get('Total Revenue'))
                    
                    # Calcular variações (comparar com o trimestre anterior)
                    eps_change = "N/A"
                    revenue_change = "N/A"
                    
                    if eps is not None and revenue is not None:
                        prev_row = financial_data.shift(-1).loc[date]
                        prev_eps = self._safe_float(prev_row.get('EPS'))
                        prev_revenue = self._safe_float(prev_row.get('Total Revenue'))
                        
                        if prev_eps:
                            eps_change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                        if prev_revenue:
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
            return self.handle_error(e, ticker, "Investpy Quarterly")

    def get_yearly_data(self, ticker: str) -> List[Tuple[str, str, str]]:
        """
        Obtém dados anuais de EPS
        """
        try:
            financial_data = investpy.get_stock_financial_summary(
                stock=ticker,
                country=self.country,
                summary_type='income_statement',
                period='annual'
            )
            
            result = []
            if not financial_data.empty:
                # Ordenar por data decrescente e pegar os últimos 10 anos
                financial_data = financial_data.sort_index(ascending=False).head(10)
                
                for date, row in financial_data.iterrows():
                    year_str = str(date.year)
                    eps = self._safe_float(row.get('EPS'))
                    
                    # Calcular variação
                    change = "N/A"
                    if eps is not None:
                        prev_row = financial_data.shift(-1).loc[date]
                        prev_eps = self._safe_float(prev_row.get('EPS'))
                        if prev_eps:
                            change = f"{((eps / prev_eps) - 1) * 100:+.1f}%"
                    
                    result.append((
                        year_str,
                        f"{eps:.2f}" if eps else "N/A",
                        change
                    ))
            
            return result
        except Exception as e:
            return self.handle_error(e, ticker, "Investpy Yearly")

    def get_ratings_data(self, ticker: str) -> List[Tuple[str, str]]:
        """
        Obtém dados de ratings e indicadores técnicos
        """
        try:
            technical = investpy.get_stock_technical_indicators(stock=ticker, country=self.country)
            info = investpy.get_stock_information(stock=ticker, country=self.country)
            
            ratings = []
            
            if not technical.empty:
                # Adicionar indicadores técnicos
                tech_dict = technical.to_dict()
                for indicator, value in tech_dict.items():
                    if isinstance(value, (int, float)):
                        ratings.append((
                            indicator.replace('_', ' ').title(),
                            f"{value:.2f}" if isinstance(value, float) else str(value)
                        ))
            
            if not info.empty:
                # Adicionar métricas fundamentalistas relevantes
                info_dict = info.to_dict()
                key_metrics = [
                    ('P/E Ratio', 'P/E Ratio'),
                    ('Price to Book', 'P/B Ratio'),
                    ('ROE', 'ROE'),
                    ('Dividend Yield', 'Dividend Yield'),
                    ('Beta', 'Beta')
                ]
                
                for label, key in key_metrics:
                    if key in info_dict:
                        value = info_dict[key]
                        if isinstance(value, (int, float)):
                            ratings.append((label, f"{value:.2f}"))
                        else:
                            ratings.append((label, str(value)))
            
            return ratings
        except Exception as e:
            return self.handle_error(e, ticker, "Investpy Ratings")

    def handle_error(self, error: Exception, ticker: str, service_name: str) -> None:
        """
        Tratamento de erros específico para Investpy
        """
        error_msg = str(error)
        if "ConnectionError" in error_msg:
            logging.error(f"Erro de conexão ao acessar {ticker}: Verifique sua conexão com a internet")
        elif "Stock not found" in error_msg:
            logging.error(f"Ação {ticker} não encontrada no {service_name}")
        else:
            logging.error(f"Erro no serviço {service_name} para {ticker}: {error}")
        return None