from functools import wraps
from flask import session, redirect, url_for, request
from hlasys2_app.config import HLASYS_ENV, DEV_USERS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if HLASYS_ENV == "development":
            if "oidc_auth_profile" not in session:
                default_user = DEV_USERS[0]
                session["oidc_auth_profile"] = {
                    "preferred_username": str(default_user["id"]),
                    "family_name": default_user["family_name"],
                }
            return f(*args, **kwargs)
        else:
            from hlasys2_app import oidc
            return oidc.require_login(f)(*args, **kwargs)
    return decorated_function
