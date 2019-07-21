#!coding:utf8
import time
import datetime
from flask import jsonify
from corelibs.store import db


def get_resp(t):
    resp = jsonify(t[1])
    resp.status_code = t[0]
    return resp


def GetCurrDbTime():
    res = db.select([db.func.current_timestamp(type_=db.TIMESTAMP, bind=db.engine)]).execute()
    for row in res:
        return row[0]


globalDbTime = 0
globalServerTime = 0


def GetCurrDbTimeSecs(dbtime=None):
    # 国际化操作，这里似乎其实直接返回timestamp就好了
    return time.time()
    # global globalDbTime
    # global globalServerTime
    # currTime = time.time()
    # if currTime - globalServerTime < 5:
    #     return currTime - globalServerTime + globalDbTime
    # if dbtime == None:
    #     dbtime = GetCurrDbTime()
    # globalDbTime = (dbtime - datetime.datetime(1970, 1, 1, tzinfo=dbtime.tzinfo)).total_seconds()
    # globalServerTime = time.time()
    # return globalDbTime


def GetDateTimeFromSecs(secs):
    return datetime.datetime.utcfromtimestamp(secs)
