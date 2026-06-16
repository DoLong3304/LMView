FROM flink:1.18.1-java11

# â”€â”€ Python 3.11 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RUN apt-get update -o Acquire::Retries=3 && apt-get install -y --no-install-recommends \
        python3 python3-pip python3-dev wget curl && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# â”€â”€ Python dependencies â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RUN pip3 install --no-cache-dir \
    apache-flink==1.18.1 \
    influxdb-client==1.44.0 \
    redis==5.0.3 \
    prometheus_client==0.20.0

# â”€â”€ Kafka SQL connector JAR (Flink 1.18) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Avro Confluent Registry format JAR (for avro-confluent deserialization)
RUN wget -q -P /opt/flink/lib/ \
    https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.1.0-1.18/flink-sql-connector-kafka-3.1.0-1.18.jar && \
    wget -q -P /opt/flink/lib/ \
    https://repo1.maven.org/maven2/org/apache/flink/flink-sql-avro-confluent-registry/1.18.1/flink-sql-avro-confluent-registry-1.18.1.jar

# â”€â”€ Flink config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
COPY flink-conf.yaml /opt/flink/conf/flink-conf.yaml
# Install filesystem plugins where Flink actually loads them from.
RUN mkdir -p /opt/flink/plugins/flink-s3-fs-hadoop \
    /opt/flink/plugins/flink-s3-fs-presto && \
    cp /opt/flink/opt/flink-s3-fs-hadoop-1.18.1.jar /opt/flink/plugins/flink-s3-fs-hadoop/ && \
    cp /opt/flink/opt/flink-s3-fs-presto-1.18.1.jar /opt/flink/plugins/flink-s3-fs-presto/


# â”€â”€ Fix checkpoint directory permissions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
RUN mkdir -p /tmp/flink-checkpoints && chown -R flink:flink /tmp/flink-checkpoints

ENV PYFLINK_PYTHON=python3
