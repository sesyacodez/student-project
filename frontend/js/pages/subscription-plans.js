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
    const tableBody = document.querySelector("#plans-table tbody");
    const form = document.getElementById("plan-form");
    const formTitle = document.getElementById("plan-form-title");
    const saveButton = document.getElementById("plan-save");
    const resetButton = document.getElementById("plan-reset");
    const planIdField = document.getElementById("plan-id");
    const nameInput = document.getElementById("plan-name");
    const branchSelect = document.getElementById("plan-branch");
    const typeSelect = document.getElementById("plan-type");
    const statusSelect = document.getElementById("plan-status");
    const subjectSelect = document.getElementById("plan-subjects");
    const tierRows = document.getElementById("plan-tier-rows");
    const btnAddTier = document.getElementById("btn-add-tier-row");
    const btnReload = document.getElementById("btn-reload-plans");
    const filterBranch = document.getElementById("filter-plan-branch");
    const filterType = document.getElementById("filter-plan-type");
    const filterStatus = document.getElementById("filter-plan-status");
    const filterSearch = document.getElementById("filter-plan-search");

    let editingId = null;
    let allSubjects = [];

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
      if (filterType.value) params.set("type", filterType.value);
      if (filterStatus.value) params.set("status", filterStatus.value);
      if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
      const query = params.toString();
      return query ? `?${query}` : "";
    }

    function resetForm() {
      editingId = null;
      form.reset();
      planIdField.value = "";
      formTitle.textContent = "Create plan";
      saveButton.textContent = "Create plan";
      branchSelect.disabled = false;
      statusSelect.value = "active";
      tierRows.innerHTML = "";
      addTierRow();
      addTierRow();
      renderSubjectOptions();
    }

    function addTierRow(values = {}) {
      const row = document.createElement("div");
      row.className = "app-form__row app-form__row--inline plan-tier-row";
      row.innerHTML = `
        <label class="app-form__label">
          Lessons / month
          <input class="app-form__input plan-tier-lessons" type="number" min="1" value="${values.lessons_per_month || ""}" />
        </label>
        <label class="app-form__label">
          Price / lesson
          <input class="app-form__input plan-tier-price" type="number" min="0" step="0.01" value="${values.price_per_lesson || ""}" />
        </label>
        <button type="button" class="app-btn app-btn--ghost plan-tier-remove">Remove</button>
      `;
      row.querySelector(".plan-tier-remove").addEventListener("click", () => row.remove());
      tierRows.appendChild(row);
    }

    function renderSubjectOptions(selectedIds = []) {
      const branchId = branchSelect.value;
      const subjects = branchId
        ? allSubjects.filter((subject) => String(subject.branch?.id || "") === String(branchId))
        : [];
      const options = subjects.map((subject) => {
        const selected = selectedIds.includes(String(subject.id)) ? " selected" : "";
        return `<option value="${subject.id}"${selected}>${escapeHtml(subject.name)} (${escapeHtml(subject.branch?.name || "—")})</option>`;
      }).join("");
      subjectSelect.innerHTML = branchId
        ? options || '<option value="">No subjects for this branch</option>'
        : '<option value="">Choose a branch first</option>';
    }

    function getSelectedSubjectIds() {
      return Array.from(subjectSelect.selectedOptions).map((option) => option.value);
    }

    function getTierPayload() {
      const rows = Array.from(tierRows.querySelectorAll(".plan-tier-row"));
      const tiers = [];

      for (const row of rows) {
        const lessonsValue = row.querySelector(".plan-tier-lessons").value.trim();
        const priceValue = row.querySelector(".plan-tier-price").value.trim();
        if (!lessonsValue && !priceValue) {
          continue;
        }
        if (!lessonsValue || !priceValue) {
          throw new Error("Fill or remove incomplete pricing tier rows.");
        }
        tiers.push({
          lessons_per_month: Number(lessonsValue),
          price_per_lesson: priceValue,
        });
      }

      return tiers;
    }

    function fillForm(plan) {
      editingId = plan.id;
      planIdField.value = plan.id;
      formTitle.textContent = `Edit plan #${plan.id}`;
      saveButton.textContent = "Save changes";
      nameInput.value = plan.name || "";
      branchSelect.value = plan.branch?.id ? String(plan.branch.id) : "";
      branchSelect.disabled = true;
      typeSelect.value = plan.type || "individual";
      statusSelect.value = plan.status || "active";
      renderSubjectOptions((plan.subjects || []).map((subject) => String(subject.id)));
      const subjectIds = (plan.subjects || []).map((subject) => String(subject.id));
      Array.from(subjectSelect.options).forEach((option) => {
        option.selected = subjectIds.includes(option.value);
      });
      tierRows.innerHTML = "";
      (plan.pricing_tiers || []).forEach((tier) => addTierRow(tier));
      if (!plan.pricing_tiers || !plan.pricing_tiers.length) {
        addTierRow();
      }
    }

    function renderRow(plan) {
      const subjects = Array.isArray(plan.subjects) && plan.subjects.length
        ? plan.subjects.map((subject) => subject.name).join(", ")
        : "—";
      const tiers = Array.isArray(plan.pricing_tiers) ? plan.pricing_tiers.length : 0;
      const archiveButton = plan.status === "archived"
        ? `<button type="button" class="app-btn app-btn--ghost" data-action="restore" data-id="${plan.id}">Restore</button>`
        : `<button type="button" class="app-btn app-btn--danger" data-action="archive" data-id="${plan.id}">Archive</button>`;

      return `<tr>
        <td>${escapeHtml(plan.name || "—")}</td>
        <td>${escapeHtml(plan.branch?.name || "—")}</td>
        <td>${escapeHtml(plan.type || "—")}</td>
        <td>${escapeHtml(plan.status || "—")}</td>
        <td>${escapeHtml(subjects)}</td>
        <td>${escapeHtml(String(tiers))}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${plan.id}">Edit</button>
          ${archiveButton}
        </td>
      </tr>`;
    }

    async function loadOptions() {
      try {
        const [branches, subjects] = await Promise.all([
          requestList("/branches/"),
          requestList("/subjects/"),
        ]);
        allSubjects = subjects;
        populateSelect(branchSelect, branches, "Choose branch", (branch) => `${branch.name} (${branch.city})`);
        populateSelect(filterBranch, branches, "All branches", (branch) => `${branch.name} (${branch.city})`);
        renderSubjectOptions();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    async function loadPlans() {
      clearBanner(banner);
      try {
        const response = await request(`/subscription-plans/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="7" class="app-empty">No subscription plans found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const plan = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (plan) fillForm(plan);
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
        await request(`/subscription-plans/${id}/${action}/`, { method: "POST" });
        await loadPlans();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    branchSelect.addEventListener("change", () => {
      if (!editingId) {
        renderSubjectOptions();
      }
    });

    btnAddTier.addEventListener("click", () => addTierRow());

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);

      let pricingTiers;
      try {
        pricingTiers = getTierPayload();
      } catch (error) {
        showBanner(banner, error.message);
        return;
      }

      const payload = {
        name: nameInput.value.trim(),
        type: typeSelect.value,
        status: statusSelect.value || "active",
        subject_ids: getSelectedSubjectIds(),
        pricing_tiers: pricingTiers,
      };

      if (!editingId) {
        payload.branch_id = branchSelect.value;
      }

      if (!editingId && !payload.branch_id) {
        showBanner(banner, "Choose a branch before creating the plan.");
        return;
      }

      try {
        if (editingId) {
          delete payload.branch_id;
          await request(`/subscription-plans/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Plan updated.", "success");
        } else {
          await request("/subscription-plans/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Plan created.", "success");
        }
        resetForm();
        await loadPlans();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => resetForm());
    btnReload.addEventListener("click", () => void loadPlans());
    statusSelect.value = "active";
    addTierRow();
    addTierRow();

    await loadOptions();
    await loadPlans();
  })();
}