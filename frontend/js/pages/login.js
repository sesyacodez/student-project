import { devLoginAsAdmin, devLoginAsTeacher, isLoggedIn, login } from "../auth.js";
import { renderNav } from "../nav.js";
import { clearBanner, showBanner, formatApiError } from "../ui.js";

renderNav();

if (isLoggedIn()) {
  window.location.href = "dashboard.html";
}

const form = document.getElementById("login-form");
const banner = document.getElementById("banner");
const devAdmin = document.getElementById("dev-admin");
const devTeacher = document.getElementById("dev-teacher");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  clearBanner(banner);
  const phone = document.getElementById("phone").value.trim();
  const password = document.getElementById("password").value;
  try {
    await login(phone, password);
    window.location.href = "dashboard.html";
  } catch (err) {
    showBanner(banner, formatApiError(err));
  }
});

devAdmin.addEventListener("click", () => {
  devLoginAsAdmin();
  window.location.href = "dashboard.html";
});

devTeacher.addEventListener("click", () => {
  devLoginAsTeacher();
  window.location.href = "dashboard.html";
});
