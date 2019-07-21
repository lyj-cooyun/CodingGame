#!coding: utf8
from corelibs.config import server_config, energy_shop_config, game_config, gold_shop_config
from corelibs.store import db
from models.user import UserDb


class CellDb(db.Model):
    __tablename__ = 'cells'
    id = db.Column(db.Integer, primary_key=True)
    x = db.Column(db.Integer)
    y = db.Column(db.Integer)
    owner = db.Column(db.Integer, default=0)
    occupy_time = db.Column(db.Float, default=0)
    is_taking = db.Column(db.Boolean, default=False)
    attacker = db.Column(db.Integer, default=0)
    attack_time = db.Column(db.Float, default=0)
    attack_type = db.Column(db.String(15), default="normal")
    finish_time = db.Column(db.Float, default=0)
    last_update = db.Column(db.Float, default=0)
    timestamp = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    cell_type = db.Column(db.String(15), default="normal")
    build_type = db.Column(db.String(15), default="empty")
    build_finish = db.Column(db.Boolean, default=True)
    build_time = db.Column(db.Float, default=0)

    def Init(self, owner, currTime):
        self.owner = owner
        self.attack_time = currTime
        self.is_taking = True
        self.finish_time = currTime
        self.attacker = owner
        self.build_time = 0
        if game_config.BASE_ENABLE:
            self.build_type = "base"
        else:
            self.build_type = "empty"
        self.build_finish = True

    def GetTakeTimeEq(self, timeDiff):
        if timeDiff <= 0:
            return 33
        return 30 * (2 ** (-timeDiff / 30.0)) + 3

    def GetTakeTime(self, currTime):
        if self.is_taking is False:
            if self.owner != 0:
                takeTime = self.GetTakeTimeEq(currTime - self.occupy_time)
            else:
                takeTime = 2
        else:
            takeTime = -1
        return takeTime

    def ToDict(self, currTime):
        return {
            'o': int(self.owner),
            'a': int(self.attacker),
            'c': int(self.is_taking),
            'x': int(self.x),
            'y': int(self.y),
            'ot': float(self.occupy_time),
            'at': float(self.attack_time),
            'aty': str(self.attack_type),
            't': self.GetTakeTime(currTime),
            'f': float(self.finish_time),
            'ct': str(self.cell_type),
            'b': str(self.build_type),
            'bt': float(self.build_time),
            'bf': bool(self.build_finish)
        }

    def Refresh(self, currTime):
        if self.is_taking == True and self.finish_time < currTime:
            if self.build_type == "base" and self.owner != self.attacker:
                self.build_type = "empty"
                if not self.build_finish:
                    self.build_finish = True
                    self.build_time = 0
            self.is_taking = False
            self.owner = self.attacker
            self.occupy_time = self.finish_time
            self.last_update = currTime
            self.attack_type = 'normal'
            return True
        return False

    def RefreshBuild(self, currTime):
        if self.build_type == "base" and\
                self.build_finish is False and self.build_time + 30 <= currTime:
            self.build_finish = True
            return True
        return False

    # user is a locked instance of UserDb
    # user CD is ready, checked already
    # Here we already made sure x and y is valid
    # Do not commit inside this function, it will be done outside of the function
    def Attack(self, user, currTime, boost=False, adjCells=0):
        if self.is_taking is True:
            return False, 2, "This cell is being taken."

        if self.owner != user.id and adjCells == 0:
            return False, 1, "Cell position invalid or it's not adjacent to your cell."

        takeTime = (self.GetTakeTime(currTime) * min(1, 1 - 0.25 * (adjCells - 1))) / (1 + user.energy / 200.0)

        if server_config.BOOST_ENABLE and boost == True:
            if user.energy < energy_shop_config.BOOST:
                return False, 5, "You don't have enough energy"
            else:
                user.energy -= energy_shop_config.BOOST
                takeTime = max(1, takeTime * 0.25)
        else:
            if user.energy > 0 and self.owner != 0 and user.id != self.owner:
                user.energy = user.energy * 0.95

        self.attacker = user.id
        self.attack_time = currTime
        self.finish_time = currTime + takeTime
        self.is_taking = True
        self.last_update = currTime
        self.attack_type = 'normal'
        user.cd_time = max(user.cd_time, self.finish_time)
        return True, None, None

    def BuildBase(self, user, currTime):
        if not game_config.BASE_ENABLE:
            return True, None, None
        if self.is_taking is True:
            return False, 2, "This cell is being taken."
        if self.build_type == "base":
            return False, 6, "This cell is already a base."

        user.gold = user.gold - gold_shop_config.BASE
        user.build_cd_time = currTime + 30
        self.build_type = "base"
        self.build_time = currTime
        self.build_finish = False
        return True, None, None

    def Blast(self, uid, direction, currTime):
        energyCost = 0
        goldCost = 0
        if not game_config.BLAST_ENABLE:
            return True, None, None
        energyCost = energy_shop_config.BLASK_ATTACK

        if self.owner != uid:
            return False, 1, "Cell position invalid!"

        if direction == "square":
            db.session.commit()
            cells = CellDb.query.filter(CellDb.x >= self.x - 1).filter(CellDb.x <= self.x + 1) \
                .filter(CellDb.y >= self.y - 1).filter(CellDb.y <= self.y + 1) \
                .with_for_update().all()
        elif direction == "vertical":
            db.session.commit()
            cells = CellDb.query.filter(CellDb.y >= self.y - 4).filter(CellDb.y <= self.y + 4) \
                .filter(CellDb.x == self.x) \
                .with_for_update().all()
        elif direction == "horizontal":
            db.session.commit()
            cells = CellDb.query.filter(CellDb.x >= self.x - 4).filter(CellDb.x <= self.x + 4) \
                .filter(CellDb.y == self.y) \
                .with_for_update().all()
        else:
            return False, 1, "Invalid direction"

        user = UserDb.query.with_for_update().get(uid)
        if user.cd_time > currTime:
            return False, 3, "You are in CD time!"
        if user.energy < energyCost:
            return False, 5, "Not enough energy!"
        user.energy = user.energy - energyCost

        for cell in cells:
            if (cell.x != self.x or cell.y != self.y) and (
                    cell.owner != uid or (cell.is_taking and cell.attacker != uid)):
                cell.attacker = 0
                cell.attack_time = currTime
                cell.finish_time = currTime + 1
                cell.attack_type = 'blast'
                cell.is_taking = True

        user.cd_time = currTime + 1

        db.session.commit()
        return True, None, None
