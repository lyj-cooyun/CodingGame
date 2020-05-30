#!coding: utf8
from flask import Blueprint, request, redirect, render_template
from models.info import InfoDb

bp = Blueprint("index", __name__, url_prefix="")


@bp.route('/')
@bp.route('/index')
@bp.route('/index.html')
def Index():
    if request.url.startswith('https://'):
        url = request.url.replace('https://', "http://", 1)
        return redirect(url, 301)
    i = InfoDb.query.get(0)
    if i is not None:
        aiOnly = i.ai_only
    else:
        aiOnly = False
    return render_template('index.html', aiOnly=aiOnly)
