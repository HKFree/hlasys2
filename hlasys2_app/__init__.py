import os

from flask import Flask, redirect, session
import locale

locale.setlocale(locale.LC_TIME, "cs_CZ.UTF-8")

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'hlasys2.sqlite'),
    )

    from . import db
    db.init_app(app=app)

    from . import auth
    app.wsgi_app = auth.middleware(app.wsgi_app)

    from . import proposals
    app.register_blueprint(proposals.bp)

    from . import users
    app.register_blueprint(users.bp)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    def hello():
        return redirect('/overview/vv')

    @app.route("/tmp/<int:id>")
    def tmp(id):
        print(f"Registering {id}")
        session['id'] = id
        return redirect('/overview/vv')

    return app