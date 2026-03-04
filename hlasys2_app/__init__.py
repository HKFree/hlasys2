import os

from flask import Flask, redirect, session, render_template, flash, request
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_oidc import OpenIDConnect
import locale

from .util import HkfreeRole
from .config import HlasysConfig, FLASK_SECRET_KEY, HLASYS_ENV, DEV_USERS
from .decorators import login_required
from .version import HLASYS2_VERSION, HLASYS2_COMMIT_HASH

locale.setlocale(locale.LC_TIME, "cs_CZ.UTF-8")
oidc = OpenIDConnect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=FLASK_SECRET_KEY,
        DATABASE=os.path.join(app.instance_path, "hlas.sqlite"),
    )
    app.config.from_object(HlasysConfig)

    if HLASYS_ENV != "development":
        oidc.init_app(app)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    from . import db

    db.init_app(app=app)

    from . import proposals

    app.register_blueprint(proposals.bp)

    from . import users

    app.register_blueprint(users.bp)

    from . import votes

    app.register_blueprint(votes.bp)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route("/")
    @login_required
    def hello():
        print(session["oidc_auth_profile"])
        return redirect("/overview/pd")

    @app.route("/whoami")
    @login_required
    def what():
        profile = session.get("oidc_auth_profile")
        return f"{profile} <br> {profile.get('groups')}"

    @app.route("/flash")
    def flashes():
        flash("Hlas změněn 🎉", "success")
        flash("tak tohle ne!!!!", "danger")
        flash("bachaaaaaaa", "warning")
        return render_template("base.html")

    @app.route("/s")
    @login_required
    def session_tmp():
        print(session)
        return redirect("/overview/vv")

    if HLASYS_ENV == "development":
        @app.route("/dev-switch-user/<int:user_id>")
        def dev_switch_user(user_id):
            user = next((u for u in DEV_USERS if u["id"] == user_id), None)
            if user:
                session["oidc_auth_profile"] = {
                    "given_name": str(user["id"]),
                    "family_name": user["family_name"],
                }
                flash(f"Přepnuto na uživatele: {user['family_name']}", "success")
            else:
                flash("Uživatel nenalezen", "danger")
            return redirect(request.referrer or "/")

    @app.context_processor
    def inject_version():
        commit_hash = HLASYS2_COMMIT_HASH[:7] if HLASYS2_COMMIT_HASH != "unknown" else "unknown"
        return dict(
            hlasys2_version=HLASYS2_VERSION,
            hlasys2_build_str=f"v{HLASYS2_VERSION}-{commit_hash} ({HLASYS_ENV})",
            hlasys_env=HLASYS_ENV,
            dev_users=DEV_USERS,
        )

    return app
