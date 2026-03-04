from os import environ

FLASK_SECRET_KEY = ""
USERDB_API_USER = ""
USERDB_API_KEY = ""
USERDB_API_CACHE_TIMEOUT_HOURS = 1
USERDB_API_URL = "https://userdb.hkfree.org/userdb/api/hlasys/get-spravce?typSpravce="
APP_BASE_URL = ""
SLACK_WEBHOOK_URL = ""
SLACK_WEBHOOK_URL_VV = SLACK_WEBHOOK_URL
SLACK_WEBHOOK_URL_PD = SLACK_WEBHOOK_URL
SLACK_WEBHOOK_URL_CS = SLACK_WEBHOOK_URL
# Users that can change state of a proposal
USERS_CHANGE_STATE = [656, 9000]

DEBUG = True

class HlasysConfig:
    OIDC_SCOPES = "phone openid email groupshkfree"
    OIDC_CLIENT_SECRETS = "client_secrets.json"
    OIDC_SERVER_METADATA_URL = "https://sso.hkfree.org/realms/hkftests/.well-known/openid-configuration"
    OIDC_OVERWRITE_REDIRECT_URI = "https://hlasovani-dev.hkfree.org/oidc_callback"
    
    HLASYS2_VERSION = "2.0.4-dev"
    HLASYS2_REF_NAME = environ.get('HLASYS2_REF_NAME', 'unknown_ref')
    HLASYS2_COMMIT_HASH = environ.get('HLASYS2_COMMIT_HASH', 'unknown_hash')
    
