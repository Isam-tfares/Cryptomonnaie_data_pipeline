
**This repository demonstrates a data engineering pipeline for managing cryptocurrency data. It retrieves real-time crypto data from an API, sends the data to Kafka topics via Airflow, processes it with Spark Structured Streaming, and stores it in a Cassandra database.**

# System Architecture

![alt text](img/architecture.png)

## Components:

**Data Source:** Uses a cryptocurrency data API to generate real-time data. \
**Apache Airflow:** Orchestrates the pipeline and schedules data ingestion. \
**Apache Kafka & Zookeeper:** Stream data from PostgreSQL to Spark. \
**Apache Spark:** Processes data in real time. \
**Cassandra:** Stores the processed data. \
**Scripts:**

**kafka_stream.py:** Airflow DAG script that pushes API data to Kafka if a price was changing \
**spark_stream.py:** Consumes and processes data from Kafka using Spark Structured Streaming. 

## What You'll Learn:

Setting up and orchestrating pipelines with Apache Airflow. \
Real-time data streaming with Apache Kafka. \
Synchronization with Apache Zookeeper. \
Data processing with Apache Spark. \
Storage solutions with Cassandra and PostgreSQL. \
Containerization of the entire setup using Docker. \
**Technologies:** \
Apache Airflow, Python, Apache Kafka, Apache Zookeeper, Apache Spark, Cassandra, PostgreSQL, Docker 

## Getting Started

### WebUI links

`Airflow`  : <http://localhost:8080/> \
`Kafka UI` : <http://localhost:8085/> \

### Clone the repository:

`$ git clone https://github.com/akarce/Cryptomonnaie_data_pipeline`

### Navigate to the project directory:

`$ cd Cryptomonnaie_data_pipeline`

### Create an .env file in project folder and set an AIRFLOW_UID

`$ echo -e "AIRFLOW_UID=$(id -u)" > .env`

`$ echo AIRFLOW_UID=50000 >> .env`


### Run Docker Compose to perform database migrations and create the first user account

`$ docker-compose up airflow-init`

![alt text](img/airflow-init.png)


### Run Docker Compose again to spin up the services:

`$ docker compose up -d`

![alt text](img/compose-up-d.png)


### Copy the dependencies.zip and spark_stream.py files into spark-master container

`$ docker cp dependencies.zip spark-master:/dependencies.zip`

`$ docker cp spark_stream.py spark-master:/spark_stream.py`

![alt text](img/docker-cp.png)

### Run the docker exec command to access cqlsh shell in cassandra container 

`$ docker exec -it cassandra cqlsh -u cassandra -p cassandra localhost 9042`

### Run describe command to see there are no keyspaces named in cassandra instance

`cqlsh> DESCRIBE KEYSPACES;`

![cqlsh no keyspace](img/cqlsh_no_keyspace.png)

### Unpause the dag crypto_price_automation using Airflow UI

**Go to Airflow UI using :** <http://localhost:8080/>

**Login using** Username: `admin` Password: `admin`

![unpause the crypto_price_automation](img/unpause_crypto_price_automation.png)

**You can track the topic creation and message queue using the open source tool named UI for Apache Kafka that is running as a container, WebUI link:**  <http://localhost:8085/>

![alt text](img/kafkaui.png)

**Message schema looks like this**

![alt text](img/kafkaui-message.png)

### In a new terminal run the docker exec command to run spark job to read the streaming from kafka topic:

`$ docker exec -it spark-master spark-submit     --packages com.datastax.spark:spark-cassandra-connector_2.12:3.5.1,org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1     --py-files /dependencies.zip     /spark_stream.py`


### Now go back to the cqlsh shell terminal back and run the command to see data is inserted to cassandra table called created_users

`cqlsh> SELECT * FROM crypto_data.daily_prices;`

![alt text](img/crypto_data.png)

#### and run count query several times to approve data is being inserted while running crypto_price_automation dag

`cqlsh> SELECT count(*) FROM crypto_data.daily_prices;`

![alt text](img/count-crypto_data.png)
