FROM trinodb/trino:442

# Copy config templates (with __PLACEHOLDER__ tokens)
COPY docker/trino/etc/ /etc/trino/

# Pre-download JMX Prometheus agent at build time.
# Stored in /opt/trino-jmx/ (not /etc/trino/jmx/) because the compose
# volume mount at /etc/trino/jmx is read-only and would shadow this jar.
USER root
RUN mkdir -p /opt/trino-jmx && \
    curl -fsSL -o /opt/trino-jmx/jmx_prometheus_javaagent.jar \
      "https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar"

# Entrypoint that substitutes env vars then starts Trino
COPY docker/trino/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh && \
    sed -i -e 's/\r$//' /usr/local/bin/entrypoint.sh && \
    chown -R trino:trino /etc/trino
USER trino

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
