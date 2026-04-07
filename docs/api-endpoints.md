Educational Center Management System
API Endpoints Specification (Planned)

1. General API Conventions
--------------------------
Base URL:
- /api/v1/

Authentication:
- JWT Bearer token in header: Authorization: Bearer <access_token>
- Protected endpoints require a valid access token.

Roles:
- ADMIN: full access within assigned branch(es)
- TEACHER: read own schedule, view own lesson students, mark attendance for own lessons

Branch isolation:
- Branch-owned resources are always filtered by branch.
- Server must verify the current user has access to the branch.

Common statuses:
- ACTIVE, ARCHIVED for entities that support archiving
- SCHEDULED, COMPLETED, CANCELLED for lessons
- PRESENT, ABSENT for attendance

Common HTTP codes:
- 200 OK, 201 Created, 204 No Content
- 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict

2. Authentication
-----------------
1) POST /auth/login/
- Access: public
- Description: Login by phone + password, return token pair and user profile.
- Request body:
  {
    "phone": "+380501112233",
    "password": "secret"
  }
- Success response:
  {
    "access": "...",
    "refresh": "...",
    "user": {
      "id": 1,
      "phone": "+380501112233",
      "first_name": "John",
      "last_name": "Doe",
      "role": "ADMIN",
      "branches": [1, 3]
    }
  }

2) POST /auth/refresh/
- Access: public (valid refresh token)
- Description: Rotate refresh token and issue a new token pair.
- Request body:
  {
    "refresh": "..."
  }

3) POST /auth/logout/
- Access: ADMIN, TEACHER
- Description: Invalidate current refresh token (blacklist).

4) GET /auth/me/
- Access: ADMIN, TEACHER
- Description: Return current authenticated user profile.

3. Branches
-----------
1) GET /branches/
- Access: ADMIN
- Description: List assigned branches.
- Filters: status, city, search

2) POST /branches/
- Access: ADMIN
- Description: Create branch.

3) GET /branches/{id}/
- Access: ADMIN

4) PATCH /branches/{id}/
- Access: ADMIN

5) POST /branches/{id}/archive/
- Access: ADMIN
- Description: Archive branch (soft state change).

6) POST /branches/{id}/restore/
- Access: ADMIN
- Description: Restore archived branch.

4. Users (Staff: ADMIN and TEACHER)
-----------------------------------
1) GET /users/
- Access: ADMIN
- Description: List users in accessible branches.
- Filters: role, is_active, branch_id, search

2) POST /users/
- Access: ADMIN
- Description: Create staff user and assign role.

3) GET /users/{id}/
- Access: ADMIN

4) PATCH /users/{id}/
- Access: ADMIN

5) POST /users/{id}/archive/
- Access: ADMIN
- Description: Set is_active=false.

6) POST /users/{id}/branches/
- Access: ADMIN
- Description: Assign user to branch.
- Request body:
  {
    "branch_id": 2
  }

7) DELETE /users/{id}/branches/{branch_id}/
- Access: ADMIN
- Description: Unassign user from branch.

5. Subjects
-----------
1) GET /subjects/
- Access: ADMIN
- Filters: branch_id, status, search

2) POST /subjects/
- Access: ADMIN
- Description: Create subject in branch. Name must be unique in branch.

3) GET /subjects/{id}/
- Access: ADMIN

4) PATCH /subjects/{id}/
- Access: ADMIN

5) POST /subjects/{id}/archive/
- Access: ADMIN

6) POST /subjects/{id}/restore/
- Access: ADMIN

6. Students
-----------
1) GET /students/
- Access: ADMIN
- Filters: branch_id, status, group_id, search (first_name/last_name)

2) POST /students/
- Access: ADMIN

3) GET /students/{id}/
- Access: ADMIN

4) PATCH /students/{id}/
- Access: ADMIN

5) POST /students/{id}/archive/
- Access: ADMIN

6) POST /students/{id}/restore/
- Access: ADMIN

7. Groups
---------
1) GET /groups/
- Access: ADMIN
- Filters: branch_id, status, search

2) POST /groups/
- Access: ADMIN

3) GET /groups/{id}/
- Access: ADMIN

4) PATCH /groups/{id}/
- Access: ADMIN

5) POST /groups/{id}/archive/
- Access: ADMIN

6) POST /groups/{id}/restore/
- Access: ADMIN

7) GET /groups/{id}/students/
- Access: ADMIN, TEACHER (if teacher has lessons with group)

8) POST /groups/{id}/students/
- Access: ADMIN
- Description: Add student to group (must be same branch).
- Request body:
  {
    "student_id": 77,
    "join_date": "2026-09-01"
  }

9) DELETE /groups/{id}/students/{student_id}/
- Access: ADMIN
- Description: Remove student from group (history preserved).

8. Subscription Plans and Pricing
---------------------------------
1) GET /subscription-plans/
- Access: ADMIN
- Filters: branch_id, type, status, search

2) POST /subscription-plans/
- Access: ADMIN
- Description: Create plan with subjects and pricing tiers.
- Request body (example):
  {
    "branch_id": 1,
    "name": "Group Math Standard",
    "type": "GROUP",
    "subject_ids": [2, 4],
    "pricing_tiers": [
      {"lessons_per_month": 4, "price_per_lesson": "21.00"},
      {"lessons_per_month": 8, "price_per_lesson": "19.00"}
    ]
  }

3) GET /subscription-plans/{id}/
- Access: ADMIN

4) PATCH /subscription-plans/{id}/
- Access: ADMIN

5) POST /subscription-plans/{id}/archive/
- Access: ADMIN

6) POST /subscription-plans/{id}/restore/
- Access: ADMIN

