# coding=utf-8
import os
import base64


from flask import Flask
from flask_cors import CORS
from corelibs.config import server_config
from corelibs.store import db
from views import init_bp


def init_config(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = server_config.DATABASE_URL
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    app.config['JSON_SORT_KEYS'] = False
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = base64.urlsafe_b64encode(os.urandom(24))


def init_db(app):
    db.init_app(app)


def create_app():
    app = Flask(__name__, static_url_path='/static')
    init_config(app)
    init_db(app)
    init_bp(app)
    CORS(app)
    return app


app = create_app()
wsgi = app.wsgi_app


@app.cli.command("create_table")
def create_table():
    db.create_all(app=app)


if __name__ == "__main__":
    # debug
    app.config['DEBUG'] = True
    app.run("0.0.0.0", port=8888)
