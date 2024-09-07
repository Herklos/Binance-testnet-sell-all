from dotenv import load_dotenv
import os
import ccxt
import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

def create_client(exchange_id: str):
    exchange_class = getattr(ccxt, exchange_id)
    client = exchange_class({
        'apiKey': os.getenv('BINANCE_TESTNET_API_KEY'),
        'secret': os.getenv('BINANCE_TESTNET_API_SECRET'),
        'enableRateLimit': True
    })
    client.set_sandbox_mode(True)
    logger.info(f"Successfully created {exchange_id} client.")
    return client

def fetch_balance(client):
    logger.info("Fetching balance...")
    try:
        return client.fetch_balance()
    except Exception as e:
        logger.error(f"Failed fetch balance: {e}")

def sell_market(client, symbol, quantity, total_quantity, retry_attempt=0):
    if quantity > 10:
        quantity = int(quantity)
    logger.info(f"Selling {quantity} {symbol}...")

    symbol_market = client.market(symbol)
    symbol_max_quantity = symbol_market['limits']['amount']['max']
    if quantity > symbol_max_quantity:
        logger.warning(f"Quantity is too large!")
        quantity = symbol_max_quantity

    symbol_min_quantity = symbol_market['limits']['amount']['min']
    if quantity < symbol_min_quantity:
        logger.warning(f"Quantity is too low!")
        return
    
    try:
        client.create_market_sell_order(symbol, 1)
        if retry_attempt > 0:
            logger.info(f"Retry succeeded with quantity: {quantity}. Try to sell remainings...")
            
        logger.info(f"** Sold {quantity} of {symbol} **")
        if quantity < (total_quantity - quantity):
            sell_market(client, symbol, quantity, 
                        total_quantity, 
                        retry_attempt=retry_attempt)
    except ccxt.BadRequest as badRequestError:
        if "Filter failure: NOTIONAL" in str(badRequestError):
            logger.warning(f"Quantity was too large!")
            if retry_attempt < 3:
                retry_attempt+=1
                sell_market(client, symbol, quantity / 10 * retry_attempt, 
                            total_quantity, 
                            retry_attempt=retry_attempt)
            else:
                logger.error(f"Stopped to retry after attempt {retry_attempt}")
        else:
            raise badRequestError
    except Exception as e:
        logger.error(f"Failed to sell {quantity} {symbol}: {e}")

if __name__ == '__main__':
    load_dotenv()
    client = create_client('binance')
    client.load_markets()
    balance = fetch_balance(client)

    # sell free quantity of each assets
    for asset, free_quantity in balance['free'].items():
        if free_quantity > 0 and asset != os.getenv('TARGET_COIN'):
            sell_market(client, f"{asset}/{os.getenv('TARGET_COIN')}", free_quantity, free_quantity)
