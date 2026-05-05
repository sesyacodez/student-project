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
    if (b.message) return b.message;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
