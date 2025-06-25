import os

from flask import Flask, redirect, session, render_template, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_oidc import OpenIDConnect
import locale

from .util import HkfreeRole
from .config import config_app, FLASK_SECRET_KEY

locale.setlocale(locale.LC_TIME, "cs_CZ.UTF-8")
oidc = OpenIDConnect()


def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=FLASK_SECRET_KEY,
        DATABASE=os.path.join(app.instance_path, 'hlasys2.sqlite'),
    )

    config_app(app)
    oidc.init_app(app)
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    from . import db
    db.init_app(app=app)

    from . import proposals
    app.register_blueprint(proposals.bp)

    from . import users
    app.register_blueprint(users.bp)

    from . import votes
    app.register_blueprint(votes.bp)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    @oidc.require_login
    def hello():
        print(session['oidc_auth_profile'])
        return redirect('/overview/pd')

    @app.route("/whoami")
    @oidc.require_login
    def what():
        profile = session.get('oidc_auth_profile')
        return f"{profile} <br> {profile.get('groups')}"
    
    @app.route("/flash")
    def flashes():
        flash("Hlas změněn 🎉", "success")
        flash("tak tohle ne!!!!", "danger")
        flash("bachaaaaaaa", "warning")
        return render_template('base.html')

    @app.route("/s")
    def session_tmp():
        print(session)
        return redirect("/overview/vv")

    return app
