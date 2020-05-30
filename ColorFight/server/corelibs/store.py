import redis
from flask_sqlalchemy import SQLAlchemy
from corelibs.config import server_config



def create_redis():
    redisConn = None
    if server_config.REDIS_URL:
        pool = redis.BlockingConnectionPool.from_url(server_config.REDIS_URL, max_connections=9)
        redisConn = redis.Redis(connection_pool=pool)
    return redisConn


db = SQLAlchemy()
redis_conn = create_redis()
