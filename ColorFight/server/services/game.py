#!coding:utf8
import random
import json

from corelibs.store import db, redis_conn
from corelibs.cache import cache
from corelibs.config import game_config, server_config, energy_shop_config, gold_shop_config
from models.cell import CellDb
from models.user import UserDb
from models.info import InfoDb


def ClearCell(uid):
    CellDb.query.filter_by(attacker=uid).with_for_update().update({'is_taking': False, 'attacker': 0})
    db.session.commit()
    CellDb.query.filter_by(owner=uid).with_for_update().update(
        {'owner': 0, 'build_type': 'empty', 'build_finish': True, 'build_time': 0})
    db.session.commit()


def MoveBase(baseMoveList):
    for baseData in baseMoveList:
        uid = baseData[0]
        x = baseData[1]
        y = baseData[2]
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        random.shuffle(directions)
        for d in directions:
            cell = CellDb.query.filter_by(x=x + d[0], y=y + d[1], owner=uid,
                                          build_type="empty").with_for_update().first()
            if cell == None:
                db.session.commit()
            else:
                cell.build_type = "base"
                cell.build_finish = True
                db.session.commit()
                break


@cache(key="cache:func:get_game_size")
def GetGameSize():
    i = InfoDb.query.get(0)
    if i is not None:
        return i.width, i.height
    return None, None


def UpdateGame(currTime, timeDiff):
    # Refresh the cells that needs to be refreshed first because this will
    # lock stuff
    cells = CellDb.query.filter(CellDb.finish_time < currTime).filter_by(is_taking=True).with_for_update().all()

    dirtyUserIds = {}
    baseMoveList = []
    for cell in cells:
        owner = cell.owner
        isBase = cell.build_type == "base" and cell.build_finish == True
        if cell.attacker not in dirtyUserIds:
            dirtyUserIds[cell.attacker] = set()
        if cell.owner not in dirtyUserIds:
            dirtyUserIds[cell.owner] = set()
        if isBase:
            dirtyUserIds[cell.attacker].add('base')
            dirtyUserIds[cell.owner].add('base')
        if cell.cell_type == 'energy':
            dirtyUserIds[cell.attacker].add('energy')
            dirtyUserIds[cell.owner].add('energy')
        if cell.cell_type == 'gold':
            dirtyUserIds[cell.attacker].add('gold')
            dirtyUserIds[cell.owner].add('gold')
        if cell.Refresh(currTime):
            if isBase and owner != cell.owner:
                baseMoveList.append((owner, cell.x, cell.y))

    db.session.commit()

    cells = CellDb.query.filter(CellDb.build_type == "base").filter(CellDb.build_finish == False).filter(
        CellDb.build_time + 30 <= currTime).with_for_update().all()
    for cell in cells:
        if cell.RefreshBuild(currTime):
            if cell.owner not in dirtyUserIds:
                dirtyUserIds[cell.owner] = set()
            dirtyUserIds[cell.owner].add('base')

    db.session.commit()

    MoveBase(baseMoveList)

    users = UserDb.query.with_for_update().all()
    userInfo = []
    deadUserIds = []
    for user in users:
        if user.id in dirtyUserIds:
            if 'base' in dirtyUserIds[user.id]:
                user.bases = db.session.query(db.func.count(CellDb.id)).filter(CellDb.owner == user.id).filter(
                    CellDb.build_type == "base").filter(CellDb.build_finish == True).scalar()

            if 'energy' in dirtyUserIds[user.id]:
                user.energy_cells = db.session.query(db.func.count(CellDb.id)).filter(CellDb.owner == user.id).filter(
                    CellDb.cell_type == 'energy').scalar()

            if 'gold' in dirtyUserIds[user.id]:
                user.gold_cells = db.session.query(db.func.count(CellDb.id)).filter(CellDb.owner == user.id).filter(
                    CellDb.cell_type == 'gold').scalar()

            cellNum = db.session.query(db.func.count(CellDb.id)).filter(CellDb.owner == user.id).scalar()
            cellNum += 9 * user.gold_cells
            user.cells = cellNum

        if (user.cells == 0 or (game_config.BASE_ENABLE and user.bases == 0)) and user.dead_time == 0:
            deadUserIds.append(user.id)
            if not user.Dead(currTime):
                userInfo.append(user.ToDict())

        else:
            if timeDiff > 0:
                if user.energy_cells > 0:
                    user.energy = user.energy + timeDiff * user.energy_cells * 0.5
                    user.energy = min(100, user.energy)
                else:
                    user.energy = max(user.energy, 0)

                if game_config.GOLD_ENABLE and user.gold_cells > 0:
                    user.gold = user.gold + timeDiff * user.gold_cells * 0.5
                    user.gold = min(100, user.gold)
                else:
                    user.gold = max(user.gold, 0)
            userInfo.append(user.ToDict())

    db.session.commit()

    for uid in deadUserIds:
        ClearCell(uid)

    return userInfo


def ClearGame(currTime, softRestart, gameSize, gameId):
    width = gameSize[0]
    height = gameSize[1]

    if softRestart:
        CellDb.query.with_for_update().update(
            {'owner': 0, 'occupy_time': 0, 'is_taking': False, 'attacker': 0, 'attack_time': 0, 'attack_type': 'normal',
             'last_update': currTime, 'cell_type': 'normal', 'build_type': "empty", 'build_finish': "true",
             'build_time': 0})
    else:
        for y in range(height):
            for x in range(width):
                c = CellDb.query.with_for_update().get(x + y * width)
                if c == None:
                    c = CellDb(id=x + y * width, x=x, y=y, last_update=currTime, build_type="empty", build_finish=True)
                    db.session.add(c)
                else:
                    c.owner = 0
                    c.x = x
                    c.y = y
                    c.occupy_time = 0
                    c.is_taking = False
                    c.attacker = 0
                    c.attack_time = 0
                    c.attack_type = 'normal'
                    c.last_update = currTime
                    c.cell_type = 'normal'
                    c.build_type = 'empty'
                    c.build_finish = True

    users = UserDb.query.with_for_update().all()
    for user in users:
        db.session.delete(user)

    db.session.commit()

    totalCells = gameSize[0] * gameSize[1]

    goldenCells = CellDb.query.order_by(db.func.random()).with_for_update().limit(int(0.02 * totalCells))
    for cell in goldenCells:
        cell.cell_type = 'gold'

    if game_config.ENERGY_ENABLE:
        energyCells = CellDb.query.filter_by(cell_type='normal').order_by(db.func.random()).with_for_update().limit(
            int(0.02 * totalCells))
        for cell in energyCells:
            cell.cell_type = 'energy'

    db.session.commit()

    if redis_conn:
        redis_conn.set('gameid', str(gameId))
        info = InfoDb.query.get(0)
        redis_conn.set('gameInfo', json.dumps(info.ToDict(currTime)))
        db.session.commit()
