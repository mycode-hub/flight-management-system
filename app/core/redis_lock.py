import time
import redis

class RedisLock:
    def __init__(self, redis_client: redis.Redis, lock_key: str, timeout: int = 10):
        self.redis_client = redis_client
        self.lock_key = lock_key
        self.timeout = timeout

    def __enter__(self):
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            if self.redis_client.setnx(self.lock_key, "locked"):
                self.redis_client.expire(self.lock_key, self.timeout)
                return self
            time.sleep(0.1)
        raise TimeoutError("Could not acquire lock")

    def __exit__(self, exc_type, exc_value, traceback):
        self.redis_client.delete(self.lock_key)
