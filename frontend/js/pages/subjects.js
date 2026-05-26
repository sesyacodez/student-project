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
    const tableBody = document.querySelector("#subjects-table tbody");
    const form = document.getElementById("subject-form");
    const formTitle = document.getElementById("subject-form-title");
    const saveButton = document.getElementById("subject-save");
    const resetButton = document.getElementById("subject-reset");
    const subjectIdField = document.getElementById("subject-id");
    const nameInput = document.getElementById("subject-name");
    const branchSelect = document.getElementById("subject-branch");
    const statusSelect = document.getElementById("subject-status");
    const filterBranch = document.getElementById("filter-subject-branch");
    const filterStatus = document.getElementById("filter-subject-status");
    const filterSearch = document.getElementById("filter-subject-search");
    const btnReload = document.getElementById("btn-reload-subjects");

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

    function currentFilters() {
      const params = new URLSearchParams();
      if (filterBranch.value) params.set("branch_id", filterBranch.value);
      if (filterStatus.value) params.set("status", filterStatus.value);
      if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
      const query = params.toString();
      return query ? `?${query}` : "";
    }

    function resetForm() {
      editingId = null;
      form.reset();
      subjectIdField.value = "";
      formTitle.textContent = "Create subject";
      saveButton.textContent = "Create subject";
      branchSelect.disabled = false;
      statusSelect.value = "active";
    }

    function fillForm(subject) {
      editingId = subject.id;
      subjectIdField.value = subject.id;
      formTitle.textContent = `Edit subject #${subject.id}`;
      saveButton.textContent = "Save changes";
      nameInput.value = subject.name || "";
      statusSelect.value = subject.status || "active";
      branchSelect.value = subject.branch?.id ? String(subject.branch.id) : "";
      branchSelect.disabled = true;
    }

    function buildPayload() {
      const payload = {
        name: nameInput.value.trim(),
        status: statusSelect.value || "active",
      };
      if (!editingId) {
        payload.branch_id = branchSelect.value;
      }
      return payload;
    }

    function renderRow(subject) {
      const archiveButton = subject.status === "archived"
        ? `<button type="button" class="app-btn app-btn--ghost" data-action="restore" data-id="${subject.id}">Restore</button>`
        : `<button type="button" class="app-btn app-btn--danger" data-action="archive" data-id="${subject.id}">Archive</button>`;

      return `<tr>
        <td>${escapeHtml(subject.name || "—")}</td>
        <td>${escapeHtml(subject.branch?.name || "—")}</td>
        <td>${escapeHtml(subject.status || "—")}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${subject.id}">Edit</button>
          ${archiveButton}
        </td>
      </tr>`;
    }

    async function loadOptions() {
      const branches = await requestList("/branches/");
      populateSelect(branchSelect, branches, "Choose branch", (branch) => `${branch.name} (${branch.city})`);
      populateSelect(filterBranch, branches, "All branches", (branch) => `${branch.name} (${branch.city})`);
    }

    async function loadSubjects() {
      clearBanner(banner);
      try {
        const response = await request(`/subjects/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="4" class="app-empty">No subjects found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const subject = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (subject) fillForm(subject);
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
        await request(`/subjects/${id}/${action}/`, { method: "POST" });
        await loadSubjects();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);
      const payload = buildPayload();

      if (!editingId && !payload.branch_id) {
        showBanner(banner, "Choose a branch before creating the subject.");
        return;
      }

      try {
        if (editingId) {
          delete payload.branch_id;
          await request(`/subjects/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Subject updated.", "success");
        } else {
          await request("/subjects/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Subject created.", "success");
        }

        resetForm();
        await loadSubjects();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => {
      resetForm();
    });

    btnReload.addEventListener("click", () => void loadSubjects());

    await loadOptions();
    await loadSubjects();
    statusSelect.value = "active";
  })();
}
