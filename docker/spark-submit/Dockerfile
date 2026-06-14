# Spark submit supervisor image.
#
# Reuses apache/spark:3.5.5 (has JDK 11 + spark-submit at
# /opt/spark/bin/spark-submit + pyspark at /opt/spark/python).
# The supervisor script keeps the pipeline running and restarts
# it on JVM exit (OOM, code error, network blip).

FROM apache/spark:3.5.5

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# pip3 is provided by the base image but is not strictly needed;
# pyspark 3.5.5 ships with the Spark distribution.
ENV SPARK_HOME=/opt/spark
ENV PATH="${SPARK_HOME}/bin:${PATH}"
ENV PYTHONPATH=/app:${PYTHONPATH}

WORKDIR /app

COPY --chmod=0755 docker/spark-submit/spark-submit.sh /usr/local/bin/spark-submit.sh

CMD ["/usr/local/bin/spark-submit.sh"]
