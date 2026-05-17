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
    const groupsBody = document.querySelector("#groups-table tbody");
    const membersBody = document.querySelector("#members-table tbody");
    const form = document.getElementById("group-form");
    const formTitle = document.getElementById("group-form-title");
    const saveButton = document.getElementById("group-save");
    const resetButton = document.getElementById("group-reset");
    const groupIdField = document.getElementById("group-id");
    const nameInput = document.getElementById("group-name");
    const branchSelect = document.getElementById("group-branch");
    const statusSelect = document.getElementById("group-status");
    const filterBranch = document.getElementById("filter-group-branch");
    const filterStatus = document.getElementById("filter-group-status");
    const filterSearch = document.getElementById("filter-group-search");
    const memberGroupSelect = document.getElementById("member-group-id");
    const memberStudentSelect = document.getElementById("member-student-id");
    const memberJoinDate = document.getElementById("member-join-date");
    const btnReloadGroups = document.getElementById("btn-reload-groups");
    const btnLoadMembers = document.getElementById("btn-load-members");
    const btnAddMember = document.getElementById("btn-add-member");

    let editingId = null;
    let currentMemberGroupId = "";

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
      groupIdField.value = "";
      formTitle.textContent = "Create group";
      saveButton.textContent = "Create group";
      branchSelect.disabled = false;
      statusSelect.value = "active";
    }

    function fillForm(group) {
      editingId = group.id;
      groupIdField.value = group.id;
      formTitle.textContent = `Edit group #${group.id}`;
      saveButton.textContent = "Save changes";
      nameInput.value = group.name || "";
      branchSelect.value = group.branch?.id ? String(group.branch.id) : "";
      branchSelect.disabled = true;
      statusSelect.value = group.status || "active";
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

    function renderGroupRow(group) {
      const studentCount = Array.isArray(group.student_ids) ? group.student_ids.length : 0;
      const archiveButton = group.status === "archived"
        ? `<button type="button" class="app-btn app-btn--ghost" data-action="restore" data-id="${group.id}">Restore</button>`
        : `<button type="button" class="app-btn app-btn--danger" data-action="archive" data-id="${group.id}">Archive</button>`;

      return `<tr>
        <td>${escapeHtml(group.name || "—")}</td>
        <td>${escapeHtml(group.branch?.name || "—")}</td>
        <td>${escapeHtml(group.status || "—")}</td>
        <td>${escapeHtml(String(studentCount))}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${group.id}">Edit</button>
          <button type="button" class="app-btn app-btn--ghost" data-action="members" data-id="${group.id}">Members</button>
          ${archiveButton}
        </td>
      </tr>`;
    }

    function renderMemberRow(record) {
      const student = record.student;
      const studentLabel = student ? `${student.first_name || ""} ${student.last_name || ""}`.trim() : "—";
      return `<tr>
        <td>${escapeHtml(studentLabel)}</td>
        <td>${escapeHtml(student?.branch?.name || "—")}</td>
        <td>${escapeHtml(record.join_date || "—")}</td>
        <td>
          <button type="button" class="app-btn app-btn--danger" data-remove-member="${student?.id || ""}">Remove</button>
        </td>
      </tr>`;
    }

    async function loadOptions() {
      const [branches, students, groups] = await Promise.all([
        requestList("/branches/"),
        requestList("/students/"),
        requestList("/groups/"),
      ]);
      populateSelect(branchSelect, branches, "Choose branch", (branch) => `${branch.name} (${branch.city})`);
      populateSelect(filterBranch, branches, "All branches", (branch) => `${branch.name} (${branch.city})`);
      populateSelect(memberGroupSelect, groups, "Choose group", (group) => `${group.name} (#${group.id})`);
      populateSelect(memberStudentSelect, students, "Choose student", (student) => `${student.first_name} ${student.last_name} (#${student.id})`);
    }

    async function loadGroups() {
      clearBanner(banner);
      try {
        const response = await request(`/groups/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          groupsBody.innerHTML = '<tr><td colspan="5" class="app-empty">No groups found.</td></tr>';
          return;
        }

        groupsBody.innerHTML = rows.map(renderGroupRow).join("");
        groupsBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const group = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (group) fillForm(group);
          });
        });
        groupsBody.querySelectorAll("[data-action='members']").forEach((button) => {
          button.addEventListener("click", () => {
            const groupId = button.getAttribute("data-id");
            memberGroupSelect.value = groupId;
            currentMemberGroupId = groupId;
            void loadMembers();
          });
        });
        groupsBody.querySelectorAll("[data-action='archive']").forEach((button) => {
          button.addEventListener("click", () => void toggleStatus(button.getAttribute("data-id"), "archive"));
        });
        groupsBody.querySelectorAll("[data-action='restore']").forEach((button) => {
          button.addEventListener("click", () => void toggleStatus(button.getAttribute("data-id"), "restore"));
        });
      } catch (error) {
        groupsBody.innerHTML = "";
        showBanner(banner, formatApiError(error));
      }
    }

    async function toggleStatus(id, action) {
      try {
        await request(`/groups/${id}/${action}/`, { method: "POST" });
        await loadGroups();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    async function loadMembers() {
      const groupId = memberGroupSelect.value || currentMemberGroupId;
      currentMemberGroupId = groupId;
      if (!groupId) {
        membersBody.innerHTML = '<tr><td colspan="4" class="app-empty">Choose a group to see members.</td></tr>';
        return;
      }

      try {
        const members = await requestList(`/groups/${groupId}/students/`);
        if (!members.length) {
          membersBody.innerHTML = '<tr><td colspan="4" class="app-empty">This group has no active members.</td></tr>';
          return;
        }

        membersBody.innerHTML = members.map(renderMemberRow).join("");
        membersBody.querySelectorAll("[data-remove-member]").forEach((button) => {
          button.addEventListener("click", () => {
            const studentId = button.getAttribute("data-remove-member");
            if (studentId) void removeMember(groupId, studentId);
          });
        });
      } catch (error) {
        membersBody.innerHTML = "";
        showBanner(banner, formatApiError(error));
      }
    }

    async function removeMember(groupId, studentId) {
      try {
        await request(`/groups/${groupId}/students/${studentId}/`, { method: "DELETE" });
        await loadMembers();
        await loadGroups();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);
      const payload = buildPayload();

      if (!editingId && !payload.branch_id) {
        showBanner(banner, "Choose a branch before creating the group.");
        return;
      }

      try {
        if (editingId) {
          delete payload.branch_id;
          await request(`/groups/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Group updated.", "success");
        } else {
          await request("/groups/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Group created.", "success");
        }
        resetForm();
        await loadGroups();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => {
      resetForm();
    });

    btnReloadGroups.addEventListener("click", () => void loadGroups());
    btnLoadMembers.addEventListener("click", () => void loadMembers());
    btnAddMember.addEventListener("click", async () => {
      clearBanner(banner);
      const groupId = memberGroupSelect.value;
      const studentId = memberStudentSelect.value;
      const joinDate = memberJoinDate.value || null;
      if (!groupId || !studentId) {
        showBanner(banner, "Choose both a group and a student.");
        return;
      }

      try {
        await request(`/groups/${groupId}/students/`, {
          method: "POST",
          body: {
            student_id: studentId,
            join_date: joinDate,
          },
        });
        showBanner(banner, "Student added to the group.", "success");
        await loadMembers();
        await loadGroups();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    memberGroupSelect.addEventListener("change", () => {
      currentMemberGroupId = memberGroupSelect.value;
      void loadMembers();
    });

    statusSelect.value = "active";
    memberJoinDate.value = new Date().toISOString().slice(0, 10);
    await loadOptions();
    await loadGroups();
    await loadMembers();
  })();
}