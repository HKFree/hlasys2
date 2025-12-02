FLASK_SECRET_KEY = "<secret>"
USERDB_API_USER = "<api-user>"
USERDB_API_KEY = "<api-key>"
USERDB_API_CACHE_TIMEOUT_HOURS = 1
USERDB_API_URL = "<hkf-userdb-url>"
APP_BASE_URL = "https://hlasovani-dev.hkfree.org"
SLACK_WEBHOOK_URL_VV = "<wenhook-url>"
SLACK_WEBHOOK_URL_PD = "<wenhook-url>"
SLACK_WEBHOOK_URL_CS = "<wenhook-url>"

# Users that can change state of a proposal
USERS_CHANGE_STATE = [656, 9000]

DEBUG = False

class HlasysConfig:
    OIDC_SCOPES = "phone openid email groupshkfree"
    OIDC_CLIENT_SECRETS = "client_secrets.json"
    OIDC_SERVER_METADATA_URL = "<oidc-metadata-url>"
    OIDC_OVERWRITE_REDIRECT_URI = "https://hlasovani-dev.hkfree.org/oidc_callback"
    APP_VERSION = "2.0.4-dev"