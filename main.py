# main.py
from config import portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS, DATA_INICIO
from portfolio_manager import PortfolioManager
from gui import PortfolioGUI

def main():
    pm = PortfolioManager(portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS)
    pm.data_inicio = DATA_INICIO  # define a data de início conforme o config
    PortfolioGUI(pm)

if __name__ == "__main__":
    main()
