# portfolio_manager.py

import yfinance as yf
import pandas as pd
import logging

class PortfolioManager:
    """
    Gerencia os dados e cálculos da carteira.
    """
    def __init__(self, portfolio, valor_inicial_total, valor_inicial_total_reais):
        """
        Inicializa a carteira.
        
        :param portfolio: dict com os dados de cada ticker.
        :param valor_inicial_total: valor total inicial em US$ (ações + saldo).
        :param valor_inicial_total_reais: valor total inicial em R$.
        """
        self.portfolio = portfolio
        self.valor_inicial_total = valor_inicial_total
        self.valor_inicial_total_reais = valor_inicial_total_reais

    def get_dollar_rate(self):
        """
        Retorna a taxa de câmbio US$/R$ a partir do yfinance.
        """
        try:
            ticker = yf.Ticker("USDBRL=X")
            data = ticker.history(period="1d")
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            logging.error(f"Erro ao obter taxa do dólar: {e}")
        return 5.5

    def update_portfolio(self):
        """
        Atualiza os dados da carteira usando consulta em lote via yf.download.
        
        Retorna:
            total_portfolio: valor total da carteira (ações + saldo)
            variacao_total: variação percentual da carteira
            valor_variacao_total: variação em US$
            total_investido: soma dos valores investidos (conforme 'custo_medio' de cada ticker)
            saldo_restante: saldo em caixa
        """
        total_valor_acoes = 0
        total_investido = 0

        tickers = list(self.portfolio.keys())
        try:
            data = yf.download(tickers, period="1d", group_by='ticker', threads=True)
        except Exception as e:
            logging.error(f"Erro ao baixar dados para múltiplos tickers: {e}")
            data = None

        for ticker in tickers:
            if data is not None:
                try:
                    if isinstance(data.columns, pd.MultiIndex):
                        # Os tickers estão no nível 0 do MultiIndex
                        if ticker in data.columns.get_level_values(0):
                            preco_atual = data[ticker]['Close'].iloc[-1]
                        else:
                            logging.warning(f"Dados para {ticker} não encontrados.")
                            continue
                    else:
                        preco_atual = data['Close'].iloc[-1]
                    self.portfolio[ticker]["preco_atual"] = preco_atual
                    self.portfolio[ticker]["valor_atual"] = preco_atual * self.portfolio[ticker]["quantidade"]
                    preco_medio = self.portfolio[ticker]["preco_medio"]
                    self.portfolio[ticker]["variacao"] = ((preco_atual / preco_medio) - 1) * 100
                    total_valor_acoes += self.portfolio[ticker]["valor_atual"]
                except Exception as e:
                    logging.error(f"Erro ao atualizar {ticker}: {e}")
            else:
                logging.error("Nenhum dado disponível para atualizar a carteira.")

        # Calcula o total investido (soma dos 'custo_medio' de cada ticker)
        for ticker in tickers:
            total_investido += self.portfolio[ticker].get("custo_medio", 0)
        saldo_restante = self.valor_inicial_total - total_investido
        total_portfolio = total_valor_acoes + saldo_restante

        # Calcula a composição de cada ticker na carteira
        for ticker in tickers:
            if "valor_atual" in self.portfolio[ticker]:
                self.portfolio[ticker]["composicao"] = (self.portfolio[ticker]["valor_atual"] / total_portfolio) * 100

        variacao_total = ((total_portfolio - self.valor_inicial_total) / self.valor_inicial_total) * 100
        valor_variacao_total = total_portfolio - self.valor_inicial_total

        return total_portfolio, variacao_total, valor_variacao_total, total_investido, saldo_restante
