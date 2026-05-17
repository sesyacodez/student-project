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
      "Шлях API не знайдено. Перевірте, чи запущений сервер Django."
    );
  }
  
  if (!res.ok) {
    const msg =
      data.message ||
      (typeof data.detail === "string" ? data.detail : null) ||
      "Не вдалося увійти. Перевірте телефон та пароль.";
    throw new Error(msg);
  }
  
  if (data.access) {
    setTokens({ access: data.access, refresh: data.refresh });
    
    setUser({
      first_name: data.first_name,
      role: data.role,
      branch_id: data.branch_id
    });
  }
}

/** For local demo before JWT exists: navigate as ADMIN (API still AllowAny). */
export function devLoginAsAdmin() {
  setTokens({ access: "dev-local", refresh: "" });
  setUser({
    phone: "+dev-admin",
    first_name: "Dev",
    last_name: "Admin",
    role: "ADMIN",
    branches: [],
  });
}

/** For local demo: TEACHER (no id — own-lesson checks skipped until real JWT /me). */
export function devLoginAsTeacher() {
  setTokens({ access: "dev-local", refresh: "" });
  setUser({
    phone: "+dev-teacher",
    first_name: "Dev",
    last_name: "Teacher",
    role: "TEACHER",
    branches: [],
  });
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