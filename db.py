# db.py
from pymongo import MongoClient
from datetime import datetime

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

def record_portfolio_history(valor_total, data=None):
    """
    Registra o valor total da carteira na coleção "portfolio_history".
    Isso permite calcular o rendimento em diferentes períodos.
    """
    client = get_mongo_client()
    db = client.portfolio_db
    if data is None:
        data = datetime.now()
    history_record = {
        "valor_total": valor_total,
        "data": data
    }
    db.portfolio_history.insert_one(history_record)
