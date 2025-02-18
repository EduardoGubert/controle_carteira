from pymongo import MongoClient

def get_mongo_client(uri="mongodb://localhost:27017"):
    return MongoClient(uri)

def get_config():
    """
    Retorna as configurações do banco de dados.
    Procura um documento na coleção "config" do banco "portfolio_db".
    Se não existir, retorna valores padrão.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    config_doc = db.config.find_one({})
    if not config_doc:
        config_doc = {
            "valor_inicial_total_usd": 1277.32,
            "valor_inicial_total_reais": 7500,
            "update_interval_ms": 30000
        }
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