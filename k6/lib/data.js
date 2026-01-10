// k6/lib/data.js
// Test data helpers for FerrisKey performance tests

import { SharedArray } from 'k6/data';

// Load users from CSV file - SharedArray ensures data is loaded once and shared across VUs
// Note: This file is created by the seed script
export const users = new SharedArray('users', function () {
  // During actual test runs, this will load from the generated file
  // For now, return a default set that matches our seed data pattern
  const userList = [];
  for (let i = 1; i <= 200; i++) {
    const paddedNum = String(i).padStart(3, '0');
    userList.push({
      username: `perf-user-${paddedNum}`,
      password: 'perf-password',
      email: `perf${paddedNum}@test.local`,
    });
  }
  return userList;
});

/**
 * Get a random user from the test data
 * @returns {object} - Random user with username, password, email
 */
export function getRandomUser() {
  return users[Math.floor(Math.random() * users.length)];
}

/**
 * Get user by index (for deterministic selection per VU)
 * @param {number} index - User index
 * @returns {object} - User at given index (wraps around if index > length)
 */
export function getUserByIndex(index) {
  return users[index % users.length];
}
