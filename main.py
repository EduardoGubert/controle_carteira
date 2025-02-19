# main.py
from config import portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS
from portfolio_manager import PortfolioManager
from gui import PortfolioGUI

def main():
    pm = PortfolioManager(portfolio, VALOR_INICIAL_TOTAL_USD, VALOR_INICIAL_TOTAL_REAIS)
    PortfolioGUI(pm)

if __name__ == "__main__":
    main()
