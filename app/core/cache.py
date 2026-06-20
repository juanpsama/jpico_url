import asyncio
import secrets
import time
from typing import Callable, Optional
import redis.asyncio as aioredis
from redis.exceptions import WatchError

from app.core.config import settings

ACQUIRE_LOCK_SCRIPT = """
if redis.call('SET', KEYS[1], ARGV[1], 'NX', 'PX', ARGV[2]) then
    return 1
end
return 0
"""

RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""


class RedisCache:

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        prefix: str = "cache:url:",
        ttl: int = 30,
        lock_ttl_ms: int = 2000,
        wait_poll_ms: int = 25,
    ) -> None:
        self.redis = redis_client
        self.prefix = prefix
        self.ttl = ttl
        self.lock_ttl_ms = lock_ttl_ms
        self.wait_poll_ms = wait_poll_ms

        self._acquire_lock = self.redis.register_script(ACQUIRE_LOCK_SCRIPT)
        self._release_lock = self.redis.register_script(RELEASE_LOCK_SCRIPT)

        self._stats_lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
        self._stampedes_suppressed = 0

    def _cache_key(self, entity_id: str) -> str:
        return f"{self.prefix}{entity_id}"

    def _lock_key(self, entity_id: str) -> str:
        return f"lock:{self.prefix}{entity_id}"

    async def get(
        self,
        entity_id: str,
        loader: Callable[[str], Optional[dict[str, str]]],
    ) -> tuple[Optional[dict[str, str]], bool, float]:
        cache_key = self._cache_key(entity_id)

        started = time.perf_counter()
        cached = await self.redis.hgetall(cache_key)
        redis_latency_ms = (time.perf_counter() - started) * 1000.0

        if cached:
            async with self._stats_lock:
                self._hits += 1
            return cached, True, redis_latency_ms

        async with self._stats_lock:
            self._misses += 1

        record = await self._load_with_single_flight(entity_id, loader)
        return record, False, redis_latency_ms

    async def _load_with_single_flight(
        self,
        entity_id: str,
        loader: Callable[[str], Optional[dict[str, str]]],
    ) -> Optional[dict[str, str]]:
        cache_key = self._cache_key(entity_id)
        lock_key = self._lock_key(entity_id)
        token = secrets.token_hex(8)

        acquired = await self._acquire_lock(
            keys=[lock_key],
            args=[token, self.lock_ttl_ms],
        )

        if acquired:
            try:
                record = loader(entity_id)
                if record is None:
                    return None
                pipe = self.redis.pipeline()
                pipe.delete(cache_key)
                pipe.hset(cache_key, mapping=record)
                pipe.expire(cache_key, self.ttl)
                await pipe.execute()
                return record
            finally:
                await self._release_lock(keys=[lock_key], args=[token])

        async with self._stats_lock:
            self._stampedes_suppressed += 1

        deadline = time.monotonic() + (self.lock_ttl_ms / 1000.0)
        while time.monotonic() < deadline:
            await asyncio.sleep(self.wait_poll_ms / 1000.0)
            cached = await self.redis.hgetall(cache_key)
            if cached:
                return cached

        return loader(entity_id)

    async def invalidate(self, entity_id: str) -> bool:
        return await self.redis.delete(self._cache_key(entity_id)) == 1

    async def update_field(self, entity_id: str, field: str, value: str) -> bool:
        cache_key = self._cache_key(entity_id)
        pipe = self.redis.pipeline()
        while True:
            try:
                await pipe.watch(cache_key)
                if not await pipe.exists(cache_key):
                    await pipe.unwatch()
                    return False
                pipe.multi()
                pipe.hset(cache_key, field, value)
                pipe.expire(cache_key, self.ttl)
                await pipe.execute()
                return True
            except WatchError:
                continue

    async def ttl_remaining(self, entity_id: str) -> int:
        return int(await self.redis.ttl(self._cache_key(entity_id)))

    async def stats(self) -> dict:
        async with self._stats_lock:
            total = self._hits + self._misses
            hit_rate = round(100.0 * self._hits / total, 1) if total else 0.0
            return {
                "hits": self._hits,
                "misses": self._misses,
                "stampedes_suppressed": self._stampedes_suppressed,
                "hit_rate_pct": hit_rate,
            }

    async def reset_stats(self) -> None:
        async with self._stats_lock:
            self._hits = 0
            self._misses = 0
            self._stampedes_suppressed = 0

_redis_client: aioredis.Redis | None = None


async def get_redis_cache():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            ssl=True,
            decode_responses=True,
        )
    cache = RedisCache(
        redis_client=_redis_client,
        prefix="cache:url:",
        ttl=settings.CACHED_TTL_SECONDS,
    )
    yield cache
    # Client is module-level singleton — do not close per-request