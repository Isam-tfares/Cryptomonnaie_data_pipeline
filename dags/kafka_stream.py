from datetime import datetime
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

# List of cryptocurrency symbols to monitor
CRYPTO_SYMBOLS = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'LTCUSDT', 'XRPUSDT', 'DOGEUSDT',
    'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'MATICUSDT',
    'AVAXUSDT', 'SHIBUSDT', 'ATOMUSDT', 'LINKUSDT', 'TRXUSDT',
    'UNIUSDT', 'XLMUSDT', 'FTMUSDT', 'NEARUSDT', 'ICPUSDT',
    'FILUSDT', 'ALGOUSDT', 'HBARUSDT', 'SANDUSDT', 'MANAUSDT',
    'VETUSDT', 'XTZUSDT', 'THETAUSDT', 'AXSUSDT', 'FTTUSDT'
]


# Dictionary to keep track of the last price for each symbol
last_prices = {symbol: None for symbol in CRYPTO_SYMBOLS}

def fetch_and_compare_prices():
    changed_prices = []
    current_date = datetime.utcnow().date()

    for symbol in CRYPTO_SYMBOLS:
        try:
            # Fetch the latest data from Binance API
            response = requests.get(f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=1')
            response.raise_for_status()
            data = response.json()

            if data:
                # Extract the latest close price
                latest_close_price = float(data[0][4])

                # Check if the price has changed compared to the last stored price
                if last_prices[symbol] is None or last_prices[symbol] != latest_close_price:
                    price_info = {
                        'symbol': symbol,
                        'date': current_date.strftime('%Y-%m-%d'),
                        'open': float(data[0][1]),
                        'high': float(data[0][2]),
                        'low': float(data[0][3]),
                        'close': latest_close_price,
                        'volume': float(data[0][5])
                    }

                    # Store the new price as the last fetched price
                    last_prices[symbol] = latest_close_price
                    changed_prices.append(price_info)  # Add only if price has changed

        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")

    return changed_prices  # Only return prices that changed

def stream_data_on_price_change():
    producer = KafkaProducer(bootstrap_servers='kafka:9093', max_block_ms=5000)

    while True:  # Continuous fetch loop
        changed_prices = fetch_and_compare_prices()

        for price in changed_prices:
            try:
                # Send data to Kafka only if price has changed
                producer.send('crypto_prices', json.dumps(price).encode('utf-8'))
                logger.info(f"Data sent to Kafka: {price} on topic 'crypto_prices'")
            except Exception as e:
                logger.error(f"Error sending data to Kafka for {price['symbol']}: {e}")

        # Delay between fetches to avoid overwhelming the API
        time.sleep(random.uniform(5, 15))  # Adjust time as needed for your use case

# Define Airflow DAG
default_args = {
    'owner': 'admin',
    'start_date': datetime(2024, 10, 24, 10, 00)
}
with DAG('crypto_price_automation',
         default_args=default_args,
         schedule_interval='@daily',
         catchup=False) as dag:

    streaming_task = PythonOperator(
        task_id='stream_crypto_prices_on_change',
        python_callable=stream_data_on_price_change
    )
