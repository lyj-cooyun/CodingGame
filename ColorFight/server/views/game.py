#!coding: utf8
import random
import json
import base64
import os

from flask import Blueprint, request

from corelibs.decoreator import require
from corelibs.config import server_config, game_config, energy_shop_config, gold_shop_config
from corelibs.store import redis_conn, db
from models.info import InfoDb
from models.cell import CellDb
from models.user import UserDb
from services.game import ClearGame, UpdateGame, GetGameSize
from utils import get_resp, GetCurrDbTimeSecs, GetDateTimeFromSecs, GetCurrDbTime

bp = Blueprint("game", __name__, url_prefix="")


@bp.route('/startgame', methods=['POST'])
@require('admin_password', 'last_time', 'ai_join_time')
def StartGame():
    data = request.get_json()
    if data['admin_password'] != server_config.ADMIN_PASSWORD:
        return get_resp((200, {"msg": "Fail"}))
    softRestart = False
    if "soft" in data and data["soft"] is True:
        softRestart = True
    if "ai_only" in data and data["ai_only"] is True:
        aiOnly = True
    else:
        aiOnly = False

    width = 30
    height = 30

    globalGameWidth = width
    globalGameHeight = height

    currTime = GetCurrDbTimeSecs()
    if data['last_time'] != 0:
        endTime = currTime + data['last_time']
    else:
        endTime = 0
    if data['ai_join_time'] != 0:
        joinEndTime = currTime + data['ai_join_time']
    else:
        joinEndTime = 0

    plan_start_time = 0
    if 'plan_start_time' in data and data['plan_start_time'] != 0:
        plan_start_time = data['plan_start_time']
        if endTime != 0:
            endTime += plan_start_time
        if joinEndTime != 0:
            joinEndTime += plan_start_time
        plan_start_time += currTime
    gameId = int(random.getrandbits(30))

    # dirty hack here, set end_time = 1 during initialization so Attack() and
    # Join() will not work while initialization
    if plan_start_time == 0:
        infoId = 0
        i = InfoDb.query.with_for_update().get(infoId)
    else:
        if redis_conn:
            redis_conn.set("planStartTime", plan_start_time)
        infoId = 1
        i = InfoDb.query.with_for_update().get(infoId)
    if i == None:
        i = InfoDb(id=infoId, width=width, height=height, max_id=width * height, end_time=endTime,
                   join_end_time=joinEndTime, ai_only=aiOnly, last_update=currTime, game_id=gameId,
                   plan_start_time=plan_start_time)
        db.session.add(i)
    else:
        i.width = width
        i.height = height
        i.max_id = width * height
        i.end_time = endTime
        i.join_end_time = joinEndTime
        i.ai_only = aiOnly
        i.last_update = currTime
        i.game_id = gameId
        i.plan_start_time = plan_start_time

    if redis_conn:
        redis_conn.set("lastUpdate", 0)

    if plan_start_time == 0:
        ClearGame(currTime, softRestart, (width, height), gameId)
    else:
        i = InfoDb.query.with_for_update().get(0)
        i.plan_start_time = plan_start_time
        db.session.commit()

    return get_resp((200, {"msg": "Success"}))