7) PUT /subscription-plans/{id}/subjects/
- Access: ADMIN
- Description: Replace list of subjects linked to plan.

8) GET /subscription-plans/{id}/pricing-tiers/
- Access: ADMIN

9) POST /subscription-plans/{id}/pricing-tiers/
- Access: ADMIN

10) PATCH /pricing-tiers/{id}/
- Access: ADMIN

11) DELETE /pricing-tiers/{id}/
- Access: ADMIN

9. Student Subscriptions
------------------------
1) GET /student-subscriptions/
- Access: ADMIN
- Filters: student_id, subject_id, subscription_plan_id, branch_id

2) POST /student-subscriptions/
- Access: ADMIN
- Description: Assign plan to student for subject.
- Validation: subject must be in plan.subjects.
- Request body:
  {
    "student_id": 77,
    "subscription_plan_id": 10,
    "subject_id": 2,
    "start_date": "2026-09-01"
  }

3) GET /student-subscriptions/{id}/
- Access: ADMIN

4) PATCH /student-subscriptions/{id}/
- Access: ADMIN

10. Lessons
-----------
1) GET /lessons/
- Access: ADMIN, TEACHER
- Description: List lessons with role-based visibility.
- Filters: branch_id, teacher_id, student_id, group_id, subject_id, status, date_from, date_to

2) POST /lessons/
- Access: ADMIN
- Description: Create one-time lesson (individual or group).
- Validation:
  - either student_id or group_id is required (not both)
  - no overlap conflicts for teacher
  - no overlap conflicts for student(s)
  - cancelled lessons are ignored in conflict checks

3) GET /lessons/{id}/
- Access: ADMIN, TEACHER (owner lesson)

4) PATCH /lessons/{id}/
- Access: ADMIN
- Description: Update date/time/teacher/subject/participant with conflict re-check.

5) POST /lessons/{id}/cancel/
- Access: ADMIN
- Description: Change status to CANCELLED.

6) POST /lessons/{id}/complete/
- Access: ADMIN, TEACHER (owner lesson)
- Description: Mark lesson as COMPLETED (usually after attendance is set).

7) POST /lessons/conflicts/check/
- Access: ADMIN
- Description: Validate candidate lesson against schedule conflicts without creating it.

11. Lesson Templates (Recurring)
--------------------------------
1) GET /lesson-templates/
- Access: ADMIN
- Filters: branch_id, teacher_id, subject_id, is_active

2) POST /lesson-templates/
- Access: ADMIN
- Description: Create recurring template and generate lessons.
- Request body:
  {
    "teacher_id": 6,
    "subject_id": 2,
    "student_id": 77,
    "group_id": null,
    "days_of_week": [1, 3],
    "start_time": "10:00:00",
    "end_time": "11:00:00",
    "start_date": "2026-09-01",
    "end_date": "2026-12-31",
    "is_active": true
  }

3) GET /lesson-templates/{id}/
- Access: ADMIN

4) PATCH /lesson-templates/{id}/
- Access: ADMIN
- Description: Update template rules. Existing generated lessons remain unchanged.

5) POST /lesson-templates/{id}/deactivate/
- Access: ADMIN
- Description: Stop future generation. Existing lessons remain.

6) POST /lesson-templates/{id}/generate/
- Access: ADMIN
- Description: Generate missing lessons for active period.

7) POST /lesson-templates/preview-conflicts/
- Access: ADMIN
- Description: Return conflict list for planned template dates.

12. Attendance
--------------
1) GET /lessons/{id}/attendance/
- Access: ADMIN, TEACHER (owner lesson)

2) PUT /lessons/{id}/attendance/
- Access: ADMIN, TEACHER (owner lesson)
- Description: Upsert attendance in batch for lesson participants.
- Request body:
  {
    "records": [
      {"student_id": 77, "status": "PRESENT", "note": "Good progress"},
      {"student_id": 81, "status": "ABSENT", "note": "Sick"}
    ]
  }

3) PATCH /attendance/{id}/
- Access: ADMIN, TEACHER (owner lesson)

Validation:
- cannot mark attendance for cancelled lessons
- one attendance record per lesson + student (update existing record on repeat)
- for group lesson, student must be a participant

13. Reports
-----------
1) GET /reports/teacher-schedule/
- Access: ADMIN, TEACHER
- Filters: teacher_id, date_from, date_to
- Rule: TEACHER can request only own teacher_id.

2) GET /reports/student-attendance/
- Access: ADMIN, TEACHER
- Filters: student_id, subject_id, date_from, date_to
- Rule: TEACHER can access only students from own lessons.

3) GET /reports/branch-stats/
- Access: ADMIN
- Filters: branch_id, date_from, date_to
- Returns minimum metrics:
  - active_students_count
  - lessons_completed_count
  - lessons_cancelled_count
  - attendance_percent

14. Error Response Format
-------------------------
Validation error example:
{
  "code": "validation_error",
  "message": "Validation failed",
  "details": {
    "subject_id": ["Subject is archived and cannot be used for new lessons."]
  }
}

Conflict error example:
{
  "code": "schedule_conflict",
  "message": "Teacher has an overlapping lesson",
  "details": {
    "teacher_id": 6,
    "conflict_lesson_ids": [1002]
  }
}

Permission error example:
{
  "code": "permission_denied",
  "message": "You do not have access to this branch."
}

15. Notes for Implementation
----------------------------
- Prefer ViewSets + Routers in DRF for CRUD resources.
- Document all endpoints in Swagger/OpenAPI.
- Add pagination for list endpoints.
- Enforce branch-level permissions in queryset and object-level checks.
- For overlap checks, use rule: start_1 < end_2 AND start_2 < end_1 on same date.