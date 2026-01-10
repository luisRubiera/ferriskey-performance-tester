// k6/lib/auth.js
// Authentication helpers for FerrisKey performance tests

import http from 'k6/http';
import { config } from './config.js';

/**
 * Get access token using client_credentials grant
 * @param {string} realm - Realm name
 * @param {string} clientId - Client ID
 * @param {string} clientSecret - Client secret
 * @returns {object} - Token response or null on failure
 */
export function getClientCredentialsToken(realm, clientId, clientSecret) {
  const url = `${config.baseUrl}${config.endpoints.token(realm)}`;

  const payload = {
    grant_type: 'client_credentials',
    client_id: clientId,
    client_secret: clientSecret,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'token', grant_type: 'client_credentials' },
  };

  const res = http.post(url, payload, params);

  if (res.status === 200) {
    return res.json();
  }
  return null;
}

/**
 * Get access token using password grant
 * @param {string} realm - Realm name
 * @param {string} clientId - Client ID
 * @param {string} clientSecret - Client secret (optional for public clients)
 * @param {string} username - User's username
 * @param {string} password - User's password
 * @returns {object} - Token response or null on failure
 */
export function getPasswordToken(realm, clientId, clientSecret, username, password) {
  const url = `${config.baseUrl}${config.endpoints.token(realm)}`;

  const payload = {
    grant_type: 'password',
    client_id: clientId,
    username: username,
    password: password,
  };

  if (clientSecret) {
    payload.client_secret = clientSecret;
  }

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'token', grant_type: 'password' },
  };

  const res = http.post(url, payload, params);

  if (res.status === 200) {
    return res.json();
  }
  return null;
}

/**
 * Refresh an access token
 * @param {string} realm - Realm name
 * @param {string} clientId - Client ID
 * @param {string} clientSecret - Client secret
 * @param {string} refreshToken - Refresh token
 * @returns {object} - Token response or null on failure
 */
export function refreshToken(realm, clientId, clientSecret, refreshToken) {
  const url = `${config.baseUrl}${config.endpoints.token(realm)}`;

  const payload = {
    grant_type: 'refresh_token',
    client_id: clientId,
    client_secret: clientSecret,
    refresh_token: refreshToken,
  };

  const params = {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    tags: { endpoint: 'token', grant_type: 'refresh_token' },
  };

  const res = http.post(url, payload, params);

  if (res.status === 200) {
    return res.json();
  }
  return null;
}

/**
 * Get user info using access token
 * @param {string} realm - Realm name
 * @param {string} accessToken - Access token
 * @returns {object} - Userinfo response or null on failure
 */
export function getUserInfo(realm, accessToken) {
  const url = `${config.baseUrl}${config.endpoints.userinfo(realm)}`;

  const params = {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    tags: { endpoint: 'userinfo' },
  };

  const res = http.get(url, params);

  if (res.status === 200) {
    return res.json();
  }
  return null;
}

/**
 * Get JWKS (JSON Web Key Set)
 * @param {string} realm - Realm name
 * @returns {object} - JWKS response or null on failure
 */
export function getJwks(realm) {
  const url = `${config.baseUrl}${config.endpoints.certs(realm)}`;

  const params = {
    tags: { endpoint: 'jwks' },
  };

  const res = http.get(url, params);

  if (res.status === 200) {
    return res.json();
  }
  return null;
}
