#!coding: utf8
import functools
import flask
from flask import request
from utils import get_resp
from models.info import InfoDb


def require(*required_args, **kw_req_args):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            data = request.get_json()
            if data is None:
                resp = flask.jsonify(msg="No json!")
                resp.status_code = 400
                return resp
            for arg in required_args:
                if arg not in data:
                    resp = flask.jsonify(code=400, msg="wrong args! need "+arg)
                    resp.status_code = 400
                    return resp

            if kw_req_args is not None:
                if "action" in kw_req_args:
                    if kw_req_args['action'] is True:
                        info = InfoDb.query.get(0)
                        if info.end_time != 0 and GetCurrDbTimeSecs() > info.end_time:
                            return get_resp((200, {"err_code":4, "err_msg":"Game is ended"}))

                    width, height = GetGameSize()
                    cellx = data['cellx']
                    celly = data['celly']
                    if width == None:
                        return get_resp((400, {"msg":"no valid game"}))
                    if (cellx < 0 or cellx >= width or
                            celly < 0 or celly >= height):
                        return get_resp((200, {"err_code":1, "err_msg":"Invalid cell position"}))

                if "protocol" in kw_req_args:
                    if "protocol" not in data:
                        return get_resp((400, {"msg":"Need protocol!"}))
                    if data['protocol'] < kw_req_args['protocol']:
                        return get_resp((400, {"msg":"Protocol version too low. If you are using ColorFightAI, please update(git pull) in your directory!"}))
            return func(*args, **kw)
        return wrapper
    return decorator