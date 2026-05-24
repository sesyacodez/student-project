import { requireRole } from "../auth.js";
import { request, requestList } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, formatApiError, showBanner } from "../ui.js";

renderNav();
if (!requireRole(["ADMIN"])) {
  /* redirected */
} else {
  void (async function main() {
    const banner = document.getElementById("banner");
    const tbody = document.querySelector("#tpl-table tbody");
    const selSubject = document.getElementById("subject_id");
    const selStudent = document.getElementById("student_id");
    const selGroup = document.getElementById("group_id");
    const selTeacher = document.getElementById("teacher_id");

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

    function escape(s) {
      return String(s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/"/g, "&quot;");
    }

    async function loadDropdowns() {
      try {
        const [subjects, students, groups, users] = await Promise.all([
          requestList("/subjects/"),
          requestList("/students/"),
          requestList("/groups/"),
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
                `<option value="${s.id}">${escape(s.name)}</option>`
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
          groups.map((g) => `<option value="${g.id}">${escape(g.name)}</option>`).join("");
        populateSelect(selTeacher, teachers, "— teacher —", teacherLabel);
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

    function selectedWeekdays() {
      const boxes = document.querySelectorAll(".dow:checked");
      return Array.from(boxes).map((c) => parseInt(c.value, 10));
    }

    function templatePayload() {
      const kind = document.querySelector('input[name="tpl_kind"]:checked')?.value;
      const body = {
        teacher_id: parseInt(selTeacher.value, 10),
        subject_id: parseInt(selSubject.value, 10),
        days_of_week: selectedWeekdays(),
        start_time: document.getElementById("start_time").value,
        end_time: document.getElementById("end_time").value,
        start_date: document.getElementById("start_date").value,
        end_date: document.getElementById("end_date").value,
        is_active: document.getElementById("is_active").checked,
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

    async function loadTable() {
      clearBanner(banner);
      try {
        const rows = await requestList("/lesson-templates/");
        if (!rows.length) {
          tbody.innerHTML = `<tr><td colspan="5" class="app-empty">No templates</td></tr>`;
          return;
        }
        tbody.innerHTML = rows
          .map(
            (t) => `<tr>
          <td>${t.id}</td>
          <td>${escape(t.name)}</td>
          <td>${t.start_date} → ${t.end_date}</td>
          <td>${t.is_active ? "yes" : "no"}</td>
          <td>
            <button type="button" class="app-btn app-btn--primary" data-gen="${t.id}">Generate</button>
            <button type="button" class="app-btn app-btn--ghost" data-off="${t.id}">Deactivate</button>
          </td>
        </tr>`
          )
          .join("");
        tbody.querySelectorAll("[data-gen]").forEach((btn) =>
          btn.addEventListener("click", () => generate(btn.getAttribute("data-gen")))
        );
        tbody.querySelectorAll("[data-off]").forEach((btn) =>
          btn.addEventListener("click", () => deactivate(btn.getAttribute("data-off")))
        );
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

    async function generate(id) {
      clearBanner(banner);
      try {
        const res = await request(`/lesson-templates/${id}/generate/`, {
          method: "POST",
        });
        const out = document.getElementById("gen-output");
        out.textContent = JSON.stringify(res, null, 2);
        await loadTable();
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

    async function deactivate(id) {
      clearBanner(banner);
      try {
        await request(`/lesson-templates/${id}/deactivate/`, { method: "POST" });
        await loadTable();
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    }

    document.getElementById("btn-create").addEventListener("click", async () => {
      clearBanner(banner);
      try {
        await request("/lesson-templates/", {
          method: "POST",
          body: templatePayload(),
        });
        showBanner(banner, "Template created.", "success");
        await loadTable();
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    });

    document.getElementById("btn-preview").addEventListener("click", async () => {
      clearBanner(banner);
      try {
        const res = await request("/lesson-templates/preview-conflicts/", {
          method: "POST",
          body: templatePayload(),
        });
        document.getElementById("gen-output").textContent = JSON.stringify(
          res,
          null,
          2
        );
      } catch (e) {
        showBanner(banner, formatApiError(e));
      }
    });

    document.querySelectorAll('input[name="tpl_kind"]').forEach((r) => {
      r.addEventListener("change", () => {
        const g = document.getElementById("row-tpl-group");
        const s = document.getElementById("row-tpl-student");
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
    await loadTable();
  })();
}
