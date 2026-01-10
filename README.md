# FerrisKey Performance Tester

Performance testing suite for [FerrisKey](https://github.com/ferriskey/ferriskey) - a modern, open-source Identity & Access Management system built in Rust.

## Overview

This project provides comprehensive performance tests for FerrisKey using [k6](https://k6.io/), covering:

- **Token Endpoint** - OAuth2 client credentials and password grants
- **JWKS Endpoint** - JSON Web Key Set retrieval
- **Userinfo Endpoint** - OpenID Connect userinfo
- **Mixed Workload** - Realistic traffic patterns

## Project Structure

```
ferriskey-perf-tester/
├── k6/
│   ├── scenarios/                    # Test scenarios
│   │   ├── token_client_credentials.js
│   │   ├── token_password.js
│   │   ├── jwks.js
│   │   ├── userinfo.js
│   │   └── mixed_workload.js
│   └── lib/                          # Shared libraries
│       ├── config.js                 # Configuration & thresholds
│       ├── auth.js                   # Authentication helpers
│       └── data.js                   # Test data helpers
├── scripts/
│   ├── seed_test_data.py            # Seed test data (Python)
│   └── cleanup_test_data.py         # Clean up test data (Python)
├── data/
│   ├── realm.json                   # Realm fixture
│   ├── clients.json                 # Client fixtures
│   └── users.csv                    # User fixtures
├── results/                         # Test results (gitignored)
├── .github/workflows/
│   ├── perf-smoke.yml              # PR smoke tests
│   └── perf-nightly.yml            # Nightly comprehensive tests
├── .env.example                     # Environment configuration template
├── pyproject.toml                   # Python project configuration (uv)
└── README.md
```

## Prerequisites

- [k6](https://k6.io/docs/getting-started/installation/) installed
- [uv](https://docs.astral.sh/uv/) installed (Python package manager)
- Python 3.10+ installed
- FerrisKey running locally or accessible via network

### Installing uv

[uv](https://docs.astral.sh/uv/) is an extremely fast Python package manager written in Rust.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS with Homebrew
brew install uv

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installing k6

```bash
# macOS
brew install k6

# Debian/Ubuntu
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update && sudo apt-get install k6

# Windows
choco install k6

# Docker
docker pull grafana/k6
```

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/ferriskey/ferriskey-perf-tester.git
cd ferriskey-perf-tester

# Copy environment configuration
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your FerrisKey settings:

```bash
# .env
BASE_URL=http://localhost:3333
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ADMIN_REALM=master
PERF_REALM=perf
CLIENT_ID=perf-client
CLIENT_SECRET=perf-client-secret
USER_COUNT=50
USER_PASSWORD=perf-password
```

Default values work for local FerrisKey development setup.

### 3. Start FerrisKey

```bash
# Clone FerrisKey if you haven't
git clone https://github.com/ferriskey/ferriskey.git
cd ferriskey

# Start with Docker Compose
docker compose --profile local up -d

# Or run locally
cd api && cargo run
```

### 4. Seed Test Data

```bash
# Using uv (recommended)
uv run python scripts/seed_test_data.py

# Or with standard Python (after uv sync)
uv sync
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python scripts/seed_test_data.py
```

This creates:
- A `perf` realm
- Test clients (`perf-client`)
- 50 test users (`perf-user-001` through `perf-user-050`)

### 5. Run Performance Tests

```bash
# Quick smoke test
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/token_client_credentials.js

# Full load test with custom parameters
k6 run \
  --env BASE_URL=http://localhost:3333 \
  --env REALM=perf \
  --env CLIENT_ID=perf-client \
  --env CLIENT_SECRET=perf-client-secret \
  --env VUS=100 \
  --env DURATION=5m \
  k6/scenarios/mixed_workload.js
```

### 6. Cleanup (Optional)

```bash
uv run python scripts/cleanup_test_data.py
```

## Environment Configuration

All configuration is managed via `.env` file or environment variables.

### .env.example

```bash
# FerrisKey Performance Tester Configuration

# FerrisKey connection
BASE_URL=http://localhost:3333

# Admin credentials (for seeding/cleanup)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
ADMIN_REALM=master

# Performance test realm
PERF_REALM=perf

# Test client configuration
CLIENT_ID=perf-client
CLIENT_SECRET=perf-client-secret

# Test user configuration
USER_COUNT=50
USER_PASSWORD=perf-password
TEST_USERNAME=perf-user-001
TEST_PASSWORD=perf-password
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:3333` | FerrisKey base URL |
| `ADMIN_USERNAME` | `admin` | Admin username for seeding |
| `ADMIN_PASSWORD` | `admin` | Admin password for seeding |
| `ADMIN_REALM` | `master` | Admin realm for authentication |
| `PERF_REALM` | `perf` | Performance test realm name |
| `CLIENT_ID` | `perf-client` | Test client ID |
| `CLIENT_SECRET` | `perf-client-secret` | Test client secret |
| `USER_COUNT` | `50` | Number of test users to create |
| `USER_PASSWORD` | `perf-password` | Password for all test users |
| `TEST_USERNAME` | `perf-user-001` | Default test user for password grant |
| `TEST_PASSWORD` | `perf-password` | Default test user password |

## Test Scenarios

### Token - Client Credentials

Tests machine-to-machine authentication using the OAuth2 client credentials grant.

```bash
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/token_client_credentials.js
```

**Default thresholds:**
- p95 latency < 100ms
- Error rate < 1%

### Token - Password Grant

Tests user authentication using the OAuth2 password grant with a pool of test users.

```bash
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/token_password.js
```

**Default thresholds:**
- p95 latency < 150ms (higher due to password hashing)
- Error rate < 1%

### JWKS

Tests the JSON Web Key Set endpoint used for JWT validation.

```bash
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/jwks.js
```

**Default thresholds:**
- p95 latency < 20ms (should be very fast)
- Error rate < 0.1%

### Userinfo

Tests the OpenID Connect userinfo endpoint with Bearer token authentication.

```bash
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/userinfo.js
```

**Default thresholds:**
- p95 latency < 50ms
- Error rate < 1%

### Mixed Workload

Simulates realistic IAM traffic with weighted distribution:
- 40% client_credentials tokens
- 20% password grant tokens
- 30% userinfo requests
- 10% JWKS requests

```bash
k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/mixed_workload.js
```

## k6 Test Configuration

### Environment Variables for k6

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `http://localhost:3333` | FerrisKey base URL |
| `REALM` | `perf` | Realm for tests |
| `CLIENT_ID` | `perf-client` | OAuth2 client ID |
| `CLIENT_SECRET` | `perf-client-secret` | OAuth2 client secret |
| `TEST_USERNAME` | `perf-user-001` | Test user for password grant |
| `TEST_PASSWORD` | `perf-password` | Test user password |
| `VUS` | `50` | Number of virtual users |
| `DURATION` | `5m` | Test duration |

### Customizing Thresholds

Edit `k6/lib/config.js` to adjust SLO thresholds:

```javascript
export const thresholds = {
  token: {
    p95: 100,  // ms
    p99: 250,  // ms
    errorRate: 0.01,  // 1%
  },
  jwks: {
    p95: 20,   // ms
    p99: 50,   // ms
    errorRate: 0.001,  // 0.1%
  },
  userinfo: {
    p95: 50,   // ms
    p99: 100,  // ms
    errorRate: 0.01,  // 1%
  },
};
```

## Seeding Scripts

The seeding scripts are written in Python and managed with [uv](https://docs.astral.sh/uv/).

### Running with uv

```bash
# Seed test data (reads from .env)
uv run python scripts/seed_test_data.py

# Override specific settings
USER_COUNT=200 uv run python scripts/seed_test_data.py

# Cleanup test data
uv run python scripts/cleanup_test_data.py
```

### Running with Virtual Environment

```bash
# Create and sync virtual environment
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Run scripts
python scripts/seed_test_data.py
python scripts/cleanup_test_data.py
```

### Script Details

#### seed_test_data.py

Creates the performance test environment:

1. Authenticates as admin
2. Creates the `perf` realm
3. Creates test clients from `data/clients.json`
4. Creates test users (configurable count)
5. Sets passwords for all users

#### cleanup_test_data.py

Removes all test data by deleting the `perf` realm (cascade deletes all users, clients, etc.).

## CI/CD Integration

### Smoke Test (Pull Requests)

The `perf-smoke.yml` workflow runs on every PR:
- 30-second quick tests
- Validates no major regressions
- Uploads results as artifacts

### Nightly Test

The `perf-nightly.yml` workflow runs at 2 AM UTC:
- 5-10 minute load tests per scenario
- Memory leak detection
- Comprehensive results report

### Running in Your Own CI

```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v4

- name: Seed test data
  run: uv run python scripts/seed_test_data.py
  env:
    BASE_URL: ${{ env.FERRISKEY_URL }}
    USER_COUNT: 100

- name: Run performance tests
  run: |
    k6 run \
      --env BASE_URL=${{ env.FERRISKEY_URL }} \
      --env VUS=50 \
      --env DURATION=5m \
      --out json=results.json \
      k6/scenarios/mixed_workload.js
```

## Interpreting Results

### k6 Output

```
     ✓ status is 200
     ✓ response has access_token

     checks.........................: 100.00% ✓ 12000     ✗ 0
     data_received..................: 15 MB   50 kB/s
     http_req_duration..............: avg=45ms min=12ms med=42ms max=234ms p(90)=78ms p(95)=95ms
     http_reqs......................: 6000    20/s
     iteration_duration.............: avg=1.05s min=1.01s med=1.04s max=1.25s p(90)=1.09s p(95)=1.12s
```

Key metrics to watch:
- **http_req_duration p(95)**: Should be under threshold
- **checks**: Should be 100% (or very close)
- **http_reqs**: Throughput in requests/second

### Memory Analysis

The nightly test tracks memory growth:

```csv
baseline_kb,final_kb,growth_pct
45000,52000,15
```

Growth under 50% is considered normal. Higher growth may indicate a memory leak.

## Extending the Tests

### Adding a New Scenario

1. Create `k6/scenarios/my_scenario.js`
2. Import helpers from `lib/`
3. Define `options` with scenarios and thresholds
4. Implement `setup()`, `default()`, and `teardown()`

```javascript
import { config, thresholds } from '../lib/config.js';

export const options = {
  scenarios: {
    my_test: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m',
    },
  },
  thresholds: {
    'http_req_duration': ['p(95)<100'],
  },
};

export default function () {
  // Your test logic
}
```

### Phase 2 Improvements (Future)

- [ ] Authorization code flow test
- [ ] Stress test scenario (ramp to failure)
- [ ] Custom Prometheus metrics from FerrisKey
- [ ] Grafana dashboard for results visualization
- [ ] Baseline comparison in CI

## Troubleshooting

### "Failed to get admin token"

Ensure FerrisKey is running and the admin credentials are correct:
```bash
curl -X POST http://localhost:3333/realms/master/protocol/openid-connect/token \
  -d "grant_type=password&client_id=admin-cli&username=admin&password=admin"
```

### "Realm may already exist"

This is normal on repeated seeding. The script handles existing resources gracefully.

### High Error Rate in Tests

1. Check FerrisKey logs for errors
2. Verify test data was seeded correctly
3. Ensure database connections aren't exhausted
4. Check if rate limiting is enabled

### uv Issues

```bash
# Ensure uv is installed correctly
uv --version

# Force reinstall dependencies
uv sync --reinstall
```

## License

MIT License - see [LICENSE](LICENSE)