@bp.route('/getgameinfo', methods=['POST'])
def GetGameInfo():
    currTime = GetCurrDbTimeSecs()
    data = request.get_json()

    timeAfter = 0
    if data and 'timeAfter' in data:
        timeAfter = data['timeAfter']
    else:
        print('Info! Get a full cell request.')

    useSimpleDict = False

    timeDiff = 0

    retInfo = {}

    # Here we try to use redis to get a better performance
    if redis_conn:
        pipe = redis_conn.pipeline()
        lastUpdate, gameInfoStr, plan_start_time = pipe.get("lastUpdate").get("gameInfo").get("planStartTime").execute()
        if lastUpdate is None:
            return get_resp((400, {"msg": "No game established"}))

        retInfo['info'] = json.loads(gameInfoStr)
        retInfo['info']['time'] = currTime
        retInfo['info']['plan_start_time'] = plan_start_time
        if lastUpdate is not None and currTime - float(lastUpdate) < server_config.gameRefreshInterval:
            refreshGame = False
        else:
            pipe = redis_conn.pipeline()
            if plan_start_time is not None and float(plan_start_time) != 0 and float(plan_start_time) < currTime:
                info = InfoDb.query.with_for_update().get(0)
                infoNext = InfoDb.query.get(1)
                info.Copy(infoNext)
                ClearGame(currTime, True, (info.width, info.height), info.game_id)
                pipe.set("planStartTime", 0)

            timeDiff = currTime - float(lastUpdate)
            pipe.set("lastUpdate", currTime)
            pipe.execute()
            refreshGame = True
            db.session.commit()
    else:
        info = InfoDb.query.with_for_update().get(0)
        if info is None:
            return get_resp((400, {"msg": "No game established"}))
        if currTime - info.last_update > server_config.gameRefreshInterval:
            timeDiff = currTime - info.last_update
            info.last_update = currTime
            refreshGame = True
        else:
            refreshGame = False

        if info.plan_start_time != 0 and info.plan_start_time < currTime:
            infoNext = InfoDb.query.get(1)
            info.Copy(infoNext)
            ClearGame(currTime, True, (info.width, info.height), info.game_id)

        retInfo['info'] = {'width': info.width, 'height': info.height, 'time': currTime, 'end_time': info.end_time,
                           'join_end_time': info.join_end_time, 'game_id': info.game_id,
                           'game_version': server_config.GAME_VERSION, 'plan_start_time': info.plan_start_time}

        db.session.commit()

    if refreshGame:
        userInfo = UpdateGame(currTime, timeDiff)
    else:
        users = UserDb.query.all()
        userInfo = []
        for user in users:
            userInfo.append(user.ToDict(useSimpleDict))
        db.session.commit()

    retInfo['users'] = userInfo

    retCells = []

    # We give a 0.5 sec buffer so it will have a higher chance to pick up
    # all the changes even with some delay
    changedCells = CellDb.query.filter(CellDb.timestamp >= GetDateTimeFromSecs(timeAfter - 0.5)).order_by(
        CellDb.id).all()
    for c in changedCells:
        retCells.append(c.ToDict(currTime))

    retInfo['cells'] = retCells

    resp = get_resp((200, retInfo))

    return resp


@bp.route('/joingame', methods=['POST'])
@require('name')
def JoinGame():
    info = InfoDb.query.get(0)
    if info.end_time != 0 and GetCurrDbTimeSecs() > info.end_time:
        return get_resp((200, {'err_code': 4, "err_msg": "Game is ended"}))

    if info.join_end_time != 0 and GetCurrDbTimeSecs() > info.join_end_time:
        return get_resp((200, {'err_code': 4, "err_msg": "Join time is ended"}))

    data = request.get_json()

    if server_config.ROOM_PASSWORD is not None:
        if 'password' not in data or data['password'] != server_config.ROOM_PASSWORD:
            return get_resp((403, {'err_code': 11, "err_msg": "You need password to enter the room"}))

    users = UserDb.query.order_by(UserDb.id).with_for_update().all()
    availableId = 1
    for u in users:
        if u.id != availableId:
            break
        availableId += 1

    token = base64.urlsafe_b64encode(os.urandom(24))
    newUser = UserDb(id=availableId, name=data['name'], token=token, cells=1, bases=1, energy_cells=0, gold_cells=0,
                     dirty=False, energy=0, gold=30, dead_time=0)
    db.session.add(newUser)
    db.session.commit()
    cell = CellDb.query.filter_by(is_taking=False, owner=0).order_by(db.func.random()).with_for_update().limit(
        1).first()
    if cell is None:
        cell = CellDb.query.filter_by(is_taking=False).order_by(db.func.random()).with_for_update().limit(1).first()

    if cell is not None:
        cell.Init(availableId, GetCurrDbTimeSecs())
        db.session.commit()
        return get_resp((200, {'token': token, 'uid': availableId}))
    else:
        db.session.commit()
        return get_resp((200, {'err_code': 10, 'err_msg': 'No cell available to start'}))


