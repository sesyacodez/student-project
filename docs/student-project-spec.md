Educational Center Management System
Technical Requirements — Course Project
1. Project Overview
Domain
An educational center provides individual and group lessons in various subjects (math, English, programming, etc.). The center
can have multiple branches in different cities. Each branch has its own staff of teachers, students, and schedule.

System Users
Administrator — manages a branch: creates schedules, registers students and teachers, monitors attendance
Teacher — views their own schedule and marks student attendance
Students do not have access to the system — their data is entered by an administrator.

What the System Must Do
1. Manage students, teachers, subjects, and groups across branches
2. Create lesson schedules — both one-time and recurring from templates
3. Prevent scheduling conflicts (overlapping lessons for a teacher or student)
4. Track student attendance
5. Manage subscription plans (pricing tiers) that determine lesson costs
6. Provide basic reporting (teacher schedule, attendance history)
2. Architecture Guidelines
Base Technologies
Component Requirement
Backend Django + Django REST Framework
Database PostgreSQL
Authentication JWT (JSON Web Tokens)
Containerization Docker Compose (backend + DB)
Student's Choice
Component Options
Frontend React, Vue, Angular, or Django Templates — any option
API Documentation Swagger/OpenAPI
Additional libraries At student's discretion
3. User Roles & Permissions
Roles
The system has two roles: ADMIN and TEACHER.

Administrator (ADMIN)
Has full access within their branch(es):

Manage branches, subjects, students, groups
Create and edit lesson schedules
Create and assign subscription plans
View and edit attendance
Manage teacher accounts
View reports
Teacher (TEACHER)
Limited access:

View only their own lesson schedule
Mark attendance on their own lessons
View student list for their own lessons
Cannot create lessons, students, or groups
Cannot view other teachers' schedules
Permission Matrix
Action ADMIN TEACHER
Create/edit branches Yes No
Manage subjects Yes No
Register students Yes No
Create groups Yes No
Create schedules Yes No
View own schedule Yes Yes
View others' schedules Yes No
Mark attendance Yes Own lessons only
View reports Yes Own data only
Manage subscription plans Yes No
Action ADMIN TEACHER
4. Functional Requirements
4.1. Authentication & Authorization
Business Rules
Users are identified by phone number, not email
After successful login, the system issues a pair of JWT tokens (access + refresh)
The access token has a limited lifetime; the refresh token allows obtaining a new access token without re-entering
credentials
Every request to protected resources must include a valid access token
Use Cases
Login: 1. User enters phone number and password 2. System verifies credentials 3. On success — returns a token pair and
user info (role, name, accessible branches) 4. On failure — returns an error without specifying the reason (security)

Token Refresh: 1. Access token has expired 2. Client sends the refresh token 3. System returns a new token pair

Edge Cases
An inactive user cannot log in
Login attempt with a non-existent phone number returns the same error as an incorrect password
A refresh token can only be used once (token rotation)
4.2. Branch Management
Business Rules
Each branch is a separate educational center with its own address
All data (students, lessons, subjects) belongs to a specific branch
A branch can be active or archived
An archived branch is not deleted — it is only hidden from listings
Branch Information
Name (required)
Address
City
Status (active / archived)
Use Cases
Creating a branch: 1. Administrator enters name, address, and city 2. System creates the branch with active status

Archiving: 1. Administrator archives a branch 2. Branch disappears from main listings but all its data is preserved 3. Active
lessons in this branch are NOT automatically cancelled

Edge Cases
A branch cannot be deleted if it has active students or lessons — it can only be archived
An administrator can only see branches they are assigned to
4.3. Subject Management
Business Rules
A subject belongs to a specific branch
No two subjects in the same branch can have the same name
A subject can be active or archived
Subject Information
Name (required)
Branch (required)
Status (active / archived)
Use Cases
Creating a subject: 1. Administrator selects a branch and enters a subject name 2. System checks name uniqueness within the
branch 3. Creates the subject with active status

Archiving: 1. Administrator archives a subject 2. Existing lessons with this subject remain in the schedule 3. New lessons with
an archived subject cannot be created

