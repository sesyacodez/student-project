import { requireRole } from "../auth.js";
import { requestList } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();
if (!requireRole(["TEACHER"])) {
  /* redirected */
} else {
  void (async function () {
    const banner = document.getElementById("banner");
    const tbody = document.querySelector("#schedule-table tbody");

    async function load() {
      clearBanner(banner);
      const p = new URLSearchParams();
      const from = document.getElementById("from").value;
      const to = document.getElementById("to").value;
      if (from) p.set("date_from", from);
      if (to) p.set("date_to", to);
      const q = p.toString();
      try {
        const path = q ? `/lessons/?${q}` : `/lessons/`;
        const rows = await requestList(path);
        if (!rows.length) {
          tbody.innerHTML = `<tr><td colspan="6" class="app-empty">No lessons</td></tr>`;
          return;
        }
        tbody.innerHTML = rows
          .map((lesson) => {
            const subj = lesson.subject ? lesson.subject.name : "—";
            let who = "—";
            if (lesson.student) {
              who = `${lesson.student.first_name} ${lesson.student.last_name}`;
            } else if (lesson.group) {
              who = `Group: ${lesson.group.name}`;
            }
            return `<tr>
            <td>${lesson.date}</td>
            <td>${lesson.start_time}–${lesson.end_time}</td>
            <td>${subj}</td>
            <td>${who}</td>
            <td>${lesson.status}</td>
            <td>
              <a class="app-btn app-btn--ghost" href="lesson-detail.html?id=${lesson.id}">Open</a>
              <a class="app-btn app-btn--primary" href="attendance.html?lesson_id=${lesson.id}">Attendance</a>
            </td>
          </tr>`;
          })
          .join("");
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

    document.getElementById("btn-load").addEventListener("click", load);
    await load();
  })();
}
