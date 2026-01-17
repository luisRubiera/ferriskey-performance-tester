# CLAUDE.md - Project Intelligence

## Project Overview

**FerrisKey Performance Tester** is a comprehensive performance testing suite for benchmarking IAM (Identity & Access Management) systems. It primarily targets **FerrisKey** (a Rust-based IAM system) but also supports **Keycloak** (Java-based).

The suite uses **k6** for load testing and **Python with uv** for test data seeding/cleanup.

## Tech Stack

- **k6** - Load testing framework (scenarios written in JavaScript)
- **Python 3.10+** with **uv** package manager
- **requests** + **python-dotenv** for Python scripts
- **PostgreSQL 15** - Database backend for IAM systems
- **GitHub Actions** - CI/CD

## Project Structure

```
ferriskey-perf-tester/
├── k6/
│   ├── scenarios/           # Performance test scenarios
│   │   ├── token_client_credentials.js   # OAuth2 client credentials grant
│   │   ├── token_password.js             # OAuth2 password grant
│   │   ├── jwks.js                       # JWKS endpoint test
│   │   ├── userinfo.js                   # OpenID Connect userinfo
│   │   └── mixed_workload.js             # Realistic weighted traffic
│   └── lib/                 # Shared k6 libraries
│       ├── config.js        # Thresholds, scenarios, base config
│       ├── auth.js          # Authentication helpers
│       └── data.js          # Test data helpers (SharedArray)
├── scripts/                 # Python setup/teardown
│   ├── seed_test_data.py           # Unified seeding (uses IAM_PROVIDER)
│   ├── cleanup_test_data.py        # FerrisKey cleanup
│   ├── cleanup_test_data_keycloak.py
│   └── lib/                        # Shared Python library
│       ├── __init__.py
│       ├── config.py               # Configuration loading
│       ├── console.py              # Colored output helpers
│       ├── base_provider.py        # Abstract IAMProvider class
│       ├── ferriskey_provider.py   # FerrisKey implementation
│       └── keycloak_provider.py    # Keycloak implementation
├── data/                    # Test fixtures
│   ├── realm.json           # Realm configuration
│   ├── clients.json         # OAuth2 client definitions
│   └── users.csv            # User fixture data
├── .github/workflows/       # CI/CD
│   ├── perf-smoke.yml       # PR smoke tests (30s)
│   └── perf-nightly.yml     # Nightly comprehensive tests
├── results/                 # Test results (gitignored)
├── pyproject.toml           # Python project config
├── .env.example             # Environment template
└── README.md
```

## Key Commands

### Setup
```bash
uv sync                              # Install Python dependencies
cp .env.example .env                 # Create environment config (minimal config needed)
```

### Seed Test Data
```bash
# FerrisKey (default)
uv run python scripts/seed_test_data.py

# Keycloak (minimal .env: IAM_PROVIDER, BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
IAM_PROVIDER=keycloak uv run python scripts/seed_test_data.py

# Seeder auto-generates CLIENT_ID and retrieves CLIENT_SECRET from server
# Creates .env.test with all k6 configuration
```

### Run k6 Tests
```bash
# Use generated .env.test (contains CLIENT_ID, CLIENT_SECRET, etc.)
set -a && source .env.test && set +a

# Individual scenarios
k6 run k6/scenarios/token_client_credentials.js
k6 run k6/scenarios/token_password.js
k6 run k6/scenarios/jwks.js
k6 run k6/scenarios/userinfo.js
k6 run k6/scenarios/mixed_workload.js

# With custom VUs and duration
k6 run --env VUS=100 --env DURATION=5m k6/scenarios/mixed_workload.js
```

### Cleanup
```bash
uv run python scripts/cleanup_test_data.py        # FerrisKey
uv run python scripts/cleanup_test_data_keycloak.py  # Keycloak
```

## Environment Variables

### IAM Provider
| Variable | Description | Default |
|----------|-------------|---------|
| `IAM_PROVIDER` | IAM backend: `ferriskey` or `keycloak` | `ferriskey` |

### Server Connection
| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | IAM server URL | `http://localhost:3333` (FK) / `http://localhost:8080` (KC) |
| `REQUEST_TIMEOUT` | HTTP request timeout in seconds | `30` |

