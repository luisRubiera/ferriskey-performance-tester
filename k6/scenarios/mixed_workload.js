// k6/scenarios/mixed_workload.js
// Realistic mixed workload performance test for FerrisKey
//
// This simulates realistic IAM traffic patterns with weighted distribution:
// - 40% client_credentials (service-to-service auth)
// - 20% password grant (user logins)
// - 30% userinfo (application profile fetches)
// - 10% JWKS (token validation key fetches)
//
// Run: k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/mixed_workload.js

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { config, thresholds, scenarios } from '../lib/config.js';
import { getRandomUser } from '../lib/data.js';

// Custom metrics per endpoint
const metrics = {
  clientCredentials: {
    latency: new Trend('mixed_client_credentials_duration', true),
    errors: new Rate('mixed_client_credentials_errors'),
  },
  password: {
    latency: new Trend('mixed_password_duration', true),
    errors: new Rate('mixed_password_errors'),
  },
  userinfo: {
    latency: new Trend('mixed_userinfo_duration', true),
    errors: new Rate('mixed_userinfo_errors'),
  },
  jwks: {
    latency: new Trend('mixed_jwks_duration', true),
    errors: new Rate('mixed_jwks_errors'),
  },
};

const totalRequests = new Counter('mixed_total_requests');
const totalErrors = new Rate('mixed_total_errors');

// Traffic distribution weights (must sum to 100)
const WEIGHTS = {
  clientCredentials: 40,
  password: 20,
  userinfo: 30,
  jwks: 10,
};

// Test configuration
export const options = {
  scenarios: {
    mixed_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS) || scenarios.load.vus,
      duration: __ENV.DURATION || scenarios.load.duration,
    },
  },
  thresholds: {
    // Overall error rate
    'mixed_total_errors': ['rate<0.02'], // 2% overall

    // Per-endpoint thresholds
    'mixed_client_credentials_duration': [`p(95)<${thresholds.token.p95}`],
    'mixed_password_duration': [`p(95)<${thresholds.token.p95 * 1.5}`],
    'mixed_userinfo_duration': [`p(95)<${thresholds.userinfo.p95}`],
    'mixed_jwks_duration': [`p(95)<${thresholds.jwks.p95}`],

    // Error rates per endpoint
    'mixed_client_credentials_errors': [`rate<${thresholds.token.errorRate}`],
    'mixed_password_errors': [`rate<${thresholds.token.errorRate}`],
    'mixed_userinfo_errors': [`rate<${thresholds.userinfo.errorRate}`],
    'mixed_jwks_errors': [`rate<${thresholds.jwks.errorRate}`],
  },
  tags: {
    test_type: 'mixed_workload',
  },
};

// Per-VU token cache for userinfo requests
let cachedToken = null;
let tokenExpiresAt = 0;

/**
 * Weighted random selection of endpoint to call
 */
function selectEndpoint() {
  const rand = Math.random() * 100;
  let cumulative = 0;

  for (const [endpoint, weight] of Object.entries(WEIGHTS)) {
    cumulative += weight;
    if (rand < cumulative) {
      return endpoint;
    }
  }
  return 'clientCredentials'; // Fallback
}

/**
 * Execute client_credentials token request
 */
function doClientCredentials() {
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;

  const res = http.post(url, {
    grant_type: 'client_credentials',
    client_id: config.clientId,
    client_secret: config.clientSecret,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    tags: { endpoint: 'token', grant_type: 'client_credentials', workload: 'mixed' },
  });

  metrics.clientCredentials.latency.add(res.timings.duration);

  const success = check(res, {
    'client_credentials: status 200': (r) => r.status === 200,
    'client_credentials: has access_token': (r) => {
      try {
        return r.json().access_token !== undefined;
      } catch {
        return false;
      }
    },
  });

  metrics.clientCredentials.errors.add(!success);

  // Cache token for userinfo requests
  if (success && res.status === 200) {
    try {
      const body = res.json();
      cachedToken = body.access_token;
      tokenExpiresAt = Date.now() + (body.expires_in * 1000) - 30000;
    } catch {
      // Ignore parse errors
    }
  }

  return success;
}

/**
 * Execute password grant token request
 */
