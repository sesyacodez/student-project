import { API_BASE } from "./config.js";
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  setTokens,
} from "./auth.js";

export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {{ status?: number, body?: unknown }} extra
   */
  constructor(message, extra = {}) {
    super(message);
    this.name = "ApiError";
    this.status = extra.status;
    this.body = extra.body;
  }
}

let refreshPromise = null;

async function parseBody(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

async function tryRefresh() {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const res = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return false;
  const data = await res.json().catch(() => ({}));
  if (data.access) {
    setTokens({
      access: data.access,
      refresh: data.refresh != null ? data.refresh : refresh,
    });
    return true;
  }
  return false;
}

/**
 * @param {string} path - e.g. "/lessons/" or "lessons/"
 * @param {{ method?: string, body?: unknown, skipAuth?: boolean }} options
 */
export async function request(path, options = {}) {
  const method = options.method || "GET";
  const skipAuth = !!options.skipAuth;
  const url = `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;

  const headers = { ...(options.headers || {}) };
  if (options.body !== undefined && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const fetchOpts = {
    method,
    headers,
    body:
      options.body !== undefined ? JSON.stringify(options.body) : undefined,
  };

  let res = await fetch(url, fetchOpts);

  if (res.status === 401 && !skipAuth) {
    if (!refreshPromise) {
      refreshPromise = tryRefresh().finally(() => {
        refreshPromise = null;
      });
    }
    const refreshed = await refreshPromise;
    if (refreshed) {
      const h2 = { ...headers };
      const t = getAccessToken();
      if (t) h2["Authorization"] = `Bearer ${t}`;
      res = await fetch(url, {
        method,
        headers: h2,
        body:
          options.body !== undefined
            ? JSON.stringify(options.body)
            : undefined,
      });
    } else {
      clearSession();
      window.location.href = "index.html";
      throw new ApiError("Session expired", { status: 401 });
    }
  }

  const parsed = await parseBody(res);
  if (!res.ok) {
    let msg = res.statusText || "Request failed";
    if (parsed && typeof parsed === "object") {
      if (parsed.message) msg = parsed.message;
      else if (typeof parsed.detail === "string") msg = parsed.detail;
    }
    throw new ApiError(msg, { status: res.status, body: parsed });
  }
  return parsed;
}

/** DRF paginated list → array */
export async function requestList(path) {
  const data = await request(path);
  if (data && Array.isArray(data.results)) return data.results;
  if (Array.isArray(data)) return data;
  return [];
}

/** DRF paginated list → array (all pages) */
export async function requestAllPages(path, maxPages = 50) {
  const results = [];
  let nextPath = path;
  let pages = 0;

  while (nextPath && pages < maxPages) {
    pages += 1;
    const data = await request(nextPath);
    if (data && Array.isArray(data.results)) {
      results.push(...data.results);
      if (!data.next) break;
      if (data.next.startsWith(API_BASE)) {
        nextPath = data.next.slice(API_BASE.length);
      } else if (data.next.startsWith("http")) {
        try {
          const url = new URL(data.next);
          nextPath = `${url.pathname}${url.search}`;
        } catch {
          nextPath = null;
        }
      } else {
        nextPath = data.next;
      }
    } else if (Array.isArray(data)) {
      return data;
    } else {
      break;
    }
  }

  return results;
}
