import { ApiError } from "./http.js";

export function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** @param {HTMLElement | null} container */
export function showBanner(container, message, kind = "error") {
  if (!container) return;
  const cls =
    kind === "success" ? "app-banner app-banner--success" : "app-banner app-banner--error";
  container.innerHTML = `<div class="${cls}">${escapeHtml(message).replace(/\n/g, "<br>")}</div>`;
}

export function clearBanner(container) {
  if (container) container.innerHTML = "";
}

function flattenValidationErrors(body) {
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return null;
  }

  const lines = [];
  for (const [key, value] of Object.entries(body)) {
    if (key === "code" || key === "message" || key === "details") {
      continue;
    }
    if (Array.isArray(value)) {
      lines.push(`${key}: ${value.join("; ")}`);
    } else if (value && typeof value === "object") {
      const nested = flattenValidationErrors(value);
      if (nested) {
        lines.push(`${key}: ${nested}`);
      }
    } else if (value != null && value !== "") {
      lines.push(`${key}: ${String(value)}`);
    }
  }
  return lines.length ? lines.join("\n") : null;
}

/** @param {unknown} err */
export function formatApiError(err) {
  if (err instanceof ApiError && err.body && typeof err.body === "object") {
    let b = err.body;
    if (
      b.detail &&
      typeof b.detail === "object" &&
      !Array.isArray(b.detail) &&
      (b.detail.code || b.detail.message)
    ) {
      b = b.detail;
    }
    if (b.code === "schedule_conflict" && b.details) {
      const ids = (b.details.conflict_lesson_ids || []).join(", ");
      return `${b.message || "Schedule conflict"}. Conflicting lesson id(s): ${ids}`;
    }
    if (b.message && b.details && typeof b.details === "object") {
      const lines = Object.entries(b.details).map(([k, v]) => {
        const val = Array.isArray(v) ? v.join("; ") : String(v);
        return `${k}: ${val}`;
      });
      return [b.message, ...lines].join("\n");
    }
    if (typeof b.message === "string" && b.message) {
      return b.message;
    }
    if (typeof b.detail === "string" && b.detail) {
      return b.detail;
    }
    if (Array.isArray(b.detail)) {
      return b.detail.join("; ");
    }
    if (Array.isArray(b.non_field_errors)) {
      return b.non_field_errors.join("; ");
    }
    const fieldErrors = flattenValidationErrors(b);
    if (fieldErrors) {
      return fieldErrors;
    }
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
