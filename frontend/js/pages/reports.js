import { getUser, requireRole } from "../auth.js";
import { request, requestAllPages } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, escapeHtml, formatApiError, showBanner } from "../ui.js";

renderNav();
if (!requireRole(["ADMIN", "TEACHER"])) {
  /* redirected */
} else {
  void (async function () {
    const user = getUser();
    const banner = document.getElementById("banner");
    const isAdmin = user.role === "ADMIN";

    const selTeacher = document.getElementById("r-teacher-id");
    const selStudent = document.getElementById("r-student-id");
    const selSubject = document.getElementById("r-subject-id");
    const selBranch = document.getElementById("r-branch-id");

    function populateSelect(select, items, placeholder, labelFn) {
      select.innerHTML =
        `<option value="">${escapeHtml(placeholder)}</option>` +
        items
          .map(
            (item) =>
              `<option value="${item.id}">${escapeHtml(labelFn(item))}</option>`
          )
          .join("");
    }

    function teacherLabel(teacher) {
      const name = `${teacher.first_name || ""} ${teacher.last_name || ""}`.trim();
      return `${name || teacher.phone || "User"} (${teacher.role})`;
    }

    function addStudent(students, student) {
      if (!student) return;
      students.set(String(student.id), student);
    }

    function addSubject(subjects, subject) {
      if (!subject) return;
      subjects.set(String(subject.id), subject);
    }

    async function teacherReportOptions() {
      const lessons = await requestAllPages("/lessons/");
      const students = new Map();
      const subjects = new Map();
      const groupCache = new Map();

      for (const lesson of lessons) {
        addSubject(subjects, lesson.subject);
        addStudent(students, lesson.student);

        if (lesson.group) {
          const gid = lesson.group.id;
          if (!groupCache.has(gid)) {
            groupCache.set(gid, await requestAllPages(`/groups/${gid}/students/`));
          }
          for (const membership of groupCache.get(gid) || []) {
            addStudent(students, membership.student);
          }
        }
      }

      return {
        students: Array.from(students.values()),
        subjects: Array.from(subjects.values()),
      };
    }

    async function loadDropdowns() {
      clearBanner(banner);
      try {
        let students = [];
        let subjects = [];

        if (isAdmin) {
          const [adminStudents, adminSubjects, users, branches] = await Promise.all([
            requestAllPages("/students/"),
            requestAllPages("/subjects/"),
            requestAllPages("/users/"),
            requestAllPages("/branches/"),
          ]);
          students = adminStudents;
          subjects = adminSubjects;
          const teachers = users.filter(
            (u) => u.role === "TEACHER" || u.role === "ADMIN"
          );

          populateSelect(selTeacher, teachers, "Select teacher", teacherLabel);
          populateSelect(
            selBranch,
            branches,
            "Select branch",
            (branch) => `${branch.name} (${branch.city})`
          );
        } else {
          const options = await teacherReportOptions();
          students = options.students;
          subjects = options.subjects;
        }

        populateSelect(
          selStudent,
          students,
          "Select student",
          (student) => `${student.first_name} ${student.last_name}`
        );
        populateSelect(selSubject, subjects, "All subjects", (subject) => subject.name);

      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

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
        const tid = selTeacher.value.trim();
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
      const studentId = selStudent.value.trim();
      if (!studentId) {
        showBanner(banner, "Please select a student.");
        return;
      }
      const p = new URLSearchParams();
      p.set("student_id", studentId);
      const sid = selSubject.value.trim();
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
        const branchId = selBranch.value.trim();
        if (!branchId) {
          showBanner(banner, "Please select a branch.");
          return;
        }
        const p = new URLSearchParams();
        p.set("branch_id", branchId);
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

    await loadDropdowns();
  })();
}
