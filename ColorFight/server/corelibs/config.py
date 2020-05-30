#!coding: utf-8
import os


class ConfigBase:
    kw = {}

    def __getattr__(self, item):
        return os.getenv(item) or self.kw.get(item)

    def __setattr__(self, key, value):
        if os.getenv(key) is not None:
            raise EnvironmentError("Environment Vars is setted!")
        if self.kw.get(key) != value:
            self.kw[key] = value

    def __init__(self):
        # load configurations from EVN
        for key in self.kw.keys():
            v = os.getenv(key)
            if v is not None:
                self.kw[key] = v


class ServerConfig(ConfigBase):
    def __init__(self):
        self.kw = {
            "DATABASE_URL": "postgresql+psycopg2://test:test@localhost:5432/colorfight",
            "REDIS_URL": None,
            "ADMIN_PASSWORD": "",
            "ROOM_PASSWORD": None,
            "PROFILE": True,
            "PROFILE_INTERVAL": 5,
            "GAME_VERSION": "full",
            "GAME_REFREASH_INTERVAL": 0.1
        }


class GameConfig(ConfigBase):
    def __init__(self, game_mode="full"):
        self.kw = {
            "BASE_ENABLE": True,
            "GOLD_ENABLE": True,
            "ENERGY_ENABLE": True,
            "BOOST_ENABLE": True,
            "BLAST_ENABLE": True,
            "MULTIATTACK_ENABLE": True,
        }
        if game_mode == "release":
            self.kw.update(ENERGY_ENABLE=False, BOOST_ENABLE=False,
                           BLAST_ENABLE=False, MULTIATTACK_ENABLE=False)


class EnergyShopConfig(ConfigBase):
    def __init__(self):
        self.kw = {
            "BLAST_ATTACK": 30,
            "BLAST_DEFENCE": 40,
            "BOOST": 15,
            "ATTACK": 2,
        }


class GoldShopConfig(ConfigBase):
    def __init__(self):
        self.kw = {
            "MULTI_ATTACK": 40,
            "BLAST_DEFENCE": 40,
            "BASE": 60
        }


server_config = ServerConfig()
game_config = GameConfig()
energy_shop_config = EnergyShopConfig()
gold_shop_config = GoldShopConfig()
