// k6/scenarios/token_client_credentials.js
// Performance test for OAuth2 client_credentials grant
//
// This tests the most common machine-to-machine authentication flow.
// The token endpoint is typically the most called endpoint in an IAM system.
//
// Run: k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/token_client_credentials.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { config, thresholds, scenarios } from '../lib/config.js';

// Custom metrics
const tokenLatency = new Trend('token_client_credentials_duration', true);
const tokenErrors = new Rate('token_client_credentials_errors');
const tokenSuccess = new Counter('token_client_credentials_success');

// Test configuration
export const options = {
  scenarios: {
    // Default: load test scenario
    client_credentials_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS) || scenarios.load.vus,
      duration: __ENV.DURATION || scenarios.load.duration,
    },
  },
  thresholds: {
    // SLO: p95 < 100ms for token endpoint
    'token_client_credentials_duration': [`p(95)<${thresholds.token.p95}`],
    'http_req_duration{endpoint:token}': [`p(95)<${thresholds.token.p95}`, `p(99)<${thresholds.token.p99}`],
    'token_client_credentials_errors': [`rate<${thresholds.token.errorRate}`],
  },
  // Tags for filtering in dashboards
  tags: {
    test_type: 'token_client_credentials',
  },
};

// Setup function - runs once before the test
export function setup() {
  console.log(`Testing against: ${config.baseUrl}`);
  console.log(`Realm: ${config.realm}`);
  console.log(`Client ID: ${config.clientId}`);

  // Verify the endpoint is reachable
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;
  const res = http.post(url, {
    grant_type: 'client_credentials',
    client_id: config.clientId,
    client_secret: config.clientSecret,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (res.status !== 200) {
    console.error(`Setup failed: ${res.status} - ${res.body}`);
    throw new Error(`Cannot reach token endpoint. Status: ${res.status}`);
  }

  console.log('Setup successful - token endpoint is reachable');
  return { setupTime: new Date().toISOString() };
}

// Main test function - runs for each VU iteration
export default function (data) {
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;

  const payload = {
    grant_type: 'client_credentials',
    client_id: config.clientId,
    client_secret: config.clientSecret,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'token', grant_type: 'client_credentials' },
  };

  const res = http.post(url, payload, params);

  // Record custom metrics
  tokenLatency.add(res.timings.duration);

  // Validate response
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has access_token': (r) => {
      try {
        const body = r.json();
        return body.access_token !== undefined;
      } catch {
        return false;
      }
    },
    'response has token_type': (r) => {
      try {
        const body = r.json();
        return body.token_type !== undefined;
      } catch {
        return false;
      }
    },
    'response has expires_in': (r) => {
      try {
        const body = r.json();
        return body.expires_in !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (success) {
    tokenSuccess.add(1);
    tokenErrors.add(0);
  } else {
    tokenErrors.add(1);
    if (res.status !== 200) {
      console.warn(`Request failed: ${res.status} - ${res.body}`);
    }
  }

  // Think time between requests (simulates real user behavior)
  sleep(Math.random() * 2 + 0.5); // 0.5-2.5 seconds
}

// Teardown function - runs once after the test
export function teardown(data) {
  console.log(`Test completed. Started at: ${data.setupTime}`);
}