Edge Cases
Attempting to create a subject with a name that already exists in the branch must be rejected
When archiving a subject, existing lesson templates remain active
4.4. Student Management
Business Rules
A student belongs to one branch
A student can be active or archived
The system stores contact information for both the student and one parent/guardian
Student Information
First name, last name (required)
Date of birth
Phone, email
Address
Parent/guardian contact: name, phone, email, relationship (mother, father, etc.)
Status (active / archived)
Branch (required)
Use Cases
Registering a student: 1. Administrator fills out the student profile 2. System creates the student in the selected branch with
active status

Search and filtering: 1. Administrator searches for a student by first or last name 2. Filters by branch, status, group

Archiving: 1. Administrator archives a student (e.g., stopped attending) 2. Student disappears from listings but their data and
history are preserved

Edge Cases
When archiving a student, their scheduled lessons are NOT automatically deleted — the administrator must decide what to
do with them
A student can be in multiple groups simultaneously
4.5. Group Management
Business Rules
A group is a set of students who study together
A group belongs to one branch
A student can belong to multiple groups
A group can be active or archived
Group Information
Name (required)
Branch (required)
Status (active / archived)
List of member students
Use Cases
Creating a group: 1. Administrator enters a name and selects a branch 2. Adds students to the group

Adding a student to a group: 1. Administrator selects a student and adds them to the group 2. System records the join date

Removing a student from a group: 1. Administrator removes a student from the group 2. System records the leave date 3.
Historical data (lessons, attendance) is preserved

Edge Cases
Cannot add a student from a different branch to a group
When removing a student from a group, their past lessons remain in history
An archived group does not appear in selection lists when creating a lesson
4.6. Subscription Plans (Pricing)
Business Rules
A subscription plan defines the cost of lessons for a student in a specific subject
A plan belongs to a branch and is linked to one or more subjects
Plan type: individual or group
Price depends on the number of lessons per month (pricing grid)
A student is assigned a plan for a specific subject
Important: a subscription plan is NOT a prepaid package. It is simply a pricing grid that determines the per-lesson cost based
on monthly lesson count.

Pricing Grid (Example)
Lessons per month Price per lesson Total cost
1 $25 $
2 $23 $
4 $21 $
8 $19 $
More lessons per month means a lower per-lesson price (volume discount).

Use Cases
Creating a subscription plan: 1. Administrator enters a name, selects a branch, chooses type (individual/group) 2. Defines
which subjects the plan applies to 3. Fills in the pricing grid: number of lessons → price

Assigning a plan to a student: 1. Administrator selects a student and subject 2. Selects the appropriate subscription plan 3.
Sets the start date

Viewing a student's subscriptions: 1. Administrator sees which plans are assigned to a student 2. For each — subject, plan,
start date

Edge Cases
One student can have different plans for different subjects
A plan cannot be assigned for a subject that is not in the plan's subject list
When archiving a plan, existing subscriptions remain active — new ones cannot be created
4.7. Lesson Scheduling
This is the core functionality of the system. Lessons come in two types: individual (one student) and group (a group of
students).

4.7.1. Individual Lessons
Business Rules:

A lesson is tied to one student, one teacher, and one subject
Has a date, start time, and end time
Lesson status: SCHEDULED → COMPLETED or CANCELLED
Creation scenario: 1. Administrator selects a student, teacher, and subject 2. Specifies date, start time, and end time 3. System
checks for conflicts (see 4.7.3) 4. Lesson is created with SCHEDULED status

4.7.2. Group Lessons
Business Rules:

A lesson is tied to a group, not to an individual student
All current group members are automatically participants of the lesson
Teacher and subject are the same for the entire group
Creation scenario: 1. Administrator selects a group, teacher, and subject 2. Specifies date and time 3. System checks for
conflicts for the teacher and for every student in the group 4. Lesson is created for the entire group

4.7.3. Conflict Prevention
Business Rules:

The system must prevent the following conflicts:

1. Teacher conflict: a teacher cannot have two lessons that overlap in time
2. Student conflict: a student cannot have two lessons that overlap in time
Overlap definition: two lessons overlap if start_1 < end_2 AND start_2 < end_1 (on the same date).

Scenario: 1. Administrator creates a lesson for teacher Smith at 10:00–11:00 2. Attempts to create another lesson for Smith at
10:30–11:30 on the same day 3. System rejects the creation with a conflict message 4. Same for students: if student Jones has
a lesson at 10:00, they cannot be in another lesson at 10:

