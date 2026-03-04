# HlaSys 2

Web-based voting system for [hkfree.org z.s.](https://hkfree.org) built with Flask and SQLite.

## Requirements

- Python 3.11+
- Poetry (for development)
- Docker (for production/staging)
- OpenID Connect provider (for production/staging)

## Development Setup

### 1. Clone and install dependencies

```bash
git clone https://code.darkne.dev/nextgenerationnetwork/hlasys2.git
cd hlasys2
poetry install
```

### 2. Configure

The app uses `hlasys2_app/config.py` for configuration (not committed to git).

```bash
# Create config from example
cp hlasys2_app/config.example.py hlasys2_app/config.py
```

Edit `config.py` with your settings. For local development:
- Set `HLASYS_ENV = "development"`
- Configure `DEV_USERS` for test user accounts
- OAuth is bypassed in development mode

### 3. Initialize database

```bash
poetry run flask init-db
```

### 4. Run

```bash
poetry run flask run
# or with waitress
poetry run waitress-serve --call 'hlasys2_app:create_app'
```

### Development Mode Features

- OAuth bypassed - no `client_secrets.json` needed
- Dev banner with user switcher at top of page
- Pre-configured test users from `DEV_USERS`

## Production / Staging Deployment

### 1. Prepare configuration files

```bash
# Config file
cp hlasys2_app/config.example.py config.py
# Edit config.py with production settings

# OAuth secrets
cp client_secrets.example.json client_secrets.json
# Edit with your OIDC provider credentials
```

### 2. Build and run

**Production:**
```bash
docker-compose -f docker-compose.prod.yaml build --build-arg HLASYS2_COMMIT_HASH=$(git log --pretty=format:"%h" -n 1)
docker-compose -f docker-compose.prod.yaml up -d
```

**Staging:**
```bash
docker-compose -f docker-compose.stage.yaml build --build-arg HLASYS2_COMMIT_HASH=$(git log --pretty=format:"%h" -n 1)
docker-compose -f docker-compose.stage.yaml up -d
```

### Environment-specific configuration

In `config.py`, set:
- Production: `HLASYS_ENV = "production"`
- Staging: `HLASYS_ENV = "staging"`

Both require valid OAuth configuration.

## Configuration Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `HLASYS_ENV` | Environment: `development`, `staging`, `production` | Yes |
| `FLASK_SECRET_KEY` | Secret key for session encryption | Yes |
| `USERDB_API_USER` | UserDB API username | Yes |
| `USERDB_API_KEY` | UserDB API key | Yes |
| `APP_BASE_URL` | Public URL of the application | Yes |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | No |
| `USERS_CHANGE_STATE` | User IDs allowed to change proposal state | No |
| `DEV_USERS` | Test users for development mode | Dev only |

### OAuth Configuration

Create `client_secrets.json`:
```json
{
    "web": {
        "client_id": "<your-client-id>",
        "client_secret": "<your-client-secret>",
        "auth_uri": "<auth-uri>",
        "token_uri": "<token-uri>",
        "issuer": "<issuer>"
    }
}
```

## Version Information

- Version is defined in `hlasys2_app/version.py`
- Commit hash is injected at Docker build time
- Footer displays: `v<version>-<commit-hash> (<environment>)`

## License

[GNU GPLv3](https://www.gnu.org/licenses/gpl-3.0.en.html)
