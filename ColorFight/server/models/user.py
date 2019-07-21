#!coding: utf8
from corelibs.store import db
from models.info import InfoDb

class UserDb(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    token = db.Column(db.String(32), default="")
    cd_time = db.Column(db.Float, default=0)
    build_cd_time = db.Column(db.Float, default=0)
    cells = db.Column(db.Integer, default=0)
    bases = db.Column(db.Integer, default=0)
    energy_cells = db.Column(db.Integer, default=0)
    gold_cells = db.Column(db.Integer, default=0)
    dirty = db.Column(db.Boolean, default=False)
    energy = db.Column(db.Float, default=0)
    gold = db.Column(db.Float, default=0)
    dead_time = db.Column(db.Float, default=0)

    # Pre: lock user
    # Post: lock user
    def Dead(self, currTime):
        info = InfoDb.query.get(0);
        if info.end_time != 0:
            self.dead_time = currTime
            self.token = ""
            self.energy = 0
            self.gold = 0
            self.energy_cells = 0
            self.gold_cells = 0
            self.bases = 0
            return False
        else:
            db.session.delete(self)
            return True

    def ToDict(self, simple=False):
        # Web display will request for a simple version
        if simple:
            return {"name": self.name, "id": self.id, "cd_time": self.cd_time, "cell_num": self.cells,
                    "energy": self.energy, "gold": self.gold, "dead_time": self.dead_time}
        return {
            "name": self.name.encode("utf-8", "ignore"),
            "id": int(self.id),
            "cd_time": float(self.cd_time),
            "build_cd_time": float(self.build_cd_time),
            "cell_num": int(self.cells),
            "base_num": int(self.bases),
            "energy_cell_num": int(self.energy_cells),
            "gold_cell_num": int(self.gold_cells),
            "energy": float(self.energy),
            "gold": float(self.gold),
            "dead_time": float(self.dead_time)
        }