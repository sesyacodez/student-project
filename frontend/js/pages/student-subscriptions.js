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
    const tableBody = document.querySelector("#subscriptions-table tbody");
    const form = document.getElementById("subscription-form");
    const formTitle = document.getElementById("subscription-form-title");
    const saveButton = document.getElementById("subscription-save");
    const resetButton = document.getElementById("subscription-reset");
    const subscriptionIdField = document.getElementById("subscription-id");
    const branchSelect = document.getElementById("subscription-branch");
    const studentSelect = document.getElementById("subscription-student");
    const planSelect = document.getElementById("subscription-plan");
    const subjectSelect = document.getElementById("subscription-subject");
    const startDateInput = document.getElementById("subscription-start-date");
    const filterBranch = document.getElementById("filter-subscription-branch");
    const filterStudent = document.getElementById("filter-subscription-student");
    const filterPlan = document.getElementById("filter-subscription-plan");
    const filterSubject = document.getElementById("filter-subscription-subject");
    const filterSearch = document.getElementById("filter-subscription-search");
    const btnReload = document.getElementById("btn-reload-subscriptions");

    let editingId = null;
    let studentsCache = [];
    let plansCache = [];
    let subjectsCache = [];

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
      if (filterStudent.value) params.set("student_id", filterStudent.value);
      if (filterPlan.value) params.set("subscription_plan_id", filterPlan.value);
      if (filterSubject.value) params.set("subject_id", filterSubject.value);
      if (filterSearch.value.trim()) params.set("search", filterSearch.value.trim());
      const query = params.toString();
      return query ? `?${query}` : "";
    }

    function resetForm() {
      editingId = null;
      form.reset();
      subscriptionIdField.value = "";
      formTitle.textContent = "Create subscription";
      saveButton.textContent = "Create subscription";
      startDateInput.value = new Date().toISOString().slice(0, 10);
      renderStudentOptions();
      renderPlanOptions();
      renderSubjectOptions();
    }

    function branchOfStudent(student) {
      return student?.branch?.id ? String(student.branch.id) : "";
    }

    function branchOfPlan(plan) {
      return plan?.branch?.id ? String(plan.branch.id) : "";
    }

    function branchOfSubscription(subscription) {
      return branchOfStudent(subscription.student) || branchOfPlan(subscription.subscription_plan) || "";
    }

    function renderStudentOptions(selectedValue = "") {
      const branchId = branchSelect.value;
      const students = branchId
        ? studentsCache.filter((student) => branchOfStudent(student) === String(branchId))
        : studentsCache;
      populateSelect(
        studentSelect,
        students,
        branchId ? "Choose student" : "Choose branch first or pick any student",
        (student) => `${student.first_name} ${student.last_name} (#${student.id})`,
        selectedValue,
      );
    }

    function renderPlanOptions(selectedValue = "") {
      const branchId = branchSelect.value;
      const plans = branchId
        ? plansCache.filter((plan) => branchOfPlan(plan) === String(branchId))
        : plansCache;
      populateSelect(
        planSelect,
        plans,
        branchId ? "Choose plan" : "Choose branch first or pick any plan",
        (plan) => `${plan.name} (#${plan.id})`,
        selectedValue,
      );
    }

    function renderSubjectOptions(selectedValue = "") {
      const planId = planSelect.value;
      const plan = plansCache.find((item) => String(item.id) === String(planId));
      const subjects = plan?.subjects || subjectsCache;
      populateSelect(
        subjectSelect,
        subjects,
        planId ? "Choose subject" : "Choose a plan first",
        (subject) => `${subject.name} (#${subject.id})`,
        selectedValue,
      );
    }

    function fillForm(subscription) {
      editingId = subscription.id;
      subscriptionIdField.value = subscription.id;
      formTitle.textContent = `Edit subscription #${subscription.id}`;
      saveButton.textContent = "Save changes";
      branchSelect.value = branchOfSubscription(subscription);
      renderStudentOptions(subscription.student?.id ? String(subscription.student.id) : "");
      renderPlanOptions(subscription.subscription_plan?.id ? String(subscription.subscription_plan.id) : "");
      renderSubjectOptions(subscription.subject?.id ? String(subscription.subject.id) : "");
      studentSelect.value = subscription.student?.id ? String(subscription.student.id) : "";
      planSelect.value = subscription.subscription_plan?.id ? String(subscription.subscription_plan.id) : "";
      subjectSelect.value = subscription.subject?.id ? String(subscription.subject.id) : "";
      startDateInput.value = subscription.start_date || "";
    }

    function renderRow(subscription) {
      const studentLabel = subscription.student
        ? `${subscription.student.first_name || ""} ${subscription.student.last_name || ""}`.trim()
        : "—";
      const planName = subscription.subscription_plan?.name || "—";
      const subjectName = subscription.subject?.name || "—";
      return `<tr>
        <td>${escapeHtml(studentLabel)}</td>
        <td>${escapeHtml(subscription.student?.branch?.name || subscription.subscription_plan?.branch?.name || "—")}</td>
        <td>${escapeHtml(planName)}</td>
        <td>${escapeHtml(subjectName)}</td>
        <td>${escapeHtml(subscription.start_date || "—")}</td>
        <td>
          <button type="button" class="app-btn app-btn--ghost" data-action="edit" data-id="${subscription.id}">Edit</button>
        </td>
      </tr>`;
    }

    async function loadOptions() {
      try {
        const [students, plans, branches, subjects] = await Promise.all([
          requestList("/students/"),
          requestList("/subscription-plans/"),
          requestList("/branches/"),
          requestList("/subjects/"),
        ]);
        studentsCache = students;
        plansCache = plans;
        subjectsCache = subjects;

        populateSelect(filterBranch, branches, "All branches", (branch) => `${branch.name} (${branch.city})`);
        populateSelect(branchSelect, branches, "Choose branch", (branch) => `${branch.name} (${branch.city})`);
        populateSelect(filterStudent, students, "All students", (student) => `${student.first_name} ${student.last_name} (#${student.id})`);
        populateSelect(filterPlan, plans, "All plans", (plan) => `${plan.name} (#${plan.id})`);
        populateSelect(filterSubject, subjects, "All subjects", (subject) => `${subject.name} (#${subject.id})`);
        renderStudentOptions();
        renderPlanOptions();
        renderSubjectOptions();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    }

    async function loadSubscriptions() {
      clearBanner(banner);
      try {
        const response = await request(`/student-subscriptions/${currentFilters()}`);
        const rows = Array.isArray(response?.results) ? response.results : Array.isArray(response) ? response : [];

        if (!rows.length) {
          tableBody.innerHTML = '<tr><td colspan="6" class="app-empty">No student subscriptions found.</td></tr>';
          return;
        }

        tableBody.innerHTML = rows.map(renderRow).join("");
        tableBody.querySelectorAll("[data-action='edit']").forEach((button) => {
          button.addEventListener("click", () => {
            const subscription = rows.find((item) => String(item.id) === button.getAttribute("data-id"));
            if (subscription) fillForm(subscription);
          });
        });
      } catch (error) {
        tableBody.innerHTML = "";
        showBanner(banner, formatApiError(error));
      }
    }

    branchSelect.addEventListener("change", () => {
      renderStudentOptions();
      renderPlanOptions();
      renderSubjectOptions();
    });

    planSelect.addEventListener("change", () => {
      renderSubjectOptions();
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      clearBanner(banner);

      if (!studentSelect.value || !planSelect.value || !subjectSelect.value) {
        showBanner(banner, "Choose a student, plan, and subject.");
        return;
      }

      const payload = {
        student_id: studentSelect.value,
        subscription_plan_id: planSelect.value,
        subject_id: subjectSelect.value,
        start_date: startDateInput.value,
      };

      try {
        if (editingId) {
          await request(`/student-subscriptions/${editingId}/`, {
            method: "PATCH",
            body: payload,
          });
          showBanner(banner, "Subscription updated.", "success");
        } else {
          await request("/student-subscriptions/", {
            method: "POST",
            body: payload,
          });
          showBanner(banner, "Subscription created.", "success");
        }
        resetForm();
        await loadSubscriptions();
      } catch (error) {
        showBanner(banner, formatApiError(error));
      }
    });

    resetButton.addEventListener("click", () => resetForm());
    btnReload.addEventListener("click", () => void loadSubscriptions());
    filterBranch.addEventListener("change", () => void loadSubscriptions());

    startDateInput.value = new Date().toISOString().slice(0, 10);
    await loadOptions();
    await loadSubscriptions();
  })();
}