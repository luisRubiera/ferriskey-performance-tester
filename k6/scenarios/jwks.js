// k6/scenarios/jwks.js
// Performance test for JWKS (JSON Web Key Set) endpoint
//
// The JWKS endpoint returns the public keys used to verify JWT signatures.
// This endpoint should be extremely fast as it's typically cached and
// called by every service that validates tokens.
//
// Run: k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/jwks.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { config, thresholds, scenarios } from '../lib/config.js';

// Custom metrics
const jwksLatency = new Trend('jwks_duration', true);
const jwksErrors = new Rate('jwks_errors');
const jwksSuccess = new Counter('jwks_success');

// Test configuration
export const options = {
  scenarios: {
    jwks_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS) || scenarios.load.vus,
      duration: __ENV.DURATION || scenarios.load.duration,
    },
  },
  thresholds: {
    // JWKS should be ultra-fast - strict thresholds
    'jwks_duration': [`p(95)<${thresholds.jwks.p95}`],  // 20ms
    'http_req_duration{endpoint:jwks}': [`p(95)<${thresholds.jwks.p95}`, `p(99)<${thresholds.jwks.p99}`],
    'jwks_errors': [`rate<${thresholds.jwks.errorRate}`],  // 0.1%
  },
  tags: {
    test_type: 'jwks',
  },
};

export function setup() {
  console.log(`Testing against: ${config.baseUrl}`);
  console.log(`Realm: ${config.realm}`);

  const url = `${config.baseUrl}${config.endpoints.certs(config.realm)}`;
  const res = http.get(url);

  if (res.status !== 200) {
    console.error(`Setup failed: ${res.status} - ${res.body}`);
    throw new Error(`Cannot reach JWKS endpoint. Status: ${res.status}`);
  }

  // Validate JWKS structure
  try {
    const jwks = res.json();
    if (!jwks.keys || !Array.isArray(jwks.keys)) {
      throw new Error('Invalid JWKS structure - missing keys array');
    }
    console.log(`Setup successful - JWKS has ${jwks.keys.length} key(s)`);
  } catch (e) {
    throw new Error(`Invalid JWKS response: ${e.message}`);
  }

  return { setupTime: new Date().toISOString() };
}

export default function (data) {
  const url = `${config.baseUrl}${config.endpoints.certs(config.realm)}`;

  const params = {
    tags: { endpoint: 'jwks' },
  };

  const res = http.get(url, params);

  // Record metrics
  jwksLatency.add(res.timings.duration);

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response has keys array': (r) => {
      try {
        const body = r.json();
        return Array.isArray(body.keys);
      } catch {
        return false;
      }
    },
    'keys have required fields': (r) => {
      try {
        const body = r.json();
        if (!body.keys || body.keys.length === 0) return true; // Empty is valid
        const key = body.keys[0];
        // RSA keys should have: kty, use, kid, n, e
        return key.kty !== undefined && key.kid !== undefined;
      } catch {
        return false;
      }
    },
    'response time < 50ms': (r) => r.timings.duration < 50,
  });

  if (success) {
    jwksSuccess.add(1);
    jwksErrors.add(0);
  } else {
    jwksErrors.add(1);
    if (res.status !== 200) {
      console.warn(`JWKS request failed: ${res.status}`);
    }
  }

  // Short think time - JWKS is called frequently by token validators
  sleep(Math.random() * 0.5 + 0.1); // 0.1-0.6 seconds
}

export function teardown(data) {
  console.log(`Test completed. Started at: ${data.setupTime}`);
}
