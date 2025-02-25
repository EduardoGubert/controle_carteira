# db.py
from pymongo import MongoClient
from datetime import datetime, time
from zoneinfo import ZoneInfo
import pandas as pd

def get_mongo_client(uri="mongodb://localhost:27017"):
    return MongoClient(uri)

def get_config():
    """
    Retorna as configurações do banco de dados.
    Procura um documento na coleção "config" do banco "portfolio_db".
    Se não existir, cria um documento padrão com data de criação.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    config_doc = db.config.find_one({})
    if not config_doc:
        config_doc = {
            "valor_inicial_total_usd": 1277.32,
            "valor_inicial_total_reais": 7500,
            "update_interval_ms": 30000,
            "data_criacao": datetime.now(),      # data de criação do config
            "data_inicio": None                   # data de início da carteira (para inserir manualmente)
        }
        db.config.insert_one(config_doc)
    return config_doc

def get_portfolio():
    """
    Retorna os dados da carteira a partir da coleção "portfolio" do banco "portfolio_db".
    Cada documento deve conter um campo "ticker" e os demais dados da ação.
    O retorno será um dicionário com o ticker como chave.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    portfolio_docs = db.portfolio.find({})
    portfolio = {}
    for doc in portfolio_docs:
        ticker = doc.get("ticker", "").upper().strip()
        if ticker:
            portfolio[ticker] = {
                "quantidade": doc.get("quantidade", 0),
                "preco_medio": doc.get("preco_medio", 0),
                "custo_medio": doc.get("custo_medio", 0)
            }
    return portfolio

def get_first_purchase_date():
    """
    Retorna a data da primeira compra registrada manualmente.
    Consulta a coleção "transactions" buscando documentos do tipo "compra" 
    que possuem o campo "data_operacao_manual" e retorna a menor data.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    # Filtra transações de compra que tenham data_operacao_manual
    result = db.transactions.find({
        "tipo": "compra",
        "data_operacao_manual": {"$exists": True}
    }).sort("data_operacao_manual", 1).limit(1)
    first_purchase = list(result)
    if first_purchase:
        return first_purchase[0]["data_operacao_manual"]
    else:
        return None

def update_portfolio_in_db(portfolio):
    """
    Atualiza a coleção "portfolio" com os dados do dicionário `portfolio`.
    Para cada ticker, realiza um upsert (atualiza se existir; insere se não).
    """
    client = get_mongo_client()
    db = client.portfolio_db
    for ticker, data in portfolio.items():
        db.portfolio.update_one(
            {"ticker": ticker},
            {"$set": data, "$setOnInsert": {"ticker": ticker}},
            upsert=True
        )

def update_config_in_db(config):
    """
    Atualiza (ou insere) o documento de configuração na coleção "config".
    """
    client = get_mongo_client()
    db = client.portfolio_db
    db.config.update_one({}, {"$set": config}, upsert=True)

def record_transaction(transaction):
    """
    Insere uma nova transação na coleção "transactions".
    O dicionário 'transaction' deve conter os campos:
      - ticker, tipo (compra/venda), quantidade, preco,
      - data_operacao_manual (opcional, se informado manualmente),
      - e data_registro (data de registro da operação no sistema).
    """
    client = get_mongo_client()
    db = client.portfolio_db
    # Define a data de registro como a data atual, se não estiver definida
    if "data_registro" not in transaction:
        transaction["data_registro"] = datetime.now()
    # Se o usuário não forneceu uma data manual, podemos igualá-la à data de registro
    if "data_operacao_manual" not in transaction:
        transaction["data_operacao_manual"] = transaction["data_registro"]
    db.transactions.insert_one(transaction)



def remove_stock_from_portfolio(ticker):
    """
    Remove a ação zerada da coleção "portfolio"..
    """
    client = get_mongo_client()
    db = client.portfolio_db
    db.portfolio.delete_one({"ticker": ticker})

def record_portfolio_history(valor_total, data=None):
    """
    Registra o valor total da carteira na coleção "portfolio_history".
    Isso permite calcular o rendimento em diferentes períodos.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    if data is None:
        #data = datetime.now()
        data = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    history_record = {
        "valor_total": valor_total,
        "data": data
    }
    db.portfolio_history.insert_one(history_record)


def get_portfolio_history():
    client = get_mongo_client()
    db = client.portfolio_db
    cursor = db.portfolio_history.find({}, {"_id": 0, "data": 1, "valor_total": 1}).sort("data", 1)
    data = list(cursor)
    if data:
        return pd.DataFrame(data)
    else:
        return pd.DataFrame(columns=["data", "valor_total"])
    
    
def record_portfolio_history_if_market_closed(total_portfolio):
    """
    Registra o valor total da carteira na coleção 'portfolio_history'
    se o horário atual (em horário de Nova York) for após 16:00 (fechamento da bolsa americana)
    e se não houver um registro para o dia atual.
    """
    # Obtém a data e hora atual no fuso America/New_York
    now = datetime.now(ZoneInfo("America/New_York"))
    market_close = time(16, 0, 0)  # 4:00 PM
    
    if now.time() < market_close:
        # Mercado ainda não fechou, não registra.
        return

    client = get_mongo_client()
    db = client.portfolio_db
    # Obtem o último registro (ordenado por data decrescente)
    last_record = db.portfolio_history.find_one({}, sort=[("data", -1)])
    today_date = now.date()
    if (last_record is None) or (last_record["data"].date() < today_date):
        # Registra um novo histórico para hoje
        history_record = {"valor_total": total_portfolio, "data": now}
        db.portfolio_history.insert_one(history_record)

