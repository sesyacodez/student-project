import { requireRole } from "../auth.js";
import { request, requestList } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, escapeHtml, formatApiError, showBanner } from "../ui.js";

renderNav();

if (!requireRole(["ADMIN"])) {
  /* redirected */
} else {
  void (async function main() {
    const banner = document.getElementById("banner");
    const tableBody = document.querySelector("#students-table tbody");
    const form = document.getElementById("student-form");
    const formTitle = document.getElementById("student-form-title");
    const saveButton = document.getElementById("student-save");
    const resetButton = document.getElementById("student-reset");
    const studentIdField = document.getElementById("student-id");
    const branchSelect = document.getElementById("student-branch");
    const statusSelect = document.getElementById("student-status");
    const filterBranch = document.getElementById("filter-student-branch");
    const filterGroup = document.getElementById("filter-student-group");
    const filterStatus = document.getElementById("filter-student-status");
    const filterSearch = document.getElementById("filter-student-search");

    const firstName = document.getElementById("student-first-name");
    const lastName = document.getElementById("student-last-name");
    const dateOfBirth = document.getElementById("student-date-of-birth");
    const phone = document.getElementById("student-phone");
    const email = document.getElementById("student-email");
    const address = document.getElementById("student-address");
    const parentName = document.getElementById("student-parent-name");
    const parentPhone = document.getElementById("student-parent-phone");
    const parentEmail = document.getElementById("student-parent-email");
    const parentRelation = document.getElementById("student-parent-relation");
    const btnReload = document.getElementById("btn-reload-students");

    let editingId = null;

    function populateSelect(select, items, placeholder, labelFn, selectedValue = "") {
      const options = items
        .map((item) => `<option value="${item.id}">${escapeHtml(labelFn(item))}</option>`)
        .join("");
      select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
      if (selectedValue !== "") {
        select.value = String(selectedValue);
      }
    }

    function optionalText(input) {
      const value = input.value.trim();
      return value || "";
    }

    function optionalDate(input) {
      const value = input.value.trim();
      return value || null;
    }

    function currentFilters() {
      const params = new URLSearchParams();
      if (filterBranch.value) params.set("branch_id", filterBranch.value);
      if (filterGroup.value) params.set("group_id", filterGroup.value);
      if (filterStatus.value) params.set("status", filterStatus.value);
      if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
      const query = params.toString();
      return query ? `?${query}` : "";
    }

    function resetForm() {
      editingId = null;
      form.reset();
      studentIdField.value = "";
      formTitle.textContent = "Create student";
      saveButton.textContent = "Create student";
      branchSelect.disabled = false;
      statusSelect.value = "active";
    }

    function fillForm(student) {
      editingId = student.id;
      studentIdField.value = student.id;
      formTitle.textContent = `Edit student #${student.id}`;
      saveButton.textContent = "Save changes";
      firstName.value = student.first_name || "";
      lastName.value = student.last_name || "";
      dateOfBirth.value = student.date_of_birth || "";
      phone.value = student.phone || "";
      email.value = student.email || "";
      address.value = student.address || "";
      parentName.value = student.parent_name || "";
      parentPhone.value = student.parent_phone || "";
      parentEmail.value = student.parent_email || "";
      parentRelation.value = student.parent_relation || "";
      statusSelect.value = student.status || "active";
      branchSelect.value = student.branch?.id ? String(student.branch.id) : "";
      branchSelect.disabled = true;
    }

    function buildPayload() {
      const payload = {
        first_name: firstName.value.trim(),
        last_name: lastName.value.trim(),
        date_of_birth: optionalDate(dateOfBirth),
        phone: optionalText(phone),
        email: optionalText(email),
        address: optionalText(address),
        parent_name: optionalText(parentName),
        parent_phone: optionalText(parentPhone),
        parent_email: optionalText(parentEmail),
        parent_relation: parentRelation.value,
        status: statusSelect.value || "active",
      };

      if (!editingId) {
        payload.branch_id = branchSelect.value;
      }

      return payload;
    }

    function renderRow(student) {
      const groups = Array.isArray(student.group_ids) && student.group_ids.length
        ? student.group_ids.join(", ")
        : "—";
      const parent = student.parent_name
        ? `${student.parent_name}${student.parent_relation ? ` (${student.parent_relation})` : ""}`
        : "—";
      const archiveButton = student.status === "archived"
        ? `<button type="button" class="app-btn app-btn--ghost" data-action="restore" data-id="${student.id}">Restore</button>`
        : `<button type="button" class="app-btn app-btn--danger" data-action="archive" data-id="${student.id}">Archive</button>`;

      return `<tr>
        <td>${escapeHtml(`${student.first_name || ""} ${student.last_name || ""}`.trim())}</td>
        <td>${escapeHtml(student.branch?.name || "—")}</td>
        <td>${escapeHtml(student.status || "—")}</td>
        <td>${escapeHtml(groups)}</td>
        <td>${escapeHtml(parent)}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${student.id}">Edit</button>
          ${archiveButton}
        </td>
      </tr>`;
    }

    async function loadOptions() {
      const [branches, groups] = await Promise.all([
        requestList("/branches/"),
        requestList("/groups/"),
      ]);
      populateSelect(branchSelect, branches, "Choose branch", (branch) => `${branch.name} (${branch.city})`);
      populateSelect(filterBranch, branches, "All branches", (branch) => `${branch.name} (${branch.city})`);
      populateSelect(filterGroup, groups, "All groups", (group) => `${group.name} (#${group.id})`);
    }

    async function loadStudents() {
      clearBanner(banner);
      try {
        const response = await request(`/students/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="6" class="app-empty">No students found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const student = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (student) fillForm(student);
          });
        });
        tableBody.querySelectorAll("[data-action='archive']").forEach((button) => {
          button.addEventListener("click", () => void toggleStatus(button.getAttribute("data-id"), "archive"));
        });
        tableBody.querySelectorAll("[data-action='restore']").forEach((button) => {
          button.addEventListener("click", () => void toggleStatus(button.getAttribute("data-id"), "restore"));
        });
      } catch (error) {
        tableBody.innerHTML = "";
        showBanner(banner, formatApiError(error));
      }
    }

    async function toggleStatus(id, action) {
      try {
        await request(`/students/${id}/${action}/`, { method: "POST" });
        await loadStudents();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);
      const payload = buildPayload();

      if (!editingId && !payload.branch_id) {
        showBanner(banner, "Choose a branch before creating the student.");
        return;
      }

      try {
        if (editingId) {
          delete payload.branch_id;
          await request(`/students/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Student updated.", "success");
        } else {
          await request("/students/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Student created.", "success");
        }

        resetForm();
        await loadStudents();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => {
      resetForm();
    });

    btnReload.addEventListener("click", () => void loadStudents());

    await loadOptions();
    await loadStudents();
    statusSelect.value = "active";
  })();
}