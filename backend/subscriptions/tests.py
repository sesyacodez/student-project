from rest_framework import status
from branches.models import Branch, Subject
from rest_framework.test import APITestCase

from students_and_groups.models import Student
from users.models import User

from subscriptions.models import SubscriptionPlan


class SubscriptionApiTests(APITestCase):
	def setUp(self):
		self.admin = User.objects.create_user(
			phone="+38000000002",
			password="secret",
			first_name="Admin",
			last_name="User",
			role="ADMIN",
		)
		self.client.force_authenticate(user=self.admin)
		self.branch_one = Branch.objects.create(name="Branch One", address="A", city="Kyiv")
		self.branch_two = Branch.objects.create(name="Branch Two", address="B", city="Odesa")
		self.subject_one = Subject.objects.create(name="Math", branch=self.branch_one)
		self.subject_two = Subject.objects.create(name="English", branch=self.branch_one)
		self.student = Student.objects.create(first_name="Olha", last_name="Petrenko", branch=self.branch_one)

	def _create_plan(self):
		response = self.client.post(
			"/api/v1/subscription-plans/",
			{
				"branch_id": self.branch_one.id,
				"name": "Standard Plan",
				"type": "group",
				"subject_ids": [self.subject_one.id],
				"pricing_tiers": [
					{"lessons_per_month": 4, "price_per_lesson": "21.00"},
					{"lessons_per_month": 8, "price_per_lesson": "19.00"},
				],
			},
			format="json",
		)
		self.assertEqual(response.status_code, 201)
		return response.data

	def test_subscription_plans_list_is_paginated(self):
		self._create_plan()
		response = self.client.get("/api/v1/subscription-plans/")

		self.assertEqual(response.status_code, 200)
		self.assertIn("results", response.data)
		self.assertEqual(response.data["count"], 1)

	def test_subscription_plan_archive_restore_and_filter(self):
		plan = self._create_plan()

		archive = self.client.post(f"/api/v1/subscription-plans/{plan['id']}/archive/")
		self.assertEqual(archive.status_code, status.HTTP_200_OK)
		self.assertEqual(archive.data["status"], "archived")

		archived = self.client.get("/api/v1/subscription-plans/?status=archived")
		self.assertEqual(archived.status_code, status.HTTP_200_OK)
		self.assertEqual(archived.data["count"], 1)
		self.assertEqual(archived.data["results"][0]["id"], plan["id"])

		restore = self.client.post(f"/api/v1/subscription-plans/{plan['id']}/restore/")
		self.assertEqual(restore.status_code, status.HTTP_200_OK)
		self.assertEqual(restore.data["status"], "active")

	def test_student_subscription_rejects_unlinked_subject(self):
		plan = self._create_plan()
		response = self.client.post(
			"/api/v1/student-subscriptions/",
			{
				"student_id": self.student.id,
				"subscription_plan_id": plan["id"],
				"subject_id": self.subject_two.id,
				"start_date": "2026-05-05",
			},
			format="json",
		)

		self.assertEqual(response.status_code, 400)
		self.assertIn("subject_id", response.data)
