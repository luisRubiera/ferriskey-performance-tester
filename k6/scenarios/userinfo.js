// k6/scenarios/userinfo.js
// Performance test for OpenID Connect userinfo endpoint
//
// The userinfo endpoint returns claims about the authenticated user.
// It requires a valid access token and is called by applications
// to get user profile information.
//
// Run: k6 run --env BASE_URL=http://localhost:3333 k6/scenarios/userinfo.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { config, thresholds, scenarios } from '../lib/config.js';
import { getClientCredentialsToken } from '../lib/auth.js';

// Custom metrics
const userinfoLatency = new Trend('userinfo_duration', true);
const userinfoErrors = new Rate('userinfo_errors');
const userinfoSuccess = new Counter('userinfo_success');
const tokenRefreshCount = new Counter('token_refresh_count');

// Test configuration
export const options = {
  scenarios: {
    userinfo_load: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS) || scenarios.load.vus,
      duration: __ENV.DURATION || scenarios.load.duration,
    },
  },
  thresholds: {
    'userinfo_duration': [`p(95)<${thresholds.userinfo.p95}`],  // 50ms
    'http_req_duration{endpoint:userinfo}': [`p(95)<${thresholds.userinfo.p95}`, `p(99)<${thresholds.userinfo.p99}`],
    'userinfo_errors': [`rate<${thresholds.userinfo.errorRate}`],
  },
  tags: {
    test_type: 'userinfo',
  },
};

// Per-VU state for token caching
let cachedToken = null;
let tokenExpiresAt = 0;

/**
 * Get a valid access token, refreshing if needed
 */
function getValidToken() {
  const now = Date.now();
  const bufferMs = 30000; // Refresh 30 seconds before expiry

  if (cachedToken && tokenExpiresAt > now + bufferMs) {
    return cachedToken;
  }

  // Get new token
  const tokenResponse = getClientCredentialsToken(
    config.realm,
    config.clientId,
    config.clientSecret
  );

  if (tokenResponse && tokenResponse.access_token) {
    cachedToken = tokenResponse.access_token;
    // expires_in is in seconds, convert to milliseconds
    tokenExpiresAt = now + (tokenResponse.expires_in * 1000);
    tokenRefreshCount.add(1);
    return cachedToken;
  }

  return null;
}

export function setup() {
  console.log(`Testing against: ${config.baseUrl}`);
  console.log(`Realm: ${config.realm}`);

  // Get a token first
  const tokenResponse = getClientCredentialsToken(
    config.realm,
    config.clientId,
    config.clientSecret
  );

  if (!tokenResponse || !tokenResponse.access_token) {
    throw new Error('Failed to obtain access token for setup');
  }

  // Test userinfo endpoint
  const url = `${config.baseUrl}${config.endpoints.userinfo(config.realm)}`;
  const res = http.get(url, {
    headers: { Authorization: `Bearer ${tokenResponse.access_token}` },
  });

  if (res.status !== 200) {
    console.error(`Setup failed: ${res.status} - ${res.body}`);
    throw new Error(`Userinfo endpoint failed. Status: ${res.status}`);
  }

  console.log('Setup successful - userinfo endpoint is working');
  return { setupTime: new Date().toISOString() };
}

export default function (data) {
  // Get a valid token (cached or refreshed)
  const accessToken = getValidToken();

  if (!accessToken) {
    userinfoErrors.add(1);
    console.error('Failed to obtain access token');
    sleep(1);
    return;
  }

  const url = `${config.baseUrl}${config.endpoints.userinfo(config.realm)}`;

  const params = {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    tags: { endpoint: 'userinfo' },
  };

  const res = http.get(url, params);

  // Record metrics
  userinfoLatency.add(res.timings.duration);

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response is valid JSON': (r) => {
      try {
        r.json();
        return true;
      } catch {
        return false;
      }
    },
    'response has sub claim': (r) => {
      try {
        const body = r.json();
        return body.sub !== undefined;
      } catch {
        return false;
      }
    },
  });

  if (success) {
    userinfoSuccess.add(1);
    userinfoErrors.add(0);
  } else {
    userinfoErrors.add(1);
    if (res.status === 401) {
      // Token might have expired, clear cache
      cachedToken = null;
      tokenExpiresAt = 0;
      console.warn('Got 401, clearing token cache');
    } else if (res.status !== 200) {
      console.warn(`Userinfo request failed: ${res.status}`);
    }
  }

  // Think time
  sleep(Math.random() * 1 + 0.5); // 0.5-1.5 seconds
}

export function teardown(data) {
  console.log(`Test completed. Started at: ${data.setupTime}`);
}
