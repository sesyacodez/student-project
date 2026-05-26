from datetime import time

from rest_framework import status
from branches.models import Branch, Subject
from rest_framework.test import APITestCase

from users.models import User
from scheduling.models import Lesson, LessonStatus

from .models import Group, Student


class StudentAndGroupApiTests(APITestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			phone="+38000000001",
			password="secret",
			first_name="Admin",
			last_name="User",
			role="ADMIN",
		)
		self.client.force_authenticate(user=self.admin)
		self.branch_one = Branch.objects.create(name="Branch One", address="A", city="Kyiv")
		self.branch_two = Branch.objects.create(name="Branch Two", address="B", city="Lviv")
		self.student_one = Student.objects.create(first_name="Anna", last_name="Ivanenko", branch=self.branch_one)
		self.student_two = Student.objects.create(first_name="Bohdan", last_name="Shevchenko", branch=self.branch_two)
		self.group_one = Group.objects.create(name="Group 1", branch=self.branch_one)
		self.group_two = Group.objects.create(name="Group 2", branch=self.branch_one)

	def test_lists_are_paginated(self):
		student_response = self.client.get("/api/v1/students/")
		group_response = self.client.get("/api/v1/groups/")

		self.assertEqual(student_response.status_code, 200)
		self.assertIn("results", student_response.data)
		self.assertEqual(student_response.data["count"], 2)

		self.assertEqual(group_response.status_code, 200)
		self.assertIn("results", group_response.data)
		self.assertEqual(group_response.data["count"], 2)

	def test_student_filters_and_archive_restore(self):
		response = self.client.get(
			f"/api/v1/students/?branch_id={self.branch_one.id}&search=Anna"
		)

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)
		self.assertEqual(response.data["results"][0]["id"], self.student_one.id)

		archive = self.client.post(f"/api/v1/students/{self.student_one.id}/archive/")
		self.assertEqual(archive.status_code, status.HTTP_200_OK)
		self.assertEqual(archive.data["status"], "archived")

		archived = self.client.get("/api/v1/students/?status=archived")
		self.assertEqual(archived.status_code, status.HTTP_200_OK)
		self.assertEqual(archived.data["count"], 1)
		self.assertEqual(archived.data["results"][0]["id"], self.student_one.id)

		restore = self.client.post(f"/api/v1/students/{self.student_one.id}/restore/")
		self.assertEqual(restore.status_code, status.HTTP_200_OK)
		self.assertEqual(restore.data["status"], "active")

	def test_group_rejects_student_from_other_branch(self):
		response = self.client.post(
			f"/api/v1/groups/{self.group_one.id}/students/",
			{"student_id": self.student_two.id, "join_date": "2026-05-05"},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("student_id", response.data)

	def test_group_archive_restore_and_search_filter(self):
		response = self.client.get("/api/v1/groups/?search=Group 1")
		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.assertEqual(response.data["count"], 1)
		self.assertEqual(response.data["results"][0]["id"], self.group_one.id)

		archive = self.client.post(f"/api/v1/groups/{self.group_one.id}/archive/")
		self.assertEqual(archive.status_code, status.HTTP_200_OK)
		self.assertEqual(archive.data["status"], "archived")

		archived = self.client.get("/api/v1/groups/?status=archived")
		self.assertEqual(archived.status_code, status.HTTP_200_OK)
		self.assertEqual(archived.data["count"], 1)
		self.assertEqual(archived.data["results"][0]["id"], self.group_one.id)

		restore = self.client.post(f"/api/v1/groups/{self.group_one.id}/restore/")
		self.assertEqual(restore.status_code, status.HTTP_200_OK)
		self.assertEqual(restore.data["status"], "active")

	def test_group_students_teacher_access(self):
		teacher = User.objects.create_user(
			phone="+38000000003",
			password="secret",
			first_name="Teach",
			last_name="Er",
			role="TEACHER",
		)
		subject = Subject.objects.create(name="Math", branch=self.branch_one)
		Lesson.objects.create(
			name="Group Lesson",
			date="2026-11-01",
			start_time=time(9, 0),
			end_time=time(10, 0),
			status=LessonStatus.SCHEDULED,
			teacher=teacher,
			subject=subject,
			group=self.group_one,
		)

		self.client.force_authenticate(user=teacher)
		allowed = self.client.get(f"/api/v1/groups/{self.group_one.id}/students/")
		self.assertEqual(allowed.status_code, status.HTTP_200_OK)

		other_teacher = User.objects.create_user(
			phone="+38000000004",
			password="secret",
			first_name="Other",
			last_name="Teacher",
			role="TEACHER",
		)
		self.client.force_authenticate(user=other_teacher)
		forbidden = self.client.get(f"/api/v1/groups/{self.group_one.id}/students/")
		self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
