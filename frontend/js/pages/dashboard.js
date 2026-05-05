import { getUser, isLoggedIn } from "../auth.js";
import { renderNav } from "../nav.js";

renderNav();

if (!isLoggedIn()) {
  window.location.href = "index.html";
} else {
  const u = getUser();
  if (u.role === "ADMIN") window.location.href = "lessons.html";
  else window.location.href = "my-schedule.html";
}
