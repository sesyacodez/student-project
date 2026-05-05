import { getUser, requireRole } from "../auth.js";
import { request } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();
if (!requireRole(["ADMIN", "TEACHER"])) {
  /* redirected */
} else {
  const user = getUser();
  const banner = document.getElementById("banner");
  const isAdmin = user.role === "ADMIN";

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-tab");
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("app-tab--active"));
      btn.classList.add("app-tab--active");
      document.querySelectorAll(".tab-panel").forEach((p) => {
        p.style.display = p.id === `panel-${id}` ? "block" : "none";
      });
    });
  });

  if (!isAdmin) {
    document.getElementById("tab-branch")?.remove();
    document.getElementById("panel-branch")?.remove();
  }

  document.getElementById("btn-teacher-rpt").addEventListener("click", async () => {
    clearBanner(banner);
    const p = new URLSearchParams();
    if (isAdmin) {
      const tid = document.getElementById("r-teacher-id").value.trim();
      if (tid) p.set("teacher_id", tid);
    }
    const from = document.getElementById("r-ts-from").value;
    const to = document.getElementById("r-ts-to").value;
    if (from) p.set("date_from", from);
    if (to) p.set("date_to", to);
    try {
      const data = await request(`/reports/teacher-schedule/?${p.toString()}`);
      const pre = document.getElementById("out-teacher");
      pre.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      showBanner(banner, formatApiError(e));
    }
  });

  document.getElementById("btn-student-rpt").addEventListener("click", async () => {
    clearBanner(banner);
    const p = new URLSearchParams();
    p.set("student_id", document.getElementById("r-student-id").value.trim());
    const sid = document.getElementById("r-subject-id").value.trim();
    if (sid) p.set("subject_id", sid);
    const from = document.getElementById("r-sa-from").value;
    const to = document.getElementById("r-sa-to").value;
    if (from) p.set("date_from", from);
    if (to) p.set("date_to", to);
    try {
      const data = await request(`/reports/student-attendance/?${p.toString()}`);
      const pre = document.getElementById("out-student");
      pre.textContent = JSON.stringify(data, null, 2);
    } catch (e) {
      showBanner(banner, formatApiError(e));
    }
  });

  const btnBranch = document.getElementById("btn-branch-rpt");
  if (btnBranch) {
    btnBranch.addEventListener("click", async () => {
      clearBanner(banner);
      const p = new URLSearchParams();
      p.set("branch_id", document.getElementById("r-branch-id").value.trim());
      const from = document.getElementById("r-br-from").value;
      const to = document.getElementById("r-br-to").value;
      if (from) p.set("date_from", from);
      if (to) p.set("date_to", to);
      try {
        const data = await request(`/reports/branch-stats/?${p.toString()}`);
        const pre = document.getElementById("out-branch");
        pre.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    });
  }

  const tTeacher = document.getElementById("r-teacher-row");
  if (!isAdmin && tTeacher) tTeacher.style.display = "none";
}
