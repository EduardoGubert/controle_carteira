# config.py
from db import get_config, get_portfolio

config_data = get_config()
portfolio = get_portfolio()

VALOR_INICIAL_TOTAL_USD = config_data.get("valor_inicial_total_usd", 1277.32)
VALOR_INICIAL_TOTAL_REAIS = config_data.get("valor_inicial_total_reais", 7500)
UPDATE_INTERVAL_MS = config_data.get("update_interval_ms", 30000)
DATA_CRIACAO = config_data.get("data_criacao")   # Data de criação do config
DATA_INICIO = config_data.get("data_inicio", "")   # Data de início da carteira (manual)
