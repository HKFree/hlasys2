HLASYS_ENV = "production"

FLASK_SECRET_KEY = "<your-secret-key>"
USERDB_API_USER = "<api-user>"
USERDB_API_KEY = "<api-key>"
USERDB_API_CACHE_TIMEOUT_HOURS = 1
USERDB_API_URL = "https://userdb.hkfree.org/userdb/api/hlasys/get-spravce?typSpravce="
APP_BASE_URL = "https://hlasovani.hkfree.org"

SLACK_WEBHOOK_URL = "<slack-webhook-url>"
SLACK_WEBHOOK_URL_VV = SLACK_WEBHOOK_URL
SLACK_WEBHOOK_URL_PD = SLACK_WEBHOOK_URL
SLACK_WEBHOOK_URL_CS = SLACK_WEBHOOK_URL

USERS_CHANGE_STATE = [9000]

# Proposal types whose deciders may delete an undecided proposal, on top of its
# author. 0 = VV, 1 = SO, 2 = PD, 3 = CS, 4 = CD. CS is left out on purpose - it
# has ~116 deciders. Optional; defaults to [0, 1, 2] when absent.
DECIDER_DELETE_TYPES = [0, 1, 2]

DEBUG = False

DEV_USERS = []


class HlasysConfig:
    OIDC_SCOPES = "phone openid email groupshkfree"
    OIDC_CLIENT_SECRETS = "client_secrets.json"
    OIDC_SERVER_METADATA_URL = "https://sso.hkfree.org/realms/hkfree/.well-known/openid-configuration"
    OIDC_OVERWRITE_REDIRECT_URI = "https://hlasovani.hkfree.org/oidc_callback"

    from .version import HLASYS2_VERSION, HLASYS2_COMMIT_HASH
