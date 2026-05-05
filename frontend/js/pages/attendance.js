import { getUser, requireRole } from "../auth.js";
import { request, requestList } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();

const params = new URLSearchParams(window.location.search);
const lessonId = params.get("lesson_id");
const banner = document.getElementById("banner");
const container = document.getElementById("attendance-root");

if (!lessonId) {
  showBanner(banner, "Missing ?lesson_id=");
} else if (!requireRole(["ADMIN", "TEACHER"])) {
  /* redirected */
} else {
  void (async function () {
    let lesson;
    try {
      lesson = await request(`/lessons/${lessonId}/`);
    } catch (e) {
      showBanner(banner, formatApiError(e));
      return;
    }

    const u = getUser();
    const uid = Number(u.id);
    if (
      u.role === "TEACHER" &&
      lesson.teacher &&
      Number.isFinite(uid) &&
      uid > 0 &&
      lesson.teacher.id !== uid
    ) {
      showBanner(banner, "You can only edit attendance for your own lessons.");
      return;
    }

    if (lesson.status === "cancelled") {
      container.innerHTML =
        "<p class=\"muted\">This lesson is cancelled — attendance is closed.</p>";
      return;
    }

    /** @type {{ id: number, name: string }[]} */
    let participants = [];
    if (lesson.student) {
      participants.push({
        id: lesson.student.id,
        name: `${lesson.student.first_name} ${lesson.student.last_name}`,
      });
    } else if (lesson.group) {
      const gid = lesson.group.id;
      const memberships = await requestList(`/groups/${gid}/students/`);
      for (const m of memberships) {
        if (m.student) {
          participants.push({
            id: m.student.id,
            name: `${m.student.first_name} ${m.student.last_name}`,
          });
        }
      }
    }

    let existing = {};
    try {
      const rows = await request(`/lessons/${lessonId}/attendance/`);
      const list = Array.isArray(rows) ? rows : [];
      for (const r of list) {
        if (r.student) existing[r.student.id] = r;
      }
    } catch {
      existing = {};
    }

    const rowsHtml = participants
      .map((p) => {
        const cur = existing[p.id];
        const st = cur ? cur.status : "present";
        const note = cur && cur.note ? cur.note : "";
        return `<tr data-student-id="${p.id}">
        <td>${escape(p.name)}</td>
        <td>
          <select class="app-form__select att-status" data-id="${p.id}">
            <option value="present" ${st === "present" ? "selected" : ""}>present</option>
            <option value="absent" ${st === "absent" ? "selected" : ""}>absent</option>
          </select>
        </td>
        <td><input class="app-form__input att-note" data-id="${p.id}" type="text" value="${escapeAttr(note)}" placeholder="Note"></td>
      </tr>`;
      })
      .join("");

    container.innerHTML = `
      <p class="muted">Lesson ${lesson.date} — ${lesson.subject?.name ?? ""}</p>
      <div class="app-table-wrap">
        <table class="app-table" id="att-table">
          <thead><tr><th>Student</th><th>Status</th><th>Note</th></tr></thead>
          <tbody>${rowsHtml || '<tr><td colspan="3" class="app-empty">No participants</td></tr>'}</tbody>
        </table>
      </div>
      <p><button type="button" class="app-btn app-btn--primary" id="btn-save">Save attendance</button></p>
    `;

    document.getElementById("btn-save").addEventListener("click", async () => {
      clearBanner(banner);
      const records = participants.map((p) => {
        const status = container.querySelector(
          `.att-status[data-id="${p.id}"]`
        ).value;
        const note = container.querySelector(`.att-note[data-id="${p.id}"]`)
          .value;
        return { student_id: p.id, status, note };
      });
      try {
        await request(`/lessons/${lessonId}/attendance/`, {
          method: "PUT",
          body: { records },
        });
        showBanner(banner, "Saved.", "success");
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    });
  })();
}

function escape(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/"/g, "&quot;");
}

function escapeAttr(s) {
  return escape(s).replace(/'/g, "&#39;");
}