Edge cases: - Lessons that follow one another without a gap (10:00–11:00 and 11:00–12:00) — this is NOT a conflict -
Cancelled lessons are not considered when checking for conflicts - For group lessons, all group members are checked

4.7.4. Lesson Templates (Recurring Schedule)
Business Rules:

A template defines lessons that repeat weekly on certain days
A template has an active period (start date and end date)
From the template, the system automatically generates individual lessons for each date
Template information: - Teacher, subject, student (for individual) or group (for group lessons) - Days of the week (e.g., Monday
and Wednesday) - Start and end time for each day - Active period (from which date to which date)

Creation scenario: 1. Administrator configures a template: "Math with Smith, Mon and Wed, 10:00–11:00, from Sep 1 to Dec
31" 2. System checks for conflicts on each planned date 3. Automatically creates individual lessons for all dates within the
period 4. Each lesson can then be edited or cancelled independently of the template

Edge cases: - If a conflict is detected for at least one date, the system reports it (the decision — whether to block the entire

template or create only conflict-free lessons — is up to the student) - Editing a template does not change already-created
lessons - Deactivating a template stops generation of new lessons but existing ones remain

4.7.5. Lesson Statuses
Status Description Changed By
SCHEDULED Lesson is planned, has not yet occurred Automatically on creation
COMPLETED Lesson took place, teacher marked attendance Teacher or administrator
CANCELLED Lesson was cancelled Administrator
4.8. Attendance
Business Rules
For each lesson, attendance is recorded for every student
Teacher marks each student as present or absent
A note (comment) can be added to each record
Each student can have only one attendance record per lesson
Only the teacher of that lesson or an administrator can mark attendance
Use Cases
Marking attendance: 1. Teacher opens a lesson 2. Sees the student list (for individual — one student, for group — all group
members) 3. Marks each student: present / absent 4. Adds notes (optional) 5. Lesson transitions to COMPLETED status

Viewing history: 1. Administrator selects a student 2. Sees attendance history: dates, subjects, presence status, notes

Edge Cases
Cannot mark attendance for a cancelled lesson
Cannot mark a student who is not a participant of the lesson (for group lessons — not in the group)
Marking again updates the existing record rather than creating a duplicate
4.9. Reporting
Teacher Schedule
Business Rules: - A teacher sees their lessons for a chosen period (week, month) - An administrator can view any teacher's
schedule

Displayed information: - Date and time of each lesson - Subject - Student or group - Lesson status

Student Attendance History
Business Rules: - Administrator sees the full attendance history for a student - Filter by period, subject

Displayed information: - List of lessons with attendance status - Summary statistics: number of attended / missed lessons

Basic Statistics
Business Rules: - Administrator sees general information about a branch

Displayed information (minimum): - Number of active students - Number of lessons for the period (completed / cancelled) -
Attendance percentage

5. Frontend Requirements
Required Pages/Screens
The frontend must provide an interface for all core system functions. Specific design, layout, and technology choices are up to
the student.

General
Login page (authentication by phone number)
Navigation adapted to user role (administrator sees more menu items)
For Administrator
Branch list and create/edit page
Subject list with create and archive functionality
Student list with search and filtering; student detail card
Group list with ability to add/remove students
Subscription plan management: create pricing plans, assign to students
Lesson schedule: view (calendar or table), create lessons
Lesson templates: create and view
Attendance: view and edit
Reports: teacher schedules, attendance statistics
For Teacher
Own lesson schedule (weekly / monthly view)
Mark attendance: student list per lesson, present/absent selection
View information about students in their lessons
General Requirements
The interface must be functional — a simple but working UI is better than a beautiful but broken one
All data is retrieved via REST API (no direct database access)
Server errors should be displayed to the user in a clear, understandable way
6. Technical Requirements
Docker Compose
The project must start with docker-compose up
Minimum configuration: backend container (Django) + PostgreSQL container
Frontend can be a separate container or served through Django
REST API
API follows REST principles
Uses proper HTTP methods (GET, POST, PUT/PATCH, DELETE)
Responses return appropriate HTTP status codes (200, 201, 400, 401, 403, 404)
Validation errors are returned in a structured format
Authentication
JWT tokens (access + refresh)
Access token is sent in the Authorization: Bearer <token> header
Refresh token allows renewing the access token without re-authentication
Testing
Unit tests for models and business logic
Tests for key API endpoints
Minimum coverage: user model, lesson creation with conflict checking, attendance marking
Git
Code stored in a Git repository
Meaningful commit history (not a single commit with all code)
.gitignore file excludes unnecessary files (.pyc, __pycache__, .env, node_modules, etc.)
Documentation
README.md with instructions:
How to start the project (docker-compose up)
How to create a superuser
How to run tests
What environment variables are needed
7. Project Phases
Phase 1: Foundation (Weeks 1–4)
Focus: data modeling, basic structure, authentication

