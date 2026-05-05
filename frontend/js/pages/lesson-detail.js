import { getUser, requireRole } from "../auth.js";
import { request } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();

const params = new URLSearchParams(window.location.search);
const lessonId = params.get("id");
const banner = document.getElementById("banner");
const main = document.getElementById("lesson-detail");

if (!lessonId) {
  showBanner(banner, "Missing ?id= in URL");
} else if (!requireRole(["ADMIN", "TEACHER"])) {
  /* redirected */
} else {
  void (async function () {
    try {
      const lesson = await request(`/lessons/${lessonId}/`);
      const u = getUser();
      const uid = Number(u.id);
      if (
        u.role === "TEACHER" &&
        lesson.teacher &&
        Number.isFinite(uid) &&
        uid > 0 &&
        lesson.teacher.id !== uid
      ) {
        showBanner(banner, "You can only open your own lessons.");
        return;
      }

      const parts = [
        `<p><strong>Date</strong> ${lesson.date} ${lesson.start_time}–${lesson.end_time}</p>`,
        `<p><strong>Status</strong> ${lesson.status}</p>`,
        `<p><strong>Subject</strong> ${lesson.subject?.name ?? "—"}</p>`,
        `<p><strong>Teacher</strong> ${lesson.teacher ? `${lesson.teacher.first_name} ${lesson.teacher.last_name}` : "—"}</p>`,
      ];
      if (lesson.student) {
        parts.push(
          `<p><strong>Student</strong> ${lesson.student.first_name} ${lesson.student.last_name}</p>`
        );
      }
      if (lesson.group) {
        parts.push(`<p><strong>Group</strong> ${lesson.group.name}</p>`);
      }

      let actions = "";
      if (u.role === "ADMIN") {
        actions += `<button type="button" class="app-btn app-btn--danger" id="btn-cancel">Cancel lesson</button> `;
      }
      actions += `<button type="button" class="app-btn app-btn--primary" id="btn-complete">Mark complete</button> `;
      actions += `<a class="app-btn app-btn--ghost" href="attendance.html?lesson_id=${lesson.id}">Attendance</a>`;

      main.innerHTML = parts.join("") + `<p class="app-form__row">${actions}</p>`;

      document.getElementById("btn-cancel")?.addEventListener("click", async () => {
        clearBanner(banner);
        try {
          await request(`/lessons/${lessonId}/cancel/`, { method: "POST" });
          showBanner(banner, "Cancelled.", "success");
        } catch (e) {
          showBanner(banner, formatApiError(e));
        }
      });

      document.getElementById("btn-complete").addEventListener("click", async () => {
        clearBanner(banner);
        try {
          await request(`/lessons/${lessonId}/complete/`, { method: "POST" });
          showBanner(banner, "Marked complete.", "success");
        } catch (e) {
          showBanner(banner, formatApiError(e));
        }
      });
    } catch (e) {
      showBanner(banner, formatApiError(e));
    }
  })();
}
