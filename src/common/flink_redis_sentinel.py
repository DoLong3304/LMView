"""
Redis client for Flink (synchronous)

Flink uses synchronous Python, so we need a sync Redis client.
Supports both direct connection and Sentinel mode.
"""

import os
import logging
import redis

log = logging.getLogger(__name__)


def get_flink_redis():
    """
    Get Redis connection for Flink writers

    Checks REDIS_SENTINELS env var:
    - If set: Use Sentinel mode
    - If not set: Direct connection to REDIS_HOST

    Returns:
        redis.Redis: Redis connection
    """
    sentinels_str = os.getenv('REDIS_SENTINELS', '')

    if sentinels_str:
        # Sentinel mode
        from redis.sentinel import Sentinel

        sentinel_nodes = [
            tuple(node.split(':')) for node in sentinels_str.split(',')
        ]
        sentinel_nodes = [
            (host, int(port)) for host, port in sentinel_nodes
        ]
        master_name = os.getenv('REDIS_MASTER_NAME', 'mymaster')

        sentinel = Sentinel(
            sentinel_nodes,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            sentinel_kwargs={
                'socket_timeout': 0.5,
                'socket_connect_timeout': 0.5
            }
        )

        log.info(f"Flink Redis Sentinel mode: sentinels={sentinel_nodes}, master={master_name}")

        return sentinel.master_for(
            master_name,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            decode_responses=True,
            socket_keepalive=True
        )
    else:
        # Direct connection mode
        redis_host = os.getenv('REDIS_HOST', 'redis-master')
        redis_port = int(os.getenv('REDIS_PORT', '6379'))
        redis_db = int(os.getenv('REDIS_DB', '0'))

        log.info(f"Flink Redis direct mode: host={redis_host}, port={redis_port}, db={redis_db}")

        return redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30
        )
