#!coding:utf8
import json
import logging
from functools import wraps
from corelibs.store import redis_conn


DEFAULT_EXPIRE = 60 * 60


def cache(key, ttl=DEFAULT_EXPIRE):
    def wrap(func):
        @wraps(func)
        def deco(*a, **kw):
            if not key.startswith("cache"):
                raise ValueError("Cache key must start with cache")
            try:
                cached = redis_conn.get(key)
                if cached is not None:
                    return json.loads(cached)
            except Exception, e:
                logging.warn("Cache service is crashed: %s" % e.message)
            val = func(*a, **kw)
            try:
                redis_conn.setex(key, json.dumps(val), ttl)
            except Exception, e:
                logging.warn("Cache service is crash: %s" % e.message)
            return val
        return deco
    return wrap


def clean_cache(key):
    redis_conn.delete([key, ])


def clean_all_cache():
    # CAUTION: command KEYS will block all redis service
    # only call this func before game start
    keys = redis_conn.keys("cache:*")
    redis_conn.delete(keys)
