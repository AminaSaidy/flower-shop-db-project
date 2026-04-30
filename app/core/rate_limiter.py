import time
import redis.asyncio as aioredis
from fastapi import Request, HTTPException
from app.core.config import settings

LUA_SCRIPT = """
local key          = KEYS[1]
local capacity     = tonumber(ARGV[1])
local refill_rate  = tonumber(ARGV[2])
local now          = tonumber(ARGV[3])

local bucket      = redis.call("HMGET", key, "tokens", "last_refill")
local tokens      = tonumber(bucket[1]) or capacity
local last_refill = tonumber(bucket[2]) or now

local elapsed = now - last_refill
local refill  = elapsed * refill_rate
tokens = math.min(capacity, tokens + refill)

if tokens >= 1 then
    tokens = tokens - 1
    redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
    redis.call("EXPIRE", key, 3600)
    return 1
else
    redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
    redis.call("EXPIRE", key, 3600)
    return 0
end
"""


class TokenBucketLimiter:
    def __init__(self, redis_client, capacity: int = 5, refill_rate: float = 0.5):
        self.redis       = redis_client
        self.capacity    = capacity
        self.refill_rate = refill_rate
        self._script     = None

    async def is_allowed(self, key: str) -> bool:
        if not self._script:
            self._script = self.redis.register_script(LUA_SCRIPT)
        now    = time.time()
        result = await self._script(
            keys=[f"rate_limit:{key}"],
            args=[self.capacity, self.refill_rate, now]
        )
        return result == 1


_redis_client = None


async def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL)
    return _redis_client


async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/api/orders" and request.method == "POST":
        redis  = await get_redis()
        limiter = TokenBucketLimiter(redis)
        client_ip = request.client.host
        allowed   = await limiter.is_allowed(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Too many order requests. Please wait before trying again."
            )
    return await call_next(request)
