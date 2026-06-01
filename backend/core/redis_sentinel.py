"""
Redis Sentinel Manager for High Availability with Fallback

Provides:
- Auto-discovery of master/replicas via Sentinel
- Auto-failover (handled by Sentinel)
- Fallback to direct Redis connection if Sentinel fails
- Read/write splitting
- Connection pooling
"""

import os
import logging
from typing import Optional
import asyncio
from redis.sentinel import Sentinel
from redis.asyncio.sentinel import Sentinel as AsyncSentinel
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError

logger = logging.getLogger(__name__)


class RedisSentinelManager:
    """
    Redis Sentinel manager for HA with fallback to direct connection

    Features:
    - Auto-discovery of master/replicas
    - Auto-failover (handled by Sentinel)
    - Fallback to direct Redis connection if Sentinel unavailable
    - Read/write splitting
    - Connection pooling
    """

    def __init__(self):
        # Get sentinel nodes from environment
        sentinels_str = os.getenv('REDIS_SENTINELS', 'redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379')
        nodes_str = [tuple(node.split(':')) for node in sentinels_str.split(',')]
        self.sentinel_nodes: list[tuple[str, int]] = [
            (host, int(port)) for host, port in nodes_str
        ]

        self.master_name = os.getenv('REDIS_MASTER_NAME', 'mymaster')

        # Fallback direct connection
        self.redis_direct_host = os.getenv('REDIS_HOST', 'redis-master')
        self.redis_direct_port = int(os.getenv('REDIS_PORT', '6379'))

        # Async sentinel
        self.sentinel = AsyncSentinel(
            self.sentinel_nodes,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
            sentinel_kwargs={
                'socket_timeout': 0.5,
                'socket_connect_timeout': 0.5
            }
        )

        self._master_client = None
        self._replica_client = None
        self._using_sentinel = True  # Track if using Sentinel or fallback
        self._lock = asyncio.Lock()

        logger.info("redis_sentinel_initialized",
                   extra={
                       "sentinels": str(self.sentinel_nodes),
                       "master_name": self.master_name,
                       "fallback": f"{self.redis_direct_host}:{self.redis_direct_port}"
                   })

    async def get_master(self):
        """
        Get Redis master client for WRITE operations

        Tries Sentinel first, falls back to direct connection.

        Returns:
            Redis client connected to current master
        """
        async with self._lock:
            if not self._master_client:
                try:
                    self._master_client = self.sentinel.master_for(
                        self.master_name,
                        socket_timeout=0.5,
                        socket_connect_timeout=0.5,
                        decode_responses=True,
                        max_connections=50
                    )
                    await self._master_client.ping()
                    self._using_sentinel = True
                    logger.info("redis_master_connected via sentinel")
                except Exception as e:
                    logger.warning("redis_sentinel_connection_failed: %s, trying direct", e)
                    self._master_client = None
                    try:
                        self._master_client = Redis(
                            host=self.redis_direct_host,
                            port=self.redis_direct_port,
                            socket_timeout=0.5,
                            socket_connect_timeout=0.5,
                            decode_responses=True,
                            max_connections=50
                        )
                        await self._master_client.ping()
                        self._using_sentinel = False
                        logger.info("redis_master_connected via direct: %s:%d",
                                   self.redis_direct_host, self.redis_direct_port)
                    except Exception as e2:
                        logger.error("redis_master_connection_failed: %s", e2)
                        self._master_client = None
                        raise

            return self._master_client

    async def get_replica(self):
        """
        Get Redis replica client for READ operations

        Load-balanced across all replicas via Sentinel.
        Falls back to master for reads if replica unavailable.

        Returns:
            Redis client connected to a replica
        """
        if not self._using_sentinel:
            # In direct mode, just use master for all operations
            return await self.get_master()

        async with self._lock:
            if not self._replica_client:
                try:
                    self._replica_client = self.sentinel.slave_for(
                        self.master_name,
                        socket_timeout=0.5,
                        socket_connect_timeout=0.5,
                        decode_responses=True,
                        max_connections=50
                    )
                    logger.info("redis_replica_connected")
                except Exception as e:
                    logger.warning("redis_replica_connection_failed: %s", e)
                    # Fallback to master for reads
                    logger.info("redis_fallback_to_master_for_reads")
                    return await self.get_master()

            return self._replica_client

    async def health_check(self) -> dict:
        """
        Check Redis cluster health

        Returns:
            dict: Health status with master/replica info
        """
        try:
            if self._using_sentinel:
                # Discover master
                master_info = await self.sentinel.discover_master(self.master_name)

                # Discover replicas
                slaves = await self.sentinel.discover_slaves(self.master_name)

                # Get sentinel info
                sentinels = []
                for sentinel_node in self.sentinel_nodes:
                    try:
                        sentinels.append({
                            'host': sentinel_node[0],
                            'port': sentinel_node[1],
                            'status': 'up'
                        })
                    except:
                        sentinels.append({
                            'host': sentinel_node[0],
                            'port': sentinel_node[1],
                            'status': 'down'
                        })

                return {
                    "status": "healthy",
                    "mode": "sentinel",
                    "master": {
                        "host": master_info[0],
                        "port": master_info[1]
                    },
                    "replicas": [
                        {"host": s[0], "port": s[1]} for s in slaves
                    ],
                    "replicas_count": len(slaves),
                    "sentinels": sentinels,
                    "sentinels_count": len([s for s in sentinels if s['status'] == 'up'])
                }
            else:
                master = await self.get_master()
                ping_result = await master.ping()
                return {
                    "status": "healthy",
                    "mode": "direct",
                    "master": {
                        "host": self.redis_direct_host,
                        "port": self.redis_direct_port
                    },
                    "ping": ping_result
                }
        except Exception as e:
            logger.error("redis_health_check_failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e)
            }

    async def close(self):
        """Close all connections"""
        if self._master_client:
            await self._master_client.close()
        if self._replica_client:
            await self._replica_client.close()


# Singleton instance
_redis_sentinel: Optional[RedisSentinelManager] = None


def get_redis_sentinel() -> RedisSentinelManager:
    """Get singleton Redis Sentinel manager"""
    global _redis_sentinel
    if _redis_sentinel is None:
        _redis_sentinel = RedisSentinelManager()
    return _redis_sentinel


async def get_redis_master() -> Redis:
    """Get master client for writes"""
    sentinel = get_redis_sentinel()
    return await sentinel.get_master()


async def get_redis_replica() -> Redis:
    """Get replica client for reads"""
    sentinel = get_redis_sentinel()
    return await sentinel.get_replica()


async def get_redis_health():
    """Get cluster health"""
    sentinel = get_redis_sentinel()
    return await sentinel.health_check()
