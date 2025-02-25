# main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('portfolio.log')
    ]
)


from config import portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS
from portfolio_manager import PortfolioManager
from gui.base_gui import BaseGUI
from gui.carteira_tab import CarteiraTab
from gui.analise_tab import AnaliseTab
from market_data_service import MarketDataService

def main():
    pm = PortfolioManager(portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS, market_data_service=MarketDataService())
    gui = BaseGUI(pm)

    # Cria as abas
    carteira_tab = CarteiraTab(gui.notebook, pm, gui.update_interval_ms)
    analise_tab = AnaliseTab(gui.notebook, pm)
    #analise_tab = AnaliseTab(gui.notebook, pm, gui.update_interval_ms)

    # Adiciona ao Notebook
    gui.add_tab(carteira_tab, "Carteira")
    gui.add_tab(analise_tab, "Análise") 

 

    gui.run()

if __name__ == "__main__":
    main()
