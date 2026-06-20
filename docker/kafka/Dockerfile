# ─────────────────────────────────────────────────────────────────────────────
# Custom Kafka image — bakes in the ZooKeeper-mode entrypoint and JMX config
# so no host-path bind mounts are needed at runtime.
# ─────────────────────────────────────────────────────────────────────────────
FROM apache/kafka:3.9.0

USER root

# Copy entrypoint and JMX config into the image
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Pre-create JMX directory and download the agent at build time
# so we don't depend on network access at runtime
RUN mkdir -p /tmp/jmx && \
    wget -q -O /tmp/jmx/jmx_prometheus_javaagent.jar \
      "https://repo1.maven.org/maven2/io/prometheus/jmx/jmx_prometheus_javaagent/0.20.0/jmx_prometheus_javaagent-0.20.0.jar" && \
    chown -R appuser:appuser /tmp/jmx

# Copy JMX config if it exists at build time
COPY --chown=appuser:appuser kafka-17x.yaml* /tmp/jmx/

# Ensure appuser can modify the server.properties at runtime
# (the entrypoint patches ZooKeeper mode config on first start)
RUN chown -R appuser:appuser /opt/kafka/config/

USER appuser

ENTRYPOINT ["/entrypoint.sh"]
