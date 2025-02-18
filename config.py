# config.py

# Dados da carteira
portfolio = {
    "MSFT": {"quantidade": 0.46705, "preco_medio": 410.23, "custo_medio": 191.60},
    "AMZN": {"quantidade": 0.55567, "preco_medio": 229.86, "custo_medio": 127.73},
    "GOOG": {"quantidade": 0.68310, "preco_medio": 186.98, "custo_medio": 127.73},
    "HWM":  {"quantidade": 0.61822, "preco_medio": 129.13, "custo_medio": 79.83},
    "AXON": {"quantidade": 0.11908, "preco_medio": 670.37, "custo_medio": 79.83},
    "V":    {"quantidade": 0.18169, "preco_medio": 351.53, "custo_medio": 63.87},
    "MA":   {"quantidade": 0.11337, "preco_medio": 563.37, "custo_medio": 63.87},
    "META": {"quantidade": 0.08792, "preco_medio": 726.44, "custo_medio": 63.87},
    "GS":   {"quantidade": 0.09845, "preco_medio": 648.71, "custo_medio": 63.87},
    "CRWD": {"quantidade": 0.07306, "preco_medio": 437.00, "custo_medio": 31.93},
    "PANW": {"quantidade": 0.16274, "preco_medio": 196.20, "custo_medio": 31.93},
    "APP":  {"quantidade": 0.07015, "preco_medio": 455.13, "custo_medio": 31.93},
    "PLTR": {"quantidade": 0.27111, "preco_medio": 117.78, "custo_medio": 31.93},
}

# Configurações iniciais
VALOR_INICIAL_TOTAL_USD = 1277.32          # Valor inicial total em US$ (ações + saldo)
VALOR_INICIAL_TOTAL_REAIS = 7500           # Valor inicial total em R$
UPDATE_INTERVAL_MS = 30000                 # Intervalo de atualização em milissegundos
