from branches.models import Branch
from rest_framework.test import APITestCase

from .models import Group, Student


class StudentAndGroupApiTests(APITestCase):
	def setUp(self):
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

	def test_group_rejects_student_from_other_branch(self):
		response = self.client.post(
			f"/api/v1/groups/{self.group_one.id}/students/",
			{"student_id": self.student_two.id, "join_date": "2026-05-05"},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("student_id", response.data)
