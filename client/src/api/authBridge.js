/**
 * DEV STUB: replace with Phase 2 auth. See docs/phase3-integration.md
 * 
 * This module is the sole bridge isolating Phase 3 frontend components
 * from Phase 2 authentication and user sessions.
 * In Phase 2, this file will be updated to read from the real session/token auth.
 */

import { useState, useEffect } from 'react';

export const DEV_USERS = [
  { user_id: 1, username: 'alex_traveler', display_name: 'Alex Mercer' },
  { user_id: 2, username: 'sarah_journeys', display_name: 'Sarah Jenkins' },
  { user_id: 3, username: 'dan_nomad', display_name: 'Dan Reynolds' },
  { user_id: 4, username: 'priya_wander', display_name: 'Priya Sharma' },
];

let currentDevUserId = 1;
const listeners = new Set();

export function setDevUserId(id) {
  const parsed = id ? Number(id) : null;
  currentDevUserId = parsed;
  listeners.forEach((listener) => listener(currentDevUserId));
}

export function getAuthHeaders() {
  if (!currentDevUserId) {
    return {};
  }
  return {
    'X-Dev-User-Id': String(currentDevUserId),
  };
}

export function useCurrentUser() {
  const [activeId, setActiveId] = useState(currentDevUserId);

  useEffect(() => {
    listeners.add(setActiveId);
    return () => {
      listeners.delete(setActiveId);
    };
  }, []);

  const user = DEV_USERS.find((u) => u.user_id === activeId) || (activeId ? {
    user_id: activeId,
    username: `user_${activeId}`,
    display_name: `Dev User ${activeId}`,
  } : null);

  return {
    user,
    isLoggedIn: Boolean(user),
    setDevUserId,
    availableDevUsers: DEV_USERS,
  };
}
