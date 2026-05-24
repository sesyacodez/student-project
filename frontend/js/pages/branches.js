import { requireRole } from "../auth.js";
import { request } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, escapeHtml, formatApiError, showBanner } from "../ui.js";

renderNav();

if (!requireRole(["ADMIN"])) {
  /* redirected */
} else {
  void (async function main() {
    const banner = document.getElementById("banner");
    const tableBody = document.querySelector("#branches-table tbody");
    const form = document.getElementById("branch-form");
    const formTitle = document.getElementById("branch-form-title");
    const saveButton = document.getElementById("branch-save");
    const resetButton = document.getElementById("branch-reset");
    const branchIdField = document.getElementById("branch-id");

    const nameInput = document.getElementById("branch-name");
    const cityInput = document.getElementById("branch-city");
    const addressInput = document.getElementById("branch-address");
    const statusSelect = document.getElementById("branch-status");

    const filterCity = document.getElementById("filter-branch-city");
    const filterStatus = document.getElementById("filter-branch-status");
    const filterSearch = document.getElementById("filter-branch-search");
    const btnReload = document.getElementById("btn-reload-branches");

    let editingId = null;

    function currentFilters() {
      const params = new URLSearchParams();
      if (filterCity.value.trim()) params.set("city", filterCity.value.trim());
      if (filterStatus.value) params.set("status", filterStatus.value);
      if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
      const query = params.toString();
      return query ? `?${query}` : "";
    }

    function resetForm() {
      editingId = null;
      form.reset();
      branchIdField.value = "";
      formTitle.textContent = "Create branch";
      saveButton.textContent = "Create branch";
      statusSelect.value = "active";
    }

    function fillForm(branch) {
      editingId = branch.id;
      branchIdField.value = branch.id;
      formTitle.textContent = `Edit branch #${branch.id}`;
      saveButton.textContent = "Save changes";
      nameInput.value = branch.name || "";
      cityInput.value = branch.city || "";
      addressInput.value = branch.address || "";
      statusSelect.value = branch.status || "active";
    }

    function buildPayload() {
      return {
        name: nameInput.value.trim(),
        city: cityInput.value.trim(),
        address: addressInput.value.trim(),
        status: statusSelect.value || "active",
      };
    }

    function renderRow(branch) {
      const archiveButton = branch.status === "archived"
        ? `<button type="button" class="app-btn app-btn--ghost" data-action="restore" data-id="${branch.id}">Restore</button>`
        : `<button type="button" class="app-btn app-btn--danger" data-action="archive" data-id="${branch.id}">Archive</button>`;

      return `<tr>
        <td>${escapeHtml(branch.name || "—")}</td>
        <td>${escapeHtml(branch.city || "—")}</td>
        <td>${escapeHtml(branch.address || "—")}</td>
        <td>${escapeHtml(branch.status || "—")}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${branch.id}">Edit</button>
          ${archiveButton}
        </td>
      </tr>`;
    }

    async function loadBranches() {
      clearBanner(banner);
      try {
        const response = await request(`/branches/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="5" class="app-empty">No branches found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const branch = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (branch) fillForm(branch);
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
        await request(`/branches/${id}/${action}/`, { method: "POST" });
        await loadBranches();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);
      const payload = buildPayload();

      if (!payload.name || !payload.city || !payload.address) {
        showBanner(banner, "Name, city, and address are required.");
        return;
      }

      try {
        if (editingId) {
          await request(`/branches/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Branch updated.", "success");
        } else {
          await request("/branches/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Branch created.", "success");
        }
        resetForm();
        await loadBranches();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => resetForm());
    btnReload.addEventListener("click", () => void loadBranches());

    resetForm();
    await loadBranches();
  })();
}
