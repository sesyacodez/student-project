import { getUser, isLoggedIn, logout } from "./auth.js";

function currentPage() {
  const name = window.location.pathname.split("/").pop() || "";
  return name.replace(/\.html$/, "") || "index";
}

export function renderNav() {
  const el = document.querySelector("[data-nav]");
  if (!el) return;

  const page = currentPage();
  const user = getUser();
  const logged = isLoggedIn();

  const link = (href, label, id) => {
    const active = id === page ? " app-nav__link--active" : "";
    return `<a class="app-nav__link${active}" href="${href}">${label}</a>`;
  };

  let inner = `<span class="app-nav__brand">EduManage</span>`;

  if (!logged) {
    inner += link("index.html", "Login", "index");
  } else if (user.role === "ADMIN") {
    inner += link("dashboard.html", "Home", "dashboard");
    inner += link("lessons.html", "Lessons", "lessons");
    inner += link("lesson-templates.html", "Templates", "lesson-templates");
    inner += link("reports.html", "Reports", "reports");
  } else {
    inner += link("dashboard.html", "Home", "dashboard");
    inner += link("my-schedule.html", "My schedule", "my-schedule");
    inner += link("reports.html", "Reports", "reports");
  }

  inner += `<span class="app-nav__spacer"></span>`;
  if (logged) {
    inner += `<span class="muted">${user.role} · ${user.phone || ""}</span>`;
    inner += `<button type="button" class="app-btn app-btn--ghost" id="nav-logout">Log out</button>`;
  }

  el.innerHTML = inner;
  const btn = document.getElementById("nav-logout");
  if (btn) btn.addEventListener("click", () => logout());
}
