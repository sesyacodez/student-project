import { getUser, requireRole } from "../auth.js";
import { request, requestList } from "../http.js";
import { renderNav } from "../nav.js";
import { clearBanner, escapeHtml, formatApiError, showBanner } from "../ui.js";

renderNav();

if (!requireRole(["ADMIN"])) {
  /* redirected */
} else {
  void (async function main() {
    const banner = document.getElementById("banner");
    const form = document.getElementById("user-form");
    const resetButton = document.getElementById("user-reset");
    const reloadButton = document.getElementById("btn-reload-users");
    const tableBody = document.querySelector("#users-table tbody");

    const firstNameInput = document.getElementById("user-first-name");
    const lastNameInput = document.getElementById("user-last-name");
    const phoneInput = document.getElementById("user-phone");
    const roleSelect = document.getElementById("user-role");
    const branchSelect = document.getElementById("user-branch");
    const statusSelect = document.getElementById("user-status");
    const passwordInput = document.getElementById("user-password");
    const passwordConfirmInput = document.getElementById("user-password-confirm");

    let branches = [];
    let branchById = new Map();
    const currentUser = getUser();
    const defaultBranchId = currentUser?.branch_id ? String(currentUser.branch_id) : "";

    function populateBranches(items) {
      const options = items
        .map((branch) => {
          const city = branch.city ? ` (${branch.city})` : "";
          return `<option value="${branch.id}">${escapeHtml(`${branch.name}${city}`)}</option>`;
        })
        .join("");

      const placeholder = items.length ? "No branch" : "No branches";
      branchSelect.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
      if (defaultBranchId && branchById.has(defaultBranchId)) {
        branchSelect.value = defaultBranchId;
      }
    }

    function branchLabel(value) {
      if (!value) return "—";
      if (typeof value === "object") return value.name || "—";
      const found = branchById.get(String(value));
      return found ? found.name : String(value);
    }

    function resetForm() {
      form.reset();
      roleSelect.value = "TEACHER";
      statusSelect.value = "active";
      if (defaultBranchId && branchById.has(defaultBranchId)) {
        branchSelect.value = defaultBranchId;
      }
    }

    function buildPayload() {
      const payload = {
        phone: phoneInput.value.trim(),
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        role: roleSelect.value,
        password: passwordInput.value,
        is_active: statusSelect.value !== "inactive",
      };

      if (branchSelect.value) {
        payload.branch = branchSelect.value;
      }

      return payload;
    }

    function renderRow(user) {
      const fullName = `${user.first_name || ""} ${user.last_name || ""}`.trim() || "—";
      const role = user.role || "—";
      const phone = user.phone || "—";
      const status = user.is_active ? "Active" : "Inactive";
      const branch = branchLabel(user.branch);
      const isAdmin = user.role === "ADMIN";
      const toggleLabel = user.is_active ? "Deactivate" : "Activate";
      const toggleClass = user.is_active ? "app-btn app-btn--danger" : "app-btn app-btn--ghost";
      const actions = isAdmin
        ? '<span class="muted">Protected</span>'
        : `<button type="button" class="${toggleClass}" data-action="toggle" data-id="${user.id}" data-active="${user.is_active ? "1" : "0"}">${toggleLabel}</button>`;

      return `<tr>
        <td>${escapeHtml(fullName)}</td>
        <td>${escapeHtml(phone)}</td>
        <td>${escapeHtml(role)}</td>
        <td>${escapeHtml(branch)}</td>
        <td>${escapeHtml(status)}</td>
        <td>
          ${actions}
        </td>
      </tr>`;
    }

    async function loadBranches() {
      try {
        branches = await requestList("/branches/");
        branchById = new Map(branches.map((branch) => [String(branch.id), branch]));
        populateBranches(branches);
      } catch (error) {
        branchSelect.innerHTML = '<option value="">No branches</option>';
        showBanner(banner, formatApiError(error));
      }
    }

    async function loadUsers() {
      clearBanner(banner);
      try {
        const response = await request("/users/");
        const rows = Array.isArray(response?.results)
          ? response.results
          : Array.isArray(response)
            ? response
            : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="6" class="app-empty">No users found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='toggle']").forEach((button) => {
          button.addEventListener("click", () => {
            const id = button.getAttribute("data-id");
            const active = button.getAttribute("data-active") === "1";
            if (id) void toggleActive(id, active);
          });
        });
      } catch (error) {
        tableBody.innerHTML = "";
        showBanner(banner, formatApiError(error));
      }
    }

    async function toggleActive(id, isActive) {
      try {
        await request(`/users/${id}/`, {
          method: "PATCH",
          body: { is_active: !isActive },
        });
        showBanner(banner, isActive ? "User deactivated." : "User activated.", "success");
        await loadUsers();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);

      const payload = buildPayload();
      if (!payload.first_name || !payload.last_name || !payload.phone) {
        showBanner(banner, "First name, last name, and phone are required.");
        return;
      }

      if (!payload.password) {
        showBanner(banner, "Password is required.");
        return;
      }

      if (payload.password !== passwordConfirmInput.value) {
        showBanner(banner, "Passwords do not match.");
        return;
      }

      try {
        await request("/users/", {
          method: "POST",
          body: payload,
        });
        showBanner(banner, "User created.", "success");
        resetForm();
        await loadUsers();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => resetForm());
    reloadButton.addEventListener("click", () => void loadUsers());

    await loadBranches();
    resetForm();
    await loadUsers();
  })();
}