### Admin Authentication
| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_REALM` | Realm for admin authentication | `perf-realm` (FK) / `master` (KC) |
| `ADMIN_USERNAME` | Admin username | `admin` |
| `ADMIN_PASSWORD` | Admin password | `admin` |
| `KEYCLOAK_AUTH_CLIENT` | Keycloak admin auth client (KC only) | `admin-cli` |

### Realm & Client
| Variable | Description | Default |
|----------|-------------|---------|
| `PERF_REALM` | Performance test realm | `perf-realm` (FK) / `perf` (KC) |
| `CLIENT_ID` | OAuth2 client ID (optional, auto-generated) | `perf-client-{random}` |
| `CLIENT_SECRET` | OAuth2 client secret (optional, retrieved from server) | (server-generated) |

### User Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `USER_COUNT` | Number of test users to create | `50` |
| `USER_PASSWORD` | Password for all test users | `perf-password` |
| `USER_PREFIX` | Username prefix (e.g., `perf-user-`) | `perf-user-` |
| `USER_FIRSTNAME` | First name for test users | `Perf` |
| `USER_LASTNAME_PREFIX` | Last name prefix (e.g., `User001`) | `User` |
| `USER_EMAIL_PREFIX` | Email prefix (e.g., `perf001@...`) | `perf` |
| `USER_EMAIL_DOMAIN` | Email domain | `test.local` |

### k6 Test Parameters
| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_USERNAME` | Primary test username | `perf-user-001` |
| `TEST_PASSWORD` | Primary test password | `perf-password` |
| `VUS` | k6 virtual users | `50` |
| `DURATION` | k6 test duration | `5m` |

## SLO Thresholds

| Endpoint | p95 | p99 | Error Rate |
|----------|-----|-----|------------|
| Token | < 100ms | < 250ms | < 1% |
| JWKS | < 20ms | < 50ms | < 0.1% |
| Userinfo | < 50ms | < 100ms | < 1% |

## k6 Scenario Profiles

- **smoke**: 5 VUs, 30s - Quick validation
- **load**: 50 VUs, 5m - Standard load test
- **stress**: Ramp 50→200 VUs, 16m - Find breaking point
- **soak**: 30 VUs, 30m - Memory leak detection

## Test Data Patterns

- Test users: `{USER_PREFIX}001` through `{USER_PREFIX}{USER_COUNT}` (default: `perf-user-001`)
- User emails: `{USER_EMAIL_PREFIX}001@{USER_EMAIL_DOMAIN}` (default: `perf001@test.local`)
- Confidential client: `perf-client` (service account enabled)
- Public client: `perf-public-client`
- Test realm: configurable via `PERF_REALM`

## API Differences: FerrisKey vs Keycloak

| Operation | FerrisKey | Keycloak |
|-----------|-----------|----------|
| Token endpoint | `/realms/{realm}/protocol/openid-connect/token` | Same |
| Admin API base | `/realms/` | `/admin/realms/` |
| Default port | 3333 | 8080 |
| Auth client | Service account | `admin-cli` |

## CI/CD Workflows

### perf-smoke.yml (On PR)
- Quick 30s validation tests
- Runs: token, JWKS, mixed workload
- Artifacts: 7-day retention

### perf-nightly.yml (2 AM UTC Daily)
- Comprehensive 5-10m tests per scenario
- Memory leak detection (50% growth threshold)
- 200 test users
- Artifacts: 30-day retention

## Code Patterns

### k6 Custom Metrics
Each scenario defines custom Trend, Rate, and Counter metrics for per-endpoint monitoring:
```javascript
const tokenDuration = new Trend('token_client_credentials_duration');
const tokenErrors = new Rate('token_client_credentials_errors');
```

### Token Caching (userinfo.js)
Tokens are cached per VU with automatic refresh before expiry.

### User Pool Rotation (token_password.js)
Uses SharedArray with random user selection for realistic auth patterns.

### Think Time
Simulates realistic user behavior with randomized delays between requests.

### IAM Provider Architecture (Python)
The seeding script uses a provider pattern for multi-backend support:
```
IAMProvider (abstract base class)
├── FerrisKeyProvider  # FerrisKey-specific API calls
└── KeycloakProvider   # Keycloak-specific API calls
```
To add a new IAM backend:
1. Create `scripts/lib/newprovider_provider.py` implementing `IAMProvider`
2. Register it in `scripts/seed_test_data.py` `get_provider()` function

## Adding New Tests

1. Create scenario in `k6/scenarios/`
2. Import helpers from `k6/lib/`
3. Define custom metrics and thresholds
4. Add to mixed_workload.js if applicable
5. Update CI workflows if needed

## Common Issues

- **Token errors**: Check CLIENT_SECRET in .env matches seeded client
- **Connection refused**: Ensure IAM server is running on correct port
- **User not found**: Run seed script before tests
- **Threshold failures**: May indicate performance regression or server issues
