from datetime import datetime, timedelta
import requests
import logging
import json
import random
import time
from kafka import KafkaProducer
from airflow import DAG
from airflow.operators.python import PythonOperator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of cryptocurrency symbols you want to fetch
CRYPTO_SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'LTCUSDT', 'XRPUSDT', 'DOGEUSDT']

# Maintain the last fetched date for each coin
last_fetched = {symbol: None for symbol in CRYPTO_SYMBOLS}

def fetch_crypto_prices():
    prices = []
    current_date = datetime.utcnow().date()

    for symbol in CRYPTO_SYMBOLS:
        if last_fetched[symbol] == current_date:
            continue  # Skip if already fetched today

        try:
            # Make a request to the Binance API
            response = requests.get(f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=1')
            response.raise_for_status()
            data = response.json()

            if data:
                price_info = {
                    'symbol': symbol,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'open': float(data[0][1]),
                    'high': float(data[0][2]),
                    'low': float(data[0][3]),
                    'close': float(data[0][4]),
                    'volume': float(data[0][5])
                }

                prices.append(price_info)
                last_fetched[symbol] = current_date  # Update the last fetched date

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")

    return prices

def stream_data():
    producer = KafkaProducer(bootstrap_servers='kafka:9093', max_block_ms=5000)
    prices = fetch_crypto_prices()

    for price in prices:
        try:
            producer.send('crypto_prices', json.dumps(price).encode('utf-8')) #cryptocurrency_prices
            logger.info(f"Data sent to Kafka: {price} on topic 'crypto_prices'")
            time.sleep(random.uniform(0.5, 2.0))  # Sleep between sends
        except Exception as e:
            logger.error(f'An error occurred while sending data: {e}')


default_args = {
    'owner': 'admin',
    'start_date': datetime(2024, 10, 25, 10, 00)
}
with DAG('crypto_price_automation',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    streaming_task = PythonOperator(
        task_id='stream_crypto_prices',
        python_callable=stream_data
    )