@bp.route('/attack', methods=['POST'])
@require('cellx', 'celly', 'token', action=True)
def Attack():
    data = request.get_json()

    cellx = data['cellx']
    celly = data['celly']
    width, height = GetGameSize()

    if not (0 <= cellx < width and 0 <= celly < height):
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell position"}))

    currTime = GetCurrDbTimeSecs()

    u = UserDb.query.with_for_update().filter_by(token=data['token']).first()
    if u == None:
        db.session.commit()
        return get_resp((200, {"err_code": 21, "err_msg": "Invalid player"}))
    if u.cd_time > currTime:
        db.session.commit()
        return get_resp((200, {"err_code": 3, "err_msg": "You are in CD time!"}))

    if 'boost' in data and data['boost'] == True:
        boost = True
    else:
        boost = False

    # Check whether it's adjacent to an occupied cell
    # Query is really expensive, we try to do only one query to finish this
    globalGameWidth, globalGameHeight = GetGameSize()
    adjCells = 0
    adjIds = []
    for d in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        xx = cellx + d[0]
        yy = celly + d[1]
        if 0 <= xx < globalGameWidth and 0 <= yy < globalGameHeight:
            adjIds.append(xx + yy * globalGameWidth)

    adjCells = CellDb.query.filter(CellDb.id.in_(adjIds), CellDb.owner == u.id).count()

    c = CellDb.query.with_for_update().get(cellx + celly * width)
    if c == None:
        db.session.commit()
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell"}))
    success, err_code, msg = c.Attack(u, currTime, boost, adjCells)
    # This commit is important because cell.Attack() will not commit
    # At this point, c and user should both be locked
    db.session.commit()
    if success:
        return get_resp((200, {"err_code": 0}))
    else:
        return get_resp((200, {"err_code": err_code, "err_msg": msg}))


@bp.route('/buildbase', methods=['POST'])
@require('cellx', 'celly', 'token', action=True)
def BuildBase():
    if not game_config.BASE_ENABLE:
        return get_resp((200, {"err_code": 0}))
    data = request.get_json()
    currTime = GetCurrDbTimeSecs()
    u = UserDb.query.with_for_update().filter_by(token=data['token']).first()
    if u == None:
        db.session.commit()
        return get_resp((200, {"err_code": 21, "err_msg": "Invalid player"}))

    if u.gold < gold_shop_config.BASE:
        return get_resp((200, {"err_code": 5, "err_msg": "Not enough gold!"}))

    if u.build_cd_time > currTime:
        return get_resp((200, {"err_code": 7, "err_msg": "You are in building cd"}))

    baseNum = db.session.query(db.func.count(CellDb.id)).filter(CellDb.owner == u.id).filter(
        CellDb.build_type == "base").scalar()

    if baseNum >= 3:
        return get_resp((200, {"err_code": 8, "err_msg": "You have reached the base number limit"}))

    cellx = data['cellx']
    celly = data['celly']
    c = CellDb.query.with_for_update().filter_by(x=cellx, y=celly, owner=u.id).first()
    if c == None:
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell"}))
    success, err_code, msg = c.BuildBase(u, currTime)
    # user and cell is both locked here, clear the lock
    db.session.commit()
    if success:
        return get_resp((200, {"err_code": 0}))
    else:
        return get_resp((200, {"err_code": err_code, "err_msg": msg}))


@bp.route('/blast', methods=['POST'])
@require('cellx', 'celly', 'token', 'direction', action=True)
def Blast():
    if not game_config.BLAST_ENABLE:
        return get_resp((200, {"err_code": 0}))
    data = request.get_json()
    u = UserDb.query.filter_by(token=data['token']).first()
    if u == None:
        db.session.commit()
        return get_resp((200, {"err_code": 21, "err_msg": "Invalid player"}))
    cellx = data['cellx']
    celly = data['celly']
    direction = data['direction']
    uid = u.id
    c = CellDb.query.with_for_update().filter_by(x=cellx, y=celly, owner=uid).first()
    if c == None:
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell"}))
    success, err_code, msg = c.Blast(uid, direction, GetCurrDbTimeSecs())
    if success:
        return get_resp((200, {"err_code": 0}))
    else:
        db.session.commit()
        return get_resp((200, {"err_code": err_code, "err_msg": msg}))


