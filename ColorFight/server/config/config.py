#!coding:utf8
import os

kw = {
    "DATABASE_URL": "postgresql+psycopg2://test:test@localhost:5432/colorfight",
    "REDIS_URL": None,
    "ADMIN_PASSWORD": '',
    "ROOM_PASSWORD": None,
    "PROFILE": False,
    "PROFILE_INTERVAL": 5,
    "GAME_VERSION": 'full',
    "GAME_REFRESH_INTERVAL": 0.1,
    "GAME_FEATURE": None,
}


class Config:
    def __getattr__(self, key):
        return os.getenv(key) or kw.get(key)

    def __setattr__(self, key, value):
        raise ValueError("Configration is READ ONLY!")


config = Config()