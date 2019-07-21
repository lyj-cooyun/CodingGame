#!coding:utf8
from corelibs.store import db
from corelibs.config import server_config


class InfoDb(db.Model):
    __tablename__ = 'info'
    id = db.Column(db.Integer, primary_key=True)
    width = db.Column(db.Integer, default=0)
    height = db.Column(db.Integer, default=0)
    max_id = db.Column(db.Integer, default=0)
    end_time = db.Column(db.Float, default=0)
    join_end_time = db.Column(db.Float, default=0)
    ai_only = db.Column(db.Boolean, default=False)
    last_update = db.Column(db.Float, default=0)
    game_id = db.Column(db.Integer, default=0)
    plan_start_time = db.Column(db.Float, default=0)

    def Copy(self, other):
        self.width = other.width
        self.height = other.height
        self.max_id = other.max_id
        self.end_time = other.end_time
        self.join_end_time = other.join_end_time
        self.ai_only = other.ai_only
        self.last_update = other.last_update
        self.game_id = other.game_id
        self.plan_start_time = 0

    def ToDict(self, currTime):
        return {
            'width': int(self.width),
            'height': int(self.height),
            'time': float(currTime),
            'end_time': float(self.end_time),
            'join_end_time': float(self.join_end_time),
            'game_id': int(self.game_id),
            'game_version': str(server_config.GAME_VERSION),
            'plan_start_time': float(self.plan_start_time),
            'ai_only': bool(self.ai_only)
        }
