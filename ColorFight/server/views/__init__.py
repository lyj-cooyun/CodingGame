#!coding: utf8

from admin import bp as admin_bp
from index import bp as index_bp
from game import bp as game_bp


def init_bp(app):
    app.register_blueprint(admin_bp)
    app.register_blueprint(index_bp)
    app.register_blueprint(game_bp)