@bp.route('/multiattack', methods=['POST'])
@require('cellx', 'celly', 'token', action=True)
def MultiAttack():
    if not game_config.MULTIATTACK_ENABLE:
        return get_resp((200, {"err_code": 0}))
    data = request.get_json()

    cellx = data['cellx']
    celly = data['celly']
    width, height = GetGameSize()

    if not (0 <= cellx < width and 0 <= celly < height):
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell position"}))

    currTime = GetCurrDbTimeSecs()

    u = UserDb.query.with_for_update().filter_by(token=data['token']).first()
    if u == None:
        db.session.commit()
        return get_resp((200, {"err_code": 21, "err_msg": "Invalid player"}))
    if u.cd_time > currTime:
        db.session.commit()
        return get_resp((200, {"err_code": 3, "err_msg": "You are in CD time!"}))
    if u.gold < gold_shop_config.MULTIATTACK:
        return get_resp((200, {"err_code": 5, "err_msg": "Not enough gold!"}))

    # Check whether it's adjacent to an occupied cell
    # Query is really expensive, we try to do only one query to finish this
    adjCells = []
    adjIds = []
    globalGameWidth, globalGameHeight = GetGameSize()
    for d in [(-2, 0), (-1, -1), (0, -2), (1, -1), (2, 0), (1, 1), (0, 2), (-1, 1), (0, 0)]:
        xx = cellx + d[0]
        yy = celly + d[1]
        if 0 <= xx < globalGameWidth and 0 <= yy < globalGameHeight:
            adjIds.append(xx + yy * globalGameWidth)
    adjCells = CellDb.query.filter(CellDb.id.in_(adjIds)).filter_by(owner=u.id).all()

    atkCells = []
    atkIds = []
    adjCellDict = {}
    for d in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        xx = cellx + d[0]
        yy = celly + d[1]

        if 0 <= xx < globalGameWidth and 0 <= yy < globalGameHeight:
            adjCellCount = 0
            for c in adjCells:
                if abs(c.x - xx) + abs(c.y - yy) == 1:
                    adjCellCount += 1
            atkId = xx + yy * globalGameWidth
            atkIds.append(atkId)
            adjCellDict[atkId] = adjCellCount

    atkCells = CellDb.query.with_for_update().filter(CellDb.id.in_(atkIds)).all()

    if not atkCells:
        db.session.commit()
        return get_resp((200, {"err_code": 1, "err_msg": "Invalid cell"}))

    for c in atkCells:
        c.Attack(u, currTime, False, adjCellDict[c.id])
    u.gold -= gold_shop_config.MULTIATTACK
    # This commit is important because cell.Attack() will not commit
    # At this point, c and user should both be locked
    db.session.commit()
    return get_resp((200, {"err_code": 0}))


@bp.route('/checktoken', methods=['POST'])
@require('token')
def CheckToken():
    data = request.get_json()
    u = UserDb.query.filter_by(token=data['token']).first()
    if u != None:
        return get_resp((200, {"name": u.name, "uid": u.id}))
    return get_resp((400, {"msg": "Fail"}))


@bp.route('/addai', methods=['POST'])
@require('name')
def AddAi():
    data = request.get_json()
    name = data['name']
    if redis_conn:
        availableAI = redis_conn.lrange("availableAI", 0, -1)
        if name in availableAI:
            redis_conn.lpush("aiList", name)
            return get_resp((200, {"msg": "Success"}))
    return get_resp((200, {"msg": "Fail"}))


@bp.route('/getailist', methods=['POST'])
def GetAiList():
    ret = []
    if redis_conn:
        availableAI = redis_conn.lrange("availableAI", 0, -1)
        ret = [name for name in availableAI]
    return get_resp((200, {"aiList": ret}))
