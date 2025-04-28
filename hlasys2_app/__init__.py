import os

from flask import Flask, redirect, session
from flask_oidc import OpenIDConnect
import locale

from .util import HkfreeRole

locale.setlocale(locale.LC_TIME, "cs_CZ.UTF-8")

def create_app():
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='deasd12312312r21rv',
        DATABASE=os.path.join(app.instance_path, 'hlasys2.sqlite'),
    )
    app.config["OIDC_SCOPES"] = "phone openid email groupshkfree"
    app.config["OIDC_CLIENT_SECRETS"] = "client_secrets.json"
    app.config["OIDC_SERVER_METADATA_URL"] = "https://sso.hkfree.org/realms/hkfree/.well-known/openid-configuration"
    app.config["OIDC_OVERWRITE_REDIRECT_URI"] = "https://new.hlasovani.hkfree.org/oidc_callback"
    oidc = OpenIDConnect(app)

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

    @app.before_request
    def check_auth():
        if not session.get('user_id'):
            session['user_id'] = 9000
            session['user_hkf_role'] = HkfreeRole.SO

    @app.route("/")
    @oidc.require_login
    def hello():
        print(session['oidc_auth_profile'])
        return "hiii!"
    
    @app.route("/whoami")
    def what():
        return str(session.get('oidc_auth_profile') if oidc.user_loggedin else oidc.user_loggedin)

    @app.route("/tmp/<int:id>")
    def tmp(id):
        print(f"Registering {id}")
        session['user_id'] = id
        print(oidc.user_loggedin)
        return redirect('/overview/vv')

    @app.route("/login/<int:login_id>")
    def login_tmp(login_id):
        tmp_auth = {
            9025: HkfreeRole.VV,
            9026: HkfreeRole.SO,
            9000: HkfreeRole.SO,
            9001: HkfreeRole.MEMBER
        }

        session['user_id'] = login_id
        session['user_hkf_role'] = tmp_auth.get(login_id, HkfreeRole.MEMBER)
        print(f"Logged in as {login_id}")

        return redirect("/overview/vv")

    @app.route("/s")
    def session_tmp():
        print(session)
        return redirect("/overview/vv")


    return app
