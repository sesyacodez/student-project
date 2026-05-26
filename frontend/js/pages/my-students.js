import { requireRole } from "../auth.js";
import { requestAllPages } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, escapeHtml, formatApiError, showBanner } from "../ui.js";

renderNav();

if (!requireRole(["TEACHER"])) {
  /* redirected */
} else {
  void (async function () {
    const banner = document.getElementById("banner");
    const tbody = document.querySelector("#students-table tbody");

    function lessonQuery() {
      const p = new URLSearchParams();
      const from = document.getElementById("from").value;
      const to = document.getElementById("to").value;
      if (from) p.set("date_from", from);
      if (to) p.set("date_to", to);
      const q = p.toString();
      return q ? `/lessons/?${q}` : "/lessons/";
    }

    function renderRow(item) {
      return `<tr>
        <td>${escapeHtml(item.name)}</td>
        <td>${escapeHtml(item.branch || "—")}</td>
        <td>${escapeHtml(item.source)}</td>
      </tr>`;
    }

    async function load() {
      clearBanner(banner);
      try {
        const lessons = await requestAllPages(lessonQuery());
        if (!lessons.length) {
          tbody.innerHTML = '<tr><td colspan="3" class="app-empty">No lessons found.</td></tr>';
          return;
        }

        const students = new Map();
        const groupCache = new Map();

        for (const lesson of lessons) {
          if (lesson.student) {
            const key = `student-${lesson.student.id}`;
            if (!students.has(key)) {
              students.set(key, {
                name: `${lesson.student.first_name || ""} ${lesson.student.last_name || ""}`.trim(),
                branch: lesson.student.branch?.name || "—",
                source: "Individual",
              });
            }
          }

          if (lesson.group) {
            const gid = lesson.group.id;
            if (!groupCache.has(gid)) {
              const members = await requestAllPages(`/groups/${gid}/students/`);
              groupCache.set(gid, members);
            }
            const members = groupCache.get(gid) || [];
            for (const membership of members) {
              const student = membership.student;
              if (!student) continue;
              const key = `student-${student.id}`;
              if (!students.has(key)) {
                students.set(key, {
                  name: `${student.first_name || ""} ${student.last_name || ""}`.trim(),
                  branch: student.branch?.name || "—",
                  source: `Group: ${lesson.group.name}`,
                });
              }
            }
          }
        }

        const rows = Array.from(students.values());
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="3" class="app-empty">No students found.</td></tr>';
          return;
        }

        tbody.innerHTML = rows.map(renderRow).join("");
      } catch (e) {
        tbody.innerHTML = "";
        showBanner(banner, formatApiError(e));
      }
    }

    document.getElementById("btn-load").addEventListener("click", load);
    await load();
  })();
}
