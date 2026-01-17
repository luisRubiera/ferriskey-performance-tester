# FerrisKey Performance Tester

Performance testing suite for [FerrisKey](https://github.com/ferriskey/ferriskey) and [Keycloak](https://www.keycloak.org/) using [k6](https://k6.io/).

## Features

- **Token Endpoint** - OAuth2 client credentials and password grants
- **JWKS Endpoint** - JSON Web Key Set retrieval
- **Userinfo Endpoint** - OpenID Connect userinfo
- **Mixed Workload** - Realistic traffic patterns
- **Multi-Provider** - Works with FerrisKey and Keycloak

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.10+

## Quick Start

### 1. Setup

```bash
git clone https://github.com/ferriskey/ferriskey-perf-tester.git
cd ferriskey-perf-tester

# Install dependencies
uv sync

# Create minimal config
cp .env.example .env
```

### 2. Configure `.env`

```bash
# IAM provider: "ferriskey" or "keycloak"
IAM_PROVIDER=keycloak

# Server URL
BASE_URL=http://localhost:8080

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

That's it! The seeder will auto-generate `CLIENT_ID` and retrieve `CLIENT_SECRET` from the server.

### 3. Seed Test Data

```bash
uv run python scripts/seed_test_data.py
```

This will:
1. Create a performance test realm
2. Create a test client (auto-generated ID)
3. Retrieve the client secret from the server
4. Create test users
5. Generate `.env.test` with all k6 configuration

### 4. Run Performance Tests

```bash
# Use the generated .env.test
set -a && source .env.test && set +a

# Run tests
k6 run k6/scenarios/token_client_credentials.js
k6 run k6/scenarios/token_password.js
k6 run k6/scenarios/jwks.js
k6 run k6/scenarios/userinfo.js
k6 run k6/scenarios/mixed_workload.js

# With custom VUs and duration
k6 run --env VUS=100 --env DURATION=5m k6/scenarios/mixed_workload.js
```

### 5. Cleanup (Optional)

```bash
uv run python scripts/cleanup_test_data.py          # FerrisKey
uv run python scripts/cleanup_test_data_keycloak.py # Keycloak
```

## Project Structure

```
ferriskey-perf-tester/
├── k6/
│   ├── scenarios/           # Test scenarios
│   │   ├── token_client_credentials.js
│   │   ├── token_password.js
│   │   ├── jwks.js
│   │   ├── userinfo.js
│   │   └── mixed_workload.js
│   └── lib/                 # Shared libraries
│       ├── config.js
│       ├── auth.js
│       └── data.js
├── scripts/
│   ├── seed_test_data.py    # Unified seeder (uses IAM_PROVIDER)
│   ├── cleanup_test_data.py
│   ├── cleanup_test_data_keycloak.py
│   └── lib/                 # Provider implementations
│       ├── base_provider.py
│       ├── ferriskey_provider.py
│       └── keycloak_provider.py
├── .env.example             # Minimal configuration template
├── .env.test                # Generated k6 configuration (after seeding)
└── README.md
```

## Configuration

### Seeder Configuration (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `IAM_PROVIDER` | `ferriskey` or `keycloak` | `ferriskey` |
| `BASE_URL` | Server URL | `localhost:3333` (FK) / `localhost:8080` (KC) |
| `ADMIN_USERNAME` | Admin username | `admin` |
| `ADMIN_PASSWORD` | Admin password | `admin` |
| `PERF_REALM` | Test realm name | `perf-realm` (FK) / `perf` (KC) |
| `USER_COUNT` | Number of test users | `50` |
| `USER_PASSWORD` | Test user password | `perf-password` |

### Generated k6 Configuration (`.env.test`)

After seeding, `.env.test` contains everything k6 needs:

```bash
BASE_URL=http://localhost:8080
REALM=perf
CLIENT_ID=perf-client-abc123    # Auto-generated
CLIENT_SECRET=xK9mLp2n...       # Retrieved from server
TEST_USERNAME=perf-user-001
TEST_PASSWORD=perf-password
VUS=50
DURATION=5m
```

## Test Scenarios

| Scenario | Description | p95 Threshold |
|----------|-------------|---------------|
| `token_client_credentials.js` | OAuth2 client credentials grant | < 100ms |
| `token_password.js` | OAuth2 password grant | < 150ms |
| `jwks.js` | JWKS endpoint | < 20ms |
| `userinfo.js` | OpenID Connect userinfo | < 50ms |
| `mixed_workload.js` | Weighted mix (40% CC, 20% PW, 30% UI, 10% JWKS) | varies |

## CI/CD Integration

```yaml
- name: Seed test data
  run: uv run python scripts/seed_test_data.py
  env:
    IAM_PROVIDER: keycloak
    BASE_URL: ${{ secrets.KEYCLOAK_URL }}
    ADMIN_USERNAME: ${{ secrets.ADMIN_USERNAME }}
    ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}

- name: Run performance tests
  run: |
    set -a && source .env.test && set +a
    k6 run --out json=results.json k6/scenarios/mixed_workload.js
```

## Troubleshooting

### "Failed to get admin token"

1. Check server is running at `BASE_URL`
2. Verify admin credentials
3. For Keycloak, ensure `ADMIN_REALM=master`

### "Connection refused"

Check the `BASE_URL` in your `.env` matches where your IAM server is running.

### k6 "undefined" errors

Make sure to source `.env.test` before running k6:
```bash
set -a && source .env.test && set +a && k6 run ...
```

## License

MIT License - see [LICENSE](LICENSE)
