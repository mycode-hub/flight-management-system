
import redis
from app.core.config import settings

def test_redis_connection():
    """Tests the connection to Redis."""
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        print("Successfully connected to Redis!")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")

if __name__ == "__main__":
    test_redis_connection()
