"""
Redis Sentinel client for Flink (synchronous)

Flink uses synchronous Python, so we need a sync version of Sentinel client.
Supports both Sentinel mode and direct connection fallback.
"""

import os
import logging
from redis.sentinel import Sentinel
import redis

log = logging.getLogger(__name__)


class FlinkRedisSentinel:
    """
    Synchronous Redis Sentinel client for Flink

    Provides master connection for writes.
    Flink writers only write, so we only need master connection.
    Falls back to direct Redis connection if Sentinel is not configured.
    """

    def __init__(self):
        # Check if Sentinel is configured
        sentinels_str = os.getenv('REDIS_SENTINELS', '')

        if sentinels_str:
            self._mode = 'sentinel'
            self.sentinel_nodes = [
                tuple(node.split(':')) for node in sentinels_str.split(',')
            ]
            # Convert port to int
            self.sentinel_nodes = [
                (host, int(port)) for host, port in self.sentinel_nodes
            ]

            self.master_name = os.getenv('REDIS_MASTER_NAME', 'mymaster')

            # Create sentinel
            self.sentinel = Sentinel(
                self.sentinel_nodes,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                sentinel_kwargs={
                    'socket_timeout': 0.5,
                    'socket_connect_timeout': 0.5
                }
            )
            log.info(f"Flink Redis Sentinel initialized: sentinels={self.sentinel_nodes}, master={self.master_name}")
        else:
            self._mode = 'direct'
            self._redis_host = os.getenv('REDIS_HOST', 'redis-master')
            self._redis_port = int(os.getenv('REDIS_PORT', '6379'))
            self._redis_db = int(os.getenv('REDIS_DB', '0'))
            log.info(f"Flink Redis direct mode: host={self._redis_host}, port={self._redis_port}, db={self._redis_db}")

    def get_master(self):
        """
        Get Redis master connection for writes

        Returns:
            redis.Redis: Master connection
        """
        if self._mode == 'sentinel':
            return self.sentinel.master_for(
                self.master_name,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                decode_responses=True,
                socket_keepalive=True
            )
        else:
            return redis.Redis(
                host=self._redis_host,
                port=self._redis_port,
                db=self._redis_db,
                socket_timeout=0.5,
                socket_connect_timeout=0.5,
                decode_responses=True,
                socket_keepalive=True,
                health_check_interval=30
            )


# Global instance (created once per Flink task)
_flink_sentinel = None


def get_flink_redis():
    """Get Redis master connection with dynamic Sentinel resolution.

    Uses ``sentinel.master_for()`` which re-resolves the master on every
    connection attempt. This avoids stale-IP bugs after Sentinel failover
    (the previous ``discover_master()`` + static pool cached the IP once
    and never updated — causing "No route to host" errors after failover).
    """
    global _flink_sentinel
    if _flink_sentinel is None:
        _flink_sentinel = FlinkRedisSentinel()

    if _flink_sentinel._mode == 'sentinel':
        return _flink_sentinel.get_master()
    else:
        return redis.Redis(
            host=_flink_sentinel._redis_host,
            port=_flink_sentinel._redis_port,
            db=_flink_sentinel._redis_db,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            decode_responses=True,
            socket_keepalive=True,
            health_check_interval=30
        )
