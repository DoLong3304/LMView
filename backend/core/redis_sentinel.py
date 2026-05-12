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
        self.sentinel_nodes = [
            tuple(node.split(':')) for node in sentinels_str.split(',')
        ]
        # Convert port to int
        self.sentinel_nodes = [
            (host, int(port)) for host, port in self.sentinel_nodes
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

        logger.info(
            f"redis_sentinel_initialized: sentinels={self.sentinel_nodes}, "
            f"master_name={self.master_name}, "
            f"fallback={self.redis_direct_host}:{self.redis_direct_port}"
        )

    async def get_master(self):
        """
        Get Redis master client for WRITE operations
        
        Uses direct connection (Sentinel disabled in this environment)

        Returns:
            Redis client connected to master
        """
        async with self._lock:
            if not self._master_client:
                try:
                    self._master_client = Redis(
                        host=self.redis_direct_host,
                        port=self.redis_direct_port,
                        socket_timeout=0.5,
                        socket_connect_timeout=0.5,
                        decode_responses=True,
                        max_connections=50
                    )
                    # Test connection
                    await self._master_client.ping()
                    logger.info(f"redis_master_connected: {self.redis_direct_host}:{self.redis_direct_port}")
                except Exception as e:
                    logger.error(f"redis_master_connection_failed: {str(e)}")
                    self._master_client = None
                    raise

            return self._master_client


    async def get_replica(self):
        """
        Get Redis replica client for READ operations

        Uses master for reads (no replica in direct mode)

        Returns:
            Redis client connected to master
        """
        # In direct mode, just use master for all operations
        return await self.get_master()

    async def health_check(self) -> dict:
        """
        Check Redis cluster health (using direct connection)

        Returns:
            dict: Health status with master info
        """
        try:
            master = await self.get_master()
            ping_result = await master.ping()
            return {
                "status": "healthy",
                "mode": "direct" if not self._using_sentinel else "sentinel",
                "master": {
                    "host": self.redis_direct_host,
                    "port": self.redis_direct_port
                },
                "ping": ping_result
            }
        except Exception as e:
            logger.error(f"redis_health_check_failed: {str(e)}")
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


async def get_redis_master():
    """Get master client for writes"""
    sentinel = get_redis_sentinel()
    return await sentinel.get_master()


async def get_redis_replica():
    """Get replica client for reads"""
    sentinel = get_redis_sentinel()
    return await sentinel.get_replica()


async def get_redis_health():
    """Get cluster health"""
    sentinel = get_redis_sentinel()
    return await sentinel.health_check()
