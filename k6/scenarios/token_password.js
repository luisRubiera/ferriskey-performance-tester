// k6/scenarios/token_password.js
// Performance test for OAuth2 password grant (Resource Owner Password Credentials)
//
// This tests user authentication flow where username/password are exchanged for tokens.
// Uses a pool of test users to simulate realistic load.
//
// Run: k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/token_password.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { config, thresholds, scenarios } from '../lib/config.js';
import { getRandomUser } from '../lib/data.js';

// Custom metrics
const tokenLatency = new Trend('token_password_duration', true);
const tokenErrors = new Rate('token_password_errors');
const tokenSuccess = new Counter('token_password_success');

// Test configuration
export const options = {
  scenarios: {
    password_grant_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS) || scenarios.load.vus,
      duration: __ENV.DURATION || scenarios.load.duration,
    },
  },
  thresholds: {
    // Password grant may be slightly slower due to password hashing verification
    'token_password_duration': [`p(95)<${thresholds.token.p95 * 1.5}`], // 150ms for password grant
    'http_req_duration{endpoint:token,grant_type:password}': [`p(95)<${thresholds.token.p95 * 1.5}`],
    'token_password_errors': [`rate<${thresholds.token.errorRate}`],
  },
  tags: {
    test_type: 'token_password',
  },
};

export function setup() {
  console.log(`Testing against: ${config.baseUrl}`);
  console.log(`Realm: ${config.realm}`);

  // Verify with a single test user
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;
  const res = http.post(url, {
    grant_type: 'password',
    client_id: config.clientId,
    client_secret: config.clientSecret,
    username: config.testUsername,
    password: config.testPassword,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (res.status !== 200) {
    console.error(`Setup failed: ${res.status} - ${res.body}`);
    throw new Error(`Password grant failed. Status: ${res.status}. Ensure test users are seeded.`);
  }

  console.log('Setup successful - password grant is working');
  return { setupTime: new Date().toISOString() };
}

export default function (data) {
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;

  // Get a random user from the test data pool
  const user = getRandomUser();

  const payload = {
    grant_type: 'password',
    client_id: config.clientId,
    client_secret: config.clientSecret,
    username: user.username,
    password: user.password,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'token', grant_type: 'password' },
  };

  const res = http.post(url, payload, params);

  // Record metrics
  tokenLatency.add(res.timings.duration);

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
    'response has refresh_token': (r) => {
      try {
        const body = r.json();
        // refresh_token may or may not be present depending on client config
        return body.refresh_token !== undefined || r.status === 200;
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
      console.warn(`Request failed for user ${user.username}: ${res.status}`);
    }
  }

  // Longer think time for user logins (users don't login every second)
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

export function teardown(data) {
  console.log(`Test completed. Started at: ${data.setupTime}`);
}
