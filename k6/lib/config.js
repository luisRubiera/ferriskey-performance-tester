// k6/lib/config.js
// Environment configuration for FerrisKey performance tests

export const config = {
  // Base URL - override with BASE_URL env var
  baseUrl: __ENV.BASE_URL || 'http://localhost:3333',

  // Realm for performance tests
  realm: __ENV.REALM || 'perf-realm',

  // Admin credentials for seeding (used by setup scripts, not k6)
  adminUsername: __ENV.ADMIN_USERNAME || 'admin',
  adminPassword: __ENV.ADMIN_PASSWORD || 'admin',

  // Test client credentials
  clientId: __ENV.CLIENT_ID || 'perf-client',
  clientSecret: __ENV.CLIENT_SECRET || 'perf-client-secret',

  // Test user credentials (for password grant)
  testUsername: __ENV.TEST_USERNAME || 'perf-user-001',
  testPassword: __ENV.TEST_PASSWORD || 'perf-password',

  // Endpoints
  endpoints: {
    token: (realm) => `/realms/${realm}/protocol/openid-connect/token`,
    userinfo: (realm) => `/realms/${realm}/protocol/openid-connect/userinfo`,
    certs: (realm) => `/realms/${realm}/protocol/openid-connect/certs`,
    wellKnown: (realm) => `/realms/${realm}/.well-known/openid-configuration`,
  },
};

// SLO thresholds - adjust based on your requirements
export const thresholds = {
  // Token endpoint - critical path
  token: {
    p95: 100,  // ms
    p99: 250,  // ms
    errorRate: 0.01,  // 1%
  },
  // JWKS endpoint - should be very fast (usually cached)
  jwks: {
    p95: 20,   // ms
    p99: 50,   // ms
    errorRate: 0.001,  // 0.1%
  },
  // Userinfo endpoint
  userinfo: {
    p95: 50,   // ms
    p99: 100,  // ms
    errorRate: 0.01,  // 1%
  },
};

// Scenario configurations
export const scenarios = {
  // Smoke test - quick validation
  smoke: {
    vus: 5,
    duration: '30s',
  },
  // Load test - sustained normal traffic
  load: {
    vus: 50,
    duration: '5m',
  },
  // Stress test - find breaking point
  stress: {
    stages: [
      { duration: '2m', target: 50 },   // Ramp up
      { duration: '5m', target: 100 },  // Stay at 100
      { duration: '2m', target: 200 },  // Push higher
      { duration: '5m', target: 200 },  // Stay at 200
      { duration: '2m', target: 0 },    // Ramp down
    ],
  },
  // Soak test - long duration for leak detection
  soak: {
    vus: 30,
    duration: '30m',
  },
};
