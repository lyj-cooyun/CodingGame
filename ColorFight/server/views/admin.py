#!coding: utf8
from flask import request, Blueprint, redirect, render_template


bp = Blueprint("admin", __name__, url_prefix="/admin.html")


@bp.route('')
def Admin():
    if request.url.startswith('https://'):
        url = request.url.replace('https://', "http://", 1)
        return redirect(url, 301)
    return render_template('admin.html')