# Educational Center Management System - API Design Plan

## 1. Authentication (JWT)
Responsible for secure login via phone number and token refresh.
* `POST /api/auth/login/` - User login (returns access and refresh tokens). Accepts phone number and password.
* `POST /api/auth/refresh/` - Obtain a new access token using a refresh token.

## 2. Branch Management
* `GET /api/branches/` - Get a list of branches (accessible to Admin).
* `POST /api/branches/` - Create a new branch (Admin only).
* `GET /api/branches/{id}/` - Get details of a specific branch.
* `PUT/PATCH /api/branches/{id}/` - Update branch information.
* `POST /api/branches/{id}/archive/` - Archive a branch (soft delete instead of hard delete).

## 3. Subjects
* `GET /api/subjects/` - Get a list of subjects (filterable by branch).
* `POST /api/subjects/` - Create a new subject (checks for uniqueness within a branch).
* `POST /api/subjects/{id}/archive/` - Archive a subject.

## 4. Students
* `GET /api/students/` - Get a list of students with search and filtering capabilities (by branch, status, group).
* `POST /api/students/` - Register a new student.
* `GET /api/students/{id}/` - Get detailed student profile (contacts, history).
* `PUT/PATCH /api/students/{id}/` - Update student data.
* `POST /api/students/{id}/archive/` - Archive a student record.

## 5. Groups
* `GET /api/groups/` - Get a list of groups.
* `POST /api/groups/` - Create a new group.
* `POST /api/groups/{id}/add_student/` - Add a student to a group.
* `POST /api/groups/{id}/remove_student/` - Remove a student from a group.

## 6. Subscription Plans & Pricing
* `GET /api/plans/` - Get a list of subscription plans and their pricing tiers.
* `POST /api/plans/` - Create a new subscription plan.
* `POST /api/subscriptions/` - Assign a plan to a student for a specific subject.
* `GET /api/students/{id}/subscriptions/` - View a student's active subscriptions.

## 7. Lessons & Schedule Templates
* `POST /api/lesson-templates/` - Create a schedule template (automatically generates lessons).
* `GET /api/lessons/` - Get the schedule (filterable by date, teacher, group).
* `POST /api/lessons/individual/` - Create a one-off individual lesson (with conflict checking).
* `POST /api/lessons/group/` - Create a one-off group lesson (with conflict checking).
* `PATCH /api/lessons/{id}/status/` - Change lesson status (e.g., CANCELLED).

## 8. Attendance
* `GET /api/lessons/{id}/attendance/` - Get the list of students for a lesson to mark attendance.
* `POST /api/lessons/{id}/attendance/` - Save attendance records and comments (changes lesson status to COMPLETED).

## 9. Reports & Analytics
* `GET /api/reports/teacher-schedule/` - Get a teacher's schedule for a selected period.
* `GET /api/reports/student-attendance/` - Get a student's attendance history.
* `GET /api/reports/branch-stats/` - Get basic branch statistics (number of active students, attendance %).