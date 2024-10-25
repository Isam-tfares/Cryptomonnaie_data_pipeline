import logging
from datetime import datetime

from cassandra.cluster import Cluster
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, FloatType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)

def create_keyspace(session):
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS crypto_data
        WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}
        """)
    logger.info("Keyspace created successfully")

def create_table(session):
    session.execute("""
        CREATE TABLE IF NOT EXISTS crypto_data.daily_prices (
            symbol TEXT,
            date TEXT,
            open FLOAT,
            high FLOAT,
            low FLOAT,
            close FLOAT,
            volume FLOAT,
            PRIMARY KEY (symbol, date)
        );
    """)
    logger.info("Table created successfully")

def insert_data(session, row):
    logger.info("Inserting data")

    symbol = row['symbol']
    date = row['date']
    open_price = row['open']
    high_price = row['high']
    low_price = row['low']
    close_price = row['close']
    volume = row['volume']

    if symbol is None or date is None:
        return

    try:
        session.execute("""
            INSERT INTO crypto_data.daily_prices (symbol, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (symbol, date, open_price, high_price, low_price, close_price, volume))
        logger.info(f"Data inserted for {symbol} on {date}")

    except Exception as e:
        logger.error(f"Error while inserting data: {e}")

def create_spark_connection():
    s_conn = None

    try:
        s_conn = SparkSession.builder \
            .appName('CryptoDataStreaming') \
            .config('spark.jars.packages', "com.datastax.spark:spark-cassandra-connector_2.12:3.5.1,"
                                           "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1") \
            .config('spark.cassandra.connection.host', 'cassandra_db') \
            .getOrCreate()
        s_conn.sparkContext.setLogLevel("ERROR")
        logger.info("Spark connection created successfully")

    except Exception as e:
        logger.error(f"Error while creating spark connection: {e}")
    
    return s_conn

def connect_to_kafka(spark_conn):
    # Define schema for cryptocurrency data
    schema = StructType([
        StructField("symbol", StringType(), False),
        StructField("date", StringType(), False),
        StructField("open", FloatType(), False),
        StructField("high", FloatType(), False),
        StructField("low", FloatType(), False),
        StructField("close", FloatType(), False),
        StructField("volume", FloatType(), False)
    ])

    df = spark_conn \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:9093") \
        .option("subscribe", "crypto_prices") \
        .option("startingOffsets", "earliest") \
        .option("failOnDataLoss", "false") \
        .load() \
        .selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)") \
        .select(from_json(col("value"), schema).alias("data")) \
        .select("data.*")

    return df

def create_cassandra_connection():
    try:
        # Connection to Cassandra cluster
        cluster = Cluster(['cassandra_db'])
        cas_session = cluster.connect()
        logger.info("Cassandra connection created successfully")
        return cas_session
    
    except Exception as e:
        logger.error(f"Error while creating Cassandra connection: {e}")
        return None

def process_batch(batch_df, batch_id, session):
    logger.info(f"Processing batch {batch_id}")

    batch_df.collect()  # This ensures the batch is fully processed before proceeding
    for row in batch_df.collect():
        insert_data(session, row)

if __name__ == "__main__":
    # Create Spark connection
    spark_conn = create_spark_connection()

    if spark_conn is not None:
        # Create connection to Kafka with Spark
        selection_df = connect_to_kafka(spark_conn)

        logger.info("Selection dataframe schema:")
        selection_df.printSchema()

        # Create Cassandra connection
        session = create_cassandra_connection()
        
        if session is not None:
            create_keyspace(session)
            create_table(session)

            # Process each micro-batch of data and insert into Cassandra
            streaming_query = selection_df.writeStream \
                .foreachBatch(lambda batch_df, batch_id: process_batch(batch_df, batch_id, session)) \
                .option('checkpointLocation', '/tmp/checkpoint') \
                .start()

            streaming_query.awaitTermination()

            # Close the Cassandra session when done
            session.shutdown()
