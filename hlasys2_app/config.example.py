FLASK_SECRET_KEY = "<secretkey>"
USERDB_API_USER = "<apiusername>"
USERDB_API_KEY = "<apikey>"
USERDB_API_CACHE_TIMEOUT_HOURS = 1
USERDB_API_URL = "https://userdb.hkfree.org/userdb/api/hlasys/get-spravce?typSpravce="
DEBUG = False
# Users that can change state of a proposal
USERS_CHANGE_STATE = [122345, 9000, 111]

def config_app(app):
    app.config["OIDC_SCOPES"] = "phone openid email groupshkfree"
    app.config["OIDC_CLIENT_SECRETS"] = "client_secrets.json"
    app.config["OIDC_SERVER_METADATA_URL"] = "<metadata_url>"
    app.config["OIDC_OVERWRITE_REDIRECT_URI"] = "<redirect_uri>"