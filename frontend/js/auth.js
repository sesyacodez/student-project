import { API_BASE } from "./config.js";

const KEY_ACCESS = "edu_access";
const KEY_REFRESH = "edu_refresh";
const KEY_USER = "edu_user";

export function getAccessToken() {
  return localStorage.getItem(KEY_ACCESS);
}

export function getRefreshToken() {
  return localStorage.getItem(KEY_REFRESH);
}

export function setTokens({ access, refresh }) {
  if (access != null) localStorage.setItem(KEY_ACCESS, access);
  if (refresh != null) localStorage.setItem(KEY_REFRESH, refresh);
}

export function setUser(user) {
  localStorage.setItem(KEY_USER, JSON.stringify(user));
}

export function getUser() {
  const raw = localStorage.getItem(KEY_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(KEY_ACCESS);
  localStorage.removeItem(KEY_REFRESH);
  localStorage.removeItem(KEY_USER);
}

export function isLoggedIn() {
  return getUser() != null;
}

/**
 * Real login to our Django backend.
 */
export async function login(phone, password) {
  const res = await fetch(`${API_BASE}/users/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phone, password }),
  });

  const data = await res.json().catch(() => ({}));

  if (res.status === 404) {
    throw new Error(
      "API path not found. Check that the Django server is running."
    );
  }

  if (!res.ok) {
    const msg =
      data.message ||
      (typeof data.detail === "string" ? data.detail : null) ||
      "Login failed. Check your phone number and password.";
    throw new Error(msg);
  }

  if (data.access) {
    setTokens({ access: data.access, refresh: data.refresh });

    setUser({
      id: data.id,
      phone: data.phone,
      first_name: data.first_name,
      role: data.role,
      branch_id: data.branch_id,
    });
  }
}

export function logout() {
  clearSession();
  window.location.href = "index.html";
}

/**
 * User must have one of the given roles.
 * @param {string[]} roles
 */
export function requireRole(roles) {
  const u = getUser();
  if (!u) {
    window.location.href = "index.html";
    return false;
  }
  if (!roles.includes(u.role)) {
    window.location.href = "dashboard.html";
    return false;
  }
  return true;
}
