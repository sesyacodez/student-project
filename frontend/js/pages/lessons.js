import { requireRole } from "../auth.js";
import { request, requestList, ApiError } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();
if (!requireRole(["ADMIN"])) {
  /* redirected */
} else {
void (async function main() {

const banner = document.getElementById("banner");
const tbody = document.querySelector("#lesson-table tbody");
const btnReload = document.getElementById("btn-reload");
const btnCreate = document.getElementById("btn-create");
const btnCheck = document.getElementById("btn-check-conflicts");
const form = document.getElementById("lesson-form");

const selSubject = document.getElementById("subject_id");
const selStudent = document.getElementById("student_id");
const selGroup = document.getElementById("group_id");
const selTeacher = document.getElementById("teacher_id");
const filterBranch = document.getElementById("filter-branch");
const filterTeacher = document.getElementById("filter-teacher");

function filterQuery() {
  const p = new URLSearchParams();
  const branchId = filterBranch.value;
  const teacherId = filterTeacher.value;
  const status = document.getElementById("filter-status").value.trim();
  const from = document.getElementById("filter-from").value;
  const to = document.getElementById("filter-to").value;
  if (branchId) p.set("branch_id", branchId);
  if (teacherId) p.set("teacher_id", teacherId);
  if (status) p.set("status", status);
  if (from) p.set("date_from", from);
  if (to) p.set("date_to", to);
  const s = p.toString();
  return s ? `?${s}` : "";
}

function teacherLabel(user) {
  const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
  return `${name || user.phone || "User"} (${user.role})`;
}

function populateSelect(select, items, placeholder, labelFn) {
  select.innerHTML =
    `<option value="">${escape(placeholder)}</option>` +
    items
      .map((item) => `<option value="${item.id}">${escape(labelFn(item))}</option>`)
      .join("");
}

function participantLabel(lesson) {
  if (lesson.student) {
    return `${lesson.student.first_name} ${lesson.student.last_name}`;
  }
  if (lesson.group) {
    return `Group: ${lesson.group.name}`;
  }
  return "—";
}

function renderRow(lesson) {
  const subj = lesson.subject ? lesson.subject.name : "—";
  const tchr = lesson.teacher
    ? `${lesson.teacher.first_name} ${lesson.teacher.last_name}`
    : "—";
  return `<tr>
    <td>${lesson.date}</td>
    <td>${lesson.start_time}–${lesson.end_time}</td>
    <td>${escape(subj)}</td>
    <td>${escape(tchr)}</td>
    <td>${escape(participantLabel(lesson))}</td>
    <td>${escape(lesson.status)}</td>
    <td>
      <a class="app-btn app-btn--ghost" href="lesson-detail.html?id=${lesson.id}">View</a>
      <a class="app-btn app-btn--ghost" href="attendance.html?lesson_id=${lesson.id}">Attendance</a>
      <button type="button" class="app-btn app-btn--danger" data-cancel="${lesson.id}">Cancel</button>
      <button type="button" class="app-btn app-btn--primary" data-complete="${lesson.id}">Complete</button>
    </td>
  </tr>`;
}

function escape(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/"/g, "&quot;");
}

async function loadDropdowns() {
  try {
    const [subjects, students, groups, branches, users] = await Promise.all([
      requestList("/subjects/"),
      requestList("/students/"),
      requestList("/groups/"),
      requestList("/branches/"),
      requestList("/users/"),
    ]);
    const teachers = users.filter(
      (user) => user.role === "TEACHER" || user.role === "ADMIN"
    );

    selSubject.innerHTML =
      '<option value="">— subject —</option>' +
      subjects
        .map(
          (s) =>
            `<option value="${s.id}">${escape(s.name)} (branch ${s.branch?.id ?? "?"})</option>`
        )
        .join("");

    selStudent.innerHTML =
      '<option value="">— none —</option>' +
      students
        .map(
          (s) =>
            `<option value="${s.id}">${escape(s.first_name)} ${escape(s.last_name)}</option>`
        )
        .join("");

    selGroup.innerHTML =
      '<option value="">— none —</option>' +
      groups
        .map((g) => `<option value="${g.id}">${escape(g.name)}</option>`)
        .join("");

    populateSelect(selTeacher, teachers, "— teacher —", teacherLabel);
    populateSelect(filterBranch, branches, "Any branch", (branch) => `${branch.name} (${branch.city})`);
    populateSelect(filterTeacher, teachers, "Any teacher", teacherLabel);
  } catch (e) {
    showBanner(banner, formatApiError(e));
  }
}

async function loadLessons() {
  clearBanner(banner);
  try {
    const fq = filterQuery();
    const path = fq ? `/lessons/${fq}` : `/lessons/`;
    const rows = await requestList(path);
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="app-empty">No lessons</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(renderRow).join("");
    tbody.querySelectorAll("[data-cancel]").forEach((btn) => {
      btn.addEventListener("click", () => cancelLesson(btn.getAttribute("data-cancel")));
    });
    tbody.querySelectorAll("[data-complete]").forEach((btn) => {
      btn.addEventListener("click", () =>
        completeLesson(btn.getAttribute("data-complete"))
      );
    });
  } catch (e) {
    showBanner(banner, formatApiError(e));
    tbody.innerHTML = "";
  }
}

async function cancelLesson(id) {
  clearBanner(banner);
  try {
    await request(`/lessons/${id}/cancel/`, { method: "POST" });
    await loadLessons();
  } catch (e) {
    showBanner(banner, formatApiError(e));
  }
}

async function completeLesson(id) {
  clearBanner(banner);
  try {
    await request(`/lessons/${id}/complete/`, { method: "POST" });
    await loadLessons();
  } catch (e) {
    showBanner(banner, formatApiError(e));
  }
}

function lessonPayload() {
  const teacherId = parseInt(selTeacher.value, 10);
  const subjectId = parseInt(selSubject.value, 10);
  const date = document.getElementById("date").value;
  const startTime = document.getElementById("start_time").value;
  const endTime = document.getElementById("end_time").value;
  const kind = document.querySelector('input[name="lesson_kind"]:checked')?.value;

  const body = {
    teacher_id: teacherId,
    subject_id: subjectId,
    date,
    start_time: startTime,
    end_time: endTime,
  };
  if (kind === "group") {
    body.group_id = parseInt(selGroup.value, 10);
    body.student_id = null;
  } else {
    body.student_id = parseInt(selStudent.value, 10);
    body.group_id = null;
  }
  return body;
}

btnReload.addEventListener("click", () => loadLessons());

btnCheck.addEventListener("click", async () => {
  clearBanner(banner);
  try {
    const body = lessonPayload();
    const res = await request("/lessons/conflicts/check/", {
      method: "POST",
      body,
    });
    const ids = res.conflict_lesson_ids || [];
    if (!ids.length) {
      showBanner(banner, "No conflicts for this slot.", "success");
    } else {
      showBanner(
        banner,
        `Conflicts with lesson id(s): ${ids.join(", ")}`,
        "error"
      );
    }
  } catch (e) {
    showBanner(banner, formatApiError(e));
  }
});

btnCreate.addEventListener("click", async () => {
  clearBanner(banner);
  try {
    const body = lessonPayload();
    await request("/lessons/", { method: "POST", body });
    showBanner(banner, "Lesson created.", "success");
    form.reset();
    await loadLessons();
  } catch (e) {
    if (e instanceof ApiError && e.status === 409) {
      showBanner(banner, formatApiError(e));
    } else {
      showBanner(banner, formatApiError(e));
    }
  }
});

document.querySelectorAll('input[name="lesson_kind"]').forEach((r) => {
  r.addEventListener("change", () => {
    const g = document.getElementById("row-group");
    const s = document.getElementById("row-student");
    if (r.value === "group") {
      g.style.display = "";
      s.style.display = "none";
    } else {
      g.style.display = "none";
      s.style.display = "";
    }
  });
});

await loadDropdowns();
await loadLessons();

})();
}