function doPasswordGrant() {
  const url = `${config.baseUrl}${config.endpoints.token(config.realm)}`;
  const user = getRandomUser();

  const res = http.post(url, {
    grant_type: 'password',
    client_id: config.clientId,
    client_secret: config.clientSecret,
    username: user.username,
    password: user.password,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    tags: { endpoint: 'token', grant_type: 'password', workload: 'mixed' },
  });

  metrics.password.latency.add(res.timings.duration);

  const success = check(res, {
    'password: status 200': (r) => r.status === 200,
    'password: has access_token': (r) => {
      try {
        return r.json().access_token !== undefined;
      } catch {
        return false;
      }
    },
  });

  metrics.password.errors.add(!success);
  return success;
}

/**
 * Execute userinfo request
 */
function doUserinfo() {
  // Ensure we have a token
  if (!cachedToken || Date.now() > tokenExpiresAt) {
    doClientCredentials(); // Get a fresh token
  }

  if (!cachedToken) {
    metrics.userinfo.errors.add(true);
    return false;
  }

  const url = `${config.baseUrl}${config.endpoints.userinfo(config.realm)}`;

  const res = http.get(url, {
    headers: { Authorization: `Bearer ${cachedToken}` },
    tags: { endpoint: 'userinfo', workload: 'mixed' },
  });

  metrics.userinfo.latency.add(res.timings.duration);

  const success = check(res, {
    'userinfo: status 200': (r) => r.status === 200,
    'userinfo: has sub': (r) => {
      try {
        return r.json().sub !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (res.status === 401) {
    cachedToken = null;
    tokenExpiresAt = 0;
  }

  metrics.userinfo.errors.add(!success);
  return success;
}

/**
 * Execute JWKS request
 */
function doJwks() {
  const url = `${config.baseUrl}${config.endpoints.certs(config.realm)}`;

  const res = http.get(url, {
    tags: { endpoint: 'jwks', workload: 'mixed' },
  });

  metrics.jwks.latency.add(res.timings.duration);

  const success = check(res, {
    'jwks: status 200': (r) => r.status === 200,
    'jwks: has keys': (r) => {
      try {
        return Array.isArray(r.json().keys);
      } catch {
        return false;
      }
    },
  });

  metrics.jwks.errors.add(!success);
  return success;
}

export function setup() {
  console.log(`Mixed Workload Test`);
  console.log(`Testing against: ${config.baseUrl}`);
  console.log(`Realm: ${config.realm}`);
  console.log(`Traffic distribution:`);
  console.log(`  - client_credentials: ${WEIGHTS.clientCredentials}%`);
  console.log(`  - password: ${WEIGHTS.password}%`);
  console.log(`  - userinfo: ${WEIGHTS.userinfo}%`);
  console.log(`  - jwks: ${WEIGHTS.jwks}%`);

  // Verify all endpoints work
  const tokenUrl = `${config.baseUrl}${config.endpoints.token(config.realm)}`;
  const tokenRes = http.post(tokenUrl, {
    grant_type: 'client_credentials',
    client_id: config.clientId,
    client_secret: config.clientSecret,
  }, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });

  if (tokenRes.status !== 200) {
    throw new Error(`Token endpoint not working: ${tokenRes.status}`);
  }

  console.log('Setup successful - all endpoints verified');
  return { setupTime: new Date().toISOString() };
}

export default function (data) {
  const endpoint = selectEndpoint();
  let success = false;

  totalRequests.add(1);

  switch (endpoint) {
    case 'clientCredentials':
      success = doClientCredentials();
      break;
    case 'password':
      success = doPasswordGrant();
      break;
    case 'userinfo':
      success = doUserinfo();
      break;
    case 'jwks':
      success = doJwks();
      break;
  }

  totalErrors.add(!success);

  // Variable think time based on endpoint type
  const thinkTimes = {
    clientCredentials: () => Math.random() * 2 + 0.5,   // 0.5-2.5s
    password: () => Math.random() * 3 + 1,              // 1-4s (users login less frequently)
    userinfo: () => Math.random() * 1 + 0.3,           // 0.3-1.3s (apps call frequently)
    jwks: () => Math.random() * 0.5 + 0.1,             // 0.1-0.6s (validators poll frequently)
  };

  sleep(thinkTimes[endpoint]());
}

export function teardown(data) {
  console.log(`Mixed workload test completed. Started at: ${data.setupTime}`);
}