Tasks: - Design data models and relationships (ER diagram as deliverable) - Plan API endpoints (document as deliverable) -
Create Django project (SQLite is fine at this stage, Docker not required) - Implement custom User model with phone-based
authentication - Basic Django views (function-based or class-based, not DRF yet) - Minimal frontend (Django Templates or
beginning of SPA) — enough to demonstrate

Result: working project with models, basic views, and authentication

Deliverables: - ER diagram (any format: draw.io, dbdiagram.io, hand-drawn — as long as it's readable) - Document with
planned API endpoints - Working code

Phase 2: API & Business Logic (Weeks 5–8)
Focus: Django REST Framework, full API, business rules

Tasks: - Migrate views to Django REST Framework (serializers, viewsets, routers) - Implement JWT authentication - Add
validation and business logic (conflict detection, permissions) - API documentation via Swagger (drf-spectacular or similar) -
Refine models based on Phase 1 experience - Connect frontend to REST API

Result: full REST API with Swagger documentation, working business logic

Deliverables: - Working Swagger/OpenAPI documentation - Demonstration of key scenarios through API

Phase 3: Quality & DevOps (Weeks 9–12)
Focus: containerization, optimization, testing, final version

Tasks: - Docker Compose configuration (Django + PostgreSQL) - Query optimization (select_related, prefetch_related,
indexes) - Unit tests (minimum coverage of key logic) - Error handling and edge cases - Final frontend polish - Documentation
(README, setup guide)

Result: containerized project with tests, ready for demonstration

Deliverables: - Docker Compose that starts with a single command - Test results - Full project demonstration

8. Evaluation Criteria
Criterion Weight What Is Evaluated
Data Modeling & API Design 25% Model structure, relationships, naming, API design, ER diagram
Backend Implementation 30% Business logic, validation, permissions, DRF usage
Code Quality 20% Tests, project structure, Git history, documentation
Frontend 10% Functional UI, interaction with API
Presentation & Demo 15% Working demo, ability to explain design decisions
Criteria Details
Data Modeling (25%): - Are relationships correctly defined (FK, M2M, OneToOne)? - Are integrity constraints in place (unique,
not null)? - Is data normalized? - Are API endpoints logically designed?

Backend (30%): - Does schedule conflict detection work? - Are role-based permissions correctly implemented? - Are
serializers and viewsets used properly? - Are errors handled?

Code Quality (20%): - Are there tests, and what do they cover? - Is the project structured logically (apps, separation of

concerns)? - Are there meaningful commits in Git? - Is there a README with instructions?

Frontend (10%): - Can the main scenarios be performed through the interface? - Are server errors displayed to the user? -
Does authentication work?

Presentation (15%): - Live demo of key scenarios - Ability to answer questions about the architecture - Explanation of design
decisions (why this approach?)

9. Bonus Features (Optional)
For teams that want to earn extra credit:

CSV export of reports — export schedules or attendance data to CSV
Role-based dashboard — home page with statistics adapted to the user's role
Conflict visualization — display schedule on a calendar with conflict highlighting
Email notifications — alerts when a lesson is created or cancelled
Advanced search and filtering — full-text search, complex filters
Pagination and performance — cursor-based pagination, caching
CI/CD — automated test execution via GitHub Actions
Appendix: Glossary
Term Description
Branch A separate educational center with its own address and staff
Subject An academic discipline (math, English, etc.)
Group A set of students who study together in group lessons
Subscription Plan A pricing plan that determines lesson costs
Subscription A link between a student and a plan for a specific subject
Lesson Template A definition of a recurring lesson (days of week, time)
Lesson An individual lesson with a specific date and time
Attendance A record of a student's presence or absence at a lesson